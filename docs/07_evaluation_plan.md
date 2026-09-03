# Stage 6 — Evaluation Plan

## Frozen evaluation set
Exactly 20 cases, not used for prompt/retrieval tuning.

## Required variants

### Variant A — Minimal LLM
Receipt + description -> minimally instructed LLM -> decision.

### Variant B — Simplified system
Receipt + description -> structured expense understanding -> compliance decision, without policy retrieval.

### Variant C — Full system
Receipt + description -> expense understanding -> policy retrieval -> grounded compliance decision.

Keep model, evaluation set and output labels constant where possible.

## Four main criteria

### 1. Compliance Decision Accuracy
`correct final decisions / all evaluation cases`

Also report a confusion matrix for:
- APPROVE
- REJECT
- REQUEST_INFORMATION
- ESCALATE

### 2. Expense Understanding Accuracy
Report per-field accuracy for:
- merchant
- date
- amount
- currency
- category
- mismatch detection

Also provide an aggregate field accuracy, but do not hide per-field failures.

### 3. Policy Grounding Accuracy
For applicable cases:
`cases where relevant policy ID/evidence is correctly used / policy-applicable cases`

Optionally report retrieval Recall@K separately as a diagnostic:
`cases where required policy appears in top-K / cases requiring that policy`

Report Recall@K for both the production retrieval method (embedding) and the keyword-overlap
baseline, per docs/04 — the gap between them is itself part of the evidence for the retrieval
design choice, not just a diagnostic aside.

**Additional diagnostic (not one of the four required metrics): explanation-grounding heuristic.**
Decision accuracy and policy-ID grounding say nothing about whether Module 2's free-text `reason`
is actually faithful to what it cites. Rather than spend on an LLM-as-judge, a deterministic proxy
is reported alongside: what fraction of a decision's cited `policy_ids` are literally mentioned in
its own `reason` text (notebook Section 8b, `reason_grounding.csv`).

### 4. Safe Uncertainty Handling
`uncertain/incomplete cases correctly mapped to REQUEST_INFORMATION or ESCALATE / all designated uncertainty cases`

## Additional engineering metrics
- p50 and p95 total latency
- per-module latency
- input/output tokens per claim
- API cost per claim
- cost per 100 / 1,000 claims
- escalation/human-review rate
- estimated manual effort per 100 claims

## Useful plots
1. A/B/C decision accuracy bar chart
2. A/B/C four-metric comparison
3. Confusion matrix for full system
4. Module 1 per-field accuracy
5. Retrieval Recall@K
6. Latency by variant (p50/p95)
7. Cost per claim by variant
8. Accuracy vs cost trade-off
9. Accuracy vs latency trade-off
10. Human-review rate by variant
11. Before/after improvement comparison from Stage 7
12. Retrieval Recall@K: embedding vs. keyword-overlap baseline (docs/04)
13. Prompt-technique comparison: zero-shot vs. few-shot vs. prompt v1/v2 (docs/03)
14. Model comparison across candidate models (docs/03)

Do not create plots with invented results. Generate them only from run logs.
