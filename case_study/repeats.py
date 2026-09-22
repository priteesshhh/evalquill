"""Report across the three repeat runs of each prompt version on the holdout.

Usage:
    uv run case_study/repeats.py

All six planned runs are required. Exits nonzero without printing conclusions
if any run is missing, marked incomplete, not exactly the frozen holdout
cases, saved under the wrong prompt version, or disagrees with the others on
any case input or expected answer. Per-ticket counts are therefore always
out of the same number of repeats.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from evalquill.compare import compare, diff_summary
from study_inputs import StudyInputError, load_complete_run

RUNS = Path(__file__).parent / "runs"
METRIC = "normalized_exact_match"

VERSIONS = {
    "v1_naive": ["v1_naive_holdout.json",
                 "v1_naive_holdout_r2.json",
                 "v1_naive_holdout_r3.json"],
    "v2_structured": ["v2_structured_holdout.json",
                      "v2_structured_holdout_r2.json",
                      "v2_structured_holdout_r3.json"],
}


def load_study() -> dict:
    loaded = {}
    for version, files in VERSIONS.items():
        loaded[version] = []
        for name in files:
            run = load_complete_run(RUNS / name)
            meta = run["metadata"]
            if meta.get("prompt_version") != version:
                raise StudyInputError(
                    f"{name}: metadata prompt_version is {meta.get('prompt_version')!r}, "
                    f"expected {version!r}"
                )
            if meta["split"] != "holdout":
                raise StudyInputError(f"{name}: split is {meta['split']!r}, expected 'holdout'")
            loaded[version].append((name, run))

    ref_name, ref = loaded["v1_naive"][0]
    if METRIC not in ref["results"][0]["scores"]:
        raise StudyInputError(f"{ref_name} has no '{METRIC}' scores")
    for version in VERSIONS:
        for name, run in loaded[version]:
            try:
                compare(ref["results"], run["results"])
            except ValueError as e:
                raise StudyInputError(f"{name} is inconsistent with {ref_name}: {e}") from e
    return loaded


def correct(run) -> float:
    return sum(r["scores"][METRIC] for r in run["results"])


def main() -> int:
    try:
        loaded = load_study()
        per_repeat = []
        pairs = zip(loaded["v1_naive"], loaded["v2_structured"])
        for i, ((_, r1), (_, r2)) in enumerate(pairs, start=1):
            s = diff_summary(compare(r1["results"], r2["results"]))[METRIC]
            per_repeat.append((i, r1, r2, s))
    except (StudyInputError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    n_repeats = len(VERSIONS["v1_naive"])
    ref = loaded["v1_naive"][0][1]
    ids = [r["id"] for r in ref["results"]]
    expected = {r["id"]: r["expected"] for r in ref["results"]}

    print("Accuracy per run")
    for version, runs in loaded.items():
        for name, run in runs:
            n = len(run["results"])
            c = correct(run)
            print(f"  {version:<14} {name:<34} {c:.0f}/{n}  {c / n:.3f}")

    print(f"\n{len(ids)} unique tickets; {n_repeats} runs per version; "
          f"{len(ids) * n_repeats} generations per version")

    print("\nPer-repeat comparison (v1 repeat i vs v2 repeat i)")
    for i, r1, r2, s in per_repeat:
        n = len(r1["results"])
        print(f"  repeat {i}: v1 {correct(r1):.0f}/{n}, v2 {correct(r2):.0f}/{n}, "
              f"improved {s['improved']}, regressed {s['regressed']}")

    def counts(version):
        out = {tid: 0.0 for tid in ids}
        for _, run in loaded[version]:
            for r in run["results"]:
                out[r["id"]] += r["scores"][METRIC]
        return out

    c1, c2 = counts("v1_naive"), counts("v2_structured")
    print(f"\nCorrect count out of {n_repeats} runs, per ticket")
    print(f"  {'id':<6} {'expected':<12} {'v1':<5} {'v2':<5}")
    for tid in ids:
        a, b = c1[tid], c2[tid]
        mark = "  <- lower under v2" if b < a else "  <- higher under v2" if a < b else ""
        print(f"  {tid:<6} {expected[tid]:<12} {a:.0f}/{n_repeats}  {b:.0f}/{n_repeats}{mark}")

    print("\nt47, every generation")
    for version in VERSIONS:
        for name, run in loaded[version]:
            r = next(x for x in run["results"] if x["id"] == "t47")
            ok = "correct" if r["scores"][METRIC] == 1.0 else "wrong"
            print(f"  {version:<14} {name:<34} {r['response']!r:<16} {ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
