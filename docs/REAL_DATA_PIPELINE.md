# Offline real-data readiness workflow

SportProb can validate **a historical game-log CSV that you independently have
permission to use**. This workflow prepares and checks a local research
snapshot, not a live NBA.com ingestion service or a guarantee of model accuracy.

## What is and is not connected

- The Python research engine, locally exported model audits, and Safari research
  dashboard work with the same strict CSV schema.
- The source preparation step accepts locally supplied CSV records and
  user-declared source permissions. It never calls an external API.
- **No authentic, permission-reviewed NBA dataset ships with this repository.**
- A provider's free API, an MIT library, or a public repository's CC license
  does not establish rights to the underlying professional sports statistics.
  In particular, NBA.com restricts gambling-related use of NBA Statistics and
  comprehensive regularly updated databases. Confirm the original source's
  terms before importing.
- Never paste API credentials into the static browser dashboard or GitHub.

## Prepare a permitted source

Prepare locally in Terminal from the **SportProb repo root**, using
Python 3.11+ (Python 3.12 on your Mac). The source CSV must contain
**one row per player per completed game**, with stable player ID and game ID,
valid ISO game date, opponent, home/away, minutes, points, rebounds and assists.

The preparation tool recognizes common equivalent headers, such as `PTS`,
`REB`, `AST`, `MIN`, `OPP`, `Home_Away` and `Date`.
It accepts minutes in decimal or MM:SS notation. It rejects missing essential
columns, invalid dates, duplicates by player/game ID, future-dated games,
invalid counts, and impossible minutes. It does not invent missing records,
game identifiers, opponents, availability statuses, or permissions.

Try this with the **bundled synthetic fixture**:

```bash
cd ~/Desktop/project-sportbet22
git pull --ff-only origin main

PYTHONPATH=src python3.12 -m sportprob.prepare \
  --input data/demo_games.csv \
  --data-out data/processed/demo-canonical-v2.csv \
  --manifest-out data/processed/demo-canonical-v2.manifest.json \
  --dataset-id sportprob-synthetic-v2 \
  --source-name "SportProb synthetic fixture" \
  --source-reference "local://synthetic-fixture" \
  --rights-evidence "Original synthetic demonstration authored in the SportProb repository" \
  --confirm-authorized \
  --synthetic
```

The two generated files stay in `data/processed/`, which is excluded from
Git. Use new filenames for subsequent imports; the tool never silently
overwrites existing research artifacts.

For an **actually authorized historical dataset**, substitute its own
source path and real source/provenance details, omit `--synthetic`, and only
use `--confirm-authorized` when you have reviewed the original provider
terms and have legitimate permission for educational, non-wagering research.
The program can record your declaration; it cannot independently verify it.

## Check historical coverage and split readiness

```bash
PYTHONPATH=src python3.12 -m sportprob.research_check \
  --data data/processed/demo-canonical-v2.csv \
  --manifest data/processed/demo-canonical-v2.manifest.json \
  --player DEMO-001 \
  --train-end 2025-11-11 \
  --holdout-start 2025-11-16
```

The audit reports training, calibration and holdout counts by **played** games;
opponent diversity; date span; missing location/opponent fields; duplicate
player/day warnings; future-dated games; and the exact SHA-256 input snapshot.

Defaults require at least 30 played training games, 10 calibration games and
10 untouched holdout games, plus 5 distinct opponents and at least 45 days of
observation. These are **minimum research QA gates**, not enough to guarantee
high-quality forecasting. To fail with a nonzero exit code on unmet structural
requirements, add `--require-ready`.

The bundled demo is only 20 synthetic observations. Its status MUST be
`DEMONSTRATION_ONLY`; it cannot legitimately pass as real-world evidence.
Even a `STRUCTURALLY_READY_RIGHTS_AND_ACCURACY_UNVERIFIED` result means only
that the supplied CSV passed these mechanical checks.

## Continue to existing historical model validation

After resolving structural issues and documenting source permissions, choose
chronological cutoffs **before inspecting later outcomes**. The model must not
be fitted or tuned against the final holdout outcomes.

```bash
PYTHONPATH=src python3.12 -m sportprob.cli compare \
  --data data/processed/demo-canonical-v2.csv \
  --manifest data/processed/demo-canonical-v2.manifest.json \
  --player DEMO-001 \
  --stat points \
  --start 2025-11-16 \
  --output outputs/demo-v2-audit.json

open -a Safari mobile/index.html
```

Use **Dataset control** to import the prepared CSV, then use **Model
validation** to import its matching JSON audit. The model remains explicitly
uncalibrated and the sample remains synthetic.

The canonical CSV checksum travels with the audit result. The dashboard shows
the audit source identifiers but does not independently recompute the imported
CSV's hash, so manually avoid mismatching files.

## Before evaluating real historical data

1. Document a permitted research source and attribution conditions. Public
   availability alone is insufficient.
2. Check selected-player coverage and stable game IDs against the original
   records; investigate exclusions, postponed games and missing observations.
3. Freeze raw bytes, date cutoffs and availability timestamps before model
   evaluation. A date-only cutoff does not prove that revised records were
   knowable beforehand.
4. Reserve a substantial independent final holdout and report uncertainty.
5. Do not publish unverified accuracy claims or repurpose records for prohibited
   uses.

No data is scraped, transferred, or redistributed by this workflow.
