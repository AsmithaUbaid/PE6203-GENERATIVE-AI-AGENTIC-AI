# Stage 7 — Failure Analysis and Improvement

## Required failure record

| Case | Input summary | Expected | Actual | Failure source | Likely cause | Targeted fix | Retest result |
|---|---|---|---|---|---|---|---|

## Diagnostic sequence
1. Was submission/input invalid? -> deterministic issue
2. Was structured expense wrong? -> Expense Understanding failure
3. Was required policy absent from retrieved evidence? -> retrieval failure
4. Was evidence correct but decision wrong? -> Compliance Decision failure
5. Was uncertain evidence handled too confidently? -> uncertainty-handling failure

## Improvement categories
- prompt change
- few-shot example change
- retrieval/query change
- workflow/failure-routing change
- other justified change

## Retest rules
- Retest the same failed case.
- Rerun regression cases.
- Record before/after metrics.
- Never remove a difficult case because it failed.
- Never change expected ground truth after viewing model output unless the original label is independently proven wrong.
