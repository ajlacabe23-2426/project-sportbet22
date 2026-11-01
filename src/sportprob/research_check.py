"""Read-only readiness audit for locally supplied player-game observations.

A structurally ready dataset is NOT evidence of a licensed source or of
out-of-sample forecasting accuracy. All inputs remain local.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
import json

from .governance import DatasetManifest, audit_split, split_by_date, verify_snapshot
from .ingest import load_game_logs
from .schema import GameLog


@dataclass(frozen=True, slots=True)
class ResearchReadiness:
    status: str
    player_id: str
    total_rows: int
    selected_player_rows: int
    played_games: int
    first_game: str | None
    last_game: str | None
    unique_opponents: int
    train_played_games: int
    calibration_played_games: int
    holdout_played_games: int
    missing_opponent_rows: int
    missing_home_flags: int
    same_day_extra_games: int
    future_dated_rows: int
    issues: tuple[str, ...]


def inspect_research_readiness(
    logs: list[GameLog], player_id: str, *,
    synthetic: bool,
    train_end: date,
    holdout_start: date,
    min_train: int = 30,
    min_calibration: int = 10,
    min_holdout: int = 10,
) -> ResearchReadiness:
    """Check sample sufficiency and point-in-time separation before fitting."""
    if not player_id.strip():
        raise ValueError("player_id required")
    if not all(type(x) is int and 1 <= x <= 500 for x in (
        min_train, min_calibration, min_holdout
    )):
        raise ValueError("minimum partition counts must be integers between 1 and 500")
    if type(train_end) is not date or type(holdout_start) is not date:
        raise ValueError("train and holdout cutoffs must be dates")
    if train_end >= holdout_start:
        raise ValueError("training cutoff must precede holdout start")
    selected = sorted(
        (row for row in logs if row.player_id == player_id),
        key=lambda row: (row.game_date, row.game_id),
    )
    if not selected:
        raise ValueError("player was not found in game logs")
    # Treat zero-minute (DNP) records as data-quality information, not played
    # games or valid training/evaluation outcomes.
    played = [r for r in selected if r.minutes > 0]
    train, calibration, holdout = split_by_date(
        played,
        train_end_exclusive=train_end,
        holdout_start_inclusive=holdout_start,
    )
    dates = [r.game_date for r in played]
    distinct_opponents = {r.opponent.strip() for r in played if r.opponent.strip()}
    dupdates = Counter(r.game_date for r in selected)
    issues = []
    if synthetic:
        issues.append("SYNTHETIC_NOT_REAL_GAME_EVIDENCE")
    if len(train) < min_train:
        issues.append("INSUFFICIENT_TRAINING_GAMES")
    if len(calibration) < min_calibration:
        issues.append("INSUFFICIENT_CALIBRATION_GAMES")
    if len(holdout) < min_holdout:
        issues.append("INSUFFICIENT_HOLDOUT_GAMES")
    if len(distinct_opponents) < 5:
        issues.append("LOW_OPPONENT_DIVERSITY")
    if dates and (max(dates) - min(dates)).days < 45:
        issues.append("SHORT_OBSERVATION_WINDOW")
    missing_opp = sum(not r.opponent.strip() for r in selected)
    if missing_opp:
        issues.append("MISSING_OPPONENT")
    missing_home = sum(r.home is None for r in selected)
    if missing_home:
        issues.append("MISSING_HOME_AWAY_FLAGS")
    dup_count = sum(n - 1 for n in dupdates.values() if n > 1)
    if dup_count:
        issues.append("MULTIPLE_PLAYER_GAMES_SAME_DAY_REVIEW")
    future_count = sum(r.game_date > date.today() for r in selected)
    if future_count:
        issues.append("FUTURE_DATED_GAMES")
    # A structural gate does not attest a provider license or model quality.
    status = ("DEMONSTRATION_ONLY" if synthetic else
              "REVIEW_REQUIRED" if issues else
              "STRUCTURALLY_READY_RIGHTS_AND_ACCURACY_UNVERIFIED")
    return ResearchReadiness(
        status=status,
        player_id=player_id,
        total_rows=len(logs),
        selected_player_rows=len(selected),
        played_games=len(played),
        first_game=min(dates).isoformat() if dates else None,
        last_game=max(dates).isoformat() if dates else None,
        unique_opponents=len(distinct_opponents),
        train_played_games=len(train),
        calibration_played_games=len(calibration),
        holdout_played_games=len(holdout),
        missing_opponent_rows=missing_opp,
        missing_home_flags=missing_home,
        same_day_extra_games=dup_count,
        future_dated_rows=future_count,
        issues=tuple(issues),
    )


def audit_authorized_dataset(
    data_path: str,
    manifest_path: str,
    player_id: str, *,
    train_end: date,
    holdout_start: date,
    min_train: int = 30,
    min_calibration: int = 10,
    min_holdout: int = 10,
) -> dict:
    manifest = DatasetManifest.from_file(manifest_path)
    digest = verify_snapshot(data_path, manifest)
    rows = load_game_logs(data_path)
    research = inspect_research_readiness(
        rows, player_id, synthetic=manifest.synthetic,
        train_end=train_end, holdout_start=holdout_start,
        min_train=min_train, min_calibration=min_calibration,
        min_holdout=min_holdout,
    )
    return {
        "schema": "sportprob-local-research-readiness-v1",
        "research_only": True,
        "dataset_id": manifest.dataset_id,
        "source_name": manifest.source_name,
        "source_reference": manifest.source_reference,
        "dataset_sha256": digest,
        "synthetic": manifest.synthetic,
        "rights_are_not_independently_verified": True,
        "data_authenticity_is_not_independently_verified": True,
        "real_world_forecast_calibration_verified": False,
        "split_cutoffs": {
            "training_end_exclusive": train_end.isoformat(),
            "holdout_start_inclusive": holdout_start.isoformat(),
        },
        "readiness": asdict(research),
        "next_step": (
            "Resolve all quality issues and independently review data rights; "
            "then evaluate an untouched chronological holdout. Passing the "
            "structural gate alone is not validation of model accuracy."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline research-readiness gate for permissioned player game logs"
    )
    parser.add_argument("--data", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--player", required=True)
    parser.add_argument("--train-end", required=True, help="first calibration date")
    parser.add_argument("--holdout-start", required=True, help="first holdout date")
    parser.add_argument("--min-train", type=int, default=30)
    parser.add_argument("--min-calibration", type=int, default=10)
    parser.add_argument("--min-holdout", type=int, default=10)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    try:
        report = audit_authorized_dataset(
            args.data, args.manifest, args.player,
            train_end=date.fromisoformat(args.train_end),
            holdout_start=date.fromisoformat(args.holdout_start),
            min_train=args.min_train,
            min_calibration=args.min_calibration,
            min_holdout=args.min_holdout,
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))
    if args.require_ready and report["readiness"]["status"] != (
        "STRUCTURALLY_READY_RIGHTS_AND_ACCURACY_UNVERIFIED"
    ):
        parser.exit(2, "research dataset is not structurally ready\n")


if __name__ == "__main__":
    main()
