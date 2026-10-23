# Architecture and trust boundaries

`Federal Register (primary publication documents)`
→ `deterministic collector (bounded pagination, source files, hashes, failures)`
→ `screening frame (includes rejected docs)`
→ `extractor (heuristic or bounded model API)`
→ `exact-quote/source-hash validator (code)`
→ `independent review / original-date attestation (human)`
→ `accepted event frame & duplicate checks`
→ `stratified deterministic sampling (code)`
→ `pilot sample manifest & write-once freeze`.

## Agent boundaries
- **Claude Code agents** live in `.claude/agents/` and are for engineering and targeted document checks.
- **Production extractor** is `radar.extract`. AI via Anthropic is OPTIONAL, called on one stored source body, without search tools.
- **Codex reviewer** is a second engineering reviewer, directed through `.codex/prompts/` and root AGENTS.md. These are prompts, not autonomous cron jobs.
- **Human reviewer** is an explicit attestation using `radar review`. AI never approves itself.

## Invariants
- No outcome datasets anywhere in stage 1. The corpus should contain no sales data or after-event success labels.
- Frozen state cannot be recreated by modifying it in place; `freeze` refuses overwrite.
- Field-level quotations are substring-verified against the SHA256-verified source. Semantic correctness still requires human review.
- One document → at most one candidate in pilot. Amend if multiple economically independent changes per document prove common.
- Screening frame stored as JSON to allow independent negative-document samples.

## Important limitations, intentionally not hidden
1. Limited pagination (`--max-pages` / `--max-docs`) makes a **partial frame**, not a probability sample of all Federal Register events. Current collector reports `frame_complete` and cannot establish true population coverage across sites.
2. Direct text may require fallback extraction from HTML; verifier must examine layout, amendments and whether text is an original dated publication.
3. `review --date-verified` is a human attestation, not an automated proof of first public availability.
4. Sample stratifies only source and year, not all economic sectors or countries.
5. Current version has only one live source adapter; **final sample gate stays closed** until multiple independent source families and coverage audit exist.
6. API response fields/rate limits can change. Collector was designed with errors and retries but live compatibility must be verified in the target environment.
7. AI models might possess subsequent historical knowledge from training; source-only prompts do not prove no hindsight contamination.
