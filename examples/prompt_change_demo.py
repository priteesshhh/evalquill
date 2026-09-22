"""Compare two prompt versions through saved runs.

Two stub functions stand in for the same model under two prompts. v2 fixes
two tickets and breaks one, so accuracy rises while a case regresses.
"""

from evalquill import evaluate_dataset
from evalquill.metrics import normalized_exact_match
from evalquill.compare import compare, diff_summary
from evalquill.storage import save_run, load_run

DATASET = [
    {"id": "refund", "prompt": "I was charged twice this month.", "expected": "billing"},
    {"id": "login", "prompt": "The login page shows a 500 error.", "expected": "account"},
    {"id": "invite", "prompt": "My teammate never got the invite email.", "expected": "account"},
    {"id": "webhook", "prompt": "Our webhook stopped receiving events.", "expected": "integration"},
]


def llm_v1(prompt: str) -> str:
    return {
        "I was charged twice this month.": "billing",
        "The login page shows a 500 error.": "bug",
        "My teammate never got the invite email.": "account",
        "Our webhook stopped receiving events.": "bug",
    }[prompt]


def llm_v2(prompt: str) -> str:
    return {
        "I was charged twice this month.": "billing",
        "The login page shows a 500 error.": "account",
        "My teammate never got the invite email.": "integration",
        "Our webhook stopped receiving events.": "integration",
    }[prompt]


def main() -> None:
    metrics = [normalized_exact_match]

    save_run(evaluate_dataset(DATASET, llm_v1, metrics), "runs/baseline.json",
             metadata={"prompt_version": "v1"})
    save_run(evaluate_dataset(DATASET, llm_v2, metrics), "runs/candidate.json",
             metadata={"prompt_version": "v2"})

    diff = compare(load_run("runs/baseline.json")["results"],
                   load_run("runs/candidate.json")["results"])

    for name, s in diff_summary(diff).items():
        print(f"\n{name}")
        print(f"  mean: {s['baseline_mean']:.2f} -> {s['candidate_mean']:.2f} ({s['mean_delta']:+.2f})")
        print(f"  improved:      {s['improved'] or 'none'}")
        print(f"  regressed:     {s['regressed'] or 'none'}")
        print(f"  newly failing: {s['newly_failing'] or 'none'}")

    print("\nRegressed cases:")
    for case in diff["cases"]:
        if any(d < 0 for d in case["deltas"].values()):
            print(f"\n  {case['id']}")
            print(f"    ticket:    {case['prompt']}")
            print(f"    expected:  {case['expected']}")
            print(f"    v1 said:   {case['baseline_response']}")
            print(f"    v2 said:   {case['candidate_response']}")


if __name__ == "__main__":
    main()
