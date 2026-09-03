# Experimental Protocol

## Purpose
Make all comparisons reproducible and fair.

## Version everything
Record:
- dataset version
- policy version
- prompt version for each module (Module 2 has two documented versions, v1 frozen / v2 hardened —
  see docs/03; which one produced a given result must always be recorded, not assumed)
- retrieval configuration (embedding model + method vs the keyword-overlap baseline — see docs/04)
- model name/version (multiple candidates are compared in Section 5c; record which one produced a
  given result)
- experiment date
- variant
- **run mode**: `MOCK_MODE` True/False must be recorded and disclosed alongside every other
  version field above — simulated (mock) numbers must never be reported as if they were measured
  (see the notebook's own opening rule and every mock-mode banner in its output)

## Development vs evaluation
- Development/few-shot/debugging cases may be used to improve prompts and retrieval.
- Final 20 cases remain untouched until final evaluation.
- Once final evaluation begins, freeze prompts/configuration for the reported A/B/C comparison.

## Repeatability
For stochastic model settings:
- keep generation settings fixed across comparable experiments
- record temperature / sampling settings
- if variability is material, repeat runs and report mean/range

## Per-run record
- case_id
- expected decision
- predicted decision
- extraction ground truth and predictions
- expected policy IDs
- retrieved policy IDs
- final cited policy IDs
- uncertainty label
- latency
- tokens
- cost
- error/failure notes

## Analysis outputs
### Main assignment evidence
- four main metrics
- A/B/C controlled comparison
- failure analysis + retest

### Additional engineering evidence
- latency
- token/API cost
- retrieval Recall@K
- cost-quality trade-off
- latency-quality trade-off
- human-review rate
- effort/ROI scenario analysis
