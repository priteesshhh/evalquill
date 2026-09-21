"""Recompute every stored score from the saved response and expected answer.

Usage:
    uv run case_study/rescore.py                    # every run in case_study/runs
    uv run case_study/rescore.py path/to/run.json   # specific files

Exit status 0 if every stored score matches a fresh computation, 1 otherwise.

show.py, repeats.py and compare_runs.py read the stored scores. This script
calls the metric functions instead, so it detects a stored score that no
longer matches its response. No API access is needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from evalquill.storage import load_run
from evalquill.metrics import normalized_exact_match, contains_substring

METRICS = {f.__name__: f for f in (normalized_exact_match, contains_substring)}
RUNS = Path(__file__).parent / "runs"


def rescore_file(path: Path):
    """Return (scores checked, list of problems) for one run file."""
    run = load_run(str(path))
    checked = 0
    problems = []
    for row in run["results"]:
        for name, stored in row["scores"].items():
            metric = METRICS.get(name)
            if metric is None:
                problems.append(f"{row['id']}: no implementation for metric '{name}'; cannot rescore")
                continue
            fresh = metric(row["response"], row["expected"])
            checked += 1
            if fresh != stored:
                problems.append(f"{row['id']} {name}: stored {stored}, recomputed {fresh}")
    return checked, problems


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    paths = [Path(p) for p in argv] or sorted(RUNS.glob("*.json"))
    if not paths:
        print("No run files found.")
        return 1

    total_checked = 0
    failed_files = 0
    for path in paths:
        checked, problems = rescore_file(path)
        total_checked += checked
        if problems:
            failed_files += 1
            print(f"MISMATCH  {path.name}")
            for p in problems:
                print(f"    {p}")
        else:
            print(f"ok        {path.name}  ({checked} scores recomputed)")

    print(f"\n{len(paths)} files, {total_checked} scores recomputed, "
          f"{failed_files} file(s) with problems")
    return 1 if failed_files else 0


if __name__ == "__main__":
    sys.exit(main())
