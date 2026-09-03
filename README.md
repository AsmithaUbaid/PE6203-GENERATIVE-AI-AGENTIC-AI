# AI Corporate Expense Compliance Checker

## Project purpose
Build and evaluate a prototype that accepts a receipt/supporting document plus an employee expense description, understands the expense, retrieves relevant company reimbursement policy evidence, and returns one of:

- APPROVE
- REJECT
- REQUEST_INFORMATION
- ESCALATE

## Recommended working structure

```text
expense_compliance_project/
├── README.md
├── requirements.txt
├── .env                              # OPENROUTER_API_KEY etc. — gitignored, not committed
├── docs/
│   ├── 00_assignment_checklist.md
│   ├── 01_stage1_problem_success.md
│   ├── 02_stage2_architecture.md
│   ├── 03_stage3_ai_modules_prompts.md
│   ├── 04_stage4_icl_rag.md
│   ├── 05_dataset_spec.md
│   ├── 06_implementation_plan.md
│   ├── 07_evaluation_plan.md
│   ├── 08_cost_effort_roi.md
│   ├── 09_failure_analysis.md
│   ├── 10_experiment_protocol.md
│   └── 11_report_evidence_map.md
├── scripts/
│   ├── gen_policy_pdf.py             # regenerates Corporate_Expense_Policy.pdf from expense_policies.csv
│   ├── nb_set_cell.py                # dev tooling: replace one notebook cell's source by id
│   └── nb_insert_cell.py             # dev tooling: insert a new notebook cell after a given id
├── notebooks/
│   └── expense_compliance_experiments.ipynb
├── data/
│   ├── raw/
│   │   ├── policies/Corporate_Expense_Policy.pdf
│   │   └── receipts/
│   └── processed/
│       ├── employees.csv
│       ├── expense_policies.csv      # 35 policy clauses (20 required by test cases + 15 distractor/sibling)
│       ├── development_cases.csv     # 20 cases
│       ├── final_evaluation_cases.csv  # 20 cases, frozen
│       ├── all_cases.csv
│       ├── receipt_rename_manifest.csv
│       └── validation_report.csv
└── results/
    ├── variant_results.csv
    ├── module1_results.csv
    ├── retrieval_results.csv
    ├── module2_results.csv
    ├── latency_cost_results.csv
    ├── failure_retests.csv
    ├── four_required_metrics.csv
    ├── run_log.csv
    ├── prompt_ablation_module1.csv
    ├── prompt_ablation_module2.csv
    ├── model_comparison.csv
    ├── reason_grounding.csv
    ├── retrieval_embedding_vs_keyword.csv
    └── mock/                         # same file set, written here instead whenever MOCK_MODE=True
```

## Run modes
The notebook has a `MOCK_MODE` flag (Section 0). `True` (the default while developing) makes every
AI-module call a free, deterministic simulation — no network calls, no cost, results exported to
`results/mock/` so they can never be mistaken for reportable evidence. Set `MOCK_MODE = False` to
call real models; doing so requires `OPENROUTER_API_KEY` in `.env` and will not proceed for the
larger sections (final evaluation, ablation, model comparison) until `CONFIRM_REAL_RUN = True` is
set after reviewing the printed balance/cost estimate.

## Notebook purpose
The notebook should be the reproducible experimental record for:
1. data loading and validation
2. receipt/expense-understanding experiments
3. policy retrieval experiments (embedding vs. keyword-overlap comparison)
4. compliance-decision experiments, including guardrail checks (injection defense, citation validation)
5. prompt-technique ablation (zero-shot vs. few-shot vs. prompt v1/v2) and model comparison
6. Variant A/B/C evaluation
7. accuracy/grounding/uncertainty metrics, incl. an explanation-grounding heuristic
8. latency measurement
9. API/token cost measurement, incl. prompt-caching potential
10. manual-effort and ROI calculations
11. failure analysis and retesting
12. plots and final comparison tables

Keep the final 20 evaluation cases frozen and separate from development/debugging cases.
