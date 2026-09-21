"""Save and load evaluation runs as JSON."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1


def save_run(results: list, path: str, metadata: dict | None = None) -> None:
    """Write a run to path atomically.

    The payload is serialized in full before the filesystem is touched, then
    written to a temporary file in the same directory and moved onto path
    with os.replace. A failure at any stage leaves an existing file at path
    unchanged and leaves no partial file behind. An existing file at path is
    replaced on success.

    Non-finite floats (NaN, infinity) are rejected, since they are not valid
    JSON.
    """
    if not results:
        raise ValueError("Cannot save an empty run.")

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
