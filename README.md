# SportProb — Player Performance Probability Lab

A **simulation-only sports statistics research platform**. SportProb estimates probability distributions and prediction intervals for NBA player points, rebounds, and assists. It evaluates whether those forecasts are reliable using chronological backtests.

**Research only:** No live betting, sportsbook data ingestion, odds comparison, wager recommendations, or bankroll calculations. All bundled observations are explicitly **synthetic**, not real player data.

## Hosted research-data catalog (static, read-only)

The GitHub Pages Performance Desk now includes a **Data Source Manager** for reviewed public historical CSV snapshots hosted on the **same site**. The initial catalog intentionally contains only 20 fictional example games, with a SHA-256 checksum, record count, source attribution, and source snapshot date. Select **Load hosted history** after confirming Dataset control research permissions; the app validates the CSV before displaying descriptive histories. Local CSV uploads and manual entry remain available. This is **not** an automatic NBA data feed or server-side database; no unreviewed real-world sports data is included.

See [Hosted Source Manager security, source review, and publishing details](docs/HOSTED_SOURCE_MANAGER.md).

## Hosted dashboard verification

The Pages workflow now includes a post-deployment HTTP smoke test to check that the real site and its required JavaScript/CSS files load, and that only an authored synthetic demonstration CSV is publicly available. The frontend also provides an on-page **Download synthetic demo CSV** link to help verify the import and Instant stats workflow on a phone. These checks do not independently verify the real-world accuracy or licensing of imported user datasets.

See [GitHub Pages setup, hosted smoke test and synthetic phone acceptance](docs/GITHUB_PAGES_HOSTING.md). A live URL is **not confirmed** until the repository's Pages source has been enabled and the deployment job has succeeded.

## GitHub Pages static hosting setup

A GitHub Pages workflow in `.github/workflows/pages.yml` can serve the browser-only `mobile/` directory after a repository administrator enables **Settings → Pages → Source: GitHub Actions**. The workflow publishes on qualifying `main` changes and exposes the final URL in the `github-pages` environment. Until a successful deployment is verified, **do not treat the application as publicly hosted**.

[Enable Pages and run the phone acceptance checklist](docs/GITHUB_PAGES_HOSTING.md).

## Manual completed-game entry (phone-first)

The Performance Desk now supports entering completed-game observations individually in the **Enter game logs** panel. Add player/date/minutes/points/rebounds/assists records, declare the source and research permissions in Dataset control, then use **Analyze draft** to run the exact same validated CSV import path. **Export CSV** preserves the draft to a file; no browser storage, account, or network transfer is involved. Closing or reloading the page clears unexported entries.

This is descriptive educational sports research. It does not use bookmaker odds or provide wagering tools. [Step-by-step phone manual entry instructions](docs/MANUAL_GAME_ENTRY.md).

## Instant browser statistics (no Python command)

The Performance Desk now has an **Instant stats** section for local, completed-game research. Import an authorized CSV once under Dataset control, then choose a player, inclusive historical cutoff, and last 5/10/20/all played games. The browser calculates means, medians, sample standard deviations, observed percentile ranges, recent-five comparisons, and per-36-minute rates when no minutes are missing. No JSON generation, network request, or database is required.

The older **Manual research** section remains available for checksum-gated Python JSON reports and is distinct from this browser-only path. The project is not publicly hosted by these changes, and physical iPhone Safari testing and independent real-data acceptance are not yet verified.

[Instant offline browser walkthrough](docs/IN_BROWSER_RESEARCH.md).

## Manual statistics research workflow (offline)

The [manual completed-game research guide](docs/MANUAL_STATISTICS_RESEARCH.md) is the dedicated workflow for local CSV entry, source-rights/checksum verification, chronological historical summaries, and quality checks. It reuses the existing canonical game-log importer and avoids another conflicting data pipeline.

```bash
PYTHONPATH=src python3 -m sportprob.manual_research --data data/demo_games.csv --manifest data/demo_games.manifest.json --as-of 2025-11-21 --output outputs/manual-research-demo.json
```

This example is synthetic and reports historical descriptive statistics only. The command does **not** import bookmaker lines, rank wagers, estimate gambling returns, or write data to any remote server. The mobile **Manual research** panel can import the generated JSON after the corresponding CSV has been loaded under Dataset control. Its local SHA-256 and row-count checks must match before showing a selected player's completed-game statistics. This remains historical research, not a future-event forecast.

## Performance Desk (mobile-first offline interface)

The redesigned dashboard is in `mobile/index.html`, with local `mobile/app.js` and `mobile/styles.css`. Open it directly in Safari or serve it locally with a static file server; it makes no web requests.

