"""A frozen, chronological player-stat holdout for educational research.

Every evaluation forecast uses *only* observations dated before holdout_start.
No held-out result is used for training, parameter fitting or projected minutes.
Model dispersion hyperparameters remain provisional, not NBA-calibrated.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import log

from .model import forecast
from .schema import GameLog, STATS


@dataclass(frozen=True, slots=True)
class FrozenHoldout:
    player_id: str
    stat: str
    holdout_start: str
    first_evaluated_date: str
    last_evaluated_date: str
    training_games: int
    evaluated_games: int
    mean_negative_log_likelihood: float
    coverage_80: float
    coverage_90: float
    average_width_80: float
    average_width_90: float
    training_policy: str = "frozen_pre_holdout_only"
    calibrated_on_real_nba_data: bool = False


def evaluate_frozen_holdout(
    logs: list[GameLog],
    player_id: str,
    stat: str,
    *,
    holdout_start: date,
    holdout_end_exclusive: date | None = None,
    history_games: int = 20,
    min_games: int = 5,
) -> FrozenHoldout:
    """Score genuinely withheld outcomes without updating from holdout events.

    The user must choose the cutoff before inspecting held-out outcomes. This
    function checks separation, not whether the choice was made independently.
    """
    if stat not in STATS:
        raise ValueError(f"unsupported stat: {stat}")
    if type(holdout_start) is not date:
        raise ValueError("holdout_start must be a calendar date")
    if holdout_end_exclusive is not None and (
        type(holdout_end_exclusive) is not date or holdout_end_exclusive <= holdout_start
    ):
        raise ValueError("holdout_end_exclusive must follow holdout_start")
    if min_games < 1 or history_games < min_games:
        raise ValueError("invalid history_games or min_games")

    records = sorted(
        (r for r in logs if r.player_id == player_id),
        key=lambda r: (r.game_date, r.game_id),
    )
    keys = [r.game_id for r in records]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate player/game ID in evaluation data")

    development = [r for r in records if r.game_date < holdout_start and r.minutes > 0]
    observed = [
        r for r in records
        if r.game_date >= holdout_start
        and (holdout_end_exclusive is None or r.game_date < holdout_end_exclusive)
        and r.minutes > 0
    ]
    if len(development) < min_games:
        raise ValueError("not enough pre-holdout played games")
    if not observed:
        raise ValueError("no eligible holdout games")

    # Keep all held-out rows out of forecast(), including earlier held-out
    # dates. Consecutive held-out events thus use one frozen source history.
    nll = cov80 = cov90 = width80 = width90 = 0.0
    for row in observed:
        prediction = forecast(
            development, player_id, stat, row.game_date,
            history_games=history_games, min_games=min_games,
        )
        actual = getattr(row, stat)
        likelihood = prediction.pmf[actual] if actual < len(prediction.pmf) else 0.0
        nll += -log(max(likelihood, 1e-15))
        lo80, hi80 = prediction.central_interval(0.8)
        lo90, hi90 = prediction.central_interval(0.9)
        cov80 += int(lo80 <= actual <= hi80)
        cov90 += int(lo90 <= actual <= hi90)
        width80 += hi80 - lo80
        width90 += hi90 - lo90

    n = len(observed)
    return FrozenHoldout(
        player_id=player_id,
        stat=stat,
        holdout_start=holdout_start.isoformat(),
        first_evaluated_date=observed[0].game_date.isoformat(),
        last_evaluated_date=observed[-1].game_date.isoformat(),
        training_games=min(len(development), history_games),
        evaluated_games=n,
        mean_negative_log_likelihood=nll / n,
        coverage_80=cov80 / n,
        coverage_90=cov90 / n,
        average_width_80=width80 / n,
        average_width_90=width90 / n,
    )
