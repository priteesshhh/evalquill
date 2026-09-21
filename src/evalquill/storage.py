"""Save and load evaluation runs as JSON."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .validation import validate_results

SCHEMA_VERSION = 1


def save_run(results: list, path: str, metadata: dict | None = None) -> None:
    """Write a run to path atomically.

    Rows are validated before anything is written. The payload is then
    serialized in full, written to a temporary file in the same directory,
    and moved onto path with os.replace. A failure at any stage leaves an
    existing file at path unchanged and leaves no partial file behind. An
    existing file at path is replaced on success.

    Non-finite floats (NaN, infinity) are rejected, since they are not valid
    JSON.
    """
    if not results:
        raise ValueError("Cannot save an empty run.")
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("metadata must be a dict.")
    validate_results(results, "run")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
        "results": results,
    }

    # Serialize first: any TypeError or ValueError happens before disk I/O.
    text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def load_run(path: str) -> dict:
    """Load a run and validate its envelope and every row.

    A matching schema_version is necessary but not sufficient: the file must
    also contain valid metadata and a non-empty list of valid result rows.
    """
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"No run found at '{path}'.")

    def reject_constant(token):
        raise ValueError(f"'{path}' contains non-standard JSON value {token}.")

    with target.open(encoding="utf-8") as f:
        try:
            payload = json.load(f, parse_constant=reject_constant)
        except json.JSONDecodeError as e:
            raise ValueError(f"'{path}' is not valid JSON: {e}") from e

    if not isinstance(payload, dict) or "schema_version" not in payload:
        raise ValueError(f"'{path}' is not an evalquill run file.")

    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError(
            f"Run file '{path}' uses schema version {payload['schema_version']}, "
            f"but this version of evalquill reads version {SCHEMA_VERSION}."
        )

    for field in ("created_at", "metadata", "results"):
        if field not in payload:
            raise ValueError(f"'{path}' is missing required field '{field}' (results cannot be read).")
    if not isinstance(payload["created_at"], str):
        raise ValueError(f"'{path}': 'created_at' must be a string.")
    if not isinstance(payload["metadata"], dict):
        raise ValueError(f"'{path}': 'metadata' must be a dict.")
    if not isinstance(payload["results"], list):
        raise ValueError(f"'{path}': 'results' must be a list.")

    validate_results(payload["results"], f"'{path}'")
    return payload
