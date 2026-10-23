# Build plan — gated

## Phase 0 — protocol (complete as drafted, MUST REVIEW)
- [x] Draft research question, eligibility definitions, source hierarchy, sampling frame, and audit rules.
- [x] Separate prospectively observable fields from future outcome measurements.
- [ ] Approve/freeze the protocol before substantive source collection.

## Phase A — proof of provenance and 20-event pilot
- [x] Executable bounded collector for Federal Register, with local snapshots and hashes (code supplied).
- [x] Deterministic heuristic candidate screening plus optional Anthropic API extraction.
- [x] Field-level quote verifier, explicit review commands, deterministic sampling, freeze/verify commands (code supplied).
- [x] Unit tests with **synthetic** fixtures.
- [x] Execute live API collection using network access (2026-10-23: run 1 blocked by federalregister.gov access page and quarantined; run 2 = 100 GovInfo official-text snapshots, frame partial). Official dated content verified by header/FR Doc number only; independent historical-availability verification still open.
- [ ] Independently review 20 eligible events and rejected-document sample. (Review aids for 20 docs + 5 negatives produced 2026-10-23; 0 human reviews; blocked on protocol ratification + Amendment A-001, see docs/RESEARCH_LOG.md.)
- [ ] Codex adversarial review and fixes (with test evidence).

## Phase B — expand diversity and validity
- [ ] Add a second **different** primary archive adapter and contract tests.
- [ ] Sample negatives from excluded/source-fetched documents; estimate false-negative rate with uncertainty.
- [ ] Validate deduplication across multiple sources, document amendments, and dates.
- [ ] Revisit stratification, coverage and weighting before committing to N=150.

## Phase C — build 150-event frozen frame
- [ ] Complete multi-source collection and manual validation to protocol.
- [ ] Generate 150-event stratified sample using locked seed, auditable sample frame, and stable inclusion probabilities.
- [ ] Independently reproduce sample and archive input/output hashes.
- [ ] Issue honest coverage, representativeness, missing-data and quality report.

## Phase D — future, NOT part of this repo's current research
Measure after-event demand outcomes in a separate, access-controlled project, with frozen cohorts and predeclared outcomes/baselines.
