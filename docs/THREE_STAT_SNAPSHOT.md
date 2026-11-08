# Offline three-stat player research snapshot

This feature takes an **already permitted, locally available** canonical player game-log CSV and the matching provenance/checksum manifest. It prints an inspectable estimate for points, rebounds, and assists at one explicit exclusive forecast date.

It does not acquire upcoming schedules, injury news, opponent adjustments, bookmakers, betting lines, or wagers. Current Gamma-Poisson/Negative Binomial model assumptions are **uncalibrated**; intervals should not be presented as accurate until independently verified.

## Demo on Mac

From the repository root:

```bash
PYTHONPATH=src python3.12 -m sportprob.performance_snapshot   --data data/demo_games.csv   --manifest data/demo_games.manifest.json   --player DEMO-001   --as-of 2025-11-21
```

The bundled file contains synthetic observations, **not real NBA games**. The command verifies the exact file SHA-256 against the manifest, excludes all games on or after the requested date, and reports per-stat modeled mean, variance, 80%/90% intervals, observed trailing 5/20 means and median, sample coverage, source identity and limitations. No probability of success for a wagering line is calculated.

For a local report, add `--output outputs/snapshot-01.json` after creating the ignored output folder. Existing output files cannot be overwritten.

## Point-in-time sample coverage and context flags

The snapshot also records `history_coverage`: number of prior played games, the maximum 20-game model-training sample, the last-five observed minutes range, how many calendar days elapsed since the last completed played game, missing home/away context within the model window, and source rows with zero playing minutes that were excluded from model fitting.

`review_flags` are **descriptive inspection prompts only**. More than 14 calendar days since a player's last game may simply be an offseason or schedule gap, and a wide range of playing minutes is not an injury diagnosis. No upcoming availability, opponent conditions, forecasts of playing time, or independent accuracy certification is inferred. Every count uses only records strictly before the selected `--as-of` date.

## Readiness gates before trusting research

1. Confirm a lawful, authorized source and exact checksum; a matching checksum does **not** establish legal data rights.
2. Verify player identity and sufficient completed-game history.
3. Supply the forecast date *before* that game's results are known, and preserve immutable provenance.
4. Evaluate calibration, missing-game/availability effects, opponent context, and changes in projected minutes across untouched chronological periods.
5. Present unexplained uncertainty honestly. No automated betting, brokerage connection or live transactions are included.
