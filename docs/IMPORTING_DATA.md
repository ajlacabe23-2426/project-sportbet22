# Importing historical player statistics into SportProb

The SportProb Performance Desk reads a **local, user-selected CSV** in Safari, Chrome, or another modern browser. It performs descriptive research on completed game records only. No remote API or automatic scraping is built into the dashboard. Files are parsed in browser memory, not uploaded to the repository, hosted server, or external service.

## Try the interface without real data

Open `mobile/index.html` in Safari. Use the **Data source / creator** field to enter `SportProb synthetic demonstration`, confirm you have permission to use the included demo, then choose `data/demo_games.csv`. The demo fixture is synthetic and **must not be represented as NBA game history**. The separate `data/IMPORT_TEMPLATE.csv` shows a common shorthand column convention using synthetic example records.

## Import permitted game logs

1. Obtain a CSV you are authorized to use for this research project. Read the original source's licensing and reuse terms; public visibility does not itself grant database, redistribution, or commercial rights.
2. Include **one row per player per completed game**. The required columns can use either descriptive names or shorthand, with capitalization ignored:
   - Player: `player`, `player_id`, `player_name`, `name`
   - Date: `date`, `game_date`, `match_date` in strict `YYYY-MM-DD`
   - Statistics: `points`/`pts`, `rebounds`/`reb`, `assists`/`ast` (nonnegative whole-number counts)
3. Optional columns are `minutes`/`min`/`mp` (numeric or `MM:SS`), `opponent`/`opp`/`opponent_team`, `home`/`home_away`/`location` (true/false, 1/0, home/away or h/a), and `game_id`. Missing optional fields remain unavailable.
4. Open the dashboard, enter a specific source or creator, confirm your permissions, select the CSV, then choose the player, statistic, and historical window.
5. Verify the displayed source, dates, sample count, home/away counts, game log, and missing-field notices. Check the selected player record against your original source.

The dashboard rejects invalid calendar days, duplicate player/date rows, malformed numeric counts, missing required columns, unsafe row counts, and CSVs over 2 MB. It supports up to 20,000 game rows; for bigger authorized archives, create a smaller subset before import. CSV data remains in memory until page reload or another import.

## What a completed import verifies—and what it does not

A successful import means the file matched SportProb's validation rules; **it does not authenticate the provider, prove that all games are included, establish licensing rights, or validate a predictive model.** Historical averages, medians, standard deviation, and trailing five-game lines are descriptions of the supplied game log, not forecasts or future-outcome probabilities. No sportsbook integrations, betting tools, or automated wagering are included.

## Data-provider integration backlog

Before connecting a third-party provider, confirm (a) game-level fields and availability under the applicable tier, (b) rate limits, (c) licensed use and storage permissions, (d) stable game/player identifiers, (e) historical coverage and game-completion state, and (f) secure handling of any credentials. The initial release intentionally uses permissioned CSV import; do not paste API keys into this static page. A provider adapter should transform authorized records into the same validated schema and retain traceable source metadata. 
