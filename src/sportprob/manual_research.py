"""Offline, permission-gated summaries of manually supplied completed-game statistics.

No network access, sportsbook connections, odds, target lines, or bet selection.
All reports are historical and cutoff-bound; no future-game prediction.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date
import json
from pathlib import Path
from typing import Any

from .governance import DatasetManifest, verify_snapshot
from .historical_context import describe_historical_context
from .ingest import load_game_logs
from .schema import STATS


def build_manual_research_report(
    data_path: str | Path,
    manifest_path: str | Path,
    as_of: date,
    *,
    player_id: str | None = None,
    history_games: int = 40,
) -> dict[str, Any]:
    """Build historical descriptions from an authorized, checksum-matched CSV."""
    if type(as_of) is not date:
        raise ValueError("as_of must be a calendar date")
    if not 5 <= history_games <= 200:
        raise ValueError("history_games must be between 5 and 200")

    manifest = DatasetManifest.from_file(manifest_path)
    digest = verify_snapshot(data_path, manifest)
    logs = load_game_logs(data_path)
    available_ids = sorted({row.player_id for row in logs})
    if player_id is not None:
        if player_id not in available_ids:
            raise ValueError("requested player_id is not present in dataset")
        available_ids = [player_id]

    players: list[dict[str, Any]] = []
    insufficient: list[dict[str, Any]] = []
    for identifier in available_ids:
        eligible = [
            row for row in logs
            if row.player_id == identifier
            and row.game_date < as_of
            and row.minutes > 0
        ]
        if len(eligible) < 5:
            insufficient.append({
                "player_id": identifier,
                "played_games_before_cutoff": len(eligible),
                "reason": "fewer than five earlier played games",
            })
            continue

        summaries = {
            stat: asdict(describe_historical_context(
                logs, identifier, stat, as_of,
                history_games=history_games,
            ))
            for stat in STATS
        }
        players.append({
            "player_id": identifier,
            "played_games_before_cutoff": len(eligible),
            "statistics": summaries,
        })

    return {
        "schema": "sportprob-manual-statistics-v1",
        "research_only": True,
        "future_prediction": False,
        "wagering_outputs": False,
        "dataset": {
            "id": manifest.dataset_id,
            "source_name": manifest.source_name,
            "source_reference": manifest.source_reference,
            "retrieved_at": manifest.retrieved_at.isoformat(),
            "sha256": digest,
            "synthetic": manifest.synthetic,
            "rights_status_user_declared": manifest.rights_status,
            "rights_independently_verified": False,
        },
        "as_of_exclusive": as_of.isoformat(),
        "history_games_limit": history_games,
        "players": players,
        "insufficient_history": insufficient,
        "limitations": (
            "Completed-game descriptions only. No forecast, calibration, "
            "odds, betting comparison, or real-world accuracy assertion. "
            "Source permissions and completeness remain independently unverified."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manual offline player-statistics research, no wagering features"
    )
    parser.add_argument("--data", required=True, help="locally saved canonical CSV")
    parser.add_argument("--manifest", required=True, help="rights and SHA-256 manifest")
    parser.add_argument("--as-of", required=True, help="exclusive YYYY-MM-DD cutoff")
    parser.add_argument("--player", default=None, help="optional stable player ID")
    parser.add_argument("--history-games", type=int, default=40)
    parser.add_argument("--output", default=None, help="optional new JSON file")
    args = parser.parse_args()
    try:
        report = build_manual_research_report(
            args.data, args.manifest, date.fromisoformat(args.as_of),
            player_id=args.player, history_games=args.history_games,
        )
        encoded = json.dumps(report, indent=2)
        if args.output:
            destination = Path(args.output)
            if destination.suffix.lower() != ".json":
                raise ValueError("output must have .json extension")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("x", encoding="utf-8") as out:
                out.write(encoded + "\n")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(encoded)


if __name__ == "__main__":
    main()
