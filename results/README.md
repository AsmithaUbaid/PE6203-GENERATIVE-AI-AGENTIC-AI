# Results Directory

Save measured outputs here:
- variant_results.csv
- module1_results.csv
- retrieval_results.csv
- module2_results.csv
- latency_cost_results.csv
- failure_retests.csv
- four_required_metrics.csv
- run_log.csv — every AI-module call, one row each (real or simulated; see `is_mock` column)
- prompt_ablation_module1.csv / prompt_ablation_module2.csv — zero-shot vs. few-shot vs. prompt v1/v2
- model_comparison.csv — gpt-4.1-mini vs. gpt-4o-mini vs. gemini-2.5-flash
- reason_grounding.csv — explanation-grounding heuristic by variant
- retrieval_embedding_vs_keyword.csv
- generated plots

**MOCK_MODE**: while the notebook's `MOCK_MODE` flag is `True`, none of the above are measured
results — every AI-module call is a free, deterministic simulation. In that state, all of these
files are written to `results/mock/` instead of here, so simulated numbers can never be mistaken
for the reportable evidence this directory is meant to hold. Only files written directly under
`results/` (not `results/mock/`) should be cited as real evaluation evidence in the report.
