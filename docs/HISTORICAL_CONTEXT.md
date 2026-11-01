# Historical player context (offline research)

This feature analyzes **completed game observations** from a legally
permitted local CSV. It is not a live NBA API connection and does not produce
future-game forecasts, a proposed-stat-target probability, gambling odds,
or event-selection instructions.

## Running the demonstration

From the SportProb repository root:

```bash
PYTHONPATH=src python3.12 -m sportprob.cli history \
  --data data/demo_games.csv \
  --manifest data/demo_games.manifest.json \
  --player DEMO-001 --stat points \
  --as-of 2025-11-21 --history-games 20
```

The `--as-of` date is **exclusive**. Same-day and later game logs must not
enter the analysis. The output includes a source ID, declared synthetic status,
SHA-256, and a warning that neither source authenticity nor research rights
are independently verified by the application.

## Interpretation

- Last five and preceding five: averages of **observed** games only.
- Percentiles: nearest-rank 10th and 90th of observed outcomes; they are
  **not prediction intervals**.
- Per-36-minute production: total observed counts divided by total played
  minutes, multiplied by 36. It is descriptive, not an estimate of playing
  time in a future game.
- Home/away: descriptive observed splits, with number of games.
- Opponents: only groups of at least three historical games. Opponent
  observations are not causal matchup effects.
- Missing optional home/away data is reported as missing rather than
  inferred.

One or two recent games cannot establish a reliable trend. Neither the
included **synthetic** data nor the successful unit tests establish
predictive accuracy on authentic NBA games.

## Research pipeline prerequisites

Use only a dataset whose original terms allow your intended analysis.
See `docs/REAL_DATA_PIPELINE.md` to normalize local authorized records, 
verify checksum and source declaration, assess structural data quality, and
run independent holdout diagnostics. Neither the Python repository nor a
source declaration grants rights to third-party datasets.
