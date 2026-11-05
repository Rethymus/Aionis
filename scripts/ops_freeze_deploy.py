"""Freeze-channel site deploy — publish web/out to gh-pages locally while
GitHub Actions is billing-locked (docs/ops-local-refresh.md §GitHub 计费冻结
应对; "billing lock #2", 2026-11-06).

When the account is billing-frozen EVERY Actions run dies in seconds —
including `publish-site.yml` — while the local evening lane keeps pushing
main: origin/main advances nightly and the live Pages site stays on its last
pre-freeze deploy (repo-site drift). This script performs the CI lane's
publish step LOCALLY: git worktree checkout of gh-pages, mirror-copy of
web/out over it, commit, push. The legacy Pages build from the gh-pages
branch consumes zero Actions minutes, and the PAT push path is proven usable
during the freeze (the evening lane pushes every evening). The real push is
an OWNER decision — bare invocation errors out; `--dry-run` never pushes and
`--deploy` must be passed explicitly.

Semantics mirror `.github/workflows/publish-site.yml` exactly:
  rsync -a --delete --exclude .git --exclude .nojekyll web/out/ site/
  git add -A; no diff -> "nothing to publish" exit 0; else commit + push.
Windows has no rsync: robocopy /MIR is the mirror equivalent, with two
measured caveats (tmp probe, 2026-11-06):
  - robocopy exit codes 0-7 are SUCCESS flavors (1=copied, 2=extras purged,
    3=both — a month-stale mirror returns 3); >=8 is a failure;
  - /XD excludes only DIRECTORIES, and the worktree's .git is a FILE (a
    "gitdir:" pointer), so the literal `robocopy /MIR /XD .git .nojekyll`
    PURGES dst/.git and orphans the worktree (probed: dst lost .git). The
    mirror excludes are therefore `/XD .git /XF .git .nojekyll` — the exact
    translation of rsync's `--exclude .git --exclude .nojekyll` (which match
    files and dirs alike). /NFL /NDL /NP just keep the captured output sane.

Preflight (step ①) hard-codes the evaluator's measured trap as a guard — a
naive mirror would ROLL THE LIVE SITE BACK a month (at introduction web/out
carried snapshot_ts 2026-10-05 while origin/gh-pages served 2026-11-02):
  - web/out must exist with .nojekyll and api/v1/panels/data_health.json
    (.nojekyll survival is what keeps the legacy Jekyll build from dropping
    _next/ — round 86);
  - web/src/data/aionis/data_health.json's snapshot_ts must not be OLDER than
    origin/gh-pages's deployed panel (read via git show of the freshly
    fetched ref — the deployed bytes, not an assumption);
  - web/out's snapshot_ts must EQUAL web/src's — a mismatch means the local
    build is stale: run `pnpm build` first (prebuild=build-api.mjs mirrors
    the panels into public/api/v1, round 85) before deploying.

--check-recovery is the unlock detector for the nightly report: the latest
`Tests` run's conclusion == success means the billing unlock happened AND a
push re-ran the pipeline green — print 已恢复，可停止使用冻结通道 and exit 2;
still-locked or unknowable exits 0 (keep reporting the freeze channel).

Usage:
  uv run python scripts/ops_freeze_deploy.py --dry-run
      # ① preflight + ② worktree mirror sync + report; never stages/commits/pushes
  uv run python scripts/ops_freeze_deploy.py --deploy
      # OWNER USE: ①②③ full deploy — commit `deploy: local freeze-channel
      # <date>` in the worktree + push origin gh-pages
  uv run python scripts/ops_freeze_deploy.py --check-recovery
      # billing-unlock detector for the nightly report (exit 2 = recovered)
  uv run python scripts/ops_freeze_deploy.py --deploy --worktree-dir <dir>
      # override the worktree location (default: data/ops/gh_pages_worktree,
      # gitignored; created once, reused on every later run)

Exit codes: 0 = deployed / nothing-to-deploy / dry-run done / still locked;
1 = preflight or sync failure (honest FAIL — nothing was pushed);
2 = --check-recovery: Tests green again — 已恢复，可停止使用冻结通道.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKTREE = ROOT / "data" / "ops" / "gh_pages_worktree"
DEPLOYED_PANEL = "api/v1/panels/data_health.json"  # gh-pages-relative layout
TESTS_WORKFLOW = "Tests"  # ci.yml's name — the freeze kills it in ~4s
RECOVERED_MSG = "已恢复，可停止使用冻结通道"
GIT_TIMEOUT_S = 300
SYNC_TIMEOUT_S = 600

IS_WINDOWS = sys.platform.startswith("win")

# snapshot_ts parsing is shared with the evening lane's doctor layer 7 (same
# field, same naive=UTC convention) — one parser, one convention.
from ops_local_refresh import _parse_snapshot_ts  # noqa: E402


def log(line: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {line}", flush=True)


# ----------------------------------------------------- injectable I/O seams

def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Bounded git runner (UTF-8 forced, errors replaced — the lane's GBK
    lesson). Injectable seam: the fake-origin tests run REAL git against a
    local bare remote; unit tests monkeypatch the module-level wrappers."""
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          timeout=GIT_TIMEOUT_S)


