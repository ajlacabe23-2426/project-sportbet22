"""Run research-only offline source and time-split checks."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date
import json

from .governance import DatasetManifest, audit_split, verify_snapshot
from .ingest import load_game_logs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline dataset-integrity and chronological-split audit"
    )
    parser.add_argument("--data", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--train-end", required=True, help="exclusive YYYY-MM-DD")
    parser.add_argument("--holdout-start", required=True, help="inclusive YYYY-MM-DD")
    arguments = parser.parse_args()
    try:
        manifest = DatasetManifest.from_file(arguments.manifest)
        verified_hash = verify_snapshot(arguments.data, manifest)
        rows = load_game_logs(arguments.data)
        audit = audit_split(
            rows,
            train_end_exclusive=date.fromisoformat(arguments.train_end),
            holdout_start_inclusive=date.fromisoformat(arguments.holdout_start),
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    result = {
        "research_only": True,
        "data": arguments.data,
        "dataset_id": manifest.dataset_id,
        "synthetic": manifest.synthetic,
        "sha256_verified": verified_hash,
        "rights_evidence_declared": manifest.rights_evidence,
        "rights_are_not_independently_verified": True,
        "split": asdict(audit),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
