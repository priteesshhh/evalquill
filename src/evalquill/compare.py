"""Compare two evaluation runs case by case.

Comparison contract: for each case id, the input (prompt) and reference
answer (expected) must be identical in both runs. Only the response and its
scores may differ. The experimental variable - a system prompt, template or
model - lives in the llm callable and run metadata, never in these fields.
A changed input or reference answer is a different test case, so the runs
are rejected rather than compared.
"""

from . import _validate_score
from .validation import validate_results


def compare(baseline: list, candidate: list) -> dict:
    base_idx, base_metrics = validate_results(baseline, "baseline")
    cand_idx, cand_metrics = validate_results(candidate, "candidate")

    if base_idx.keys() != cand_idx.keys():
        only_base = sorted(base_idx.keys() - cand_idx.keys())
        only_cand = sorted(cand_idx.keys() - base_idx.keys())
        raise ValueError(
            "Runs cover different cases and cannot be compared. "
            f"Only in baseline: {only_base}. Only in candidate: {only_cand}."
        )

    if base_metrics != cand_metrics:
        raise ValueError(
            "Runs used different metrics and cannot be compared. "
            f"Baseline: {sorted(base_metrics)}. Candidate: {sorted(cand_metrics)}."
        )

    changed_input = [i for i in base_idx if base_idx[i]["prompt"] != cand_idx[i]["prompt"]]
    changed_expected = [i for i in base_idx if base_idx[i]["expected"] != cand_idx[i]["expected"]]
    if changed_input or changed_expected:
        problems = []
        if changed_input:
            problems.append(f"different input for cases {sorted(changed_input)}")
        if changed_expected:
            problems.append(f"different reference answer for cases {sorted(changed_expected)}")
        raise ValueError(
            "Runs are not over the same dataset: " + "; ".join(problems) + ". "
            "A changed input or reference answer would be reported as a model "
            "improvement or regression. Compare only runs over identical cases."
        )

    metrics = sorted(base_metrics)
    cases = []
    for case_id in base_idx:
        base = base_idx[case_id]
        cand = cand_idx[case_id]
        cases.append({
            "id": case_id,
            "prompt": base["prompt"],
            "expected": base["expected"],
            "baseline_response": base["response"],
            "candidate_response": cand["response"],
            "response_changed": base["response"] != cand["response"],
            "baseline_scores": dict(base["scores"]),
            "candidate_scores": dict(cand["scores"]),
            "deltas": {n: cand["scores"][n] - base["scores"][n] for n in metrics},
        })

    return {"cases": cases, "metrics": metrics}


def diff_summary(diff: dict, pass_threshold: float = 1.0) -> dict:
    try:
        _validate_score(pass_threshold, "pass_threshold")
    except ValueError as e:
        raise ValueError(
            f"pass_threshold must be a finite number between 0 and 1, got {pass_threshold!r}."
        ) from e

    summary = {}
    for name in diff["metrics"]:
        improved, regressed, newly_failing = [], [], []

        for case in diff["cases"]:
            delta = case["deltas"][name]
            if delta > 0:
                improved.append(case["id"])
            elif delta < 0:
                regressed.append(case["id"])

            was_passing = case["baseline_scores"][name] >= pass_threshold
            now_passing = case["candidate_scores"][name] >= pass_threshold
            if was_passing and not now_passing:
                newly_failing.append(case["id"])

        n = len(diff["cases"])
        baseline_mean = sum(c["baseline_scores"][name] for c in diff["cases"]) / n
        candidate_mean = sum(c["candidate_scores"][name] for c in diff["cases"]) / n

        summary[name] = {
            "baseline_mean": baseline_mean,
            "candidate_mean": candidate_mean,
            "mean_delta": candidate_mean - baseline_mean,
            "improved": improved,
            "regressed": regressed,
            "newly_failing": newly_failing,
        }

    return summary
