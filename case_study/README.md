# Case study: does stating precedence rules in a prompt change classification accuracy?

Support-ticket classification with gpt-4o-mini, comparing two prompt versions
that differ only in how much of the decision procedure they state.

**Finding: accuracy increased from 80% to 95% on the held-out set, an
increase of 15 percentage points, while one previously correct ticket failed
in all three observed repeats.**

## Method

### Dataset

50 fictional support tickets, written for this study. They describe a generic
SaaS product and contain no real user data. Ordinary tickets and edge cases
were included in proportions intended to resemble a real queue. Tickets were
written before either prompt was drafted.

Text: [tickets.md](tickets.md)

### Labels

Six single-label categories: billing, account, integration, feature, bug,
other. The labeling rules are in [labeling_guide.md](labeling_guide.md).

Classification is by requested resolution rather than technical cause, and
the three domain categories take precedence over bug and feature. A billing
problem caused by a defect is billing; a login 500 is account.

Labels were assigned by hand by the author against the guide, before any
prompt was written or any model output seen: [labels.csv](labels.csv)

They were then checked by a second labeling pass: the author gave Gemini a
condensed restatement of the guide's rules and precedence order (without its
worked examples) and the ticket texts, but not the author's labels. The model
version and interface were not recorded and the raw responses were not saved;
the file preserves only the resulting labels. The two label sets agreed on
50/50: [labels_gemini.csv](labels_gemini.csv)

The two label sets agree on this dataset. That is evidence the guide can be
applied consistently, not proof that it always yields a single answer, and it
does not establish that the labels are correct: both labelers followed the
same written procedure.

### Split

30 train / 20 holdout, split randomly with a fixed seed and committed before
any prompt was run: [split.py](split.py)

Prompts were not tuned against the holdout. Neither prompt was revised at any
point after being written.

### Prompt versions

Both in [prompts.py](prompts.py). The only variable is how much of the
decision procedure the prompt conveys.

- `v1_naive` (181 chars): the six category names, no precedence, no
  elaboration.
- `v2_structured` (994 chars): the numbered precedence order and the
  domain-priority rules from the labeling guide.

Output format is constrained identically in both ("Reply with exactly one
word from this list and nothing else") so that exact-match scoring measures
classification rather than format compliance.

### Model settings

Recorded in each run's metadata:

    model             gpt-4o-mini
    temperature       0.0
    max_tokens        10
    sdk_max_retries   0
    provider          openai
    metric            normalized_exact_match

The SDK's automatic retries are disabled so the wrapper's 3-attempt retry
budget is not multiplied. Retry policy is in [retry.py](retry.py).

### Runs

3 repeats per version over the 20 unique holdout tickets. Each repeat made
fresh generations; none reused stored outputs. 20 unique tickets, 3
generations per ticket per version, 60 generations per version.

Repeated generations do not increase the number of unique tickets. The
dataset is 20 holdout tickets in every run.

## Results

### Accuracy per run

| version | run | correct | accuracy |
|---|---|---|---|
| v1_naive | [repeat 1](runs/v1_naive_holdout.json) | 16/20 | 0.800 |
| v1_naive | [repeat 2](runs/v1_naive_holdout_r2.json) | 16/20 | 0.800 |
| v1_naive | [repeat 3](runs/v1_naive_holdout_r3.json) | 16/20 | 0.800 |
| v2_structured | [repeat 1](runs/v2_structured_holdout.json) | 19/20 | 0.950 |
| v2_structured | [repeat 2](runs/v2_structured_holdout_r2.json) | 19/20 | 0.950 |
| v2_structured | [repeat 3](runs/v2_structured_holdout_r3.json) | 19/20 | 0.950 |

80% to 95%: an increase of 15 percentage points.

### Per-ticket changes

Four tickets went from 0/3 correct under v1 to 3/3 under v2:

| id | expected | v1 predicted | v2 predicted |
|---|---|---|---|
| t12 | account | bug | account |
| t15 | integration | bug | integration |
| t18 | integration | feature | integration |
| t19 | account | bug | account |

One ticket went from 3/3 correct under v1 to 0/3 under v2:

| id | expected | v1 predicted | v2 predicted |
|---|---|---|---|
| t47 | account | account | integration |

Response text was identical across all three runs for every ticket under
both versions; no ticket produced differing strings between repeats.

## The t47 regression

Ticket text:

> Invited a colleague three days ago, they never got the email.

The expected label is `account`. The labeling guide's account rule covers
"login, passwords, permissions, profile", and a team invitation is a
permissions and user-management action, so it falls under account rather than
under the integration rule for "third-party connections, API access,
webhooks".

Predictions:

| version | repeat 1 | repeat 2 | repeat 3 |
|---|---|---|---|
| v1_naive | account | account | account |
| v2_structured | integration | integration | integration |

Observed in all three runs.

A hypothesis, not a demonstrated cause: v2 states that integration takes
precedence over bug and feature, and the word "email" may be read as a
third-party system, so the precedence instruction that corrected t12, t15,
t18 and t19 may also have pushed this ticket toward integration. Testing
that would require varying the prompt's integration wording in isolation,
which this study did not do.

What the study does show is a case the aggregate score hides. The mean rose
15 points; a ticket that v1 classified correctly, v2 did not. Reporting only
accuracy would not surface it.

## Limitations

- 20 held-out tickets is a small sample. A single ticket is 5 percentage
  points.
- Category coverage in the holdout is uneven. Of the 20 held-out tickets:
  8 bug, 5 account, 3 feature, 3 integration, 1 billing, 0 other. The
  results say nothing about `other` and almost nothing about `billing`;
  the headline accuracy covers five of the six categories.
- One model, one configuration: gpt-4o-mini at temperature 0.0. Results may
  not transfer to other models, temperatures or providers.
- All six holdout runs were made within a short window on 2026-09-20 with
  the same requested model name and settings. The backend model version and
  serving conditions were not recorded. Stability within one window is not
  stability over model versions, load conditions, or time.
- Three repeats do not establish statistical significance or reliability.
  Sampling effects have not been conclusively ruled out; the repeats show
  that the observed outputs recurred under these conditions, nothing more.
- Runs do not record request identifiers, the model version actually served,
  finish reasons, or token usage. Recording them would improve traceability.
  It would not by itself prove deterministic generation or rule out every
  intermediate cache, and nothing in these artifacts suggests caching
  produced the identical responses.
- The tickets are fictional and written by the same author who wrote the
  labeling guide.

## Reproduction

The saved runs contain every prompt, response, label and score. Nothing in
this section needs an API key.

Recompute every stored score from the saved response and expected answer,
reporting any mismatch (exits non-zero if one is found):

    uv sync --locked --dev
    uv run case_study/rescore.py

Summarize and compare the stored scores. These read the scores saved in each
run; they do not recompute them:

    uv run case_study/repeats.py
    uv run case_study/compare_runs.py \
      case_study/runs/v1_naive_holdout.json \
      case_study/runs/v2_structured_holdout.json
    uv run case_study/show.py case_study/runs/v2_structured_holdout.json

Reproducing the generations themselves requires an OpenAI API key and will
make 20 calls per invocation:

    uv sync --extra openai
    uv run case_study/run.py v1_naive holdout 4

The runner refuses an existing destination before making any model calls, so
a repeat index that already exists will stop without spending anything.
