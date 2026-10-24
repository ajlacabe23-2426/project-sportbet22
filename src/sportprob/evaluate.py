"""Walk-forward evaluation with strictly pre-event features."""
from __future__ import annotations

from dataclasses import dataclass
from math import log

from .model import forecast
from .schema import GameLog, STATS


@dataclass(frozen=True, slots=True)
class Evaluation:
    player_id: str
    stat: str
    evaluated_games: int
    mean_negative_log_likelihood: float
    coverage_80: float
    coverage_90: float
    average_width_80: float


def backtest(
    logs: list[GameLog],
    player_id: str,
    stat: str,
    *,
    min_games: int = 5,
    history_games: int = 20,
) -> Evaluation:
    if stat not in STATS:
        raise ValueError(f"unsupported stat: {stat}")
    games = sorted(
        (r for r in logs if r.player_id == player_id and r.minutes > 0),
        key=lambda r: (r.game_date, r.game_id),
    )
    if len(games) <= min_games:
        raise ValueError("not enough games for chronological holdout")
    evaluations: list[tuple[float, int, int, int]] = []
    for observed in games:
        # Uses only earlier dates; a same-day observation is never training data.
        earlier = [r for r in games if r.game_date < observed.game_date]
        if len(earlier) < min_games:
            continue
        prediction = forecast(
            earlier, player_id, stat, observed.game_date,
            min_games=min_games, history_games=history_games,
        )
        actual = getattr(observed, stat)
        likelihood = prediction.pmf[actual] if actual < len(prediction.pmf) else 0
        low80, high80 = prediction.central_interval(0.8)
        low90, high90 = prediction.central_interval(0.9)
        evaluations.append((
            -log(max(likelihood, 1e-15)),
            int(low80 <= actual <= high80),
            int(low90 <= actual <= high90),
            high80 - low80,
        ))
    if not evaluations:
        raise ValueError("no eligible holdout games")
    n = len(evaluations)
    return Evaluation(
        player_id=player_id, stat=stat, evaluated_games=n,
        mean_negative_log_likelihood=sum(r[0] for r in evaluations) / n,
        coverage_80=sum(r[1] for r in evaluations) / n,
        coverage_90=sum(r[2] for r in evaluations) / n,
        average_width_80=sum(r[3] for r in evaluations) / n,
    )
