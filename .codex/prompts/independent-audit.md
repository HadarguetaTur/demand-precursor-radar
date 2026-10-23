# Independent adversarial review — instruction to Codex

Scope: Stage-1 historical event collection and sampling only.

Read AGENTS.md, protocol/*, src/radar/*, tests/*, plus any existing collected manifests. You must try to falsify correctness. In particular:
- Show if source filters systematically exclude valid events or preferentially include successful changes.
- Create test cases for missing original pages, publication edits, quote mismatch, future-dated effective date, duplicated revisions, and a 1-document-to-many-events case.
- Test deterministic sample selection with reordered frames, multiple strata, shortages, zero allocations and tampered raw data.
- Inspect explicit human review and temporal verification gates.
- Confirm exclusion and negative screening audits are possible.
- Check for data leaks into prompts or filenames referencing later demand/outcomes.
- Check whether reported dates actually mean first-public availability.
- Find any way an agent can auto-approve its own candidate.

Report blocker/high/medium/low findings, reproduction commands, tests actually executed, protocol amendments recommended, and residual inference limits. Never claim a review of external live data unless it occurred. Do not mutate frozen data. Add independent tests on a separate branch if possible.
