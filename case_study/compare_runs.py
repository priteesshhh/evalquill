"""Compare two saved runs of the same frozen split and report what changed.

Usage:
    uv run case_study/compare_runs.py BASELINE.json CANDIDATE.json

Exits nonzero without printing conclusions if either run is missing, marked
incomplete, invalid, or not exactly its frozen split's cases, or if the two
runs are not over the same split, inputs and expected answers.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from evalquill.compare import compare, diff_summary
from study_inputs import StudyInputError, load_complete_run

USAGE = "usage: compare_runs.py BASELINE.json CANDIDATE.json"


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 2

    try:
        base = load_complete_run(argv[0])
        cand = load_complete_run(argv[1])
        if base["metadata"]["split"] != cand["metadata"]["split"]:
            raise StudyInputError(
                f"runs are from different splits: "
                f"{base['metadata']['split']} vs {cand['metadata']['split']}"
            )
        diff = compare(base["results"], cand["results"])
        summary = diff_summary(diff)
    except (StudyInputError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    bm, cm = base["metadata"], cand["metadata"]
    print(f"baseline:  {bm.get('prompt_version', 'not recorded')} / {bm['split']}")
    print(f"candidate: {cm.get('prompt_version', 'not recorded')} / {cm['split']}")
    print(f"model:     {bm.get('model', 'not recorded')} @ temp {bm.get('temperature', 'not recorded')}")
    print()

    for name, s in summary.items():
        print(f"{name}")
        print(f"  mean: {s['baseline_mean']:.3f} -> {s['candidate_mean']:.3f} ({s['mean_delta']:+.3f})")
        print(f"  improved:      {s['improved'] or 'none'}")
        print(f"  regressed:     {s['regressed'] or 'none'}")
        print(f"  newly failing: {s['newly_failing'] or 'none'}")

    print("\nRegressed cases:")
    any_reg = False
    for c in diff["cases"]:
        if any(d < 0 for d in c["deltas"].values()):
            any_reg = True
            print(f"\n  {c['id']}")
            print(f"    ticket:    {c['prompt'][:70]}")
            print(f"    expected:  {c['expected']}")
            print(f"    baseline:  {c['baseline_response']!r}")
            print(f"    candidate: {c['candidate_response']!r}")
    if not any_reg:
        print("  none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
