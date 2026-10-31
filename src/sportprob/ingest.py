"""CSV ingestion with fail-closed type validation."""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from .schema import GameLog

REQUIRED = {
    "game_id", "player_id", "game_date", "opponent", "home",
    "minutes", "points", "rebounds", "assists",
}


def _parse_home(value: str) -> bool | None:
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized in ("true", "1"):
        return True
    if normalized in ("false", "0"):
        return False
    raise ValueError("home must be true, false, 1, 0, or empty")


def load_game_logs(path: str | Path) -> list[GameLog]:
    """Load and validate CSV; reject bad records rather than inventing values."""
    logs: list[GameLog] = []
    seen: set[tuple[str, str]] = set()
    with Path(path).open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            missing = sorted(REQUIRED - set(reader.fieldnames or []))
            raise ValueError(f"missing CSV columns: {', '.join(missing)}")
        for row_index, row in enumerate(reader, start=2):
            try:
                if None in row:
                    raise ValueError("unexpected extra fields")
                record = GameLog(
                    game_id=row["game_id"].strip(),
                    player_id=row["player_id"].strip(),
                    game_date=date.fromisoformat(row["game_date"].strip()),
                    opponent=row["opponent"].strip(),
                    home=_parse_home(row["home"]),
                    minutes=float(row["minutes"]),
                    points=int(row["points"]),
                    rebounds=int(row["rebounds"]),
                    assists=int(row["assists"]),
                )
                key = (record.player_id, record.game_id)
                if key in seen:
                    raise ValueError(f"duplicate game for player: {key}")
                seen.add(key)
                logs.append(record)
            except (ValueError, TypeError, AttributeError, KeyError) as exc:
                raise ValueError(f"CSV row {row_index}: {exc}") from exc
    if not logs:
        raise ValueError("CSV has no observations")
    return sorted(logs, key=lambda r: (r.game_date, r.game_id, r.player_id))
