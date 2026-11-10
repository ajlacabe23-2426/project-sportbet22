# Manually entering completed player games on a phone

This module is an **offline player-statistics notebook**, not a sportsbook or wagering tool.

## Workflow

1. Open `mobile/index.html` in the Performance Desk. In **Enter game logs**, type the player, completed-game date, minutes, points, rebounds, and assists. Opponent, home/away, and a game ID are optional. If a player has multiple games on the same date, give each a distinct stable game ID.
2. Select **Add completed game**. The record is checked locally and added to an in-memory draft.
3. Repeat for at least five completed games. Source data should be accurate, independently permitted, and traceable; the software cannot verify it.
4. Under **Dataset control**, enter the data source and confirm that you are permitted to use the records for research.
5. Select **Analyze draft**. The app serializes the draft into the existing canonical CSV format and passes it to exactly the same browser importer used for file uploads.
6. Select your player and go to **Instant stats**. The browser calculates historical averages, sample standard deviation, observed percentiles, and recent-game comparisons without Python or any server API.
7. Select **Export CSV** to preserve the draft. No rows are saved persistently by the app. Reloading or closing the page discards the draft; exported CSVs can be re-imported through Dataset control later.

## Validation and safety

- Browser-only draft: no API calls, tracking, database, or local storage.
- Capped at 500 hand-entered records; the existing 20,000-row and 2 MB importer limits also apply.
- Real `YYYY-MM-DD` completed dates; up to 80 played minutes; nonnegative whole-number statistics up to 200.
- A zero-minute game cannot contain nonzero points, rebounds, or assists.
- Duplicate player/game IDs are rejected, and same-day duplicates without distinct IDs are rejected.
- Strings are escaped according to CSV quoting rules before importing or exporting.
- The existing importer remains the canonical validator. A rejected import clears previously loaded dataset results, but not the manual draft.
- Entered data is not automatically sourced or checked against an official provider; it remains user-declared.
- Reports are historical descriptions only, not next-game forecasts, gambling odds, bets or staking outputs.

## Hosting status

The repository source is ready for static hosting: the frontend lives entirely under `mobile/`. A tested Vercel deployment setup would use that directory as the project root. Deployment is **not** proven by a merge or GitHub Actions check; a live URL needs independent verification.

## Tests

```bash
node --test tests/manual-entry.test.cjs
RUN_BROWSER_ACCEPTANCE=1 CHROME_BIN=/usr/bin/google-chrome node --test tests/mobile-browser.test.cjs
```

GitHub CI also executes the complete Python regression suite. Real-iPhone Safari validation remains required before claiming phone production readiness.
