"""Save and load evaluation runs as JSON."""

import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1


def save_run(results: list, path: str, metadata: dict | None = None) -> None:
    if not results:
        raise ValueError("Cannot save an empty run.")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
        "results": results,
    }

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def load_run(path: str) -> dict:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"No run found at '{path}'.")

    with target.open(encoding="utf-8") as f:
        payload = json.load(f)

    if "schema_version" not in payload:
        raise ValueError(f"'{path}' is not an evalquill run file.")

    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError(
            f"Run file '{path}' uses schema version {payload['schema_version']}, "
            f"but this version of evalquill reads version {SCHEMA_VERSION}."
        )

    return payload