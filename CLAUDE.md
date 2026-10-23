@AGENTS.md

# Claude Code — project workflow
Read `docs/START_HERE.md`, `protocol/research_protocol.yaml`, and `PLANS.md` before implementation. Never run unrestricted searches or select documents using hindsight outcome signals.

## Subagents
- `source-methodologist`: review source selection, frozen protocol and selection bias before coding.
- `event-extractor`: reason over one supplied historical source (read only), output field-level direct quotations.
- `evidence-verifier`: independently dispute extraction against the original source (read only).
- `sampling-auditor`: examine sampling code/manifest for reproducibility and selection bias (read only).

They are **Claude Code development/review subagents**, NOT a substitute for the production Python pipeline. For high-volume extraction, use a constrained API call to a model and verify all quotes in Python. No autonomous web browsing for historical outcomes.

## First task
Implement/run Stage A (20 events pilot) only, with bounded retrieval. Always show real counts and audit failures. Use plan mode first for changes that could invalidate study design.
