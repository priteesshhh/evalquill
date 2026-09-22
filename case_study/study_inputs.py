"""Load case-study runs, refusing any that cannot support a conclusion.

evalquill.storage.load_run already validates file structure, every score,
and unique case ids. This adds the study-specific checks: the run is not
marked incomplete, and its cases are exactly those of the frozen split named
in its own metadata.

Older runs without newer metadata fields (repeat index, completeness flag,
input hashes) are accepted when their contents are complete and valid.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from evalquill.storage import load_run
from split import TRAIN, HOLDOUT

SPLITS = {"train": TRAIN, "holdout": HOLDOUT}


class StudyInputError(Exception):
    """An input the study cannot draw conclusions from."""


def load_complete_run(path) -> dict:
    path = Path(path)
    if not path.exists():
        raise StudyInputError(f"missing run file: {path}")
    try:
        run = load_run(str(path))
    except ValueError as e:
        raise StudyInputError(f"invalid run file {path.name}: {e}") from e

    meta = run["metadata"]
    if meta.get("incomplete"):
        done = meta.get("completed_cases", "?")
        total = meta.get("expected_cases", "?")
        raise StudyInputError(
            f"{path.name} is marked incomplete ({done}/{total} cases); "
            "refusing to draw conclusions from a partial run"
        )

    split = meta.get("split")
    if split not in SPLITS:
        raise StudyInputError(
            f"{path.name}: metadata 'split' is {split!r}; expected one of {sorted(SPLITS)}"
        )

    ids = {r["id"] for r in run["results"]}
    frozen = set(SPLITS[split])
    missing, extra = sorted(frozen - ids), sorted(ids - frozen)
    if missing or extra:
        raise StudyInputError(
            f"{path.name} does not match the frozen {split} split: "
            f"missing {missing}, extra {extra}"
        )
    return run
