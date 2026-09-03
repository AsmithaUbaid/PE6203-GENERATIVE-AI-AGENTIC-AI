# Stage 4 — ICL / Lightweight RAG

## Context strategy

| Module | Few-shot | Retrieval | Strategy |
|---|---|---|---|
| Expense Understanding | Yes, minimal | No | 2–3 examples for normal, missing-information and mismatch behaviour |
| Compliance Decision | Yes, minimal | Yes | Retrieved policy snippets are primary evidence; 2–3 examples teach outcome behaviour |

## RAG source
The realistic source artifact is:

`Corporate_Expense_Policy.pdf`

Processing flow:

```text
Corporate_Expense_Policy.pdf
  -> extract text
  -> divide into meaningful policy sections
  -> assign policy IDs / metadata
  -> index/store sections
  -> retrieve relevant sections for each structured expense
```

## Retrieval flow

```text
Structured expense/category/issues
  -> retrieval query
  -> top relevant policy sections
  -> Compliance Decision AI
  -> grounded decision + policy IDs
```

Initial K: 3.

## Retrieval method (decided during implementation; documented here per the ICL/RAG-decision
requirement)
**Primary/production method: semantic retrieval** — sentence embeddings (`all-MiniLM-L6-v2`, local
model, no API call, zero marginal cost) over each policy's title + full text, ranked by cosine
similarity against a query built from the structured expense's category, business purpose, line
items, and missing-information fields. Keyword/token overlap is implemented and measured
**only as a labelled comparison baseline** (notebook Section 4) — it is never used to select the
evidence actually supplied to Module 2.

This was a deliberate choice, not a default: an early version scored both methods with an
additional deterministic "+3.0 if Module 1's predicted category matches the policy's category"
boost, which made keyword overlap and embedding retrieval score identically (~0.89 Recall@3 on the
development set) regardless of how differently the policy text and a claim description were
worded. That boost was removed from both methods once it became clear it was masking, rather than
reflecting, real retrieval quality — with it removed, embedding retrieval scores 0.833 vs.
keyword overlap's 0.389 Recall@3 on the same cases, which is the real basis for choosing semantic
retrieval as the production method here.

The `keywords` column in `expense_policies.csv` is intentionally left **empty for every policy** —
representing a realistic corpus with no hand-curated keyword index, so retrieval genuinely has to
work from the policy prose itself. The policy corpus was also deliberately expanded to 35 clauses
(from an original 20) — a mix of additional distractor categories (mileage, relocation, home-office
stipend, etc.) and sibling clauses within categories the evaluation cases already use — specifically
to stress-test retrieval quality with more realistic corpus size and within-category competition.
See docs/05 for the full corpus-size rationale.

## Failure behaviour
- No relevant policy: ESCALATE
- Weak/uncertain policy evidence: ESCALATE
- Conflicting policy sections: ESCALATE
- Clear policy but claimant information missing: REQUEST_INFORMATION
- Never fabricate a company rule — enforced by a **citation-validation guardrail**: if Module 2
  cites a `policy_id` that was not actually part of the retrieved evidence supplied to it, the
  decision is overridden to ESCALATE rather than trusted (docs/03).
