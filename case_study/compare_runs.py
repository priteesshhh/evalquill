"""Compare two saved runs and report what changed."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from evalquill.storage import load_run
from evalquill.compare import compare, diff_summary

base, cand = load_run(sys.argv[1]), load_run(sys.argv[2])
print(f"baseline:  {base['metadata']['prompt_version']} / {base['metadata']['split']}")
print(f"candidate: {cand['metadata']['prompt_version']} / {cand['metadata']['split']}")
print(f"model:     {base['metadata']['model']} @ temp {base['metadata']['temperature']}")
print()

diff = compare(base["results"], cand["results"])
for name, s in diff_summary(diff).items():
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
