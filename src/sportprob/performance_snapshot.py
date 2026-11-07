"""Checksum-bound, point-in-time three-stat player research snapshot.

No sportsbook, lines, wagering recommendations, or automatic external data.
Input is an authorized local canonical game-log CSV and its immutable manifest.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
from statistics import mean, median

from .governance import DatasetManifest, verify_snapshot
from .ingest import load_game_logs
from .model import forecast
from .schema import STATS, GameLog


def build_player_snapshot(
    logs: list[GameLog], player_id: str, as_of: date,
    *, projected_minutes: float | None = None,
) -> dict:
    """Assemble independent points/rebounds/assists estimates using past games only."""
    history = sorted(
        (row for row in logs if row.player_id == player_id
         and row.game_date < as_of and row.minutes > 0),
        key=lambda row: (row.game_date, row.game_id),
    )
    if len(history) < 5:
        raise ValueError("At least five completed games before --as-of are required")
    recent = history[-20:]
    last_five = recent[-5:]
    results: dict[str, dict] = {}
    for stat in STATS:
        estimate = forecast(
            logs, player_id, stat, as_of, projected_minutes=projected_minutes
        )
        results[stat] = {
            "projected_mean": round(estimate.expected_stat, 3),
            "model_variance": round(estimate.variance, 3),
            "model_interval_80": list(estimate.central_interval(0.8)),
            "model_interval_90": list(estimate.central_interval(0.9)),
            "observed_last_5_mean": round(mean(getattr(r, stat) for r in last_five), 3),
            "observed_last_20_mean": round(mean(getattr(r, stat) for r in recent), 3),
            "observed_last_20_median": round(median(getattr(r, stat) for r in recent), 3),
        }
    latest = history[-1]
    return {
        "schema": "sportprob-player-tri-stat-snapshot-v1",
        "mode": "OFFLINE_STATISTICAL_RESEARCH",
        "player_id": player_id,
        "as_of_exclusive": as_of.isoformat(),
        "last_observed_game": latest.game_date.isoformat(),
        "training_games": len(recent),
        "projected_minutes": round(
            forecast(logs, player_id, "points", as_of,
                     projected_minutes=projected_minutes).projected_minutes, 2
        ),
        "stats": results,
        "limitations": {
            "model": "Uncalibrated Gamma-Poisson / Negative Binomial baseline",
            "future_results_used_for_estimate": False,
            "upcoming_game_or_availability_confirmed": False,
            "opponent_and_injury_context_modeled": False,
            "independent_predictive_accuracy_verified": False,
            "wagering_or_order_execution": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline, non-wagering NBA stat research")
    parser.add_argument("--data", required=True, help="canonical, permitted game-log CSV")
    parser.add_argument("--manifest", required=True, help="checksum and research permission")
    parser.add_argument("--player", required=True, help="player ID in the CSV")
    parser.add_argument("--as-of", required=True, help="YYYY-MM-DD exclusive estimate date")
    parser.add_argument("--minutes", type=float, help="optional hypothetical minutes")
    parser.add_argument("--output", help="optional new .json file; never overwrites")
    args = parser.parse_args()
    try:
        manifest = DatasetManifest.from_file(args.manifest)
        digest = verify_snapshot(args.data, manifest)
        output = build_player_snapshot(
            load_game_logs(args.data), args.player, date.fromisoformat(args.as_of),
            projected_minutes=args.minutes,
        )
        output.update({
            "dataset_id": manifest.dataset_id,
            "source_name": manifest.source_name,
            "dataset_sha256": digest,
            "synthetic": manifest.synthetic,
            "data_rights_independently_verified": False,
        })
        payload = json.dumps(output, indent=2, allow_nan=False) + "\n"
        if args.output:
            destination = Path(args.output)
            if destination.suffix.lower() != ".json":
                raise ValueError("--output must end in .json")
            with destination.open("x", encoding="utf-8") as handle:
                handle.write(payload)
            print(f"Created local research snapshot: {destination}")
        else:
            print(payload, end="")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
