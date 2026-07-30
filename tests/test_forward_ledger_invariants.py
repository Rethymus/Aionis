"""E3 Slice 1 - forward-ledger commit-reveal invariant tests (I1, I2, taxonomy, sha256).

TDD: these tests FAIL until ``src/aionis/reporting/forward_ledger.py`` exists and
enforces the per-prediction sha256-before-result anchor.

Scope (pre-reg ``docs/phase-e3-preregistration.md`` §9 + impl-plan §2 invariants):
  * I1 - commit-before-reveal: ``forward_outcome_scored`` is appended ONLY when a
    matching ``forward_prediction_committed`` exists AND wall-clock >= target_t.
  * I2 - immutability + idempotency: re-reveal is idempotent; mutated scores yield
    a different ``scores_sha256``; a sealed parquet is never silently overwritten.
  * Taxonomy + parsing: the §9 row schema + the per-ticker scores parquet layout
    under ``runs/forward/<config_sha256>/``.
  * I7 (ledger portion): same scores + config -> identical ``scores_sha256``.

Every fixture here is SYNTHETIC and labeled as such; every test writes to a temp
``runs_dir`` (``tmp_path``) and NEVER touches the real ``runs/ledger.jsonl``.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aionis.reporting import forward_ledger as FL

UTC = timezone.utc
PHASE = "E3"


# ---------------------------------------------------------------------------
# synthetic fixtures (labeled - no real data, no mock-data-in-real-path)
# ---------------------------------------------------------------------------


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _synth_scores(seed: int = 0, *, mutate: bool = False) -> pd.DataFrame:
    """SYNTHETIC per-ticker two-arm score panel: columns [ticker, arm, score]."""
    rng = np.random.default_rng(seed)
    tickers = ["AAA", "BBB", "CCC", "DDD", "EEE"]
    arms = ["arm_base", "arm_e13"]
    rows = [
        {"ticker": t, "arm": a, "score": float(rng.normal(0.0, 1.0))}
        for t in tickers
        for a in arms
    ]
    df = pd.DataFrame(rows)
    if mutate:
        # deliberate, unambiguous mutation of one score value
        df.loc[0, "score"] = df.loc[0, "score"] + 123.456
    return df


def _synth_config(provider: str = "glm") -> dict:
    """SYNTHETIC frozen-config stub (learner + provider + seed)."""
    return {
        "horizon_sessions": 21,
        "learner": "LightGBM",
        "provider": provider,
        "seed": 0,
    }


def _commit_one(
    tmp_path: Path,
    *,
    predict_ts: str,
    target_t: str,
    scores: pd.DataFrame | None = None,
    config: dict | None = None,
    provider: str = "glm",
) -> dict:
    return FL.commit_forward_prediction(
        predict_ts=predict_ts,
        target_t=target_t,
        scores=scores if scores is not None else _synth_scores(),
        config=config if config is not None else _synth_config(provider),
        iset_sha256="0" * 64,
        provider=provider,
        provider_cutoff="2024-01-01",
        runs_dir=tmp_path,
    )


def _ledger_rows(tmp_path: Path) -> list[dict]:
    ledger = tmp_path / "ledger.jsonl"
    if not ledger.exists():
        return []  # a refused reveal writes no ledger file (the no-commit case)
    return [json.loads(ln) for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]


# ---------------------------------------------------------------------------
# I1 - commit-before-reveal (the leakage gate)
# ---------------------------------------------------------------------------


def test_reveal_before_target_t_is_rejected(tmp_path: Path) -> None:
    """I1: reveal at now < target_t -> REJECTED, no scored row appended."""
    t0 = datetime(2026, 7, 31, 20, 0, tzinfo=UTC)
    target = t0 + timedelta(days=21)
    _commit_one(tmp_path, predict_ts=_iso(t0), target_t=_iso(target))

    res = FL.reveal_forward_outcome(
        _iso(target), 0.031, "arm_e13",
        predict_ts=_iso(t0),
        config_sha256=FL.config_sha256(_synth_config()),
        runs_dir=tmp_path,
        now=target - timedelta(days=1),  # BEFORE realization
    )
    assert res["revealed"] is False
    assert "before" in res["reason"].lower() or "target" in res["reason"].lower()
    # no forward_outcome_scored row was appended
    scored = [r for r in _ledger_rows(tmp_path) if r.get("event") == "forward_outcome_scored"]
    assert scored == []


def test_reveal_at_or_after_target_t_appends_scored_row(tmp_path: Path) -> None:
    """I1: reveal at now >= target_t WITH a prior commit -> exactly one scored row."""
    t0 = datetime(2026, 7, 31, 20, 0, tzinfo=UTC)
    target = t0 + timedelta(days=21)
    _commit_one(tmp_path, predict_ts=_iso(t0), target_t=_iso(target))

    res = FL.reveal_forward_outcome(
        _iso(target), 0.031, "arm_e13",
        predict_ts=_iso(t0),
        config_sha256=FL.config_sha256(_synth_config()),
        runs_dir=tmp_path,
        now=target,  # exactly at realization
    )
    assert res["revealed"] is True
    scored = [r for r in _ledger_rows(tmp_path) if r.get("event") == "forward_outcome_scored"]
    assert len(scored) == 1
    assert scored[0]["ic_point"] == pytest.approx(0.031)
    assert scored[0]["arm"] == "arm_e13"
    assert scored[0]["phase"] == PHASE


def test_reveal_without_prior_commit_is_rejected(tmp_path: Path) -> None:
    """I1: reveal with NO matching commit -> REJECTED (cannot reveal an unsealed pred)."""
    t0 = datetime(2026, 7, 31, 20, 0, tzinfo=UTC)
    target = t0 + timedelta(days=21)
    res = FL.reveal_forward_outcome(
        _iso(target), 0.04, "arm_base",
        predict_ts=_iso(t0),
        config_sha256=FL.config_sha256(_synth_config()),
        runs_dir=tmp_path,
        now=target + timedelta(days=5),  # wall-clock is fine, but no commit exists
    )
    assert res["revealed"] is False
    assert "commit" in res["reason"].lower()
    scored = [r for r in _ledger_rows(tmp_path) if r.get("event") == "forward_outcome_scored"]
    assert scored == []


def test_reveal_wrong_config_sha256_does_not_match_other_sequence(tmp_path: Path) -> None:
    """I1/I8: a commit under config A must not satisfy the reveal guard for config B."""
    t0 = datetime(2026, 7, 31, 20, 0, tzinfo=UTC)
    target = t0 + timedelta(days=21)
    _commit_one(tmp_path, predict_ts=_iso(t0), target_t=_iso(target))  # config = glm default

    other_cfg = _synth_config(provider="siliconflow")  # different provider -> different hash
    res = FL.reveal_forward_outcome(
        _iso(target), 0.02, "arm_e13",
        predict_ts=_iso(t0),
        config_sha256=FL.config_sha256(other_cfg),
        runs_dir=tmp_path,
        now=target,
    )
    assert res["revealed"] is False
    assert "commit" in res["reason"].lower()


# ---------------------------------------------------------------------------
# I2 - immutability + idempotency
# ---------------------------------------------------------------------------


def test_reveal_idempotent_no_duplicate_identical_ic(tmp_path: Path) -> None:
    """I2: re-running reveal for the same (predict_ts, arm) appends no duplicate."""
    t0 = datetime(2026, 6, 30, 20, 0, tzinfo=UTC)
    target = t0 + timedelta(days=21)
    csha = FL.config_sha256(_synth_config())
    _commit_one(tmp_path, predict_ts=_iso(t0), target_t=_iso(target))

    r1 = FL.reveal_forward_outcome(
        _iso(target), 0.0275, "arm_e13", predict_ts=_iso(t0),
        config_sha256=csha, runs_dir=tmp_path, now=target,
    )
    r2 = FL.reveal_forward_outcome(
        _iso(target), 0.0275, "arm_e13", predict_ts=_iso(t0),
        config_sha256=csha, runs_dir=tmp_path, now=target + timedelta(hours=1),
    )
    assert r1["revealed"] is True
    assert r2["revealed"] is True
    assert r2["ic_point"] == pytest.approx(r1["ic_point"])
    scored = [r for r in _ledger_rows(tmp_path) if r.get("event") == "forward_outcome_scored"]
    assert len(scored) == 1  # no duplicate appended


def test_reveal_per_arm_independent(tmp_path: Path) -> None:
    """I2: arm_base and arm_e13 are independent scored rows for one prediction."""
    t0 = datetime(2026, 6, 30, 20, 0, tzinfo=UTC)
    target = t0 + timedelta(days=21)
    csha = FL.config_sha256(_synth_config())
    _commit_one(tmp_path, predict_ts=_iso(t0), target_t=_iso(target))

    FL.reveal_forward_outcome(
        _iso(target), 0.01, "arm_base", predict_ts=_iso(t0),
        config_sha256=csha, runs_dir=tmp_path, now=target,
    )
    FL.reveal_forward_outcome(
        _iso(target), 0.03, "arm_e13", predict_ts=_iso(t0),
        config_sha256=csha, runs_dir=tmp_path, now=target,
    )
    scored = [r for r in _ledger_rows(tmp_path) if r.get("event") == "forward_outcome_scored"]
    assert len(scored) == 2
    arms = {r["arm"] for r in scored}
    assert arms == {"arm_base", "arm_e13"}


def test_mutated_scores_yield_different_scores_sha256(tmp_path: Path) -> None:
    """I2: mutation is detectable - differing score vectors -> differing scores_sha256."""
    t0a = datetime(2026, 6, 30, 20, 0, tzinfo=UTC)
    t0b = datetime(2026, 7, 31, 20, 0, tzinfo=UTC)
    ra = _commit_one(tmp_path, predict_ts=_iso(t0a), target_t=_iso(t0a + timedelta(days=21)),
                     scores=_synth_scores(seed=0))
    rb = _commit_one(tmp_path, predict_ts=_iso(t0b), target_t=_iso(t0b + timedelta(days=21)),
                     scores=_synth_scores(seed=0, mutate=True))  # same seed, mutated
    assert ra["scores_sha256"] != rb["scores_sha256"]


def test_committed_parquet_not_silently_overwritten_on_mutation(tmp_path: Path) -> None:
    """I2: re-committing the SAME predict_ts with MUTATED scores is refused; file untouched."""
    t0 = datetime(2026, 7, 31, 20, 0, tzinfo=UTC)
    target = t0 + timedelta(days=21)
    original = _commit_one(
        tmp_path, predict_ts=_iso(t0), target_t=_iso(target),
        scores=_synth_scores(seed=1),
    )
    fname = original["scores_path"].split("/")[-1]
    parquet_path = tmp_path / "forward" / original["config_sha256"] / fname
    assert parquet_path.exists()
    original_bytes = parquet_path.read_bytes()

    # re-commit with MUTATED scores at the same predict_ts -> must refuse, not overwrite
    res = FL.commit_forward_prediction(
        predict_ts=_iso(t0), target_t=_iso(target),
        scores=_synth_scores(seed=1, mutate=True),
        config=_synth_config(), iset_sha256="0" * 64,
        provider="glm", provider_cutoff="2024-01-01",
        runs_dir=tmp_path,
    )
    assert res["committed"] is False
    assert "mutation" in res["reason"].lower() or "sealed" in res["reason"].lower()
    # the sealed artifact is byte-identical to the original
    assert parquet_path.read_bytes() == original_bytes
    # no second commit row appended
    commits = [r for r in _ledger_rows(tmp_path) if r.get("event") == "forward_prediction_committed"
               and r.get("predict_ts") == _iso(t0)]
    assert len(commits) == 1


def test_recommit_identical_scores_is_idempotent(tmp_path: Path) -> None:
    """I2/H6: re-committing byte-identical scores is a no-op (no dup row, file unchanged)."""
    t0 = datetime(2026, 7, 31, 20, 0, tzinfo=UTC)
    target = t0 + timedelta(days=21)
    first = _commit_one(tmp_path, predict_ts=_iso(t0), target_t=_iso(target),
                        scores=_synth_scores(seed=2))
    fname = first["scores_path"].split("/")[-1]
    parquet_path = tmp_path / "forward" / first["config_sha256"] / fname
    before = parquet_path.read_bytes()

    second = FL.commit_forward_prediction(
        predict_ts=_iso(t0), target_t=_iso(target),
        scores=_synth_scores(seed=2),  # identical
        config=_synth_config(), iset_sha256="0" * 64,
        provider="glm", provider_cutoff="2024-01-01",
        runs_dir=tmp_path,
    )
    assert second["committed"] is True
    assert second["scores_sha256"] == first["scores_sha256"]
    assert parquet_path.read_bytes() == before  # not rewritten
    commits = [r for r in _ledger_rows(tmp_path) if r.get("event") == "forward_prediction_committed"
               and r.get("predict_ts") == _iso(t0)]
    assert len(commits) == 1  # no duplicate commit row


# ---------------------------------------------------------------------------
# Row taxonomy + scores-parquet layout + parsing
# ---------------------------------------------------------------------------


def test_commit_appends_forward_prediction_committed_with_section9_schema(tmp_path: Path) -> None:
    """Taxonomy: commit appends exactly one forward_prediction_committed row with §9 fields."""
    t0 = datetime(2026, 7, 31, 20, 0, tzinfo=UTC)
    target = t0 + timedelta(days=21)
    row = _commit_one(tmp_path, predict_ts=_iso(t0), target_t=_iso(target))

    assert row["event"] == "forward_prediction_committed"
    assert row["phase"] == PHASE
    # §9 schema (predict_ts, target_t, config_sha256, iset_sha256, scores_sha256)
    # + impl-plan §1.1 (provider, provider_cutoff)
    for field in ("predict_ts", "target_t", "config_sha256", "iset_sha256",
                  "scores_sha256", "provider", "provider_cutoff"):
        assert field in row and row[field], f"missing/empty §9 field: {field}"
    assert row["predict_ts"] == _iso(t0)
    assert row["target_t"] == _iso(target)
    assert row["provider"] == "glm"
    assert row["provider_cutoff"] == "2024-01-01"
    # exactly one commit row total
    commits = [
        r for r in _ledger_rows(tmp_path)
        if r.get("event") == "forward_prediction_committed"
    ]
    assert len(commits) == 1


def test_scores_parquet_under_forward_dir_not_inlined(tmp_path: Path) -> None:
    """Layout: scores go to runs/forward/<config_sha256>/scores_<ts>.parquet, NOT in JSONL."""
    t0 = datetime(2026, 7, 31, 20, 0, tzinfo=UTC)
    target = t0 + timedelta(days=21)
    scores = _synth_scores(seed=3)
    row = _commit_one(tmp_path, predict_ts=_iso(t0), target_t=_iso(target), scores=scores)

    csha = row["config_sha256"]
    fwd_dir = tmp_path / "forward" / csha
    assert fwd_dir.is_dir()
    # exactly one scores_*.parquet artifact under the per-sig dir
    parquets = sorted(fwd_dir.glob("scores_*.parquet"))
    assert len(parquets) == 1
    # the row references it via scores_path
    assert row["scores_path"].endswith(parquets[0].name)
    assert csha in row["scores_path"]
    # the per-ticker score vector is NOT inlined into the JSONL row
    assert "scores" not in row  # no inline score payload
    # and the parquet round-trips the panel (ticker, arm, score)
    df = pd.read_parquet(parquets[0])
    assert set(df.columns) >= {"ticker", "arm", "score"}
    assert len(df) == len(scores)


def test_read_forward_rows_parses_commit_and_scored(tmp_path: Path) -> None:
    """Parsing: read_forward_rows returns forward_* rows, filtered from the heterogeneous ledger."""
    t0 = datetime(2026, 5, 29, 20, 0, tzinfo=UTC)
    target = t0 + timedelta(days=21)
    csha = FL.config_sha256(_synth_config())
    _commit_one(tmp_path, predict_ts=_iso(t0), target_t=_iso(target))
    # also seed a heterogeneous non-forward row to prove filtering
    other = {"ts": _iso(t0), "event": "config_committed", "phase": "B", "config_sig": "deadbeef"}
    (tmp_path / "ledger.jsonl").open("a").write(json.dumps(other) + "\n")
    FL.reveal_forward_outcome(
        _iso(target), 0.022, "arm_e13", predict_ts=_iso(t0),
        config_sha256=csha, runs_dir=tmp_path, now=target,
    )

    rows = FL.read_forward_rows(runs_dir=tmp_path)
    events = [r["event"] for r in rows]
    assert "forward_prediction_committed" in events
    assert "forward_outcome_scored" in events
    assert all(r.get("phase") == PHASE for r in rows)  # no non-forward row leaked in
    # config_sha256 filter narrows to one sequence
    only_cfg = FL.read_forward_rows(runs_dir=tmp_path, config_sha256=csha)
    assert len(only_cfg) == 2
    assert all(r["config_sha256"] == csha for r in only_cfg)


# ---------------------------------------------------------------------------
# I7 (ledger portion) - sha256 determinism
# ---------------------------------------------------------------------------


def test_identical_scores_and_config_yield_identical_scores_sha256(tmp_path: Path) -> None:
    """I7: same scores + same config -> identical scores_sha256 (H6 determinism, ledger portion)."""
    cfg = _synth_config()
    scores = _synth_scores(seed=7)
    t0a = datetime(2026, 6, 30, 20, 0, tzinfo=UTC)
    t0b = datetime(2026, 7, 31, 20, 0, tzinfo=UTC)
    ra = _commit_one(tmp_path, predict_ts=_iso(t0a), target_t=_iso(t0a + timedelta(days=21)),
                     scores=scores, config=cfg)
    rb = _commit_one(tmp_path, predict_ts=_iso(t0b), target_t=_iso(t0b + timedelta(days=21)),
                     scores=scores.copy(), config=cfg.copy())
    assert ra["scores_sha256"] == rb["scores_sha256"]
    # config_sha256 is also stable for identical configs (the sequence key)
    assert ra["config_sha256"] == rb["config_sha256"]


def test_forward_rows_never_touch_real_ledger(tmp_path: Path) -> None:
    """Anti-leakage hygiene: the real runs/ledger.jsonl is unchanged by these ops."""
    real_ledger = Path(__file__).resolve().parents[1] / "runs" / "ledger.jsonl"
    before = real_ledger.read_bytes() if real_ledger.exists() else b""
    t0 = datetime(2026, 7, 31, 20, 0, tzinfo=UTC)
    _commit_one(tmp_path, predict_ts=_iso(t0), target_t=_iso(t0 + timedelta(days=21)))
    FL.reveal_forward_outcome(
        _iso(t0 + timedelta(days=21)), 0.01, "arm_e13",
        predict_ts=_iso(t0), config_sha256=FL.config_sha256(_synth_config()),
        runs_dir=tmp_path, now=datetime.now(tz=UTC),
    )
    after = real_ledger.read_bytes() if real_ledger.exists() else b""
    assert before == after


# ---------------------------------------------------------------------------
# Review polish - canonical timestamp key (finding 1: no parquet-path collision)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("variant", [
    "2026-07-31T20:00:00+00:00",
    "2026-07-31T20:00:00+0000",   # colon-less offset
    "2026-07-31T20:00:00Z",        # Zulu
    "2026-07-31T15:00:00-05:00",   # same instant, other zone
])
def test_canonical_ts_collapses_equivalent_timestamp_forms(variant: str) -> None:
    """Finding 1: differently-spelled equivalent timestamps -> one canonical key."""
    assert FL._canonical_ts(variant) == "2026-07-31T20:00:00+00:00"


def test_commit_with_format_variant_predict_ts_is_idempotent_not_mutation(
    tmp_path: Path,
) -> None:
    """Finding 1: re-commit with an equivalent-but-differently-spelled predict_ts
    resolves to the SAME parquet path -> idempotent, NOT a spurious mutation-refusal."""
    target = datetime(2026, 8, 21, 20, 0, tzinfo=UTC)
    scores = _synth_scores(seed=5)
    cfg = _synth_config()
    first = _commit_one(
        tmp_path, predict_ts="2026-07-31T20:00:00+00:00",
        target_t=_iso(target), scores=scores, config=cfg,
    )
    assert first["committed"] is True

    # same instant, different spelling (+0000) -> must be idempotent, not a refusal
    second = FL.commit_forward_prediction(
        predict_ts="2026-07-31T20:00:00+0000", target_t=_iso(target),
        scores=scores.copy(), config=cfg, iset_sha256="0" * 64,
        provider="glm", provider_cutoff="2024-01-01", runs_dir=tmp_path,
    )
    assert second["committed"] is True
    assert second.get("_appended") is False           # no duplicate commit row
    assert second["scores_sha256"] == first["scores_sha256"]
    # the canonical form is what landed in the (single) ledger row
    commits = [
        r for r in _ledger_rows(tmp_path)
        if r.get("event") == "forward_prediction_committed"
    ]
    assert len(commits) == 1
    assert commits[0]["predict_ts"] == "2026-07-31T20:00:00+00:00"


def test_reveal_with_format_variant_predict_ts_finds_its_commit(tmp_path: Path) -> None:
    """Finding 1: reveal accepts an equivalent-but-differently-spelled predict_ts and
    still matches the committed prediction (lookup keys are canonicalized both sides)."""
    target = datetime(2026, 8, 21, 20, 0, tzinfo=UTC)
    csha = FL.config_sha256(_synth_config())
    _commit_one(
        tmp_path, predict_ts="2026-07-31T20:00:00+00:00", target_t=_iso(target),
    )
    res = FL.reveal_forward_outcome(
        _iso(target), 0.018, "arm_e13",
        predict_ts="2026-07-31T20:00:00Z",  # Zulu form, same instant
        config_sha256=csha, runs_dir=tmp_path, now=target,
    )
    assert res["revealed"] is True


# ---------------------------------------------------------------------------
# Review polish - _normalize_scores defensive guards (finding 5)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("bad_scores", "expected", "match"),
    [
        pytest.param(
            [("AAA", "arm_base", 0.1)],
            TypeError, "pandas DataFrame",
            id="non-dataframe-list",
        ),
        pytest.param(
            pd.DataFrame({"ticker": ["AAA"], "score": [0.1]}),
            ValueError, "missing required column",
            id="missing-arm-column",
        ),
        pytest.param(
            pd.DataFrame(columns=["ticker", "arm", "score"]),
            ValueError, "empty",
            id="empty-dataframe",
        ),
    ],
)
def test_normalize_scores_defensive_guards(bad_scores, expected, match) -> None:
    """Finding 5: _normalize_scores rejects malformed input at the boundary
    (TypeError for non-DataFrame; ValueError for missing columns / empty frame)."""
    with pytest.raises(expected, match=match):
        FL._normalize_scores(bad_scores)
