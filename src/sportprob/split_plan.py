"""Reproducible chronological partition planning for completed-game research.

This is retrospective exploration, not a claim of genuinely untouched future
outcomes: the source CSV may have been inspected before the cutoff was chosen.
No odds, proposed-stat threshold, or next-game forecasts are produced.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json

from .governance import DatasetManifest, verify_snapshot
from .ingest import load_game_logs
from .research_check import inspect_research_readiness
from .schema import GameLog


def plan_historical_partitions(
    records: list[GameLog], *, player_id: str, synthetic: bool
) -> dict:
    """Use fixed 65%/15%/20% targets and never split a common calendar date."""
    played = sorted(
        (r for r in records if r.player_id == player_id and r.minutes > 0),
        key=lambda r: (r.game_date, r.game_id),
    )
    if len(played) < 50:
        raise ValueError("at least 50 played games required to plan three partitions")
    by_date = Counter(r.game_date for r in played)
    counts = sorted(by_date.items())
    if len(counts) < 3:
        raise ValueError("at least three distinct calendar dates required")
    n = len(played)
    cut_targets = (n * 0.65, n * 0.80)
    cumulative = 0
    cut_points: list[date] = []
    # Cutoff date is the first date in the NEXT partition. Boundary data
    # selection uses record dates only, never the observed stat values.
    for i, (game_date, count) in enumerate(counts):
        cumulative += count
        while len(cut_points) < 2 and cumulative >= cut_targets[len(cut_points)]:
            if i + 1 >= len(counts):
                raise ValueError("not enough calendar dates to create all partitions")
            cut_points.append(counts[i + 1][0])
    if len(cut_points) != 2 or cut_points[0] >= cut_points[1]:
        raise ValueError("cannot make three nonoverlapping calendar partitions")

    train_end, holdout_start = cut_points
    result = inspect_research_readiness(
        records, player_id, synthetic=synthetic,
        train_end=train_end, holdout_start=holdout_start,
    )
    return {
        "schema": "sportprob-retrospective-partition-plan-v1",
        "research_only": True,
        "partition_rule": "chronological_by_calendar_date_fixed_65_15_20",
        "training_end_exclusive": train_end.isoformat(),
        "holdout_start_inclusive": holdout_start.isoformat(),
        "train_played_games": result.train_played_games,
        "calibration_played_games": result.calibration_played_games,
        "historical_evaluation_games": result.holdout_played_games,
        "readiness_status": result.status,
        "quality_issues": list(result.issues),
        "observed_outcomes_previously_visible": True,
        "genuinely_untouched_forward_validation": False,
        "real_world_model_accuracy_established": False,
        "note": (
            "Fixed, reproducible historical partition only. The player "
            "records were already available for inspection, so this is NOT "
            "a prospective blind validation. No model fitting or model "
            "selection is performed by this command."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plan descriptive training/calibration/evaluation partitions"
    )
    parser.add_argument("--data", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--player", required=True)
    args = parser.parse_args()
    try:
        manifest = DatasetManifest.from_file(args.manifest)
        digest = verify_snapshot(args.data, manifest)
        logs = load_game_logs(args.data)
        output = plan_historical_partitions(
            logs, player_id=args.player, synthetic=manifest.synthetic
        )
        output.update({
            "dataset_id": manifest.dataset_id,
            "dataset_sha256": digest,
            "source_name": manifest.source_name,
            "source_rights_independently_verified": False,
        })
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
