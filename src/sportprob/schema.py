"""Typed, validated source observations."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite


STATS = ("points", "rebounds", "assists")


@dataclass(frozen=True, slots=True)
class GameLog:
    game_id: str
    player_id: str
    game_date: date
    opponent: str
    home: bool | None
    minutes: float
    points: int
    rebounds: int
    assists: int

    def __post_init__(self) -> None:
        if not self.game_id.strip() or not self.player_id.strip():
            raise ValueError("game_id and player_id must not be empty")
        if not isfinite(self.minutes) or not 0 <= self.minutes <= 80:
            raise ValueError("minutes must be finite and between 0 and 80")
        for stat in STATS:
            value = getattr(self, stat)
            if type(value) is not int or value < 0:
                raise ValueError(f"{stat} must be a nonnegative integer")
        if self.minutes == 0 and any(getattr(self, stat) != 0 for stat in STATS):
            raise ValueError("nonzero stats require positive playing time")
        if not isinstance(self.game_date, date):
            raise ValueError("game_date must be a date")
        if self.home is not None and type(self.home) is not bool:
            raise ValueError("home must be boolean or null")
