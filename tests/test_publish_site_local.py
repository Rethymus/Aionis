"""Hermetic tests for scripts/publish_site_local.py.

Owner mission publish-site-local-script (2026-11-16): pin the pure surfaces —
mirror command assembly shapes (robocopy/rsync), mirror rc semantics, exit-code
mapping, race determination, commit-message format — plus a DI-driven flow with
a fake runner proving --dry-run has zero side effects. tmp-isolated: zero
network, zero real push, zero real subprocess.
"""
from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import publish_site_local as psl  # noqa: E402

SHA_A = "a" * 40
SHA_B = "b" * 40

Runner = Callable[[list[str], Path | None, int | None], tuple[int, str, str]]


def _fake_runner(responses: list[tuple[str, tuple[int, str, str]]]) -> Runner:
    """Match injected commands by prefix; anything unexpected fails loudly."""

    def _run(cmd: list[str], cwd: Path | None, timeout: int | None) -> tuple[int, str, str]:
        key = " ".join(cmd)
        for prefix, response in responses:
            if key.startswith(prefix):
                return response
        return (1, "", f"fake runner: unexpected command: {key}")

    return _run


def _snapshot(root: Path) -> dict[str, int]:
    """Full recursive path+size map of a tree (files sized, dirs -1)."""
    out: dict[str, int] = {}
    for path in sorted(root.rglob("*")):
        rel = str(path.relative_to(root)).replace("\\", "/")
        out[rel] = path.stat().st_size if path.is_file() else -1
    return out


def _make_fixture(tmp_path: Path) -> Path:
    """Fake repo: web/out with .nojekyll + a gh-pages worktree with a marker."""
    root = tmp_path / "repo"
    (root / "web" / "out" / "_next").mkdir(parents=True)
    (root / "web" / "out" / "index.html").write_text("<html></html>", encoding="utf-8")
    (root / "web" / "out" / ".nojekyll").write_text("", encoding="utf-8")
    worktree = root / "data" / "ops" / "gh_pages_worktree"
    worktree.mkdir(parents=True)
    (worktree / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
    (worktree / "marker.txt").write_text("keep\n", encoding="utf-8")
    return root


def _happy_responses() -> list[tuple[str, tuple[int, str, str]]]:
    return [
        ("git diff", (0, "", "")),
        ("git ls-remote", (0, f"{SHA_A}\trefs/heads/gh-pages\n", "")),
        ("git rev-parse", (0, SHA_A + "\n", "")),
        ("node scripts/sitemap-parity.mjs", (0, "parity ok\n", "")),
    ]


def test_build_robocopy_cmd_shape() -> None:
    src = Path("w") / "out"
    dst = Path("d") / "wt"
    assert psl.build_robocopy_cmd(src, dst) == [
        "robocopy",
        str(src),
        str(dst),
        "/MIR",
        "/XF",
        ".git",
        ".nojekyll",
    ]


def test_build_rsync_cmd_shape() -> None:
    src = Path("w") / "out"
    dst = Path("d") / "wt"
    cmd = psl.build_rsync_cmd(src, dst)
    assert cmd[:7] == ["rsync", "-a", "--delete", "--exclude", ".git", "--exclude", ".nojekyll"]
    assert cmd[-2].endswith("/")
    assert cmd[-1].endswith("/")


def test_mirror_rc_ok_boundaries() -> None:
    for rc in (0, 1, 7):
        assert psl.mirror_rc_ok("robocopy", rc), f"robocopy rc={rc} must count as success"
    for rc in (8, 9, 16):
        assert not psl.mirror_rc_ok("robocopy", rc), f"robocopy rc={rc} must count as failure"
    assert psl.mirror_rc_ok("rsync", 0)
    for rc in (1, 23, 24):
        assert not psl.mirror_rc_ok("rsync", rc), f"rsync rc={rc} must count as failure"


def test_exit_code_mapping() -> None:
    assert psl.exit_code_for("precondition") == 3
    assert psl.exit_code_for("race") == 2
    for gate in ("build", "gate", "mirror", "commit", "push"):
        assert psl.exit_code_for(gate) == 1
    assert (psl.EXIT_OK, psl.EXIT_FAIL, psl.EXIT_RACE, psl.EXIT_PRECONDITION) == (0, 1, 2, 3)


def test_race_detected() -> None:
    assert not psl.race_detected(SHA_A, SHA_A)
    assert psl.race_detected(SHA_A, SHA_B)
    assert not psl.race_detected(None, SHA_B)  # missing remote ref = creation case, not a race


def test_build_commit_message() -> None:
    assert (
        psl.build_commit_message("abc1234abcd")
        == "deploy: main@abc1234 — site publish (local lane)"
    )


def test_dry_run_zero_side_effects(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    root = _make_fixture(tmp_path)
    before = _snapshot(root)
    rc = psl.main(["--dry-run"], repo_root=root, runner=_fake_runner(_happy_responses()))
    assert rc == psl.EXIT_OK
    assert _snapshot(root) == before, "--dry-run must not write anywhere under the repo root"
    text = capsys.readouterr().out
    assert "[dry-run]" in text
    assert "robocopy" in text or "rsync" in text
    assert "push origin gh-pages" in text


def test_precondition_refusal_rc3(tmp_path: Path) -> None:
    root = _make_fixture(tmp_path)
    before = _snapshot(root)
    responses = [("git diff", (0, " web/src/app.tsx\n", ""))]
    rc = psl.main([], repo_root=root, runner=_fake_runner(responses))
    assert rc == psl.EXIT_PRECONDITION == 3
    assert _snapshot(root) == before, "refusal must happen before any write step"


def test_race_abort_rc2_dry_run(tmp_path: Path) -> None:
    root = _make_fixture(tmp_path)
    before = _snapshot(root)
    responses = [
        ("git diff", (0, "", "")),
        ("git ls-remote", (0, f"{SHA_B}\trefs/heads/gh-pages\n", "")),
        ("git rev-parse", (0, SHA_A + "\n", "")),
        ("node scripts/sitemap-parity.mjs", (0, "parity ok\n", "")),
    ]
    rc = psl.main(["--dry-run"], repo_root=root, runner=_fake_runner(responses))
    assert rc == psl.EXIT_RACE == 2
    after = _snapshot(root)
    assert after == before, "race abort must not write; web/out must survive"
    assert "web/out/.nojekyll" in after


def test_missing_out_without_build_rc1(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    import shutil

    root = _make_fixture(tmp_path)
    shutil.rmtree(root / "web" / "out")
    responses = [("git diff", (0, "", ""))]
    rc = psl.main([], repo_root=root, runner=_fake_runner(responses))
    assert rc == psl.EXIT_FAIL == 1
    text = capsys.readouterr().out
    assert "--build" in text, "guidance must point at --build or a manual web/ build"
