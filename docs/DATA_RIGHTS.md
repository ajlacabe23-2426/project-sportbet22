# Data rights and scientific reproducibility

## Current status
**No real NBA historical-statistics dataset is included or connected.**
The repository contains only synthetic demonstration records. The model has
not been calibrated on real NBA data; no claims about real-world predictive
quality are supported.

NBA.com states that use of its statistics for gambling is prohibited. Its Stats
FAQ also states its statistics are not provided as downloadable data. A
third-party repository's permissive code/data license does **not** automatically
clear the rights of underlying statistics. Do not copy, scrape, rehost or
repackage an unauthorized source.

References checked 2026-10-24:
- https://www.nba.com/termsofuse
- https://api-hub.nba.com/stats/help/faq

## Offline manifest
Every dataset used for educational research should have an adjacent metadata
file documenting its source, permitted purpose, and SHA-256 of the exact CSV
bytes. This records asserted permissions and provenance; it is **not** legal
approval, does not independently validate upstream rights, and must not be
used to override a source's restrictions.

```bash
PYTHONPATH=src python -m sportprob.audit \
  --data data/demo_games.csv \
  --manifest data/demo_games.manifest.json \
  --train-end 2025-11-11 \
  --holdout-start 2025-11-16
```

## Time-split policy
- Training observations must have game dates **before** train-end.
- Calibration observations begin at train-end and end before holdout-start.
- Final holdout observations begin **on** holdout-start and are never
  used for fitting or selecting the model.
- All games on the same date go in the same partition.
- Partitions must be nonempty and game identifiers unique per player.
- In any real experiment, freeze dataset-version hashes and feature
  availability timestamps; a game date alone is insufficient to prevent
  reporting/revision leakage.

## Still required before genuine real-world evaluation
1. A reviewed, appropriate data-rights basis **for the intended use**.
2. Explicit upstream attribution/consent where required.
3. Versioned source payloads and as-of availability timestamps.
4. Data-quality investigation and documented sampling/exclusion rules.
5. Untouched chronological holdout and model audit (not wagering evaluation).

There is no external data acquisition job, automated scraper, sportsbook API,
or financial decision system in this project.
