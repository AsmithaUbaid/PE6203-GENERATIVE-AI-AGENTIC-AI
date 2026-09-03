# Stage 5 — Implementation Plan

## Goal
Implement the already-designed workflow. Do not use implementation tools to redesign the architecture, prompts, knowledge strategy or evaluation.

## Build order
1. Create synthetic corporate expense policy PDF. ✓ (`scripts/gen_policy_pdf.py` — regenerable from `expense_policies.csv`)
2. Convert policy sections into retrieval-ready structured records. ✓
3. Create small synthetic employee table. ✓
4. Create realistic SGD development receipt cases. ✓
5. Implement deterministic submission validation. ✓ (`validate_submission()` — an ACTIVE-employee gate that runs before any AI module and can reject a claim at zero cost; see docs/02)
6. Implement Expense Understanding module. ✓
7. Implement policy retrieval. ✓ (embedding-based; see docs/04)
8. Implement Compliance Decision module. ✓ (plus the injection and citation-validation guardrails; see docs/02/03)
9. Connect full flow. ✓ (Variant A/B/C wrappers + the frozen final-evaluation loop)
10. Log intermediate outputs, token usage, latency and errors. ✓ (`RUN_LOG`, exported as `run_log.csv`)
11. Validate using development cases only. ✓
12. Freeze final evaluation set after the development system is stable. ✓ — frozen and, per deliberate choice, left untouched even after later gap-coverage additions went only into the development set (see docs/05's disclosed limitation).

## Minimum logging required
For every system run save:
- run_id
- timestamp
- case_id
- variant
- model
- prompt/version
- raw/structured module outputs
- retrieved policy IDs
- final decision
- error status
- module latency
- total latency
- input/output token counts where available
- estimated API cost where available
- **is_mock** — whether this record came from a real API call or a simulated (`MOCK_MODE`) one;
  added once dry-run development made it clear this distinction had to be explicit in the log
  itself, not just asserted in prose

This logging is essential for reproducible experiments and later plots.
