# Architecture and boundaries

## Research purpose
Create **reproducible distributions** for player performance, not point-score certainty. This initial repository deliberately excludes real-money sports betting and financial decisions.

## Flow
1. **Acquire:** Accept CSV data only from sources with appropriate rights and terms.
2. **Validate:** Enforce typed rows, nonnegative counts, plausible minutes and unique game IDs.
3. **Freeze:** Use the historical state known *strictly before* an as-of game date.
4. **Fit:** Learn per-minute stat rates using Gamma–Poisson conjugacy.
5. **Predict:** Use a moment-matched Negative Binomial distribution that includes a provisional game-to-game dispersion factor.
6. **Aggregate:** Report equal-width non-overlapping count buckets and central prediction intervals.
7. **Evaluate:** Walk-forward backtests on games held out chronologically with coverage, width and log likelihood.
8. **Expose:** CLI JSON now; later add a human-reviewed research dashboard.

## Data contracts
`game_id,player_id,game_date,opponent,home,minutes,points,rebounds,assists`

- `game_date`: ISO 8601 calendar date, game-local as supplied by the source.
- `home`: true/false if supplied; empty means unknown.
- `minutes`: finite number in [0,80]. A zero-minute entry may record DNP; it does not update a per-minute stat rate.
- Counts: nonnegative integers. Synthetic fixture is not suitable as a real-world benchmark.
- `game_id`: unique per player per observation, allows future doubleheaders.
- All real ingestion must also save source URL/license, `retrieved_at`, original payload and event-time availability. CSV v1 does not yet retain that provenance; do not treat it as production-grade.

## Model
Per-minute intensity `lambda` has Gamma(shape=a, rate=b) prior. Played games with count y and minutes m contribute to shape and rate: `a_post = a + sum(y)`, `b_post = b + sum(m)`. Expected count for forecast minutes M is `M * a_post/b_post`.

The predictive Negative Binomial is **moment-matched**, accounting for both posterior uncertainty and provisional independent game-to-game intensity variation. Its dispersion is *not learned* at this stage. The model ignores opponent, injury, pace and rest context. Therefore, performance intervals are research prototypes, not calibrated probability claims.

## Guardrails
- No sportsbook APIs or odds/edge logic.
- No bet rankings, automatic wagering, staking or money tracking.
- No site bypassing, unlicensed collection or private data.
- Read-only inputs; no hosted mutations or deployment.
- No LLM-generated numeric game statistics: agents later may extract candidate records, but source reconciliation and validation gate model entry.
- No claim of accuracy without strictly out-of-sample evaluation.

## Next milestones
1. Introduce versioned ingestors and immutable raw snapshots with provenance.
2. Implement rolling-opportunity, minutes/role, home/away, opponent and schedule features.
3. Learn dispersion from training sets and compare against empirical and hurdle models.
4. Calibrate intervals on an untouched chronological evaluation period.
5. Build a dashboard displaying uncertainty, historical forecast-versus-actual and model monitoring.
