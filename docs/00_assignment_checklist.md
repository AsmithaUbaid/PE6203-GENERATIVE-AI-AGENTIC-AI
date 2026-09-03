# Assignment Checklist

A checked box below means the design/implementation artefact the item asks for exists in
docs/ or the notebook — **not** that it has been run for real. The notebook's `MOCK_MODE = True`
means every number produced so far is a free, deterministic simulation; the mechanism to produce
the real thing is complete and tested, but a real run (`MOCK_MODE = False`, budget permitting)
still has to happen before any of these numbers can go in the report.

## Mandatory
- [x] One focused problem and clearly defined primary user (docs/01)
- [x] 2–4 success criteria fixed before implementation (docs/01)
- [x] Input-to-output architecture diagram (docs/02)
- [x] Major module responsibilities explained (docs/02, incl. guardrails)
- [x] At least two AI-enabled behaviours with different purposes (Module 1 extraction, Module 2 decision, plus Variant A as a third)
- [x] Exact model names recorded (docs/03 — `openai/gpt-4.1-mini` via OpenRouter, primary; 2 more candidates compared)
- [x] Exact prompts/instructions recorded (docs/03 — Module 1, Module 2 v1 + v2, Variant A, all verbatim)
- [x] Inputs, context and structured outputs for every AI module (docs/03)
- [ ] Important prompt instructions justified (still needs report-writing prose beyond the design notes already in docs/03/04)
- [x] ICL / external-evidence decision documented (docs/04)
- [x] Lightweight RAG design documented if used (docs/04)
- [ ] Working prototype with major modules visible — the notebook implements and can run the full pipeline end-to-end, but there is no standalone deployed app/UI yet
- [ ] AI builders/tools and their implementation role documented — not yet written up anywhere (this session used Claude Code throughout; needs a short section in the report)
- [x] 20 final evaluation cases frozen before final evaluation (`final_evaluation_cases.csv`, untouched since freeze — see docs/05 for the one disclosed limitation)
- [x] Same 20 cases used for Variant A / B / C (notebook Section 7)
- [x] Four evaluation criteria reported (notebook Section 8)
- [x] Failure cases diagnosed, fixed and retested (notebook Sections 17–18, incl. one real code fix verified by real retrieval re-scoring, not just mock)
- [ ] PDF report within 10 pages excluding cover — not started
- [ ] Cover: member names, emails, contributions — not started
- [ ] Working system link at end of report — not started
- [ ] <=10-minute presentation: 6 min explanation, 2 min demo, 2 min Q&A — not started

## Additional engineering evidence we choose to include
- [x] Latency per variant/module (notebook Section 10)
- [x] Token/API cost per variant and per claim (notebook Section 11, incl. prompt-caching estimate)
- [x] Manual-effort assumptions (notebook Section 13)
- [x] Cost/effort/ROI scenario analysis (notebook Sections 14–15)
- [x] Sensitivity analysis (notebook Section 16)
