# SportProb — Player Performance Probability Lab

A **simulation-only sports statistics research platform**. SportProb estimates probability distributions and prediction intervals for NBA player points, rebounds, and assists. It evaluates whether those forecasts are reliable using chronological backtests.

**Research only:** No live betting, sportsbook data ingestion, odds comparison, wager recommendations, or bankroll calculations. All bundled observations are explicitly **synthetic**, not real player data.

## Phase 1 capabilities
- Typed, validated CSV game-log ingestion (date, player, opponent, minutes, points/rebounds/assists).
- Point-in-time forecasting: never trains on games dated on or after the forecast date.
- Exposure-adjusted Gamma–Poisson model with a conservative Negative Binomial predictive approximation for game-level dispersion.
- Probabilities for **fixed-width, non-overlapping performance buckets**; most probable bucket; central prediction intervals.
- Rolling out-of-sample backtest: negative log likelihood, empirical interval coverage, and average interval width.
- Local CLI, synthetic fixture, standard-library unit tests, and least-privilege CI.

## Quick start
Requires Python 3.11+; no runtime dependencies.

```bash
# From repo root (Mac/Linux)
PYTHONPATH=src python -m sportprob.cli forecast --data data/demo_games.csv --player DEMO-001 --stat points --as-of 2025-11-19
PYTHONPATH=src python -m sportprob.cli backtest --data data/demo_games.csv --player DEMO-001 --stat points

# From repo root (PowerShell)
$env:PYTHONPATH = "src"
python -m sportprob.cli forecast --data data/demo_games.csv --player DEMO-001 --stat rebounds --as-of 2025-11-19
python -m unittest discover -s tests -v
```

For editable installation:
```bash
python -m pip install -e .
python -m sportprob.cli --help
```

## Accuracy and interpretation
A single most-likely 5-point bucket might have only 30% probability. A wider 80% interval is a **model-based prediction interval**, not a guarantee. In particular, the v1 dispersion values are research defaults and **not fitted or calibrated against actual NBA game data**. Run walk-forward backtests on licensed/authorized real data before interpreting any reliability claim. Compare forecasts produced before each event to later observations; do not permit revisions or post-game knowledge to leak into historic features.

See [architecture](docs/ARCHITECTURE.md). Proposed changes are kept on a feature branch for review; no deployment is configured.
