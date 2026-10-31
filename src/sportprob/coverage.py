"""Local, read-only player game-log coverage audit.

Does not acquire data or output odds, wagers, or profit promises.
Checksum verification establishes byte identity, not truth or rights.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
import json

from .governance import DatasetManifest, verify_snapshot
from .ingest import load_game_logs
from .schema import GameLog


@dataclass(frozen=True)
class PlayerCoverage:
    player_id: str
    played_games: int
    unique_opponents: int
    first_played: str | None
    last_played: str | None
    missing_home_flags: int
    zero_minute_records: int
    status: str
    review_reasons: tuple[str, ...]


def evaluate_player_coverage(
    logs: list[GameLog], player_id: str, *,
    synthetic: bool, minimum_games: int = 30
) -> PlayerCoverage:
    if not player_id.strip() or not 5 <= minimum_games <= 500:
        raise ValueError("player required and minimum_games must be between 5 and 500")
    rows = sorted((row for row in logs if row.player_id == player_id),
                  key=lambda row: (row.game_date, row.game_id))
    played = [row for row in rows if row.minutes > 0]
    dates = [row.game_date for row in played]
    reasons = []
    if synthetic:
        reasons.append("SYNTHETIC_DATA_NOT_REAL_WORLD_EVIDENCE")
    if len(played) < minimum_games:
        reasons.append("INSUFFICIENT_PLAYED_GAMES")
    if len({row.opponent for row in played}) < 5:
        reasons.append("LOW_OPPONENT_DIVERSITY")
    if dates and (max(dates) - min(dates)).days < 45:
        reasons.append("SHORT_OBSERVATION_WINDOW")
    missing_home = sum(row.home is None for row in played)
    if missing_home:
        reasons.append("MISSING_HOME_AWAY_FLAGS")
    if dates and max(dates) > date.today():
        reasons.append("FUTURE_DATED_OBSERVATIONS")
    status = ("DEMONSTRATION_ONLY" if synthetic else
              "REVIEW_REQUIRED" if reasons else
              "STRUCTURALLY_READY_FOR_RESEARCH_UNVERIFIED")
    return PlayerCoverage(
        player_id=player_id, played_games=len(played),
        unique_opponents=len({row.opponent for row in played}),
        first_played=min(dates).isoformat() if dates else None,
        last_played=max(dates).isoformat() if dates else None,
        missing_home_flags=missing_home,
        zero_minute_records=len(rows)-len(played),
        status=status, review_reasons=tuple(reasons),
    )


def audit_local_coverage(data_path: str, manifest_path: str,
                         player_id: str, minimum_games: int = 30) -> dict:
    manifest = DatasetManifest.from_file(manifest_path)
    digest = verify_snapshot(data_path, manifest)
    rows = load_game_logs(data_path)
    player = evaluate_player_coverage(
        rows, player_id, synthetic=manifest.synthetic, minimum_games=minimum_games)
    return {
        "schema": "sportprob-local-player-coverage-v1",
        "research_only": True,
        "data_authenticity_independently_verified": False,
        "forecast_calibration_verified": False,
        "rights_independently_verified": False,
        "dataset_id": manifest.dataset_id,
        "dataset_source": manifest.source_name,
        "dataset_sha256": digest,
        "row_count": len(rows),
        "player_count": len(Counter(row.player_id for row in rows)),
        "synthetic": manifest.synthetic,
        "player_coverage": asdict(player),
        "next_validation": (
            "Obtain appropriately sourced historical observations, freeze a chronological "
            "train/calibration/holdout split, and evaluate model calibration."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline provenance and player-coverage audit")
    parser.add_argument("--data", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--player", required=True)
    parser.add_argument("--minimum-games", type=int, default=30)
    args = parser.parse_args()
    try:
        result = audit_local_coverage(
            args.data, args.manifest, args.player, args.minimum_games)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
