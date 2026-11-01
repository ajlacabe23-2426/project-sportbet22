# Free SportsDataverse historical basketball data — offline viewer

SportProb supports inspecting a **user-downloaded, local** SportsDataverse
player-box CSV for historical, non-wagering research. This feature does not
download data automatically, invoke the probability engine, calculate the
likelihood of a future stat target, or connect to sportsbooks.

## 1. Check provenance and permissions first

- GitHub source and project: https://github.com/sportsdataverse/hoopR-nba-data
- Author-declared repository license: https://github.com/sportsdataverse/hoopR-nba-data/blob/main/LICENSE.md (CC BY 4.0; attribution required).
- Actual season CSV release: https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_nba_player_boxscores
- **Upstream source is ESPN**. The downstream open-source license does not
  independently establish all upstream rights. Ensure the intended use is
  permitted by the original data providers. Use no restricted data in public
  or commercial applications without permission.
- The adapter never treats an acknowledgment as independent legal clearance.

The release describes `player_box_2026.csv` as the player-level historical
box-score data for the **2025–26** season (the *ending* year is in the name).
No subscription, API key, or automatic scraping is needed to inspect this
already-published release.

## 2. Save a copy locally

Only if your intended educational research use is permitted, open the release
page, select `player_box_2026.csv`, and save the CSV as:

```
~/Desktop/project-sportbet22/data/raw/player_box_2026.csv
```

`data/raw/` and `data/processed/` are already excluded by the repository's
`.gitignore`. **Do not commit or redistribute source game records.**

To inspect the CSV headers without changing any data:

```bash
cd ~/Desktop/project-sportbet22
python3.12 -c "import csv; print(next(csv.reader(open('data/raw/player_box_2026.csv',encoding='utf-8-sig',newline=''))))"
```

The converter supports source columns:
`game_id`, `game_date`, `team_id`, `minutes`, `points`,
`rebounds`, `assists`, `athlete_id` (or `player_id`) and
`athlete_display_name` (or `athlete_name` / `player_name`).
It **fails closed** if those fields are absent or incompatible; the upstream
CSV's actual schema still needs to be verified by a local acceptance test.

## 3. Find an ESPN athlete ID

```bash
PYTHONPATH=src python3.12 -m sportprob.sdv_history \
  --source data/raw/player_box_2026.csv \
  --find-player "Stephen Curry"
```

Change the name for any player. This reads the local file and returns matches
with their **ESPN athlete IDs**, which are not the same namespace as IDs from
the `nba_api` library.

## 4. Create a historical-browser CSV

Replace `ESPN_ID_FROM_LOOKUP` with the numeric ESPN athlete ID printed by
the previous command. Only after checking the provider's use permissions:

```bash
PYTHONPATH=src python3.12 -m sportprob.sdv_history \
  --source data/raw/player_box_2026.csv \
  --player-id ESPN_ID_FROM_LOOKUP \
  --output data/processed/player-history-2026.csv \
  --confirm-private-research

open -a Safari mobile/index.html
```

In Safari, enter `SportsDataverse ESPN player-box historical research` as
the dataset source, confirm your permission, and choose
`data/processed/player-history-2026.csv` in Dataset control.

The CSV contains **only that player's completed-game observations** for the
offline history viewer. It does not feed or certify the Python predictive
model, does not supply probabilities for future stat lines, and is not a
source-permissions certificate.

## Technical limitations

- Game opponents are described by **ESPN team ID** where exactly one other
  team ID can be found for that game; missing opponents remain blank.
- Home/away fields are included only when expressly present in the source.
  We never guess them from player/team IDs.
- Rows with incomplete counts/minutes and zero played minutes are excluded
  and counted as excluded. Source gaps are not fabricated.
- The browser limits imports to 20,000 game rows and 2 MB. The converter
  restricts its **single-player** output to 1,500 played games.
- Neither authenticity, permissions, season completeness, nor the accuracy of
  real-world forecasts is independently established by this software.
