"""Point-in-time, retrospective player-performance context.

Research-only descriptions of completed games. No proposed target line,
wagering probabilities, sportsbook information, or future event decisions.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from math import ceil, sqrt
from statistics import mean, median, stdev

from .schema import GameLog, STATS


@dataclass(frozen=True, slots=True)
class ObservedGroup:
    games: int
    average: float
    average_minutes: float


@dataclass(frozen=True, slots=True)
class PlayerHistoricalContext:
    schema: str
    research_only: bool
    future_prediction: bool
    player_id: str
    stat: str
    as_of_exclusive: str
    games_used: int
    first_game: str
    last_game: str
    average: float
    median: float
    sample_standard_deviation: float
    observed_10th_percentile: int
    observed_90th_percentile: int
    average_minutes: float
    production_per_36_played_minutes: float
    last_five_average: float
    preceding_five_average: float | None
    home_games: ObservedGroup | None
    away_games: ObservedGroup | None
    opponent_samples: dict[str, ObservedGroup]
    missing_home_flags: int
    note: str


def _percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    return ordered[max(0, ceil(len(ordered) * fraction) - 1)]


def _group(rows: list[GameLog], stat: str) -> ObservedGroup | None:
    if not rows:
        return None
    return ObservedGroup(
        games=len(rows),
        average=round(mean(getattr(r, stat) for r in rows), 3),
        average_minutes=round(mean(r.minutes for r in rows), 3),
    )


def describe_historical_context(
    logs: list[GameLog], player_id: str, stat: str, as_of: date, *,
    history_games: int = 40, min_games: int = 5,
) -> PlayerHistoricalContext:
    """Summarize only strictly earlier, played games.

    Historical opponent and venue samples are observational; they must not be
    represented as causally estimated matchup effects or next-game outcomes.
    """
    if stat not in STATS:
        raise ValueError("unsupported statistic")
    if type(as_of) is not date:
        raise ValueError("as_of must be a date")
    if not player_id or not player_id.strip():
        raise ValueError("player_id must be nonempty")
    if not 5 <= history_games <= 200 or not 5 <= min_games <= history_games:
        raise ValueError("history_games and min_games must be between 5 and 200")
    rows = sorted(
        (
            r for r in logs
            if r.player_id == player_id and r.game_date < as_of and r.minutes > 0
        ),
        key=lambda r: (r.game_date, r.game_id),
    )[-history_games:]
    if len(rows) < min_games:
        raise ValueError(f"at least {min_games} prior played games required")
    values = [getattr(r, stat) for r in rows]
    hours = sum(r.minutes for r in rows)
    opponents: dict[str, list[GameLog]] = defaultdict(list)
    for row in rows:
        if row.opponent.strip():
            opponents[row.opponent.strip()].append(row)
    # Minimum sample threshold prevents single-game opponent splits being
    # misread as a meaningful trend. Do not rank these samples.
    opponent_samples = {
        name: group
        for name, games in sorted(opponents.items())
        if len(games) >= 3
        if (group := _group(games, stat)) is not None
    }
    return PlayerHistoricalContext(
        schema="sportprob-retrospective-context-v1",
        research_only=True,
        future_prediction=False,
        player_id=player_id,
        stat=stat,
        as_of_exclusive=as_of.isoformat(),
        games_used=len(rows),
        first_game=rows[0].game_date.isoformat(),
        last_game=rows[-1].game_date.isoformat(),
        average=round(mean(values), 3),
        median=round(median(values), 3),
        sample_standard_deviation=round(stdev(values), 3),
        observed_10th_percentile=_percentile(values, .10),
        observed_90th_percentile=_percentile(values, .90),
        average_minutes=round(mean(r.minutes for r in rows), 3),
        production_per_36_played_minutes=round(36 * sum(values) / hours, 3),
        last_five_average=round(mean(values[-5:]), 3),
        preceding_five_average=(
            round(mean(values[-10:-5]), 3) if len(values) >= 10 else None
        ),
        home_games=_group([r for r in rows if r.home is True], stat),
        away_games=_group([r for r in rows if r.home is False], stat),
        opponent_samples=opponent_samples,
        missing_home_flags=sum(r.home is None for r in rows),
        note=(
            "Observed completed games only; percentile range is historical "
            "and is not a forecast or the probability of a proposed line. "
            "Venue and opponent splits do not establish causality or accuracy."
        ),
    )
