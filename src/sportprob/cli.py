"""Research CLI; produces no odds, betting recommendations or actions."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date
import json

from .evaluate import backtest
from .ingest import load_game_logs
from .governance import DatasetManifest, verify_snapshot
from .holdout import evaluate_frozen_holdout
from .model import forecast
from .report import render_forecast_report, save_forecast_report
from .schema import STATS


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sportprob", description="Simulation-only player performance research"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("forecast", "backtest", "holdout", "report"):
        command = commands.add_parser(name)
        command.add_argument("--data", required=True, help="authorized game-log CSV")
        command.add_argument("--player", required=True, help="stable player ID")
        command.add_argument("--stat", required=True, choices=STATS)
    forecast_parser = commands.choices["forecast"]
    forecast_parser.add_argument("--as-of", required=True, help="YYYY-MM-DD; excludes this date")
    forecast_parser.add_argument("--minutes", type=float, default=None)
    report_parser = commands.choices["report"]
    report_parser.add_argument("--manifest", required=True, help="research rights/checksum manifest")
    report_parser.add_argument("--as-of", required=True, help="YYYY-MM-DD; excludes this date")
    report_parser.add_argument("--minutes", type=float, default=None)
    report_parser.add_argument("--output", required=True, help="local .html destination")
    report_parser.add_argument("--overwrite", action="store_true", help="explicitly replace an existing report")
    holdout_parser = commands.choices["holdout"]
    holdout_parser.add_argument("--manifest", required=True, help="research rights/checksum manifest")
    holdout_parser.add_argument("--start", required=True, help="first withheld YYYY-MM-DD")
    holdout_parser.add_argument("--end", default=None, help="optional exclusive YYYY-MM-DD")
    args = parser.parse_args()
    try:
        logs = load_game_logs(args.data)
        if args.command == "forecast":
            prediction = forecast(
                logs, args.player, args.stat, date.fromisoformat(args.as_of),
                projected_minutes=args.minutes,
            )
            output = {
                "research_only": True,
                "player_id": prediction.player_id,
                "stat": prediction.stat,
                "as_of": prediction.as_of.isoformat(),
                "training_games": prediction.training_games,
                "projected_minutes": round(prediction.projected_minutes, 2),
                "expected_stat": round(prediction.expected_stat, 3),
                "variance": round(prediction.variance, 3),
                "interval_80": prediction.central_interval(0.8),
                "interval_90": prediction.central_interval(0.9),
                "most_probable_fixed_bucket": asdict(prediction.modal_bucket()),
                "fixed_width_buckets": [asdict(bucket) for bucket in prediction.buckets()],
                "model_status": "uncalibrated research baseline",
            }
        elif args.command == "backtest":
            output = {
                "research_only": True,
                "model_status": "uncalibrated research baseline",
                **asdict(backtest(logs, args.player, args.stat)),
            }
        elif args.command == "report":
            manifest = DatasetManifest.from_file(args.manifest)
            verified_hash = verify_snapshot(args.data, manifest)
            prediction = forecast(
                logs, args.player, args.stat, date.fromisoformat(args.as_of),
                projected_minutes=args.minutes,
            )
            if not args.output.lower().endswith(".html"):
                raise ValueError("report output path must end in .html")
            html = render_forecast_report(
                prediction, dataset_id=manifest.dataset_id,
                dataset_sha256=verified_hash, source_name=manifest.source_name,
                synthetic=manifest.synthetic,
            )
            destination = save_forecast_report(html, args.output, overwrite=args.overwrite)
            output = {
                "research_only": True, "model_status": "uncalibrated research baseline",
                "local_html_report": str(destination), "synthetic": manifest.synthetic,
                "dataset_sha256": verified_hash, "network_requests": False,
            }
        else:
            manifest = DatasetManifest.from_file(args.manifest)
            verified_hash = verify_snapshot(args.data, manifest)
            result = evaluate_frozen_holdout(
                logs, args.player, args.stat,
                holdout_start=date.fromisoformat(args.start),
                holdout_end_exclusive=date.fromisoformat(args.end) if args.end else None,
            )
            output = {
                "research_only": True,
                "model_status": "uncalibrated research baseline",
                "dataset_id": manifest.dataset_id,
                "synthetic": manifest.synthetic,
                "sha256_verified": verified_hash,
                "rights_are_not_independently_verified": True,
                **asdict(result),
            }
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
