# Development Dataset Specification

## Files

### 1. employees.csv
Synthetic employee records used only for deterministic prototype identity/status context. Deliberately
includes one `FINANCE_REVIEWER` role (E004) and one `INACTIVE` status (E006) — the latter exists
specifically to exercise the deterministic Submission Validation gate (docs/02), which rejects any
claim from a non-`ACTIVE` employee before any AI module is invoked (see DEV012).

Suggested fields:
- employee_id
- name
- email
- department
- role
- status

### 2. Corporate_Expense_Policy.pdf
Synthetic but realistic Singapore corporate expense policy written as a normal company policy document.

### 3. expense_policies.csv
Processed retrieval representation derived from the PDF.

Fields:
- policy_id
- category
- policy_text
- keywords (optional)
- source_section / page (recommended for traceability)

### 4. development_cases.csv
Used for prompt/retrieval development and debugging.

Fields:
- case_id
- receipt_path
- employee_id
- description
- gt_merchant
- gt_date
- gt_amount
- gt_currency
- gt_category
- gt_line_items
- gt_missing_information
- gt_mismatch
- gt_policy_ids
- gt_decision
- case_category

### 5. final_evaluation_cases.csv
Same essential schema as development cases, but frozen and never used for tuning.

## Receipt strategy
Main project cases should use realistic **synthetic Singapore/SGD receipts** so policy boundaries and ground truth are controllable.

Optional public receipt datasets may be used only for supplementary robustness/development work after verifying suitability and licensing.

## Development case coverage
Include:
- normal compliant ✓ (multiple dev + eval cases)
- clear violation ✓ (`policy_violation` cases)
- threshold/boundary ✓ (`boundary` cases)
- missing information ✓ (`missing_information`, `approval_missing`, `missing_context`)
- ambiguous ✓ (DEV020, `conflicting_policy_interpretation` — two policy sections genuinely conflict)
- policy exception ✓ (`policy_exception` cases)
- receipt-description mismatch ✓ (EVAL011)
- blurry/cropped/faded/rotated receipts ✓ (DEV011, `partial_receipt_quality`)
- mixed personal/business items ✓ (EVAL019, `mixed_expense`)
- insufficient policy evidence ✓ (DEV017, `insufficient_policy_evidence` — no policy section applies)

Added beyond the original list, during implementation, once these were identified as real gaps:
- **inactive/unauthenticated employee** (DEV012, dev-only) — exercises the Submission Validation gate
- **prompt-injection attempt** (DEV019, and EVAL017 after rebalancing below) — exercises the injection-detection guardrail
- **conflicting policy interpretation** (DEV020, and EVAL013 after rebalancing below) — two policy sections genuinely conflict
- **no receipt, under the SGD 20 threshold** (DEV013, dev-only) — exercises `receipt_present=False` handling

**Eval-set rebalancing (two passes, both before any real evaluation ran):** the frozen 20 was first
left untouched (docs/10's rule) while these gaps were only in the development set. Once the eval
set's own decision-label distribution turned out heavily skewed (ESCALATE was 1/20 = 5%, against
APPROVE at 9/20 = 45%), it was rebalanced: 3 redundant `normal_compliant`/`policy_exception` APPROVE
cases (EVAL001, EVAL013, EVAL017) were replaced **in place** (same case_id, new content — receipt
image, description, and every ground-truth field) with new ESCALATE scenarios covering
insufficient-policy-evidence, conflicting-policy, and prompt-injection respectively. New decision
distribution: APPROVE 6/20, REQUEST_INFORMATION 6/20, ESCALATE 4/20, REJECT 4/20. This closed most
of the dev-only gap above; **inactive_employee, no_receipt_under_threshold, partial_receipt_quality,
approval_missing, missing_context and policy_prohibited remain development-only** — a smaller,
disclosed limitation rather than a hidden one (see notebook Section 2 for the live breakdown). The
frozen set is not expected to change again once real evaluation begins.

## Recommended sizes
- employees: 4–6 → **6 used** (see note above on E004/E006)
- policy snippets: 15–25 → **35 used**, deliberately larger than recommended. 20 are the
  "real" policies test cases require; 15 more (8 new distractor categories + 7 sibling clauses
  within existing categories) were added specifically to stress-test retrieval quality — see
  docs/04 for why a bigger, more realistic corpus with genuine within-category competition was
  needed to make the embedding-vs-keyword retrieval comparison meaningful rather than trivial.
- few-shot examples: 3–6 total → **4 per module** (Module 1: normal/missing-info/mismatch;
  Module 2: APPROVE/REQUEST_INFORMATION/REJECT/ESCALATE — the ESCALATE example was added after an
  initial gap review found no few-shot example demonstrated it, a majority-label-bias risk)
- development/debugging cases: ~20–30 → **20 used**
- final evaluation: exactly 20 frozen cases → **still 20** — 3 of the 20 were replaced in place
  during the rebalancing described above (same case_ids, new content); count never changed
