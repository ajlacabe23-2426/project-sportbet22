# Hosted Historical Data Source Manager

The Performance Desk is a **static GitHub Pages website** with a browser-side player-history viewer. CSS styles the interface; it never stores player statistics. The Data Source Manager introduces **read-only, publicly hosted snapshot files** without collecting user-uploaded records on a server.

## Working architecture

- The site downloads a small, reviewed catalog at `mobile/datasets/catalog.json` from its **own origin only**.
- The catalog identifies an approved CSV already deployed with the site. The current only allowed entry is `mobile/demo_games.csv`, a repository-authored **synthetic** game-log fixture.
- Choosing **Load hosted history** fetches that same-origin CSV only after the user explicitly selects it and confirms dataset-use permission in Dataset control.
- Its exact byte-level SHA-256 fingerprint and canonical parsed record count must match the catalog before the dashboard replaces its current dataset. No provider or rights authenticity is implied by a checksum.
- The existing `SportProbIngestFile` CSV parser and complete-game validation are reused. Player selection, game log, historical means, and other on-device descriptive views work as before.
- User file imports and manual input still work. No user-supplied CSV is uploaded; the hosted CSV is public, read-only, and processed in browser memory.

## Deploying datasets

The `.github/workflows/pages.yml` workflow publishes only the contents of `mobile/` to the existing GitHub Pages site. The catalog and its public snapshots ship in the same artifact and are readable by anyone visiting that page. Do not put personal data, paid feeds, proprietary files, API credentials, tokens, or unreviewed real player records in this directory.

To add or revise a **fictional, original** demonstration:

1. Create a CSV with `game_id,player_id,game_date,opponent,home,minutes,points,rebounds,assists`. Ensure every game is completed and the player/game identifiers and played minutes are valid.
2. Independently confirm the public-redistribution rights of the precise bytes. This implementation **only permits original synthetic datasets**; unapproved real-source entries fail catalog validation.
3. Compute SHA-256 from the final UTF-8 bytes and record its `sha256`, `records`, `last_game_date`, `snapshot_date`, source description, and distribution basis in `datasets/catalog.json`.
4. Review the data and metadata in a PR. Run Node tests, headless Chrome acceptance, and the static asset smoke tests; merge only after success.
5. A GitHub Pages deployment must finish and its **post-deployment** HTTP smoke checks must pass. Then verify the hosted selector and statistics on an actual phone.

The current demonstration has **20 fictional games**, last game date **2025-11-20**. Its source-manifest publication snapshot date is **2026-10-24**. It is not a continuously refreshed feed.

## Network and security boundaries

The HTML Content Security Policy permits `connect-src 'self'` for the catalog and public CSV. External endpoints, browser-to-cloud uploads, persistence APIs, and private tokens are not part of this manager. The loader uses `fetch` with `mode:"same-origin"`, `credentials:"omit"`, `redirect:"error"`, limits on file size, safe CSV basenames, and a strict manifest schema. Rendering uses text-only DOM nodes. Local file mode (`file://`) retains the manual CSV import path but does not support hosted data discovery.

## Real statistics roadmap

Hosting **real NBA statistics** would be a separate approval step: establish appropriate rights from the upstream origin and the downstream feed, provenance, redistribution terms, and expected refresh cadence; then build a private server-side ingestion pipeline or an approved snapshot publishing job. Static GitHub Pages cannot receive writes from users or perform scheduled server-side ingestion by itself. A free API key or publicly viewable statistics do not authorize republishing the underlying database.

This feature is historical educational sports research only. It does not generate wagering advice, sportsbooks, betting odds, or trades.

## Verification

```bash
node --test tests/hosted-source-manager.test.cjs
node tests/hosted-pages-smoke.cjs --local-only
RUN_BROWSER_ACCEPTANCE=1 CHROME_BIN=/usr/bin/google-chrome node --test tests/mobile-browser.test.cjs
```

CI also runs the existing Python tests and, on successful GitHub Pages publication, the actual deployed HTML and data-file smoke test. A completed HTTP smoke test does not establish real iPhone Safari behavior or third-party data rights.
