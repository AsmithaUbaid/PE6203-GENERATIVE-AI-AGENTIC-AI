# Enterprise Cost, Effort and ROI Analysis

## Rule
Keep measured prototype economics separate from hypothetical enterprise economics.

## A. Measured prototype metrics
From experiment logs:
- average tokens per claim
- average model/API cost per claim
- cost per Variant A/B/C
- average and p95 latency
- number/percentage escalated

## B. Enterprise assumptions
Clearly label assumptions:
- annual claim volume
- current manual minutes per claim
- loaded finance labour rate
- current rework rate
- current escalation rate
- AI automation rate
- post-AI review time
- maintenance hours/year
- monitoring/audit hours/year
- expected failure frequency
- cost per failure

## Core calculations

### Current manual effort
`annual_volume * manual_minutes_per_case / 60`
plus explicitly modelled rework/escalation effort.

### Current labour cost
`annual_manual_hours * loaded_hourly_rate`

### Future human effort
human-review effort + AI-error rework + maintenance + monitoring.

### Effort saved
`current_manual_hours - future_human_hours`

### Gross savings
Monetize only defensible direct savings; do not double count residual review labour.

### Net annual benefit
`gross_savings - annual_operating_cost - expected_failure_cost`

### ROI
`(net_annual_benefit - initial_investment) / initial_investment * 100`

### Payback
`initial_investment / net_annual_benefit`

## Required scenario analysis
Conservative / Expected / Optimistic for:
- annual volume
- automation rate
- human-review rate
- failure rate
- operating cost
- net benefit
- payback

## Sensitivity analysis
At minimum vary:
1. transaction volume
2. human-review/automation rate
3. false-approval frequency x cost per failure

## Failure economics
Keep mutually exclusive failure outcomes where possible to avoid double counting:
- false approval / missed violation
- false rejection
- unnecessary escalation
- other AI-caused rework
