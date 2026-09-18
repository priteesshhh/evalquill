"""Frozen train/holdout split.

Generated once with a fixed seed and committed before any prompt was run.
Prompts may be tuned against TRAIN. Reported results come from HOLDOUT.
"""

import random

_ids = [f"t{i:02d}" for i in range(1, 51)]
_rng = random.Random(20260918)
_shuffled = _ids[:]
_rng.shuffle(_shuffled)

HOLDOUT = sorted(_shuffled[:20])
TRAIN = sorted(_shuffled[20:])

assert len(HOLDOUT) == 20
assert len(TRAIN) == 30
assert set(HOLDOUT) | set(TRAIN) == set(_ids)
assert not (set(HOLDOUT) & set(TRAIN))
