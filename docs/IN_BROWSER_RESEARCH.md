# Instant historical research in the phone browser

This is the **no-Python** path for exploring manually imported, completed-game statistics. It extends the existing Performance Desk. No provider API keys, network requests, persistent storage, bookmaker inputs, betting suggestions, or money-related outputs are involved.

## How it works

1. Open the static `mobile/index.html` dashboard, either from an existing local copy or a trusted static host serving its local JS/CSS assets.
2. In **Dataset control**, enter the source/creator, confirm the applicable research permissions, and import an authorized player-game CSV. All files are parsed in your browser session and are **not** sent to a server.
3. Select a **Player** in Performance overview.
4. Open **Instant stats / Research on your phone**. The browser defaults to that player's latest completed game as the inclusive cutoff, and the most recent 20 games.
5. Change **Include games through** or the observation window (5, 10, 20, or all) to see on-device summary statistics. Changing the selected player recalculates the table.

The file can use the previously supported aliases `player_id,game_date,points,rebounds,assists`, shorthand `player_name,game_date,pts,reb,ast`, and optional `minutes,opponent,home,game_id`; see `docs/IMPORTING_DATA.md`.

## Calculations

For every selected player/statistic, the panel uses only rows with game date **on or before** the chosen inclusive date. Explicit zero-minute games are excluded. At least five played-game observations are required. The selected historical window is taken **after** filtering by the cutoff.

- Mean, median, sample standard deviation (denominator `n-1`)
- Last-five and, when at least ten selected games exist, preceding-five observed means
- Observed nearest-rank 10th/90th percentiles (not prediction intervals)
- Production per 36 played minutes: `36 * sum(counts) / sum(played minutes)`, shown only when **every** selected observation supplies positive minutes
- Number of selected games, excluded zero-minute entries, missing selected minutes, exact file SHA-256 where supported, and the source's synthetic/unverified status

Changing or rejecting a CSV clears the table rather than presenting statistics from a former source. All displayed values are rendered with text-only DOM operations, avoiding HTML interpolation.

## How this differs from the Python manual report

The **Instant stats** panel calculates historical descriptive summaries immediately from the selected local CSV; no manifest or generated JSON is needed for these ephemeral browser results. The separately available **Manual research** section imports `sportprob.manual_research` JSON, which is checked against a separate source-rights/checksum manifest before generation and then matched to the same CSV by SHA-256 in the browser. They serve distinct use cases; neither is an authenticated source of record.

## Limitations and verification

- Successful CSV parsing **does not verify** data ownership, completeness, permission, or external provider accuracy. Do not import unauthorized datasets.
- All calculations are retrospective and **not** projections, calibrated probabilities, or wagering tools.
- Browser import is capped at 2 MB / 20,000 records by the existing importer.
- The repository includes synthetic example records only. Real-source acceptance and iPhone Safari device verification have not been performed.
- This work changes static browser code, **not** production hosting. A GitHub repository link is not itself a hosted browser dashboard.

## Automated checks

```bash
node --test tests/instant-research.test.cjs
node --test tests/mobile-ui.test.cjs tests/manual-report-ui.test.cjs
RUN_BROWSER_ACCEPTANCE=1 CHROME_BIN=/usr/bin/google-chrome node --test tests/mobile-browser.test.cjs
```

The GitHub CI mobile job runs the standalone tests and browser acceptance suite. No internet or account integration is needed for the research calculations.
