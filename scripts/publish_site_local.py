#!/usr/bin/env python3
"""publish_site_local.py — 本地 gh-pages 发布链（Actions 停用期；stdlib-only）。

Replicates the 2026-11-16 evening hand-verified chain as one fail-closed CLI
(owner mission publish-site-local-script, 2026-11-16; mission 2a/c/d):

  0. precondition: main worktree has NO unstaged tracked changes -> else rc=3
  1. --build (optional): in web/ run ``npx pnpm@10.34.6 install --frozen-lockfile``
     only when web/node_modules is missing, then the build; without --build,
     web/out must already exist (else guidance + rc=1)
  2. quality gates, fail-closed: ``node scripts/sitemap-parity.mjs`` (cwd=web)
     and web/out/.nojekyll present
  3. mirror web/out -> data/ops/gh_pages_worktree excluding .git/.nojekyll
     (Windows: robocopy /MIR, rc<8 = success; other OS: rsync fallback;
     --worktree overrides the destination; post-mirror .git presence guard)
  4. race gate: remote gh-pages tip != local worktree HEAD -> abort rc=2
     (mutual exclusion with publish-site.yml once Actions resume; never force)
  5. worktree: git add -A; commit only when changes exist
     (``deploy: main@<head7> — site publish (local lane)``); push origin gh-pages
  6. --clean-out (default ON): delete web/out after a successful push
     (--no-clean-out keeps it; owner storage discipline)

--dry-run runs the chain as read-only diagnostics: zero disk writes, zero
push, same exit code the real run would produce.

Exit codes: 0 success / 1 failure / 2 race abort / 3 precondition refusal.
stdout/stderr reconfigured to UTF-8 (round-139 GBK-armor precedent).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_RACE = 2
EXIT_PRECONDITION = 3

PNPM_SPEC = "pnpm@10.34.6"
GIT_TIMEOUT = 120
GATE_TIMEOUT = 600
MIRROR_TIMEOUT = 1800
BUILD_TIMEOUT = 3600

Runner = Callable[[list[str], Path | None, int | None], tuple[int, str, str]]


def exit_code_for(gate: str) -> int:
    """Map a failing gate to its exit code (mission 2-ix; pinned by tests)."""
    return {"precondition": EXIT_PRECONDITION, "race": EXIT_RACE}.get(gate, EXIT_FAIL)


def build_robocopy_cmd(src: Path, dst: Path) -> list[str]:
    """Windows mirror command (mission 2-iv; pinned by tests)."""
    return ["robocopy", str(src), str(dst), "/MIR", "/XF", ".git", ".nojekyll"]


def build_rsync_cmd(src: Path, dst: Path) -> list[str]:
    """Non-Windows fallback mirror command (mission 2-iv; pinned by tests)."""
    return [
        "rsync",
        "-a",
        "--delete",
        "--exclude",
        ".git",
        "--exclude",
        ".nojekyll",
        str(src).rstrip("\\/") + "/",
        str(dst).rstrip("\\/") + "/",
    ]


def mirror_engine() -> str:
    """robocopy on Windows (verified 2026-11-16 chain), rsync elsewhere."""
    return "robocopy" if os.name == "nt" else "rsync"


def build_mirror_cmd(engine: str, src: Path, dst: Path) -> list[str]:
    """Dispatch to the platform mirror command."""
    if engine == "robocopy":
        return build_robocopy_cmd(src, dst)
    return build_rsync_cmd(src, dst)


def mirror_rc_ok(engine: str, rc: int) -> bool:
    """robocopy: rc<8 = success (bit flags); rsync: rc==0 only (pinned by tests)."""
    return rc < 8 if engine == "robocopy" else rc == 0


def race_detected(remote_tip: str | None, local_head: str) -> bool:
    """True when the remote gh-pages tip exists and diverges from local (mission 2-v)."""
    return remote_tip is not None and remote_tip != local_head


def build_commit_message(main_head: str) -> str:
    """Commit message format (mission 2-vi; pinned by tests)."""
    return f"deploy: main@{main_head[:7]} — site publish (local lane)"


def default_runner(cmd: list[str], cwd: Path | None, timeout: int | None) -> tuple[int, str, str]:
    """Real subprocess runner: bytes captured, decoded UTF-8 with replacement."""
    resolved = shutil.which(cmd[0]) or cmd[0]
    argv = [resolved, *cmd[1:]]
    try:
        proc = subprocess.run(
            argv,
            cwd=None if cwd is None else str(cwd),
            capture_output=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return 127, "", f"executable not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s: {' '.join(cmd)}"
    return (
        proc.returncode,
        proc.stdout.decode("utf-8", errors="replace"),
        proc.stderr.decode("utf-8", errors="replace"),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """CLI surface: --build / --worktree / --dry-run / --clean-out (default ON)."""
    parser = argparse.ArgumentParser(
        prog="publish_site_local.py",
        description="Local gh-pages publish chain (Actions-disabled era); fail-closed gates.",
        epilog="exit codes: 0 success / 1 failure / 2 race abort / 3 precondition refusal",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="run pnpm install --frozen-lockfile (if node_modules missing) + build in web/",
    )
    parser.add_argument(
        "--worktree",
        type=Path,
        default=None,
        help="gh-pages worktree path (default: data/ops/gh_pages_worktree)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="full-chain read-only diagnostics: zero disk writes, zero push",
    )
    parser.add_argument(
        "--clean-out",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="delete web/out after a successful push (default ON; owner storage discipline)",
    )
    return parser.parse_args(argv)


def _check_quality_gates(
    web_dir: Path, web_out: Path, run: Runner, dry: bool, built: bool
) -> tuple[bool, int | None]:
    """Sitemap-parity + .nojekyll, fail-closed. Returns (ok, failure_rc)."""
    if not web_out.is_dir():
        if dry and built:
            print("[dry-run][gate] web/out absent pre-build; real run would create it via --build")
            return True, None
        print(
            "[gate] web/out missing and --build not given -> run with --build "
            "(pnpm install --frozen-lockfile + build) or build web/ manually first"
        )
        return False, exit_code_for("gate")
    if not (web_out / ".nojekyll").is_file():
        print("[gate] web/out/.nojekyll missing -> fail-closed (legacy Jekyll drops _next/)")
        return False, exit_code_for("gate")
    if dry and not (web_out / "sitemap.xml").is_file():
        print("[dry-run][gate] web/out/sitemap.xml absent; skipping parity probe (build recreates)")
        return True, None
    rc, out, err = run(["node", "scripts/sitemap-parity.mjs"], web_dir, GATE_TIMEOUT)
    if rc != 0:
        tail = (err.strip() or out.strip())[-600:]
        print(f"[gate] sitemap-parity rc={rc} -> fail-closed\n{tail}")
        return False, exit_code_for("gate")
    print("[gate] sitemap-parity ok + .nojekyll present")
    return True, None


def _race_gate(root: Path, worktree: Path, run: Runner) -> tuple[bool, int | None]:
    """Remote tip vs local HEAD (mission 2-v). Returns (ok, failure_rc)."""
    rc, out, err = run(["git", "ls-remote", "origin", "gh-pages"], root, GIT_TIMEOUT)
    if rc != 0:
        print(f"[race] git ls-remote failed rc={rc} -> cannot verify remote tip (fail-closed)")
        print(f"{err.strip()[:300]}")
        return False, exit_code_for("gate")
    remote_tip = out.strip().split()[0] if out.strip() else None
    rc, out, err = run(["git", "rev-parse", "HEAD"], worktree, GIT_TIMEOUT)
    if rc != 0:
        print(f"[race] worktree HEAD unreadable rc={rc}: {err.strip()[:200]}")
        return False, exit_code_for("gate")
    local_head = out.strip()
    if race_detected(remote_tip, local_head):
        print(
            f"[race] remote gh-pages tip {remote_tip[:7]} != local worktree HEAD "
            f"{local_head[:7]} -> abort (mutual exclusion with publish-site.yml; never force-push)"
        )
        print("       resolve: git -C <worktree> pull --ff-only, or investigate the remote advance")
        return False, exit_code_for("race")
    if remote_tip is None:
        print("[race] remote gh-pages ref missing -> pass (creation case)")
    else:
        print(f"[race] remote tip == local HEAD {local_head[:7]} -> pass")
    return True, None


def main(
    argv: list[str] | None = None,
    *,
    repo_root: Path | None = None,
    runner: Runner | None = None,
) -> int:
    """Run the fail-closed publish chain; returns the process exit code."""
    args = parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    run = runner or default_runner
    dry = args.dry_run
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]
    web_dir = root / "web"
    web_out = web_dir / "out"
    if args.worktree is not None:
        worktree = Path(args.worktree)
    else:
        worktree = root / "data" / "ops" / "gh_pages_worktree"
    tag = "[dry-run]" if dry else ""

    # 0. precondition: no unstaged tracked changes in the main worktree (rc=3).
    rc, out, err = run(["git", "diff", "--name-only"], root, GIT_TIMEOUT)
    if rc != 0:
        print(f"[precondition] git diff failed rc={rc}: {err.strip()[:200]}")
        return exit_code_for("precondition")
    dirty = [line for line in out.splitlines() if line.strip()]
    if dirty:
        print(f"[precondition] refuse: {len(dirty)} unstaged tracked change(s), fail-closed:")
        for line in dirty[:10]:
            print(f"  {line}")
        if len(dirty) > 10:
            print(f"  ... and {len(dirty) - 10} more")
        return exit_code_for("precondition")
    print(f"[precondition]{tag} clean (no unstaged tracked changes)")

    # 1. optional build (real work only outside --dry-run).
    built = False
    if args.build:
        need_install = not (web_dir / "node_modules").is_dir()
        if dry:
            plan = "install (node_modules missing) + " if need_install else ""
            print(f"[dry-run][build] would {plan}build in web/ (npx {PNPM_SPEC})")
            built = True
        else:
            if need_install:
                print(f"[build] node_modules missing -> npx {PNPM_SPEC} install --frozen-lockfile")
                install_cmd = ["npx", PNPM_SPEC, "install", "--frozen-lockfile"]
                rc, out, err = run(install_cmd, web_dir, BUILD_TIMEOUT)
                if rc != 0:
                    print(f"[build] install failed rc={rc}\n{(err.strip() or out.strip())[-600:]}")
                    return exit_code_for("build")
            print(f"[build] npx {PNPM_SPEC} run build (cwd=web)")
            rc, out, err = run(["npx", PNPM_SPEC, "run", "build"], web_dir, BUILD_TIMEOUT)
            if rc != 0:
                print(f"[build] build failed rc={rc}\n{(err.strip() or out.strip())[-600:]}")
                return exit_code_for("build")
            built = True

    # 2. quality gates, fail-closed.
    ok, failure = _check_quality_gates(web_dir, web_out, run, dry, built)
    if not ok:
        assert failure is not None
        return failure

    # 3. worktree health (read-only).
    if not (worktree / ".git").exists():
        print(f"[worktree]{tag} {worktree} missing or not a git worktree -> refusing")
        print("       rebuild the worktree per the 轮 165 recovery flow first")
        return exit_code_for("gate")
    rc, out, err = run(["git", "rev-parse", "HEAD"], worktree, GIT_TIMEOUT)
    if rc != 0:
        print(f"[worktree]{tag} HEAD unreadable rc={rc}: {err.strip()[:200]}")
        return exit_code_for("gate")

    # 4. mirror (write step; plan-only under --dry-run).
    engine = mirror_engine()
    mirror_cmd = build_mirror_cmd(engine, web_out, worktree)
    if dry:
        print(f"[dry-run][mirror] would run: {' '.join(mirror_cmd)}")
    else:
        rc, out, err = run(mirror_cmd, root, MIRROR_TIMEOUT)
        if not mirror_rc_ok(engine, rc):
            print(f"[mirror] {engine} rc={rc} -> fail (robocopy rc>=8 = real error)")
            print(f"{(err.strip() or out.strip())[-600:]}")
            return exit_code_for("mirror")
        print(f"[mirror] ok ({engine} rc={rc})")
        if not (worktree / ".git").exists():
            print("[mirror] worktree .git missing after mirror -> refuse (post-mirror guard)")
            return exit_code_for("mirror")

    # 5. race gate (read-only probes; aborts with rc=2 before any push).
    ok, failure = _race_gate(root, worktree, run)
    if not ok:
        assert failure is not None
        return failure

    # 6/7. commit + push (write steps; plan-only under --dry-run).
    if dry:
        rc, out, _ = run(["git", "rev-parse", "HEAD"], root, GIT_TIMEOUT)
        msg = build_commit_message(out.strip()) if rc == 0 else "deploy: main@<head7>"
        print(f"[dry-run][commit] would: git add -A; commit only if changes ({msg});")
        print("       push origin gh-pages")
        keep = "keep" if not args.clean_out else "remove"
        print(f"[dry-run][clean-out] would {keep} web/out after a successful push")
        print("[dry-run] all read-only gates passed -> real run would proceed (rc=0)")
        return EXIT_OK

    rc, _, err = run(["git", "add", "-A"], worktree, GIT_TIMEOUT)
    if rc != 0:
        print(f"[commit] git add -A failed rc={rc}: {err.strip()[:200]}")
        return exit_code_for("commit")
    rc, out, err = run(["git", "status", "--porcelain"], worktree, GIT_TIMEOUT)
    if rc != 0:
        print(f"[commit] git status failed rc={rc}: {err.strip()[:200]}")
        return exit_code_for("commit")
    changes = [line for line in out.splitlines() if line.strip()]
    if not changes:
        print("[commit] no changes in worktree -> skip commit+push (remote already == local)")
        print("[clean-out] skipped (nothing was published this run)")
        return EXIT_OK
    rc, out, _ = run(["git", "rev-parse", "HEAD"], root, GIT_TIMEOUT)
    if rc != 0:
        print(f"[commit] main HEAD unreadable rc={rc}")
        return exit_code_for("commit")
    message = build_commit_message(out.strip())
    rc, _, err = run(["git", "commit", "-m", message], worktree, GIT_TIMEOUT)
    if rc != 0:
        print(f"[commit] git commit failed rc={rc}: {err.strip()[:300]}")
        return exit_code_for("commit")
    print(f"[commit] ok ({message})")
    rc, out, err = run(["git", "push", "origin", "gh-pages"], worktree, GIT_TIMEOUT)
    if rc != 0:
        print(f"[push] failed rc={rc}\n{(err.strip() or out.strip())[-600:]}")
        return exit_code_for("push")
    print("[push] ok -> origin gh-pages")
    if args.clean_out:
        shutil.rmtree(web_out)
        print(f"[clean-out] removed {web_out} (owner storage discipline)")
    else:
        print("[clean-out] skipped (--no-clean-out)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