The historical statistics importer now accepts either the research engine's `player_id,game_date,points,rebounds,assists` CSV or common `player_name,game_date,pts,reb,ast` aliases. Optional `min`, `opponent_team`, `home_away` and `game_id` fields drive observed splits and the game log. Users declare a source and usage permission before selecting an import. See [historical data import guide](docs/IMPORTING_DATA.md) and the explicitly synthetic [example template](data/IMPORT_TEMPLATE.csv).

The interface reports actual loaded rows only: last-5/10/20/all, averages, medians, observed ranges, sample deviation, trailing five-game average, optional home/away splits, and a historical game table. Missing context remains unavailable. The static browser interface does not automatically acquire NBA game logs, store uploads in a server, run the CLI forecasting engine, or integrate a gambling platform. It does not establish dataset authenticity, rights or predictive accuracy.

Check the browser parser and static assets with `node --test tests/mobile-ui.test.cjs` (Node 22+). Full regression suite: `PYTHONPATH=src python3 -m unittest discover -s tests -v` (Python 3.11+).

## Historical multi-player comparison (offline)

The Performance Desk now includes **Player comparison** in the sidebar. Import one permitted completed-game CSV with multiple players, then choose **last 5, 10, 20 or all** observations for each player. The view displays the player's latest completed game and their **historical** points, rebounds and assists means with sample counts. Windows are **independent per player**, not matched by date or opponent. The comparison is descriptive, never a predicted next-game outcome or a wagering recommendation. It does not make network requests or retain records outside the current browser session. The comparison table displays up to 100 player summaries; the dataset's other features still process the entire permitted import.

## Checksum-gated multi-player historical evaluation

The offline cohort audit evaluates **previously completed** game logs for every player in an authorized, checksum-matched dataset. It reports training/holdout sample coverage, missing context, and frozen historical Negative Binomial vs same-mean Poisson diagnostics for points, rebounds, and assists when there are enough observations.

```bash
PYTHONPATH=src python3 -m sportprob.cohort_audit --data data/demo_games.csv --manifest data/demo_games.manifest.json --holdout-start 2025-11-16
```

The bundled example is synthetic; the five-game held-out sample demonstrates software behavior, not accuracy. The cutoff must be chosen **before** inspecting held-out outcomes for credible independent evaluation; code cannot prove that it was. Source permissions are user-declared and not independently verified. No live game ingestion, forecasts for upcoming events, wagering suggestions, server, or external requests are introduced.

The CI browser acceptance now serves and exercises `player-comparison.js` with two constructed players, checks sample-window changes, and verifies that earlier audit reports remain invalidated after a different file import. Real local history still requires a device-side check.

## Phase 5 — Report integration and local automation

The mobile Performance Desk now includes a **Research report** section.
Import the JSON produced by `sportprob.season_report` alongside the
corresponding game-log CSV. The interface displays period and season metrics
only after the browser matches the report to the **exact CSV SHA-256 bytes,
ESPN player ID, and selected game count**. Replacing the dataset instantly
hides mismatched report statistics, and displays the local missing-data
summary. No external data is sent.

The existing Python generator also supports `--auto-splits` for fixed
retrospective 65/15/20 calendar-safe partitions and `--output-stem` to
write both local HTML and JSON reports with one command. Existing explicit
cutoff and output arguments remain supported.

[Phase 5 Mac usage](docs/CONSOLIDATED_HISTORY_REPORT.md). Automated checks
cover Python 3.11–3.13, browser file import, malformed report rejection,
source mismatch, and replacement behavior. No real third-party game records
are committed to the repo; the data rights and future forecasting remain
independently unverified.

## Local consolidated historical performance report

Use `python -m sportprob.season_report` to produce a standalone offline HTML
and JSON research report from a user-supplied regular-season browser CSV.
It combines points, rebounds, assists, minutes, 3 chronological periods,
season-to-season changes, venue splits, last-five history, and exact
cross-checks to local SportsDataverse source-game IDs and DNP metadata.

No network requests or dataset uploads occur. **Source rights remain
unverified; the summary is retrospective, not calibrated forecasting.**

[Mac one-command walkthrough](docs/CONSOLIDATED_HISTORY_REPORT.md).

## Two-season historical research preparation and partitions

A local converter can bridge the browser-exported ESPN historical game rows
to the strict Python research schema without altering or redistributing the
source CSV. A deterministic date-safe 65/15/20 partition report then checks
how much observational coverage is available for retrospective evaluation.
No genuine prospective blind accuracy claim is made, because these game
outcomes have already been viewed.

The bridge records an explicit, user-supplied source-permission declaration;
SportProb **cannot independently clear upstream ESPN rights**. Do not
attest to permissions unless you have confirmed them.

See [Two-season retrospective validation](docs/TWO_SEASON_EVALUATION.md).

## Free SportsDataverse player history (manual, offline)

