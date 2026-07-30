# Risks & mitigations

> The failure modes that would invalidate a result, and how each is bounded.

- **Look-ahead / PIT leakage.** Fundamentals keyed by `filed` date; macro via
  ALFRED as-of vintages; VIXCLS unrevised (PIT via the no-revision contract, G3 —
  not vintage tracking); S&P 500 membership via PIT `constituents_on`.
- **LLM-hindsight leakage (E2).** Cutoff control *mitigates, does not eliminate*
  memorization; the E2 backtest is underpowered post-cutoff. E3 forward-live is
  zero-leak by construction (no future to leak).
- **Selection / survivorship bias.** PIT membership mask; survivorship is an
  irreducible scope limit, not a bias (same set on both arms) — the headline is a
  conservative upper bound.
- **Multiple testing.** Project-family deflation: DSR, Hansen-SPA, Harvey-Liu
  haircut. No strategy survives the n_trials=20 conservative family.
- **Statistical power.** E2 is underpowered (~10-18 post-cutoff months); E3
  requires calendar time (years) to power up.
- **Rate-limiting / politeness.** Data sources are throttled per the 7-gate G7.

## See also

- data-intake-rubric.md
- frontier_positioning.md
- phase-e2-preregistration.md
- phase-e3-preregistration.md
