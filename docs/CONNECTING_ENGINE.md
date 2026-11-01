# Connecting the offline probability engine to the SportProb dashboard

The first working connection is **local JSON exchange**, not a hosted data feed,
a browser API key, or a gambling platform. No credentials are involved.

## 1. Acquire a game log you're permitted to analyze

The project does not acquire, scrape, or automatically synchronize NBA.com data.
Do not repurpose NBA.com statistics for uses prohibited by its terms. Read
`docs/DATA_RIGHTS.md` and `docs/IMPORTING_DATA.md` before working with
third-party datasets. The GitHub demo contains **synthetic** game logs only.

SportProb's Python research engine requires these CSV columns:

```
game_id,player_id,game_date,opponent,home,minutes,points,rebounds,assists
```

Each record must be a completed game, with a stable player/game ID and a numeric
positive playing duration (or zero with all zero statistics). The browser
accepts some additional column aliases, but the Python research CLI uses the
strict above schema.

## 2. Keep an adjacent manifest

Supply a dataset-manifest JSON documenting its source, retrieval time,
permitted educational research purpose, declared rights and an SHA-256
checksum of the *exact* CSV bytes. This does not independently establish legal
rights or accuracy. See `data/demo_games.manifest.json` for a **synthetic**
example, not a rights clearance template for third-party data.

## 3. Compare distributions in Python and export a local JSON

From the repository root, using Python 3.11 or newer:

```bash
PYTHONPATH=src python3.12 -m sportprob.cli compare \
  --data data/demo_games.csv \
  --manifest data/demo_games.manifest.json \
  --player DEMO-001 \
  --stat points \
  --start 2025-11-16 \
  --output outputs/demo-model-audit.json
```

The holdout cutoff must be selected *before* examining holdout outcomes in a
real scientific evaluation. The CLI verifies the checksum, validates
permissions declarations and source records, compares the two provisional
models, then writes `outputs/demo-model-audit.json`. Existing files are not
silently overwritten; pass `--overwrite` only when you intend to replace one.

The emitted `sportprob-frozen-model-audit-v1` schema carries player,
statistic, dataset ID, source, SHA-256, synthetic status, historical holdout
policy, proper scores, and empirical interval coverage with sample
uncertainty. No betting odds, recommendations, guarantees, or execution.

## 4. Open and inspect results in Safari

```bash
open -a Safari mobile/index.html
```

In the dashboard, declare the **synthetic demonstration** source and confirm
your permission to use the included fixture. Choose
`data/demo_games.csv` in **Dataset control**. Then go to
**Model validation**, select `outputs/demo-model-audit.json`, and inspect the
two model-score rows.

The dashboard reads both files locally using browser file inputs; no uploads,
remote requests, or keys. It compares the labels of the selected player and
statistic, but it does **not** recompute the CSV's SHA-256 in Safari. The
Python CLI verifies the snapshot that produced the exported audit. Avoid
mixing a CSV and an audit from different source files.

## 5. Real data and future integration

To run the same process with an authorized real dataset, replace the CSV and
manifest inputs and supply that dataset's actual player ID and cutoff date.
Validate that all games are complete and that the date/ID relationships
accurately represent distinct observations. Choose an untouched holdout and
keep the separate source-usage evidence. Real-data calibration is **not
established** by passing the synthetic software tests.

A future scheduled data pipeline requires a provider contract that allows the
intended collection, storage, and reuse. Until then, the workflow uses a local
research dataset rather than automatically collecting or redistributing
NBA.com content.
