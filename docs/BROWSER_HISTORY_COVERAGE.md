# On-phone historical source coverage review

This module adds a read-only, browser-local **Source coverage** panel to the existing SportProb Performance Desk. It describes how many completed game-log rows are loaded, the selected historical cutoff, dates spanned, missing minute observations, and low-coverage players.

## Why it exists

A small or incomplete sample should not look like a validated sports research dataset. The module works with the already-imported CSV or original fictional hosted snapshot and makes no API requests, source uploads, persistent writes, model predictions, betting lines, or betting recommendations.

## Try it

1. Open the offline HTML page in Safari or a locally hosted Performance Desk.
2. Import the repository's fictional demo CSV and acknowledge its stated research-use permission.
3. Open **Source coverage** and change the historical cutoff date.
4. Verify later records disappear from the counts and the per-player sample flag is clearly labeled.
5. Import invalid CSV data through Dataset control: the parser rejects it and coverage clears.
6. Test source code with `node --test tests/history-coverage.test.cjs`.

The panel cannot verify the external source's rights, game accuracy, season coverage, player identification, or whether a missing game represents a true absence. At least five played games merely removes the **small sample** label; it does **not** validate a model, permit forecasting, or establish suitability for decisions. No connection to live NBA data or sports wagering is introduced.
