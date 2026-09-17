# Labeling guide: support ticket classification

Single label per ticket. Six categories. Labels are assigned by hand before
any model sees the ticket.

## Principle

Classify by the **requested resolution** - what the user wants to happen -
not by the underlying technical cause. A billing problem caused by a software
defect is still billing, because the user wants their money back, not a patch.

## Categories

Apply in this order. The first three are domain-specific and take precedence.

**billing** - charges, refunds, invoices, subscription changes. Applies even
when a software bug caused the problem.

**account** - login, passwords, permissions, profile. Applies even when the
failure is a server error. A login 500 is account.

**integration** - third-party connections, API access, webhooks. Applies even
when something is broken.

**feature** - a request for a new built-in product capability that does not
exist. Excludes anything already covered by billing, account or integration.

**bug** - an existing built-in product capability that fails. Residual: only
after billing, account and integration have been ruled out.

**other** - a clear request falling outside all five.

## Multiple issues

Use the explicitly stated primary request. Users often signal it directly:
"but the main thing is", "first and foremost", "the urgent part".

If a ticket raises several issues with no stated primary request, do not
guess. Mark it `NEEDS_REVIEW` and exclude it from the single-label dataset.
Record how many were excluded and why.

## Worked examples

These are the four overlaps identified before the guide was written.

**"The export button doesn't work"**
Label: `bug`. Not billing, account or integration. An existing capability
that fails.

**"There's no export button"**
Label: `feature`. Nothing is failing. The user wants a capability that does
not exist.

The pair matters: identical frustration, opposite labels. The distinction is
whether the capability exists.

**"I can't log in" / "Login throws a 500 error"**
Label: `account` for both. The account rule is explicit that a server error
during login stays account. Cause does not move the label; the requested
resolution is the same - get me into my account.

**"I was charged after cancelling"**
Label: `billing`. A defect probably caused it, but billing takes precedence
over bug and the user wants a refund.

**"Your Slack integration stopped posting"**
Label: `integration`. Integration takes precedence over bug; brokenness does
not override the domain rule.

## Dataset construction

Include ordinary tickets and realistic edge cases in proportions a real queue
would produce. Do not select or word tickets to manufacture a difference
between prompt versions - that would make the comparison circular. Write and
label tickets before either prompt is drafted.

## Holdout

Freeze a subset before any prompt tuning. Tune against the visible set,
report on the frozen set. Record the split and when it was frozen.
