# SportProb — Player Performance Probability Lab

A **simulation-only sports statistics research platform**. SportProb estimates probability distributions and prediction intervals for NBA player points, rebounds, and assists. It evaluates whether those forecasts are reliable using chronological backtests.

**Research only:** No live betting, sportsbook data ingestion, odds comparison, wager recommendations, or bankroll calculations. All bundled observations are explicitly **synthetic**, not real player data.

## Performance Desk (mobile-first offline interface)

The redesigned dashboard is in `mobile/index.html`, with local `mobile/app.js` and `mobile/styles.css`. Open it directly in Safari or serve it locally with a static file server; it makes no web requests.

The historical statistics importer now accepts either the research engine's `player_id,game_date,points,rebounds,assists` CSV or common `player_name,game_date,pts,reb,ast` aliases. Optional `min`, `opponent_team`, `home_away` and `game_id` fields drive observed splits and the game log. Users declare a source and usage permission before selecting an import. See [historical data import guide](docs/IMPORTING_DATA.md) and the explicitly synthetic [example template](data/IMPORT_TEMPLATE.csv).

The interface reports actual loaded rows only: last-5/10/20/all, averages, medians, observed ranges, sample deviation, trailing five-game average, optional home/away splits, and a historical game table. Missing context remains unavailable. The static browser interface does not automatically acquire NBA game logs, store uploads in a server, run the CLI forecasting engine, or integrate a gambling platform. It does not establish dataset authenticity, rights or predictive accuracy.

Check the browser parser and static assets with `node --test tests/mobile-ui.test.cjs` (Node 22+). Full regression suite: `PYTHONPATH=src python3 -m unittest discover -s tests -v` (Python 3.11+).

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


## Offline visual dashboard (no live services)

From the repository root, generate a standalone HTML report from the **checksum-verified synthetic sample**:

```powershell
$env:PYTHONPATH = "src"
python -m sportprob.cli report --data data/demo_games.csv --manifest data/demo_games.manifest.json --player DEMO-001 --stat points --as-of 2025-11-21 --output outputs/demo-points.html
```

Then open `outputs/demo-points.html` in your browser. The report shows the expected count, 80%/90% central model intervals, most probable fixed-width bucket, a probability distribution table/bar chart, and the dataset provenance. It needs **no server, dependencies, external scripts, API key, network access, or account**. Use `--overwrite` only when you deliberately want to replace your previous generated report. Change `--stat` to `rebounds` or `assists` for a different research view.

The CSV and manifest remain on your computer. A matching SHA-256 checks local file integrity but does **not** prove licensed data or statistical accuracy. For an independent research dataset, supply your own authorized CSV and corresponding explicitly documented manifest; the tooling does not acquire real NBA data. Synthetic demonstration metrics are not suitable for predictive claims. No sportsbook or wager functions are provided.

## Frozen historical holdout (research-only)

The ordinary `backtest` is a sequential walk-forward diagnostic, not a completely untouched test set. For a separate, **frozen holdout** check, choose a cutoff before inspecting the outcomes and run the checksum-gated evaluator:

```bash
PYTHONPATH=src python -m sportprob.cli holdout \
  --data data/demo_games.csv \
  --manifest data/demo_games.manifest.json \
  --player DEMO-001 --stat points --start 2025-11-16
```

The frozen report uses *only* played games strictly before the cutoff for **every** held-out prediction, without learning from any game on or after the cutoff. It reports observation counts, negative log likelihood, 80%/90% interval coverage and average widths. It checks declared research rights and file SHA-256, but does not independently establish licensing or data authenticity. The synthetic five-game holdout is a regression demonstration, **not evidence of NBA forecasting accuracy**, and repeated experiments on its labels invalidate its status as untouched.

No data acquisition, sportsbook interface, picks, payment processing, or wagering calculations are included.

## Offline player-history readiness audit

Before interpreting any forecast from an independently supplied, authorized dataset, check the manifest, checksum and per-player observation quality:

```bash
PYTHONPATH=src python -m sportprob.coverage \
  --data data/demo_games.csv \
  --manifest data/demo_games.manifest.json \
  --player DEMO-001 --minimum-games 30
```

This research diagnostic explicitly labels the bundled fixture `DEMONSTRATION_ONLY`, reports inadequate history or missing home/away flags, and never certifies model accuracy. A structurally clean real-data dataset still requires verified source rights, frozen point-in-time splits, independently measured forecast calibration, and appropriate interpretation. No sportsbook interfaces, wagers, or guaranteed income are included.

Run the full regression suite with `PYTHONPATH=src python -m unittest discover -s tests -v`.
