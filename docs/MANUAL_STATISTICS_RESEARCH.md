# Manual player-statistics research workflow

**Scope:** Offline, non-wagering research on completed games. This workflow does not import sportsbook odds, compare betting lines, generate parlays, calculate stakes, or operate a wagering service.

## What is already connected

- `mobile/index.html` accepts a permissioned, local completed-game CSV for descriptive history and player comparison.
- `sportprob.prepare` normalizes supported authorized CSV aliases to the canonical `GameLog` schema and produces a local SHA-256 manifest.
- `sportprob.manual_research` (added in this branch) verifies that manifest and produces one historical JSON summary for each eligible player and each of points, rebounds and assists.
- Existing `sportprob.cli`, `sportprob.cohort_audit`, and offline report tools remain unchanged. No external network calls or player data are committed.

## Input contract

Canonical completed-game CSV columns:

```csv
game_id,player_id,game_date,opponent,home,minutes,points,rebounds,assists
SYN-001,DEMO-001,2025-11-01,DEMO-OPP,true,34,24,5,7
```

`game_date` uses `YYYY-MM-DD`; counts are nonnegative integers; minutes are finite in 0–80; player/game IDs must be unique. A row with zero minutes cannot have nonzero counting stats. The existing `data/IMPORT_TEMPLATE.csv` illustrates the browser-compatible shorthand headers. Do not use invented missing measurements.

Every canonical CSV requires its own adjacent JSON manifest containing `dataset_id`, `source_name`, `source_reference`, `retrieved_at`, `sha256`, `rights_status`, `rights_evidence`, `permitted_purpose`, and `synthetic`. The accepted purpose is `educational_research`; see `data/demo_games.manifest.json` for a synthetic example and `docs/REAL_DATA_PIPELINE.md` for authorized normalization.

## Run a complete synthetic demonstration

From repository root, with Python 3.11+:

```bash
PYTHONPATH=src python3 -m sportprob.manual_research \
  --data data/demo_games.csv \
  --manifest data/demo_games.manifest.json \
  --as-of 2025-11-21 \
  --output outputs/manual-research-demo.json
```

Optional: `--player DEMO-001` filters a single stable player ID; `--history-games 40` adjusts the last-N historical observation window (5–200). The report requires at least five played games **strictly before** `--as-of`; otherwise that player is listed under `insufficient_history`. Output JSON is created exclusively: it will not silently overwrite an existing file.

Report content includes source/checksum provenance, historical games used, mean/median/sample standard deviation, observed 10th and 90th percentiles, rolling five-game averages, per-36-minute rates, venue and opponent sample counts, plus explicit missing-data limitations. None of these measures is a future prediction or evidence of calibration.

To view CSV data in a mobile browser, open `mobile/index.html` and select the local CSV after declaring its source and permission. The JSON report above is a **CLI artifact** and is not automatically displayed by the existing browser; adding an explicitly verified import UI is future work.

## No-cost data resources for non-wagering sports analysis

| Resource | Relevant content | Important limitation |
| --- | --- | --- |
| [nflverse releases](https://github.com/nflverse/nflverse-data/releases) | NFL player statistics, schedules and play-by-play release files | Different sport and columns; verify specific dataset rights and transform before ingest |
| [BoxScore Lab downloads](https://www.boxscorelab.com/downloads/) | NBA player **season totals** and team/game summaries in CC BY 4.0 CSV | Season totals are not individual player game logs; attribution required |
| [SportsDataverse historical data](SPORTSDATAVERSE_HISTORY.md) | NBA completed-game player box-score CSV and existing repo adapter | Underlying records originate with ESPN; downstream license does not settle upstream rights |
| [nba_api project](https://github.com/swar/nba_api) | Open-source NBA.com API client | MIT license covers client code, not the NBA's statistical content; NBA rules apply |

NBA.com Stats FAQ states that NBA Stats data is **not offered as downloadable CSV**, even for personal or academic uses. Do not scrape or automate restricted access. Confirm current provider terms before importing, storing, or sharing any real dataset. We do not include real player data in Git.

## Acceptance and safeguards

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_manual_research.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Successful checksum verification establishes only that supplied local bytes match the user's declared manifest. It cannot establish the source's identity, legal permission, completeness, or statistical representativeness. This release makes no external requests and adds no gambling capabilities.