def _fetch_gh_pages(root: Path) -> None:
    """Refresh the origin/gh-pages remote-tracking ref (network; the PAT path
    proven usable during the freeze). Raises on failure — preflight turns
    that into an honest FAIL, never a stale-ref false pass."""
    r = _git(["fetch", "origin", "gh-pages"], cwd=root)
    if r.returncode != 0:
        raise RuntimeError(
            f"git fetch origin gh-pages failed: {(r.stderr or r.stdout)[-200:]}")


def _show_deployed_panel(root: Path) -> str:
    """The DEPLOYED data_health payload, read from origin/gh-pages (git show
    of the freshly fetched ref — the ask's 'gh show 实读'). Raises when
    gh-pages lacks the panel: an honest preflight FAIL downstream, never a
    silent pass."""
    r = _git(["show", f"origin/gh-pages:{DEPLOYED_PANEL}"], cwd=root)
    if r.returncode != 0:
        raise RuntimeError(
            f"origin/gh-pages:{DEPLOYED_PANEL} unreadable: "
            f"{(r.stderr or r.stdout)[-200:]}")
    return r.stdout


def _gh_run_list_tests() -> str:
    """Latest Tests workflow run via gh CLI (read-only). Injectable seam:
    tests monkeypatch this with the three gh states (green / red / error)."""
    out = subprocess.run(
        ["gh", "run", "list", "--workflow", TESTS_WORKFLOW, "--limit", "1",
         "--json", "conclusion,createdAt"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=30)
    if out.returncode != 0:
        raise RuntimeError(
            f"gh run list failed: {(out.stderr or '').strip()[-120:]}")
    return out.stdout


def _push(worktree_dir: Path) -> None:
    r = _git(["push", "origin", "gh-pages"], cwd=worktree_dir)
    if r.returncode != 0:
        raise RuntimeError(f"push failed: {(r.stdout + r.stderr)[-300:]}")


# ----------------------------------------------------------------- mirror

def sync_command(src: Path, dst: Path, windows: bool = IS_WINDOWS) -> list[str]:
    """The mirror-copy argv — publish-site.yml's
    `rsync -a --delete --exclude .git --exclude .nojekyll web/out/ site/`
    translated per platform. Windows robocopy needs /XF for FILES (.git is a
    worktree pointer FILE; /XD alone purged it in the 2026-11-06 probe)."""
    if windows:
        return ["robocopy", str(src), str(dst),
                "/MIR", "/XD", ".git", "/XF", ".git", ".nojekyll",
                "/NFL", "/NDL", "/NP"]
    return ["rsync", "-a", "--delete", "--exclude", ".git", "--exclude",
            ".nojekyll", f"{src}/", f"{dst}/"]


def sync_ok(returncode: int, windows: bool = IS_WINDOWS) -> bool:
    """robocopy: 0-7 are success flavors (1=copied, 2=extras purged, 3=both —
    a month-stale mirror returns 3); >=8 failure. rsync: only 0 is success."""
    return returncode <= 7 if windows else returncode == 0


def _run_sync(src: Path, dst: Path) -> None:
    """Execute the mirror copy for real (the fake-origin integration test
    runs this against tmp dirs; subprocess argv, never a shell — Git Bash
    mangles `/MIR` into a path, the 2026-11-06 probe learned)."""
    argv = sync_command(src, dst)
    try:
        r = subprocess.run(argv, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           timeout=SYNC_TIMEOUT_S)
    except OSError as exc:
        raise RuntimeError(
            f"mirror copy could not start ({argv[0]}): {exc}") from exc
    if not sync_ok(r.returncode):
        tail = [ln for ln in (r.stdout or "").splitlines() if ln.strip()][-5:]
        raise RuntimeError(
            f"mirror copy failed (rc={r.returncode}): "
            f"{' | '.join(tail) or (r.stderr or '')[-200:]}")


# -------------------------------------------------------------- preflight ①

def preflight(root: Path, fetch=None, show=None) -> list[tuple[str, bool, str]]:
    """Step ① as (name, ok, detail) tuples — collect-then-render, the lane
    doctor's collect_layers pattern (one source for every surface). Any FAIL
    aborts the deploy BEFORE the worktree is touched. Guard rails, in order:
    the build candidate (web/out) must exist intact, the repo must be fresher
    than the deployed site, and the build must be current with the repo."""
    fetch = fetch or _fetch_gh_pages
    show = show or _show_deployed_panel
    out_dir = root / "web" / "out"
    out_panel = out_dir / "api" / "v1" / "panels" / "data_health.json"
    src_panel = root / "web" / "src" / "data" / "aionis" / "data_health.json"
    checks: list[tuple[str, bool, str]] = []
    checks.append(("1/6 web/out exists", out_dir.is_dir(), str(out_dir)))
    checks.append(("2/6 web/out/.nojekyll", (out_dir / ".nojekyll").is_file(),
                   "present" if (out_dir / ".nojekyll").is_file() else
                   "MISSING — legacy Jekyll would drop _next/ (round 86)"))
    checks.append(("3/6 web/out deployed panel", out_panel.is_file(),
                   str(out_panel)))
    checks.append(("4/6 web/src data_health", src_panel.is_file(),
                   str(src_panel)))
    try:
        fetch(root)
        checks.append(("5/6 fetch origin/gh-pages", True,
                       "remote-tracking ref fresh"))
    except Exception as exc:  # noqa: BLE001 — honest FAIL, never a crash
        checks.append(("5/6 fetch origin/gh-pages", False, str(exc)))
        checks.append(("6/6 snapshot freshness", False,
                       "skipped: fetch failed"))
        return checks

    def _fail(detail: str) -> list[tuple[str, bool, str]]:
        checks.append(("6/6 snapshot freshness", False, detail))
        return checks

    try:
        dep_ts = _parse_snapshot_ts(show(root))
    except Exception as exc:  # noqa: BLE001
        return _fail(f"deployed panel unreadable: {exc}")
    if dep_ts is None:
        return _fail("deployed panel has no parseable snapshot_ts")
    try:
        src_ts = _parse_snapshot_ts(src_panel.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        return _fail(f"web/src data_health unreadable: {exc}")
    if src_ts is None:
        return _fail("web/src data_health has no parseable snapshot_ts")
    try:
        out_ts = _parse_snapshot_ts(out_panel.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        return _fail(f"web/out data_health unreadable: {exc}")
    if out_ts is None:
        return _fail("web/out data_health has no parseable snapshot_ts")
    if src_ts < dep_ts:
        return _fail(
            f"web/src snapshot_ts ({src_ts.isoformat()}) 比 origin/gh-pages "
            f"线上 ({dep_ts.isoformat()}) 旧 — 部署会回退线上数据：先 git pull "
            "更新仓库，再 pnpm build 后重试")
    if out_ts != src_ts:
        return _fail(
            f"web/out snapshot_ts ({out_ts.isoformat()}) != web/src "
            f"({src_ts.isoformat()}) — 本地构建过期：先运行 pnpm build "
            "(prebuild=build-api.mjs 会把面板镜像进 public/api/v1, round 85) "
            "再部署")
    checks.append(("6/6 snapshot freshness", True,
                   f"fresh: src={src_ts.isoformat()} out={out_ts.isoformat()} "
                   f"deployed={dep_ts.isoformat()}"))
    return checks


# ------------------------------------------------------- worktree + sync ②

def ensure_worktree(root: Path, worktree_dir: Path) -> Path:
    """gh-pages checkout at worktree_dir: created on first use (DWIM branch
    from the freshly fetched origin/gh-pages), reused afterwards. Reuse
    refreshes with reset --hard origin/gh-pages — deploy commits are pushed,
    so any local-only state here is debris from a crashed attempt and is
    discarded by design (the mirror re-derives everything anyway)."""
    dot_git = worktree_dir / ".git"
    if dot_git.is_file():
        r = _git(["reset", "--hard", "origin/gh-pages"], cwd=worktree_dir)
        if r.returncode != 0:
            raise RuntimeError(
                f"worktree refresh failed: {(r.stderr or r.stdout)[-200:]}")
        log(f"worktree reused + refreshed: {worktree_dir}")
        return worktree_dir
    if worktree_dir.exists() and any(worktree_dir.iterdir()):
        raise RuntimeError(
            f"{worktree_dir} exists but is not a gh-pages worktree (no .git "
            "pointer) — human review needed, refusing to touch it")
    _git(["worktree", "prune"], cwd=root)
    r = _git(["worktree", "add", str(worktree_dir), "gh-pages"], cwd=root)
    if r.returncode != 0:
        raise RuntimeError(
            f"git worktree add failed: {(r.stderr or r.stdout)[-300:]}")
    log(f"worktree created: {worktree_dir} (gh-pages @ origin/gh-pages)")
    return worktree_dir


# --------------------------------------------------------- commit + push ③

def do_deploy(dry_run: bool, worktree_dir: Path, root: Path | None = None,
              push=None) -> int:
    """① preflight → ② worktree + mirror sync → ③ report (dry-run) or
    commit+push (owner). Returns 0 on success/no-op/dry-run, 1 on any honest
    failure (nothing is ever pushed past a failure)."""
    root = root or ROOT
    push = push or _push
    checks = preflight(root)
    for name, ok, detail in checks:
        log(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    if any(not ok for _, ok, _ in checks):
        log("PREFLIGHT-FAIL: nothing synced, nothing pushed")
        return 1
    wt = ensure_worktree(root, worktree_dir)
    src = root / "web" / "out"
    log(f"mirror sync {src} -> {wt} "
        f"({'robocopy /MIR' if IS_WINDOWS else 'rsync -a --delete'})")
    _run_sync(src, wt)
    status = _git(["status", "--porcelain"], cwd=wt)
    if status.returncode != 0:
        log(f"git status failed: {(status.stderr or '')[-200:]}")
        return 1
    changes = [ln for ln in status.stdout.splitlines() if ln.strip()]
    if not changes:
        log("NO-CHANGES: site identical to origin/gh-pages — nothing to "
            "deploy (exit 0)")
        return 0
    log(f"{len(changes)} path(s) differ from origin/gh-pages; sample:")
    for ln in changes[:15]:
        log(f"  {ln}")
    if len(changes) > 15:
        log(f"  ... and {len(changes) - 15} more")
    if dry_run:
        log("--dry-run: preflight + sync done; NOT staging/committing/pushing")
        return 0
    add = _git(["add", "-A"], cwd=wt)
    if add.returncode != 0:
        log(f"git add failed: {(add.stderr or '')[-200:]}")
        return 1
    msg = f"deploy: local freeze-channel {datetime.now().strftime('%Y-%m-%d')}"
    commit = _git(["commit", "-m", msg], cwd=wt)
    if commit.returncode != 0:
        log(f"git commit failed: {(commit.stderr or '')[-200:]}")
        return 1
    sha = _git(["rev-parse", "HEAD"], cwd=wt).stdout.strip()
    try:
        push(wt)
    except Exception as exc:  # noqa: BLE001 — loud FAIL; commit stays local
        log(f"PUSH-FAIL: commit {sha[:9]} is local-only ({exc}); "
            "rerun --deploy to retry the push")
        return 1
    log(f"DEPLOYED: {sha[:9]} '{msg}' pushed to origin/gh-pages (legacy "
        "Pages build picks it up without Actions minutes)")
    return 0


# ------------------------------------------------------------ recovery flag

def do_check_recovery(gh=None) -> int:
    """--check-recovery: three gh states, three outcomes —
    latest Tests conclusion=success → the unlock happened AND a push re-ran
    the pipeline green: print 已恢复 + exit 2 (the nightly report captures
    the code and stops the freeze-channel reporting);
    failure/anything-else → still locked, exit 0;
    gh error or no runs → cannot judge, exit 0 (keep the freeze channel —
    conservative, never a false all-clear)."""
    gh = gh or _gh_run_list_tests
    try:
        runs = json.loads(gh())
    except Exception as exc:  # noqa: BLE001 — unknowable != recovered
        log(f"UNKNOWN: cannot read the latest {TESTS_WORKFLOW} run ({exc}) — "
            "保守起见继续使用冻结通道")
        return 0
    if not isinstance(runs, list) or not runs:
        log(f"UNKNOWN: no {TESTS_WORKFLOW} run found — 保守起见继续使用冻结通道")
        return 0
    conclusion = runs[0].get("conclusion")
    if conclusion == "success":
        log(f"RECOVERED: latest {TESTS_WORKFLOW} run is green — "
            f"{RECOVERED_MSG}")
        return 2
    log(f"STILL-LOCKED: latest {TESTS_WORKFLOW} conclusion={conclusion!r} — "
        "冻结未解除，继续使用冻结通道")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true",
                       help="① preflight + ② worktree mirror sync + report — "
                            "never stages, commits or pushes")
    group.add_argument("--deploy", action="store_true",
                       help="OWNER USE: full ①②③ deploy (commit + push "
                            "origin gh-pages)")
    group.add_argument("--check-recovery", action="store_true",
                       help="billing-unlock detector: exit 2 when the latest "
                            "Tests run is green, else 0")
    parser.add_argument("--worktree-dir", type=Path, default=DEFAULT_WORKTREE,
                        help="gh-pages worktree location (default: %(default)s)")
    args = parser.parse_args()
    if args.check_recovery:
        return do_check_recovery()
    return do_deploy(dry_run=args.dry_run, worktree_dir=args.worktree_dir)


if __name__ == "__main__":
    raise SystemExit(main())