A new optional `python -m sportprob.sdv_history` helper can inspect a
**locally downloaded, permitted** SportsDataverse player-box CSV and export
one player's completed-game observations for the existing Safari history
dashboard. It supports finding ESPN athlete IDs by player name. It does not
make network requests or connect to the forecasting CLI.

The source releases are free, but the records originate from ESPN. The
SportsDataverse repository's CC BY 4.0 declaration does **not independently**
clear underlying data rights. Review the original provider's terms; do not
redistribute their full datasets or use them in restricted applications.

[Mac instructions, source and provenance requirements](docs/SPORTSDATAVERSE_HISTORY.md).

## Completed-game context research

The `history` command provides an offline, **retrospective** player profile.
It describes past minutes, per-36-minute production, recent vs earlier completed
games, home/away samples, opponent samples with at least three observations,
and the actual 10th–90th percentiles of already played games. **It does not
calculate a probability for a proposed stat target, generate odds or predict
future game outcomes.** Source-rights declarations and dataset bytes must
match the existing manifest checksum.

```bash
PYTHONPATH=src python3.12 -m sportprob.cli history \
  --data data/demo_games.csv \
  --manifest data/demo_games.manifest.json \
  --player DEMO-001 --stat points \
  --as-of 2025-11-21 --history-games 20
```

The bundled example is explicitly **synthetic**. These retrospective samples
are descriptive and should not be interpreted as real-data forecasting
accuracy. Details: [historical context research](docs/HISTORICAL_CONTEXT.md).

## Historical-data validation and normalization

SportProb can prepare a **local, independently permitted** historical
player-game CSV into its strict canonical schema without calling any external
provider. The research pipeline normalizes common column aliases, validates
minutes and game dates, rejects duplicate player/game IDs, and writes a
checksum-bound local source declaration. It then audits player coverage and
chronological training/calibration/holdout sufficiency.

Read the [Mac-first real-data workflow](docs/REAL_DATA_PIPELINE.md). All
bundled data is still **synthetic**; the research pipeline does not obtain,
scrape or redistribute NBA.com statistics. A source-rights declaration and
successful data-quality checks do not establish independent licensing,
real-world authenticity or model calibration.

## Connect the probability engine to the dashboard (offline)

The Python CLI can now export frozen historical model comparisons to a
**versioned JSON file**, which the redesigned Safari dashboard displays in its
**Model validation** section. Start with the bundled **synthetic demonstration**
before importing any authorized real game records:

```bash
PYTHONPATH=src python3.12 -m sportprob.cli compare \
  --data data/demo_games.csv \
  --manifest data/demo_games.manifest.json \
  --player DEMO-001 --stat points --start 2025-11-16 \
  --output outputs/demo-model-audit.json
open -a Safari mobile/index.html
```

In Safari, select `data/demo_games.csv` after declaring its source and
permission, then import `outputs/demo-model-audit.json` in **Model
validation**. The Python CLI checks the source CSV against its supplied
manifest; the browser now computes a local SHA-256 of the selected CSV bytes
where Web Crypto is available and flags matching or mismatching audit inputs.
A checksum match is **not** independent authentication of the provider,
research permission, record completeness or model calibration. The bundled
example remains synthetic.

Read [complete offline connection instructions](docs/CONNECTING_ENGINE.md).
There is **no automatic NBA.com or sportsbook data feed** connected to this
research dashboard.

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

## Compare model distributions on a frozen historical holdout

The Python research CLI can evaluate **two uncalibrated count-distribution assumptions**
against the same completely withheld completed games: the existing Gamma–Poisson /
negative-binomial baseline and a Poisson benchmark with the **same estimated mean**.
This isolates distributional dispersion; it is not a bet-ranking or selection feature.

Run the following from the repository root after choosing the holdout cutoff
**before looking at its outcomes**:

```bash
PYTHONPATH=src python3 -m sportprob.cli compare \
  --data data/demo_games.csv \
  --manifest data/demo_games.manifest.json \
  --player DEMO-001 --stat points \
  --start 2025-11-16
```

The comparison requires a research-permissions manifest and SHA-256 match.
It reports negative log likelihood, ranked probability score (lower is better),
mean absolute error, signed bias, 80%/90% prediction interval coverage,
80% interval width, and Wilson confidence intervals around measured coverage.
**All predictions in the holdout use only training observations before the
chosen cutoff**, with no fitting on earlier holdout outcomes.

The bundled sample contains only **five synthetic holdout games**. Such a
comparison demonstrates software behavior, not reliable NBA calibration or
evidence that one model will generalize. Meaningful external validation
requires many independently sourced, legally permitted games across time,
players, and seasons, plus a separate untouched evaluation dataset.
The program does not ingest sportsbook information or produce wagering actions.

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
