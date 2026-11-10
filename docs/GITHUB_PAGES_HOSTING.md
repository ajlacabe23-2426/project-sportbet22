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
