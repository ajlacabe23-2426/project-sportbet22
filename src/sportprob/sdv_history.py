"""Inspect a local SportsDataverse ESPN NBA player-box CSV for descriptive research.

This command neither fetches games nor calls the prediction engine. It
prepares a *browser-only historical display* CSV, not the canonical Python
forecast-ingestion schema. The user must review source rights independently.

The original source CSV remains unchanged and is never uploaded.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
from collections import Counter, defaultdict

MAX_INPUT_BYTES = 80_000_000
MAX_OUTPUT_GAMES = 1500
REQUIRED = {
    "game_id", "game_date", "team_id", "minutes",
    "points", "rebounds", "assists",
}
DISPLAY_HEADER = [
    "player_name", "game_date", "pts", "reb", "ast", "min",
    "opponent_team", "home_away", "game_id",
]


def _column(headers: set[str], *choices: str) -> str:
    matched = [name for name in choices if name in headers]
    if len(matched) != 1:
        raise ValueError("source requires exactly one of: " + ", ".join(choices))
    return matched[0]


def _minutes(raw: str) -> str | None:
    value = raw.strip()
    if not value:
        return None
    if ":" in value:
        pieces = value.split(":")
        if len(pieces) != 2 or not all(p.isdigit() for p in pieces):
            raise ValueError("invalid MM:SS playing time")
        m, seconds = map(int, pieces)
        if seconds >= 60:
            raise ValueError("playing time seconds >= 60")
        count = m + seconds / 60
    else:
        try:
            count = float(value)
        except ValueError as exc:
            raise ValueError("invalid numeric playing time") from exc
    if not isfinite(count) or not 0 <= count <= 80:
        raise ValueError("minutes outside 0-80")
    return str(round(count, 5))


def _nonnegative_count(raw: str, field: str) -> str | None:
    value = raw.strip()
    if not value:
        return None
    if not value.isdecimal() or int(value) > 200:
        raise ValueError(f"invalid {field} game count")
    return str(int(value))


def _date(raw: str) -> str:
    value = raw.strip()
    if len(value) != 10:
        raise ValueError("game_date must be YYYY-MM-DD")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value or parsed > date.today():
        raise ValueError("invalid or future-dated completed game")
    return value


def _home_flag(row: dict[str, str]) -> str:
    value = row.get("home_away", row.get("home", "")).strip().lower()
    if value in ("home", "h", "true", "1"):
        return "home"
    if value in ("away", "a", "false", "0"):
        return "away"
    if not value:
        return ""
    raise ValueError("unknown home/away field; do not guess venue")


def prepare_historical_browser_csv(
    source: str | Path, output: str | Path, *,
    player_id: str,
    acknowledge_private_research: bool,
) -> dict:
    """Extract one player's *completed* boxscores for the offline history UI.

    Does not create a rights-cleared manifest or enable the forecasting CLI.
    Data labels and permissions remain unverified; opponent identities are
    reported as source team IDs rather than invented team abbreviations.
    """
    if not acknowledge_private_research:
        raise ValueError("confirm that you've reviewed the source terms for private research")
    if not player_id.strip():
        raise ValueError("select an ESPN athlete_id")
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError("source and output must be different files")
    if output.suffix.lower() != ".csv" or output.exists():
        raise ValueError("use a new .csv output filename; existing files are never overwritten")
    if source.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("source CSV exceeds 80 MB safety limit")
    file_digest = sha256(source.read_bytes()).hexdigest()
    game_teams: dict[str, set[str]] = defaultdict(set)
    selected: list[dict[str, str]] = []
    missing_stats = dnp = 0
    source_fields: list[str]
    with source.open("r", newline="", encoding="utf-8-sig") as input_file:
        reader = csv.DictReader(input_file)
        source_fields = [x.strip().lower() for x in reader.fieldnames or []]
        if not source_fields or len(source_fields) != len(set(source_fields)):
            raise ValueError("missing or duplicate source column names")
        if len(source_fields) > 120:
            raise ValueError("too many source columns")
        heads = set(source_fields)
        required_missing = REQUIRED - heads
        if required_missing:
            raise ValueError("missing SportsDataverse columns: " + ", ".join(sorted(required_missing)))
        athlete_col = _column(heads, "athlete_id", "player_id")
        name_col = _column(heads, "athlete_display_name", "athlete_name", "player_name")
        # Do not silently accept shifted fields or fabricated identifiers.
        for i, row in enumerate(reader, start=2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"row {i}: malformed source CSV")
            row = {str(k).strip().lower(): v for k, v in row.items()}
            game = row["game_id"].strip()
            team = row["team_id"].strip()
            if not game or not team:
                raise ValueError(f"row {i}: missing game or team id")
            game_teams[game].add(team)
            if row[athlete_col].strip() != player_id:
                continue
            try:
                game_date = _date(row["game_date"])
                minutes = _minutes(row["minutes"])
                points = _nonnegative_count(row["points"], "points")
                rebounds = _nonnegative_count(row["rebounds"], "rebounds")
                assists = _nonnegative_count(row["assists"], "assists")
                if minutes is None or points is None or rebounds is None or assists is None:
                    missing_stats += 1
                    continue
                if float(minutes) == 0:
                    dnp += 1
                    continue
                player_name = row[name_col].strip()
                if not player_name or len(player_name) > 90:
                    raise ValueError("missing or oversized player name")
                selected.append({
                    "player_name": player_name + " (ESPN " + player_id + ")",
                    "game_date": game_date,
                    "pts": points, "reb": rebounds, "ast": assists,
                    "min": minutes, "opponent_team": "",
                    "home_away": _home_flag(row),
                    "game_id": game,
                    "_team_id": team,
                })
            except ValueError as exc:
                raise ValueError(f"row {i}: {exc}") from exc
    if not selected:
        raise ValueError("no valid played game records for the selected ESPN athlete_id")
    if len(selected) > MAX_OUTPUT_GAMES:
        raise ValueError("selected player exceeds the 1,500-game research limit")
    unique_games: set[str] = set()
    absent_opponent = 0
    for item in selected:
        game = item["game_id"]
        if game in unique_games:
            raise ValueError("duplicate player/game_id in selected source")
        unique_games.add(game)
        teams = game_teams[game] - {item["_team_id"]}
        if len(teams) == 1:
            item["opponent_team"] = "ESPN_TEAM_" + next(iter(teams))
        else:
            # Preserve honest missing values if the opponent cannot be determined.
            absent_opponent += 1
        del item["_team_id"]
    selected.sort(key=lambda item: (item["game_date"], item["game_id"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, DISPLAY_HEADER)
            writer.writeheader()
            writer.writerows(selected)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return {
        "schema": "sportprob-historical-browser-import-v1",
        "research_only": True,
        "source": "SportsDataverse ESPN player box scores (user-supplied)",
        "upstream": "ESPN",
        "input_sha256": file_digest,
        "player_id_namespace": "ESPN athlete_id (not NBA.com player_id)",
        "player_id": player_id,
        "played_rows_exported": len(selected),
        "missing_stat_records_skipped": missing_stats,
        "zero_minute_records_skipped": dnp,
        "opponent_unresolved_rows": absent_opponent,
        "source_terms_independently_cleared": False,
        "forecast_engine_connected": False,
        "output_path": str(output.resolve()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a local SportsDataverse player box CSV for historical Safari exploration"
    )
    parser.add_argument("--source", required=True, help="already downloaded player_box_YEAR.csv")
    parser.add_argument("--player-id", required=True, help="ESPN athlete_id, not nba_api player ID")
    parser.add_argument("--output", required=True)
    parser.add_argument("--confirm-private-research", action="store_true")
    args = parser.parse_args()
    try:
        result = prepare_historical_browser_csv(
            args.source, args.output,
            player_id=args.player_id,
            acknowledge_private_research=args.confirm_private_research,
        )
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
