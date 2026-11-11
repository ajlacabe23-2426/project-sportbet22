# Hosting the SportProb Performance Desk on GitHub Pages

This repository's mobile frontend is a static, browser-only research application in `mobile/`. It has no login, API server, sportsbook integration, external data feed, or storage backend. Source game logs stay on the device in browser memory.

## Required one-time repository setting

A repository administrator must open the repository's **Settings → Pages** page and set **Build and deployment → Source** to **GitHub Actions**. The GitHub App connector used for this project cannot enable that setting on the user's behalf.

Once Pages is enabled, the workflow `.github/workflows/pages.yml` can be started using **Actions → Publish offline Performance Desk → Run workflow**. The workflow also publishes on future pushes to `main` that change `mobile/` assets or the Pages workflow.

## What the workflow does

1. Checks out the exact branch commit and runs the offline browser-script regression tests on Node 22.
2. Packages **only** the `mobile/` static directory as a GitHub Pages artifact.
3. Uses GitHub's official Pages deployment action and supplies the final URL through the `github-pages` environment.
4. Does not publish `data/`, unverified third-party game logs, `outputs/`, repository secrets, or Python source code.

A successful GitHub Actions result is not a substitute for checking the final page from an iPhone browser. Verify the actual deployment URL reported by the workflow, the static asset responses, in-browser CSV import, manual entry, date filters, and CSV export.

## Automated live-site verification

After GitHub Pages has been enabled, the publishing workflow runs `node tests/hosted-pages-smoke.cjs "$PAGE_URL"` **after deployment**, using the deployment URL reported by GitHub. This independently checks HTTP 200 responses for the actual page, local JavaScript modules, CSS, and a synthetic demonstration CSV. It verifies the downloaded demo CSV is byte-identical to the repository's authored synthetic dataset, and confirms internal Python source files are not publicly served. If these checks fail, the workflow is marked failed rather than claiming the site is healthy.

The same script can be run without hosting as `node tests/hosted-pages-smoke.cjs --local-only`, which checks the assets and demo fixture locally before merging. It cannot replace device-level Safari testing, because HTTP checks do not execute the UI inside an iPhone browser.

## On-phone synthetic verification

1. Open the live URL from the **github-pages** environment shown in a successful deployment job.
2. Under **Dataset control**, tap **Download synthetic demo CSV (20 fictional games)** and save the file in the phone's Files app.
3. Enter `Bundled synthetic test data` as the dataset source, confirm the research permission for the repository-authored synthetic sample, and tap **Import game logs** to choose the saved CSV.
4. Confirm the UI reports **SYNTHETIC SAMPLE LOADED**, then select the sample player `DEMO-001`.
5. Under **Instant stats**, confirm the last recorded game date is `2025-11-20`, a 20-game history is available, and three statistics render.
6. Change the historical cutoff back to `2025-11-04`; the summary should be withheld because fewer than five played observations remain. Restore `2025-11-20` to recover the historical view.
7. Under **Enter game logs**, add a few fictional completed games. After at least five valid observations, select **Analyze draft** to verify the form shares the CSV validation path. Export CSV to preserve a copy.
8. Confirm no real personal records were imported, the browser reported no errors, and the app does not claim predictions or live updates.

This deliberately does not embed unlicensed real player data or use external requests to retrieve statistics. The demo file is a downloadable static asset, not an automatically fetched data source.

## Public hosted synthetic snapshots

The site now serves `datasets/catalog.json` and the authored synthetic `demo_games.csv` as public static assets. The **Data Source Manager** loads those files from the same host and rejects catalog checksum or row-count mismatches. The publishing workflow validates catalog structure, dataset SHA-256, HTTP availability, and existing browser import behavior. Static files cannot receive uploads or self-update. For detailed source governance, read [HOSTED_SOURCE_MANAGER.md](HOSTED_SOURCE_MANAGER.md).

## Live hosting acceptance checklist

- Pages workflow is successful with a real `page_url` in the deployment job.
- The live page loads all local styles and JavaScript without errors.
- Local CSV file selection, source acknowledgement, and SHA-256 report-link checks work.
- Manually enter at least five completed-game records; then use **Analyze draft** and **Instant stats**.
- Export the draft CSV and verify it can be reopened.
- Replace the dataset with an invalid CSV and confirm that stale statistics disappear.
- Perform a real iPhone Safari test with synthetic records before claiming mobile acceptance.

## Availability and limitations

Until GitHub Pages has been enabled and a successful deployment URL has been verified, **no hosted URL is claimed**. This is an alternate static hosting route after the Vercel project creation request returned a 403 permission error in the Atlas team.

No Python code executes in the browser. Browser-only descriptive statistics are distinct from the separately documented local Python historical model. Uploaded CSV records remain unverified claims from their source; a public website does not grant data redistribution rights.

This page is for historical educational research, not gambling or wagering recommendations.
