# Stage 2 — System Architecture

## Final flow

```text
Authenticated Employee
  -> Receipt + Expense Description
  -> Submission Validation
  -> Expense Understanding
  -> Policy Evidence Selection
  -> Compliance Decision
  -> APPROVE / REJECT / REQUEST_INFORMATION / ESCALATE
  -> Finance Review only when escalation requires human judgement
```

## Module responsibilities

| Module | Type | Responsibility |
|---|---|---|
| Submission Validation | Deterministic | Validate authenticated/active employee and required submission fields |
| Expense Understanding | AI-enabled | Convert receipt + description into structured expense evidence |
| Policy Evidence Selection | Retrieval/data | Select relevant company reimbursement policy evidence |
| Compliance Decision | AI-enabled | Apply supplied policy to expense evidence and choose the outcome |
| Finance Review | Human | Resolve escalated or exceptional cases |

## Important design boundary
OCR/text extraction alone answers what text is present. The AI expense-understanding behaviour is responsible for semantic interpretation: category, missing information, line-item meaning and receipt-description mismatch.

## Guardrails (implemented; "never let model text authorise an action by itself")
- **Submission Validation is a hard, deterministic gate**, not a soft check: it verifies the
  employee exists and has `status == ACTIVE` before any AI module is invoked. A failure returns
  `REJECT` immediately with zero AI calls made for that claim — no cost is spent authenticating a
  claim that was never going to be evaluated. Verified against DEV012 (an inactive employee).
- **Prompt-injection pre-check.** A deterministic regex screen on the employee-submitted
  description runs before/alongside Compliance Decision. If the description contains
  instruction-override-style text, the decision is forced to `ESCALATE` and the AI module's own
  proposed decision is discarded outright, regardless of what it returned. Verified against DEV019.
- **Citation-validation check.** Compliance Decision's own prompt says "apply the supplied policy
  as written; do not invent company rules." If its output cites a `policy_id` that was never part
  of the evidence actually supplied to it, that is treated as a fabricated citation and the
  decision is forced to `ESCALATE`.
- **Real-run cost guard.** Before any section of the notebook makes real (non-mock) API calls, it
  must print the current API-key balance and an estimated call/cost range, and requires an
  explicit `CONFIRM_REAL_RUN = True` flag to proceed — prevents an accidental full run from
  spending budget silently.

None of these guardrails call an LLM to police another LLM — each is plain deterministic code, so
each is free and cannot itself be talked into anything.
