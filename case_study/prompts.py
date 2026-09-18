"""Two prompt versions under comparison.

The only variable is how much of the decision procedure the prompt conveys.
Output format is constrained identically in both so that exact-match scoring
measures classification rather than format compliance.
"""

CATEGORIES = "billing, account, integration, feature, bug, other"

V1_NAIVE = f"""Classify this support ticket into exactly one category.

Categories: {CATEGORIES}

Reply with exactly one word from that list and nothing else."""


V2_STRUCTURED = f"""Classify this support ticket into exactly one category.

Classify by the requested resolution - what the user wants to happen - not by
the technical cause.

Apply these categories in order. The first three take priority over bug and
feature:

1. billing - charges, refunds, invoices, subscription changes. Applies even
   when a software bug caused the problem.
2. account - login, passwords, permissions, profile. Applies even when the
   failure is a server error. A login 500 is account.
3. integration - third-party connections, API access, webhooks. Applies even
   when something is broken.
4. feature - a request for a new built-in capability that does not exist.
   Excludes anything covered by 1-3.
5. bug - an existing built-in capability that fails. Only after billing,
   account and integration have been ruled out.
6. other - a clear request falling outside all five.

Reply with exactly one word from this list and nothing else:
{CATEGORIES}"""


PROMPTS = {"v1_naive": V1_NAIVE, "v2_structured": V2_STRUCTURED}
