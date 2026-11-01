"""Offline, provenance-bearing research audit export for the browser dashboard.

The output is a local JSON file. No API credentials, browser service, sportsbook
content, or implicit model certification is included.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

AUDIT_SCHEMA = "sportprob-frozen-model-audit-v1"


def save_audit_json(
    report: dict[str, Any], destination: str | Path, *, overwrite: bool = False
) -> Path:
    """Write a complete, strict JSON research result to an explicit local file."""
    if not isinstance(report, dict) or report.get("schema") != AUDIT_SCHEMA:
        raise ValueError("unsupported model audit schema")
    path = Path(destination)
    if path.suffix.lower() != ".json":
        raise ValueError("audit output must use a .json filename")
    document = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w" if overwrite else "x", encoding="utf-8") as file:
        file.write(document)
    return path.resolve()
