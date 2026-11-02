# Consolidated historical performance report — offline

This single command produces a self-contained HTML report plus a JSON report,
based on the existing local regular-season player-history CSV.

It never connects to the internet or uploads source data. The original files
remain unchanged. It does not create future-game predictions, model
calibration claims, proposed-line probabilities or wagering advice.

## Run once on MacBook

From Terminal:

    cd ~/Desktop/project-sportbet22
    git status --short
    git pull --ff-only origin main

    PYTHONPATH=src python3.12 -m sportprob.season_report \
      --data data/processed/curry-regular-season.csv \
      --espn-player-id 3975 \
      --train-end 2025-10-27 \
      --evaluation-start 2025-12-22 \
      --raw data/raw/player_box_2025.csv data/raw/player_box_2026.csv \
      --html-out outputs/curry-regular-history-v1.html \
      --json-out outputs/curry-regular-history-v1.json

    open -a Safari outputs/curry-regular-history-v1.html

The report files remain in the Git-ignored local outputs/ directory.

## What the report checks

- Overall means, medians, observed extrema, sample standard deviations
  and observed per-36-minute production for points, rebounds and assists
- Average and distribution of observed played minutes
- Chronological training, calibration and historical evaluation comparisons
- Original archive season-to-season summaries and changes in group means
- Home/away and last-five historical splits
- File SHA-256 digests, cross-matched source game IDs and per-season source
  counts by season_type, including marked did_not_play records

The script rejects invalid numeric records, duplicate IDs, mixed player IDs,
non-regular-season rows, and mismatches to the original source archive.
For your confirmed local sample, the expected selected count is 115 and
the known historical split is 75 / 17 / 23 games. The actual command verifies
the data at runtime rather than trusting that expected result.

All source data stays on the Mac. Existing report output files are never
overwritten. Change v1 to v2 in both output filenames to rerun intentionally.

## Rights and interpretation

The original ESPN-derived archive's permitted reuse has not been independently
established. Public downloads and a downstream project license do not remove
upstream restrictions. This report does not mark rights as cleared.

All results are retrospective descriptions of previously played games.
Differences in observed averages do not establish future performance
probabilities, causal venue effects or out-of-sample model accuracy.
Nothing here represents an independently validated forward test.
