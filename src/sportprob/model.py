"""Simple, inspectable count-stat forecasting baseline.

A Gamma–Poisson rate model is combined with provisional game variation.
The final Negative Binomial distribution moment-matches both uncertainty
sources; its game-dispersion hyperparameter is not yet learned from data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import exp, isfinite, log
from statistics import median

from .schema import GameLog, STATS

# Baseline research assumptions only, NOT calibrated NBA parameters.
PRIOR_RATES = {"points": 0.60, "rebounds": 0.20, "assists": 0.13}
GAME_SHAPES = {"points": 9.0, "rebounds": 7.0, "assists": 6.0}
PRIOR_EXPOSURE_MINUTES = 80.0


@dataclass(frozen=True, slots=True)
class Bucket:
    low: int
    high: int
    probability: float


@dataclass(frozen=True, slots=True)
class Forecast:
    player_id: str
    stat: str
    as_of: date
    training_games: int
    projected_minutes: float
    expected_stat: float
    variance: float
    pmf: tuple[float, ...]

    def quantile(self, probability: float) -> int:
        if not 0.0 <= probability <= 1.0:
            raise ValueError("quantile probability must be between 0 and 1")
        cumulative = 0.0
        for outcome, mass in enumerate(self.pmf):
            cumulative += mass
            if cumulative >= probability:
                return outcome
        return len(self.pmf) - 1

    def central_interval(self, coverage: float = 0.8) -> tuple[int, int]:
        if not 0.0 < coverage < 1.0:
            raise ValueError("coverage must be in (0, 1)")
        tail = (1.0 - coverage) / 2.0
        return (self.quantile(tail), self.quantile(1.0 - tail))

    def buckets(self, width: int = 5) -> tuple[Bucket, ...]:
        if width < 1:
            raise ValueError("bucket width must be positive")
        return tuple(
            Bucket(low, min(low + width - 1, len(self.pmf) - 1),
                   sum(self.pmf[low:low + width]))
            for low in range(0, len(self.pmf), width)
        )

    def modal_bucket(self, width: int = 5) -> Bucket:
        return max(self.buckets(width), key=lambda bucket: bucket.probability)


def negative_binomial_pmf(mean: float, shape: float) -> tuple[float, ...]:
    """Return a normalized PMF with <1e-10 omitted right-tail mass."""
    if not isfinite(mean) or mean < 0 or not isfinite(shape) or shape <= 0:
        raise ValueError("mean must be nonnegative; shape must be positive")
    if mean == 0:
        return (1.0,)
    success = shape / (shape + mean)
    current = exp(shape * log(success))
    masses = [current]
    total = current
    for k in range(1, 1001):
        current *= ((k - 1 + shape) / k) * (1.0 - success)
        masses.append(current)
        total += current
        if total >= 1.0 - 1e-12 and k > mean:
            break
    if total < 1.0 - 1e-10:
        raise ValueError("distribution exceeded computation support")
    return tuple(m / total for m in masses)


def forecast(
    logs: list[GameLog],
    player_id: str,
    stat: str,
    as_of: date,
    *,
    history_games: int = 20,
    projected_minutes: float | None = None,
    min_games: int = 5,
) -> Forecast:
    """Forecast a future game from only games strictly earlier than as_of."""
    if stat not in STATS:
        raise ValueError(f"unsupported stat: {stat}; choose one of {STATS}")
    if history_games < 1 or min_games < 1 or min_games > history_games:
        raise ValueError("invalid history_games or min_games")
    history = sorted(
        (r for r in logs if r.player_id == player_id
         and r.game_date < as_of and r.minutes > 0),
        key=lambda r: (r.game_date, r.game_id),
    )[-history_games:]
    if len(history) < min_games:
        raise ValueError(f"at least {min_games} prior played games required")
    if projected_minutes is None:
        projected_minutes = float(median(r.minutes for r in history[-5:]))
    if not isfinite(projected_minutes) or not 0 < projected_minutes <= 80:
        raise ValueError("projected_minutes must be finite and in (0, 80]")
    prior_shape = PRIOR_RATES[stat] * PRIOR_EXPOSURE_MINUTES
    posterior_shape = prior_shape + sum(getattr(r, stat) for r in history)
    posterior_rate = PRIOR_EXPOSURE_MINUTES + sum(r.minutes for r in history)
    expected = projected_minutes * posterior_shape / posterior_rate

    # Moment match: relative variance of the product of two independent
    # Gamma intensity factors, one posterior and one game-to-game.
    posterior_cv2 = 1.0 / posterior_shape
    game_cv2 = 1.0 / GAME_SHAPES[stat]
    combined_cv2 = posterior_cv2 + game_cv2 + posterior_cv2 * game_cv2
    effective_shape = 1.0 / combined_cv2
    variance = expected + expected * expected / effective_shape
    pmf = negative_binomial_pmf(expected, effective_shape)
    return Forecast(
        player_id=player_id, stat=stat, as_of=as_of,
        training_games=len(history), projected_minutes=projected_minutes,
        expected_stat=expected, variance=variance, pmf=pmf,
    )
