"""Frozen-holdout comparison of two inspectable count distributions.

Educational research only. The Poisson benchmark uses the same expected
counts and projected minutes as the existing Gamma–Poisson/Negative Binomial
model; this isolates the effects of distributional dispersion.

Every holdout observation is evaluated against forecasts fitted strictly to
the pre-holdout training partition. No sportsbook inputs or wagering outputs.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from math import exp, floor, isfinite, lgamma, log

from .holdout import wilson_coverage_interval
from .model import Forecast, forecast
from .schema import GameLog, STATS


def poisson_pmf(mean: float) -> tuple[float, ...]:
    """Numerically stable normalized Poisson PMF, with bounded tail truncation."""
    if not isfinite(mean) or mean < 0 or mean > 2000:
        raise ValueError("Poisson mean must be finite and in [0, 2000]")
    if mean == 0:
        return (1.0,)
    mode = floor(mean)
    masses = [0.0] * (mode + 1)
    masses[mode] = exp(-mean + mode * log(mean) - lgamma(mode + 1))
    for k in range(mode, 0, -1):
        masses[k - 1] = masses[k] * k / mean
    total = sum(masses)
    k = mode
    while total < 1.0 - 1e-12 and k < 10000:
        masses.append(masses[-1] * mean / (k + 1))
        total += masses[-1]
        k += 1
    if total < 1.0 - 1e-10:
        raise ValueError("Poisson distribution exceeded computation support")
    return tuple(p / total for p in masses)


def ranked_probability_score(pmf: tuple[float, ...], actual: int) -> float:
    """Proper score across every count threshold; lower is better.

    This is an evaluation diagnostic, not a bet selection or payoff metric.
    """
    if type(actual) is not int or not 0 <= actual <= 5000:
        raise ValueError("actual statistic must be a count from 0 to 5000")
    if not pmf or any(not isfinite(p) or p < 0 for p in pmf):
        raise ValueError("PMF must contain finite nonnegative probabilities")
    if abs(sum(pmf) - 1.0) > 1e-8:
        raise ValueError("PMF must be normalized")
    total = cumulative = 0.0
    for k in range(max(len(pmf), actual + 1)):
        if k < len(pmf):
            cumulative += pmf[k]
        target = 1.0 if k >= actual else 0.0
        total += (min(1.0, cumulative) - target) ** 2
    return total


@dataclass(frozen=True, slots=True)
class ModelScore:
    model: str
    evaluated_games: int
    mean_negative_log_likelihood: float
    mean_ranked_probability_score: float
    mean_absolute_error: float
    mean_bias_observed_minus_expected: float
    coverage_80: float
    coverage_90: float
    mean_interval_width_80: float
    coverage_80_wilson_95: tuple[float, float]
    coverage_90_wilson_95: tuple[float, float]


@dataclass(frozen=True, slots=True)
class FrozenModelComparison:
    player_id: str
    stat: str
    holdout_start: str
    holdout_end_exclusive: str | None
    training_games: int
    evaluated_games: int
    training_policy: str
    comparison_purpose: str
    calibration_status: str
    scores: tuple[ModelScore, ...]


def _score(
    model: str, predictions: list[tuple[Forecast, int]]
) -> ModelScore:
    n = len(predictions)
    nll = rps = absolute_error = bias = width = 0.0
    covered80 = covered90 = 0
    for predicted, actual in predictions:
        mass = predicted.pmf[actual] if actual < len(predicted.pmf) else 0.0
        nll -= log(max(1e-15, mass))
        rps += ranked_probability_score(predicted.pmf, actual)
        absolute_error += abs(actual - predicted.expected_stat)
        bias += actual - predicted.expected_stat
        lo80, hi80 = predicted.central_interval(0.8)
        lo90, hi90 = predicted.central_interval(0.9)
        covered80 += int(lo80 <= actual <= hi80)
        covered90 += int(lo90 <= actual <= hi90)
        width += hi80 - lo80
    return ModelScore(
        model=model,
        evaluated_games=n,
        mean_negative_log_likelihood=nll / n,
        mean_ranked_probability_score=rps / n,
        mean_absolute_error=absolute_error / n,
        mean_bias_observed_minus_expected=bias / n,
        coverage_80=covered80 / n,
        coverage_90=covered90 / n,
        mean_interval_width_80=width / n,
        coverage_80_wilson_95=wilson_coverage_interval(covered80, n),
        coverage_90_wilson_95=wilson_coverage_interval(covered90, n),
    )


def compare_frozen_distributions(
    logs: list[GameLog],
    player_id: str,
    stat: str,
    *,
    holdout_start: date,
    holdout_end_exclusive: date | None = None,
    history_games: int = 20,
    min_games: int = 5,
) -> FrozenModelComparison:
    """Compare NB and same-mean Poisson on a genuinely frozen holdout.

    This function deliberately performs no automatic model selection or fitting
    on withheld observations. Hyperparameters remain provisional.
    """
    if stat not in STATS:
        raise ValueError(f"unsupported stat: {stat}")
    if type(holdout_start) is not date:
        raise ValueError("holdout_start must be a calendar date")
    if holdout_end_exclusive is not None and (
        type(holdout_end_exclusive) is not date
        or holdout_end_exclusive <= holdout_start
    ):
        raise ValueError("holdout_end_exclusive must follow holdout_start")
    if min_games < 1 or history_games < min_games:
        raise ValueError("invalid history_games or min_games")
    rows = sorted(
        (r for r in logs if r.player_id == player_id),
        key=lambda row: (row.game_date, row.game_id),
    )
    ids = [r.game_id for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate player/game ID in comparison data")
    development = [r for r in rows if r.game_date < holdout_start and r.minutes > 0]
    held_out = [
        r for r in rows
        if r.minutes > 0
        and r.game_date >= holdout_start
        and (holdout_end_exclusive is None or r.game_date < holdout_end_exclusive)
    ]
    if len(development) < min_games:
        raise ValueError("not enough pre-holdout played games")
    if not held_out:
        raise ValueError("no eligible holdout games")
    nb_predictions: list[tuple[Forecast, int]] = []
    poisson_predictions: list[tuple[Forecast, int]] = []
    for row in held_out:
        baseline = forecast(
            development, player_id, stat, row.game_date,
            history_games=history_games, min_games=min_games,
        )
        observed = getattr(row, stat)
        if observed > 5000:
            raise ValueError("observed count exceeds comparison support")
        nb_predictions.append((baseline, observed))
        poisson_predictions.append((
            replace(
                baseline,
                pmf=poisson_pmf(baseline.expected_stat),
                variance=baseline.expected_stat,
            ),
            observed,
        ))
    return FrozenModelComparison(
        player_id=player_id,
        stat=stat,
        holdout_start=holdout_start.isoformat(),
        holdout_end_exclusive=(
            holdout_end_exclusive.isoformat() if holdout_end_exclusive else None
        ),
        training_games=min(len(development), history_games),
        evaluated_games=len(held_out),
        training_policy="frozen_pre_holdout_only",
        comparison_purpose="descriptive_model_validation_not_wager_selection",
        calibration_status="UNVERIFIED_RESEARCH_BASELINES",
        scores=(
            _score("negative_binomial_provisional", nb_predictions),
            _score("poisson_same_mean_benchmark", poisson_predictions),
        ),
    )
