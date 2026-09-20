"""Report across repeat runs of the same split.

Usage:
    uv run case_study/repeats.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from evalquill.storage import load_run

RUNS = Path(__file__).parent / "runs"

VERSIONS = {
    "v1_naive": ["v1_naive_holdout.json",
                 "v1_naive_holdout_r2.json",
                 "v1_naive_holdout_r3.json"],
    "v2_structured": ["v2_structured_holdout.json",
                      "v2_structured_holdout_r2.json",
                      "v2_structured_holdout_r3.json"],
}

loaded = {}
for version, files in VERSIONS.items():
    loaded[version] = []
    for name in files:
        path = RUNS / name
        if not path.exists():
            print(f"MISSING: {name}")
            continue
        run = load_run(str(path))
        if run["metadata"].get("incomplete"):
            print(f"INCOMPLETE, excluded: {name}")
            continue
        loaded[version].append((name, run))

print("Accuracy per run")
for version, runs in loaded.items():
    for name, run in runs:
        rs = run["results"]
        correct = sum(r["scores"]["normalized_exact_match"] for r in rs)
        print(f"  {version:<14} {name:<34} {correct:.0f}/{len(rs)}  {correct/len(rs):.3f}")

ids = [r["id"] for r in loaded["v1_naive"][0][1]["results"]]
n_runs = {v: len(rs) for v, rs in loaded.items()}
print(f"\n{len(ids)} unique tickets; "
      f"v1_naive {n_runs['v1_naive']} runs = {len(ids)*n_runs['v1_naive']} generations; "
      f"v2_structured {n_runs['v2_structured']} runs = {len(ids)*n_runs['v2_structured']} generations")

def counts(version):
    out = {}
    for _, run in loaded[version]:
        for r in run["results"]:
            out.setdefault(r["id"], []).append(r["scores"]["normalized_exact_match"])
    return out

c1, c2 = counts("v1_naive"), counts("v2_structured")

print(f"\nCorrect count out of runs, per ticket")
print(f"  {'id':<6} {'expected':<12} {'v1':<5} {'v2':<5}")
for tid in ids:
    a, b = sum(c1[tid]), sum(c2[tid])
    mark = ""
    if b < a:
        mark = "  <- lower under v2"
    elif a < b:
        mark = "  <- higher under v2"
    expected = next(r["expected"] for _, run in loaded["v1_naive"]
                    for r in run["results"] if r["id"] == tid)
    print(f"  {tid:<6} {expected:<12} {a:.0f}/{len(c1[tid])}  {b:.0f}/{len(c2[tid])}{mark}")

print("\nt47, every generation")
for version in VERSIONS:
    for name, run in loaded[version]:
        r = next(x for x in run["results"] if x["id"] == "t47")
        ok = "correct" if r["scores"]["normalized_exact_match"] == 1.0 else "wrong"
        print(f"  {version:<14} {name:<34} {r['response']!r:<16} {ok}")
