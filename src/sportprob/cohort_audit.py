"""Checksum-gated, retrospective multi-player model diagnostics.

Offline educational analysis only. This does not obtain NBA data or evaluate
sportsbook lines. Choosing a cutoff after seeing outcomes is not a genuine
prospective test. Distribution parameters are provisional.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict
from datetime import date
import json

from .compare import compare_frozen_distributions
from .governance import DatasetManifest, verify_snapshot
from .ingest import load_game_logs
from .schema import GameLog, STATS


def audit_cohort(
    logs: list[GameLog], *,
    holdout_start: date,
    holdout_end_exclusive: date | None = None,
    min_training_games: int = 10,
    min_holdout_games: int = 5,
) -> dict:
    """Summarize every player's sample and frozen historical comparison.

    Training examples are always before holdout_start. Every held-out player
    evaluation uses the *same* frozen training history; held-out outcomes do
    not update any model. No pooled model ranking or wagering selection.
    """
    if type(holdout_start) is not date:
        raise ValueError("holdout_start must be a calendar date")
    if holdout_end_exclusive is not None and (
        type(holdout_end_exclusive) is not date
        or holdout_end_exclusive <= holdout_start
    ):
        raise ValueError("holdout_end must follow holdout_start")
    if not (5 <= min_training_games <= 100 and 2 <= min_holdout_games <= 100):
        raise ValueError("minimum training/holdout sizes must be within configured bounds")
    if not logs or len(logs) > 20000:
        raise ValueError("cohort requires 1 to 20,000 completed-game records")

    by_player: dict[str, list[GameLog]] = defaultdict(list)
    for row in logs:
        by_player[row.player_id].append(row)
    if len(by_player) > 100:
        raise ValueError("cohort supports at most 100 distinct players")

    players = []
    for player_id, records in sorted(by_player.items()):
        played = sorted((r for r in records if r.minutes > 0),
                        key=lambda r: (r.game_date, r.game_id))
        training = [r for r in played if r.game_date < holdout_start]
        held_out = [
            r for r in played if r.game_date >= holdout_start and
            (holdout_end_exclusive is None or r.game_date < holdout_end_exclusive)
        ]
        reasons = []
        if len(training) < min_training_games:
            reasons.append("INSUFFICIENT_FROZEN_TRAINING_GAMES")
        if len(held_out) < min_holdout_games:
            reasons.append("INSUFFICIENT_HISTORICAL_HOLDOUT_GAMES")
        if len({r.opponent for r in played}) < 5:
            reasons.append("LOW_OPPONENT_DIVERSITY")
        if any(r.home is None for r in played):
            reasons.append("MISSING_HOME_AWAY_CONTEXT")
        eligible = len(training) >= min_training_games and len(held_out) >= min_holdout_games
        comparisons = {}
        if eligible:
            for stat in STATS:
                result = compare_frozen_distributions(
                    records, player_id, stat,
                    holdout_start=holdout_start,
                    holdout_end_exclusive=holdout_end_exclusive,
                    history_games=max(20, min_training_games),
                    min_games=min_training_games,
                )
                comparisons[stat] = {
                    "evaluated_games": result.evaluated_games,
                    "training_policy": result.training_policy,
                    "calibration_status": result.calibration_status,
                    "scores": [asdict(score) for score in result.scores],
                }
        players.append({
            "player_id": player_id,
            "played_games": len(played),
            "frozen_training_games": len(training),
            "historical_holdout_games": len(held_out),
            "first_completed_game": played[0].game_date.isoformat() if played else None,
            "last_completed_game": played[-1].game_date.isoformat() if played else None,
            "eligible_for_retrospective_comparison": eligible,
            "review_reasons": reasons,
            "stat_diagnostics": comparisons,
        })
    return {
        "schema": "sportprob-offline-cohort-evaluation-v1",
        "research_only": True,
        "future_game_predictions": False,
        "sportsbook_connected": False,
        "future_outcomes_used_in_training": False,
        "independently_verified_model_accuracy": False,
        "holdout_start": holdout_start.isoformat(),
        "holdout_end_exclusive": (
            holdout_end_exclusive.isoformat() if holdout_end_exclusive else None
        ),
        "training_policy": "frozen_pre_holdout_only",
        "minimum_training_games": min_training_games,
        "minimum_holdout_games": min_holdout_games,
        "player_count": len(players),
        "eligible_player_count": sum(p["eligible_for_retrospective_comparison"] for p in players),
        "players": players,
        "interpretation": (
            "All statistics describe completed games; model diagnostics use "
            "only pre-cutoff fitting records. This does not prove independent "
            "blind validation, future accuracy, source rights, or predictive "
            "reliability. Do not use for wagering decisions."
        ),
    }


def audit_local_cohort(
    data_path: str, manifest_path: str, *,
    holdout_start: date, holdout_end_exclusive: date | None = None,
    min_training_games: int = 10, min_holdout_games: int = 5,
) -> dict:
    manifest = DatasetManifest.from_file(manifest_path)
    digest = verify_snapshot(data_path, manifest)
    logs = load_game_logs(data_path)
    result = audit_cohort(
        logs, holdout_start=holdout_start,
        holdout_end_exclusive=holdout_end_exclusive,
        min_training_games=min_training_games,
        min_holdout_games=min_holdout_games,
    )
    return {
        **result, "dataset_id": manifest.dataset_id,
        "dataset_source": manifest.source_name,
        "dataset_sha256": digest, "synthetic": manifest.synthetic,
        "source_authenticity_independently_verified": False,
        "source_rights_independently_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline, frozen retrospective multi-player evaluation"
    )
    parser.add_argument("--data", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--holdout-start", required=True)
    parser.add_argument("--holdout-end")
    parser.add_argument("--min-training-games", type=int, default=10)
    parser.add_argument("--min-holdout-games", type=int, default=5)
    args = parser.parse_args()
    try:
        result = audit_local_cohort(
            args.data, args.manifest,
            holdout_start=date.fromisoformat(args.holdout_start),
            holdout_end_exclusive=(
                date.fromisoformat(args.holdout_end) if args.holdout_end else None
            ),
            min_training_games=args.min_training_games,
            min_holdout_games=args.min_holdout_games,
        )
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
