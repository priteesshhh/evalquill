"""Shared validation for result rows and runs.

One definition of a valid run, used by comparison and by storage, so the two
boundaries cannot drift apart.
"""

from . import _validate_score

REQUIRED_FIELDS = ("id", "prompt", "expected", "response", "scores")


def check_row(row, label: str, index: int) -> None:
    if not isinstance(row, dict):
        raise ValueError(f"{label} row {index} is not a dict.")
    missing = [f for f in REQUIRED_FIELDS if f not in row]
    if missing:
        raise ValueError(f"{label} row {index} is missing required field(s): {missing}.")
    if not isinstance(row["scores"], dict):
        raise ValueError(f"{label} case '{row['id']}': scores must be a dict.")
    for name, value in row["scores"].items():
        try:
            _validate_score(value, name)
        except ValueError as e:
            raise ValueError(f"{label} case '{row['id']}': {e}") from e


def validate_results(results, label: str):
    """Validate every row; return (rows indexed by id, the run's metric set)."""
    if not isinstance(results, list):
        raise ValueError(f"{label} results must be a list.")
    if not results:
        raise ValueError(f"{label} run must contain at least one case.")

    indexed = {}
    metric_set = None
    first_id = None
    for index, row in enumerate(results):
        check_row(row, label, index)
        case_id = row["id"]
        if case_id in indexed:
            raise ValueError(f"Duplicate case id '{case_id}' in {label} run.")
        indexed[case_id] = row

        names = set(row["scores"])
        if metric_set is None:
            metric_set, first_id = names, case_id
        elif names != metric_set:
            raise ValueError(
                f"{label} run has inconsistent metric sets: case '{first_id}' "
                f"has {sorted(metric_set)}, case '{case_id}' has {sorted(names)}."
            )
    return indexed, metric_set
