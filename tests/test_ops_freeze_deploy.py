"""Hermetic tests for the freeze-channel site deploy (scripts/ops_freeze_deploy.py).

The script exists because billing freezes kill publish-site.yml while the
evening lane keeps advancing main — its preflight guards are the evaluator's
measured traps turned into checks (a naive mirror would roll the live site
back a month), and its mirror semantics must never orphan the gh-pages
worktree (.git there is a FILE that robocopy /XD alone purges — probed
2026-11-06). Network-facing calls (git fetch/show, gh run list, push) are
injected or run against a local bare remote; the mirror copy runs the real
robocopy/rsync binary against tmp dirs only.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import ops_freeze_deploy as dep  # noqa: E402

# Real values observed in the repo at introduction (2026-11-06): the live
# web/out build was a MONTH behind the deployed site — the exact trap the
# preflight must catch.
NEW_TS = "2026-11-05T13:20:58.252918+00:00"       # web/src (fresh, committed)
DEPLOYED_TS = "2026-11-02T11:32:33.889178+00:00"  # origin/gh-pages (live)
OLD_TS = "2026-10-05T11:02:48.473501+00:00"       # stale web/out build


def _panel(ts: str) -> str:
    return json.dumps({"status": "ok", "snapshot_ts": ts})


def _snapshot_of(path: Path) -> str:
    return json.loads(
        (path / "api" / "v1" / "panels" / "data_health.json")
        .read_text(encoding="utf-8"))["snapshot_ts"]


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def _fake_out(root: Path, ts: str, files: dict[str, str] | None = None) -> Path:
    """A web/out + web/src pair carrying `ts`, plus extra out files (the
    mirror candidates). Both sides get the same ts — a current build."""
    out = root / "web" / "out"
    panels = out / "api" / "v1" / "panels"
    panels.mkdir(parents=True, exist_ok=True)
    (out / ".nojekyll").write_text("x", encoding="utf-8")
    (panels / "data_health.json").write_text(_panel(ts), encoding="utf-8")
    aionis = root / "web" / "src" / "data" / "aionis"
    aionis.mkdir(parents=True, exist_ok=True)
    (aionis / "data_health.json").write_text(_panel(ts), encoding="utf-8")
    for name, content in (files or {}).items():
        (out / name).write_text(content, encoding="utf-8")
    return out


def _no_fetch(root: Path) -> None:  # injected fetch: nothing to do
    return None


def _deployed(payload: str):
    return lambda root: payload


@pytest.fixture
def fake_origin(tmp_path):
    """A local bare origin seeded with a deployed gh-pages site (old panel,
    legacy page, .nojekyll) + a main clone whose origin points at it. Real
    git, zero network — `git fetch origin gh-pages` inside main works."""
    bare = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    main = tmp_path / "main"
    _git(["init", "--bare", str(bare)], cwd=tmp_path)
    _git(["init", "-b", "gh-pages", str(seed)], cwd=tmp_path)
    _git(["config", "user.email", "t@t"], cwd=seed)
    _git(["config", "user.name", "t"], cwd=seed)
    panels = seed / "api" / "v1" / "panels"
    panels.mkdir(parents=True)
    (seed / ".nojekyll").write_text("x", encoding="utf-8")
    (panels / "data_health.json").write_text(_panel(DEPLOYED_TS),
                                             encoding="utf-8")
    (seed / "legacy_page.html").write_text("old", encoding="utf-8")
    _git(["add", "-A"], cwd=seed)
    _git(["commit", "-m", "seed gh-pages"], cwd=seed)
    _git(["push", str(bare), "gh-pages"], cwd=seed)
    _git(["init", "-b", "main", str(main)], cwd=tmp_path)
    _git(["config", "user.email", "t@t"], cwd=main)
    _git(["config", "user.name", "t"], cwd=main)
    (main / "README.md").write_text("x", encoding="utf-8")
    _git(["add", "-A"], cwd=main)
    _git(["commit", "-m", "init"], cwd=main)
    _git(["remote", "add", "origin", str(bare)], cwd=main)
    _git(["fetch", "origin", "gh-pages"], cwd=main)
    return tmp_path, main


_needs_syncer = pytest.mark.skipif(
    shutil.which("robocopy" if sys.platform.startswith("win") else "rsync")
    is None,
    reason="mirror binary (robocopy/rsync) unavailable on this host")


# --- preflight ①: the stale/new snapshot comparison ---------------------------


def test_preflight_passes_when_candidate_fresher_than_deployed(tmp_path) -> None:
    _fake_out(tmp_path, NEW_TS)
    checks = dep.preflight(tmp_path, fetch=_no_fetch,
                           show=_deployed(_panel(DEPLOYED_TS)))
    assert all(ok for _, ok, _ in checks), checks
    assert "fresh" in checks[-1][2]
    assert NEW_TS in checks[-1][2] and DEPLOYED_TS in checks[-1][2]


def test_preflight_fails_when_local_older_than_deployed(tmp_path) -> None:
    """The rollback guard: deploying a month-old src would roll the live site
    back — FAIL with the git pull + pnpm build remedy, never a silent pass."""
    _fake_out(tmp_path, OLD_TS)  # src == out == 10-05, deployed 11-02
    checks = dep.preflight(tmp_path, fetch=_no_fetch,
                           show=_deployed(_panel(DEPLOYED_TS)))
    name, ok, detail = checks[-1]
    assert name == "6/6 snapshot freshness" and not ok
    assert "旧" in detail and "回退" in detail and "git pull" in detail


def test_preflight_fails_when_out_stale_behind_src(tmp_path) -> None:
    """The evaluator's measured trap, guarded: build inputs (web/src) fresh,
    the local build (web/out) a month old — a naive mirror would regress the
    site. FAIL must name the `pnpm build` remedy (prebuild=build-api.mjs
    mirrors the panels into public/api/v1, round 85)."""
    _fake_out(tmp_path, OLD_TS)
    (tmp_path / "web" / "src" / "data" / "aionis" / "data_health.json") \
        .write_text(_panel(NEW_TS), encoding="utf-8")  # fresh src, stale build
    checks = dep.preflight(tmp_path, fetch=_no_fetch,
                           show=_deployed(_panel(DEPLOYED_TS)))
    name, ok, detail = checks[-1]
    assert name == "6/6 snapshot freshness" and not ok
    assert "pnpm build" in detail and "round 85" in detail


def test_preflight_fails_on_missing_nojekyll(tmp_path) -> None:
    """Round 86: without .nojekyll the legacy Jekyll build drops _next/ —
    the check must fail before anything is synced."""
    _fake_out(tmp_path, NEW_TS)
    (tmp_path / "web" / "out" / ".nojekyll").unlink()
    checks = dep.preflight(tmp_path, fetch=_no_fetch,
                           show=_deployed(_panel(DEPLOYED_TS)))
    nojekyll = next(c for c in checks if ".nojekyll" in c[0])
    assert not nojekyll[1] and "round 86" in nojekyll[2]


def test_preflight_fails_honestly_on_unparseable_deployed_payload(
        tmp_path) -> None:
    _fake_out(tmp_path, NEW_TS)
    for bad in ("<html>404 Not Found</html>", '{"status": "ok"}'):
        checks = dep.preflight(tmp_path, fetch=_no_fetch,
                               show=_deployed(bad))
        name, ok, detail = checks[-1]
        assert name == "6/6 snapshot freshness" and not ok
        assert "deployed panel" in detail


# --- mirror command construction + robocopy exit-code semantics ---------------


def test_sync_command_windows_translates_the_ci_rsync(tmp_path) -> None:
    argv = dep.sync_command(tmp_path / "out", tmp_path / "wt", windows=True)
    assert argv == ["robocopy", str(tmp_path / "out"), str(tmp_path / "wt"),
                    "/MIR", "/XD", ".git", "/XF", ".git", ".nojekyll",
                    "/NFL", "/NDL", "/NP"]


def test_sync_command_posix_is_the_publish_site_rsync_verbatim(
        tmp_path) -> None:
    argv = dep.sync_command(tmp_path / "out", tmp_path / "wt", windows=False)
    # .github/workflows/publish-site.yml:86, path-for-path
    assert argv == ["rsync", "-a", "--delete", "--exclude", ".git",
                    "--exclude", ".nojekyll",
                    f"{tmp_path / 'out'}/", f"{tmp_path / 'wt'}/"]


def test_sync_command_defaults_to_host_binary(tmp_path) -> None:
    argv = dep.sync_command(tmp_path / "a", tmp_path / "b")
    assert argv[0] == ("robocopy" if sys.platform.startswith("win")
                       else "rsync")


def test_sync_ok_robocopy_success_flavors_and_rsync_strictness() -> None:
    for rc in (0, 1, 2, 3, 7):  # copied / purged / both — all success
        assert dep.sync_ok(rc, windows=True)
    for rc in (8, 16):  # >=8 is a failure
        assert not dep.sync_ok(rc, windows=True)
    assert dep.sync_ok(0, windows=False)
    for rc in (1, 2, 23, 24):  # rsync: only 0 is success
        assert not dep.sync_ok(rc, windows=False)


def test_run_sync_treats_robocopy_flavors_as_success_and_8_as_failure(
        monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        dep, "sync_command",
        lambda src, dst, windows=True: [sys.executable, "-c", "pass"])
    dep._run_sync(tmp_path, tmp_path)  # rc 0 — no raise
    monkeypatch.setattr(
        dep, "sync_command",
        lambda src, dst, windows=True: [sys.executable, "-c",
                                        "raise SystemExit(8)"])
    with pytest.raises(RuntimeError, match="rc=8"):
        dep._run_sync(tmp_path, tmp_path)


# --- worktree + mirror semantics against a fake origin ------------------------


@_needs_syncer
def test_worktree_add_reuse_and_mirror_semantics(fake_origin) -> None:
    tmp_path, main = fake_origin
    wt = tmp_path / "wt"
    dep.ensure_worktree(main, wt)
    # a worktree's .git is a pointer FILE — the thing robocopy /XD purges
    assert (wt / ".git").is_file()
    assert (wt / ".git").read_text(encoding="utf-8").startswith("gitdir:")
    assert (wt / ".nojekyll").is_file()
    assert (wt / "legacy_page.html").read_text(encoding="utf-8") == "old"

    out = _fake_out(main, NEW_TS, {"fresh_page.html": "new"})
    dep._run_sync(out, wt)
    assert not (wt / "legacy_page.html").exists()   # /MIR --delete purge
    assert (wt / "fresh_page.html").read_text(encoding="utf-8") == "new"
    assert _snapshot_of(wt) == NEW_TS
    # THE probe pin: the worktree pointer file survives the mirror purge
    assert (wt / ".git").is_file()
    assert (wt / ".git").read_text(encoding="utf-8").startswith("gitdir:")
    assert (wt / ".nojekyll").is_file()             # excluded from purge

    # reuse path: origin advances (a post-freeze CI deploy landed), the
    # existing worktree refreshes to origin/gh-pages instead of re-adding
    seed_repo = tmp_path / "seed"
    (seed_repo / "recovery_page.html").write_text("r", encoding="utf-8")
    _git(["add", "-A"], cwd=seed_repo)
    _git(["commit", "-m", "post-freeze deploy"], cwd=seed_repo)
    _git(["push", str(tmp_path / "origin.git"), "gh-pages"], cwd=seed_repo)
    _git(["fetch", "origin", "gh-pages"], cwd=main)
    dep.ensure_worktree(main, wt)  # second call -> reuse + reset --hard
    assert (wt / "recovery_page.html").exists()
    assert (wt / "legacy_page.html").exists()       # tracked: back at origin
    assert _snapshot_of(wt) == DEPLOYED_TS
    assert (wt / "fresh_page.html").exists()  # untracked debris survives
    # reset --hard by design — the next mirror is what removes it:
    out2 = _fake_out(main, NEW_TS)
    (out2 / "fresh_page.html").unlink()  # second build no longer has it
    dep._run_sync(out2, wt)
    assert not (wt / "fresh_page.html").exists()
    assert (wt / ".git").is_file()


@_needs_syncer
def test_no_diff_deploys_nothing_and_never_pushes(fake_origin) -> None:
    tmp_path, main = fake_origin
    # out mirrors the deployed site EXACTLY (same panel ts, same legacy page)
    _fake_out(main, DEPLOYED_TS, {"legacy_page.html": "old"})
    pushes: list[Path] = []
    rc = dep.do_deploy(dry_run=False, worktree_dir=tmp_path / "wt",
                       root=main, push=lambda wt: pushes.append(wt))
    assert rc == 0
    assert pushes == []            # CI semantics: no diff -> no commit/push
    assert _git(["log", "-1", "--pretty=%s"],
                cwd=tmp_path / "wt").stdout.strip() == "seed gh-pages"


@_needs_syncer
def test_full_deploy_commits_and_pushes_once(fake_origin) -> None:
    tmp_path, main = fake_origin
    _fake_out(main, NEW_TS,
              {"legacy_page.html": "old", "fresh_page.html": "new"})
    pushes: list[Path] = []
    rc = dep.do_deploy(dry_run=False, worktree_dir=tmp_path / "wt",
                       root=main, push=pushes.append)
    assert rc == 0
    assert [p.name for p in pushes] == ["wt"]
    msg = _git(["log", "-1", "--pretty=%s"],
               cwd=tmp_path / "wt").stdout.strip()
    assert re.match(r"deploy: local freeze-channel \d{4}-\d{2}-\d{2}$", msg)
    assert _snapshot_of(tmp_path / "wt") == NEW_TS


@_needs_syncer
def test_dry_run_syncs_but_never_commits_or_pushes(fake_origin) -> None:
    tmp_path, main = fake_origin
    _fake_out(main, NEW_TS, {"fresh_page.html": "new"})
    pushes: list[Path] = []
    wt = tmp_path / "wt"
    rc = dep.do_deploy(dry_run=True, worktree_dir=wt, root=main,
                       push=pushes.append)
    assert rc == 0
    assert pushes == []
    assert _git(["log", "-1", "--pretty=%s"], cwd=wt) \
        .stdout.strip() == "seed gh-pages"          # no commit created
    status = _git(["status", "--porcelain"], cwd=wt).stdout
    assert status.strip()                           # sync happened, unstaged


@_needs_syncer
def test_preflight_fetch_failure_aborts_before_the_worktree(
        fake_origin, monkeypatch) -> None:
    tmp_path, main = fake_origin
    _fake_out(main, NEW_TS)

    def _boom(root):
        raise RuntimeError("network unreachable")

    monkeypatch.setattr(dep, "_fetch_gh_pages", _boom)
    pushes: list[Path] = []
    wt = tmp_path / "wt"
    rc = dep.do_deploy(dry_run=True, worktree_dir=wt, root=main,
                       push=pushes.append)
    assert rc == 1
    assert pushes == []
    assert not wt.exists()  # aborted at ① — worktree never touched


# --- --check-recovery: the three gh states -------------------------------------


def test_check_recovery_green_exits_two(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        dep, "_gh_run_list_tests",
        lambda: json.dumps([{"conclusion": "success",
                             "createdAt": "2026-11-07T10:00:00Z"}]))
    assert dep.do_check_recovery() == 2
    assert "已恢复，可停止使用冻结通道" in capsys.readouterr().out


def test_check_recovery_red_still_locked_exits_zero(monkeypatch,
                                                    capsys) -> None:
    """The freeze signature: Tests red in seconds (billing annotation)."""
    monkeypatch.setattr(
        dep, "_gh_run_list_tests",
        lambda: json.dumps([{"conclusion": "failure",
                             "createdAt": "2026-11-06T02:00:00Z"}]))
    assert dep.do_check_recovery() == 0
    out = capsys.readouterr().out
    assert "STILL-LOCKED" in out and "failure" in out


def test_check_recovery_gh_error_conservative(monkeypatch, capsys) -> None:
    def _boom():
        raise RuntimeError("gh: auth expired")

    monkeypatch.setattr(dep, "_gh_run_list_tests", _boom)
    assert dep.do_check_recovery() == 0  # unknowable != recovered
    assert "UNKNOWN" in capsys.readouterr().out


def test_check_recovery_no_runs_conservative(monkeypatch, capsys) -> None:
    monkeypatch.setattr(dep, "_gh_run_list_tests", lambda: "[]")
    assert dep.do_check_recovery() == 0
    assert "UNKNOWN" in capsys.readouterr().out


# --- layout pins ----------------------------------------------------------------


def test_deployed_panel_layout_and_repo_source_exist() -> None:
    """The gh-pages-relative panel path and the tracked comparison source are
    load-bearing (git show target / freshness input); the repo carries the
    latter (web/out is gitignored — not asserted here, CI has none)."""
    assert dep.DEPLOYED_PANEL == "api/v1/panels/data_health.json"
    assert (dep.ROOT / "web" / "src" / "data" / "aionis" /
            "data_health.json").exists()
