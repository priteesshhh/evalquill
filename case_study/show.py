"""Print one saved run: accuracy and every case."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from evalquill.storage import load_run
from evalquill import summary_scores

path = sys.argv[1]
results = load_run(path)["results"]
acc = summary_scores(results)["normalized_exact_match"]
print(f"accuracy: {acc:.3f}  ({sum(r['scores']['normalized_exact_match'] for r in results):.0f}/{len(results)})")
print()
for r in results:
    hit = r["scores"]["normalized_exact_match"] == 1.0
    mark = "ok  " if hit else "MISS"
    print(f"{mark} {r['id']}  expected={r['expected']:<12} got={r['response']!r}")
