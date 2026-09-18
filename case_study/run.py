"""Run one prompt version over one split and save the results.

Usage:
    uv run case_study/run.py v1_naive train
    uv run case_study/run.py v2_structured holdout

Saves to case_study/runs/<version>_<split>.json so scoring and comparison
need no further API calls.
"""

import csv
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from prompts import PROMPTS
from split import TRAIN, HOLDOUT
from retry import call_with_retry
from evalquill import evaluate_dataset
from evalquill.metrics import normalized_exact_match
from evalquill.providers import openai_llm
from evalquill.storage import save_run

MODEL = "gpt-4o-mini"
TEMPERATURE = 0.0
MAX_TOKENS = 10
SECONDS_BETWEEN_CALLS = 1.0

HERE = Path(__file__).parent


def load_tickets() -> dict:
    text = (HERE / "tickets.md").read_text(encoding="utf-8")
    found = re.findall(r"\*\*(t\d\d)\*\* — (.+)", text)
    return {tid: body.strip() for tid, body in found}


def load_labels() -> dict:
    labels = {}
    with (HERE / "labels.csv").open(encoding="utf-8") as f:
        for row in csv.reader(line for line in f if not line.startswith("#")):
            if len(row) == 2 and row[0] != "id":
                labels[row[0]] = row[1].strip()
    return labels


def main() -> None:
    version, split_name = sys.argv[1], sys.argv[2]
    ids = {"train": TRAIN, "holdout": HOLDOUT}[split_name]
    system_prompt = PROMPTS[version]

    tickets = load_tickets()
    labels = load_labels()

    missing = [i for i in ids if i not in tickets or i not in labels]
    if missing:
        raise SystemExit(f"Missing ticket text or label for: {missing}")

    dataset = [{"id": i, "prompt": tickets[i], "expected": labels[i]} for i in ids]

    from openai import OpenAI, RateLimitError, InternalServerError, APIConnectionError

    # max_retries=0: this module owns the retry budget. Leaving the SDK's
    # default would multiply attempts rather than cap them.
    client = OpenAI(max_retries=0)

    base_llm, metadata = openai_llm(
        MODEL,
        system_prompt=system_prompt,
        temperature=TEMPERATURE,
        client=client,
        max_tokens=MAX_TOKENS,
    )

    calls = {"n": 0}

    def resilient_llm(prompt: str) -> str:
        if calls["n"]:
            time.sleep(SECONDS_BETWEEN_CALLS)
        calls["n"] += 1
        print(f"  {calls['n']}/{len(dataset)}", flush=True)
        return call_with_retry(
            lambda: base_llm(prompt),
            rate_limit_types=(RateLimitError,),
            server_error_types=(InternalServerError, APIConnectionError),
        )

    print(f"Running {version} on {split_name} ({len(dataset)} cases), model {MODEL}")
    results = evaluate_dataset(dataset, resilient_llm, [normalized_exact_match])

    metadata["prompt_version"] = version
    metadata["split"] = split_name
    metadata["sdk_max_retries"] = 0

    out = HERE / "runs" / f"{version}_{split_name}.json"
    save_run(results, str(out), metadata=metadata)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
