"""Compare two evaluation runs case by case."""


def _index_by_id(results: list, label: str) -> dict:
    indexed = {}
    for result in results:
        case_id = result["id"]
        if case_id in indexed:
            raise ValueError(f"Duplicate case id '{case_id}' in {label} run.")
        indexed[case_id] = result
    return indexed


def _metric_names(results: list) -> set:
    names = set()
    for result in results:
        names.update(result["scores"].keys())
    return names


def compare(baseline: list, candidate: list) -> dict:
    if not baseline or not candidate:
        raise ValueError("Both runs must contain at least one case.")

    base_idx = _index_by_id(baseline, "baseline")
    cand_idx = _index_by_id(candidate, "candidate")

    if base_idx.keys() != cand_idx.keys():
        only_base = sorted(base_idx.keys() - cand_idx.keys())
        only_cand = sorted(cand_idx.keys() - base_idx.keys())
        raise ValueError(
            "Runs cover different cases and cannot be compared. "
            f"Only in baseline: {only_base}. Only in candidate: {only_cand}."
        )

    base_metrics = _metric_names(baseline)
    cand_metrics = _metric_names(candidate)
    if base_metrics != cand_metrics:
        raise ValueError(
            "Runs used different metrics and cannot be compared. "
            f"Baseline: {sorted(base_metrics)}. Candidate: {sorted(cand_metrics)}."
        )

    cases = []
    for case_id in base_idx:
        base = base_idx[case_id]
        cand = cand_idx[case_id]

        deltas = {
            name: cand["scores"][name] - base["scores"][name]
            for name in sorted(base_metrics)
        }

        cases.append({
            "id": case_id,
            "prompt": base["prompt"],
            "expected": base["expected"],
            "baseline_response": base["response"],
            "candidate_response": cand["response"],
            "response_changed": base["response"] != cand["response"],
            "baseline_scores": base["scores"],
            "candidate_scores": cand["scores"],
            "deltas": deltas,
        })

    return {
        "cases": cases,
        "metrics": sorted(base_metrics),
    }