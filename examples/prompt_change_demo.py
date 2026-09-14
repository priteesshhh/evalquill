"""Show what changed when a prompt was edited."""

from evalquill import evaluate_dataset
from evalquill.metrics import contains_substring
from evalquill.compare import compare, diff_summary
from evalquill.storage import save_run, load_run

DATASET = [
    {"id": "capital_india", "prompt": "What is the capital of India?", "expected": "Delhi"},
    {"id": "capital_france", "prompt": "What is the capital of France?", "expected": "Paris"},
    {"id": "math_seven_two", "prompt": "What is 7 + 2?", "expected": "9"},
]


def llm_v1(prompt: str) -> str:
    """Verbose prompt: answers in full sentences."""
    answers = {
        "What is the capital of India?": "The capital of India is Delhi.",
        "What is the capital of France?": "The capital of France is Paris.",
        "What is 7 + 2?": "7 + 2 equals 9.",
    }
    return answers[prompt]


def llm_v2(prompt: str) -> str:
    """Terse prompt: 'answer in one word'. Breaks the arithmetic case."""
    answers = {
        "What is the capital of India?": "Delhi",
        "What is the capital of France?": "Paris",
        "What is 7 + 2?": "nine",
    }
    return answers[prompt]


def main() -> None:
    metrics = [contains_substring]

    baseline = evaluate_dataset(DATASET, llm_v1, metrics)
    save_run(baseline, "runs/baseline.json", metadata={"prompt_version": "v1"})

    candidate = evaluate_dataset(DATASET, llm_v2, metrics)
    save_run(candidate, "runs/candidate.json", metadata={"prompt_version": "v2"})

    diff = compare(load_run("runs/baseline.json")["results"],
                   load_run("runs/candidate.json")["results"])
    summary = diff_summary(diff)

    for name, stats in summary.items():
        print(f"\n{name}")
        print(f"  mean: {stats['baseline_mean']:.2f} -> {stats['candidate_mean']:.2f} "
              f"({stats['mean_delta']:+.2f})")
        print(f"  improved:      {stats['improved'] or 'none'}")
        print(f"  regressed:     {stats['regressed'] or 'none'}")
        print(f"  newly failing: {stats['newly_failing'] or 'none'}")

    print("\nRegressed cases:")
    for case in diff["cases"]:
        if any(d < 0 for d in case["deltas"].values()):
            print(f"\n  {case['id']}")
            print(f"    expected:  {case['expected']}")
            print(f"    v1 said:   {case['baseline_response']}")
            print(f"    v2 said:   {case['candidate_response']}")


if __name__ == "__main__":
    main()
