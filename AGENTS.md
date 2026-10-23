# Research integrity contract — shared by Codex and Claude

## Mission
Build a **reproducible historical event sampling frame**, not a list of commercially successful stories. Stage 1 covers events publicly announced during **2020-01-01 through 2025-12-31**; stage 2 demand/outcome analysis is NOT in scope.

## Absolute rules
1. Never fabricate a document, historical fact, URL, date, quotation, API result, test run, or validation status.
2. Separate source `publication_date`, date the current file was fetched, prospective `effective_date`, and independently established *first availability*. Never equate these without evidence.
3. Store raw downloads with hashes and source metadata. Never edit raw downloads after collection.
4. Every extracted claim needs an exact supporting quotation from the stored source document.
5. An AI output is a **candidate**. Only `review` with an explicit human assessment can label it accepted; do not auto-mark source/date verification.
6. Never use subsequent demand, sales, popularity, vendor outcomes, Google Trends after the event, or search results indicating later success to select events.
7. Log **all retrieved documents**, screening decisions, exclusions, errors and duplicate handling. Audit rejected documents to estimate missed events.
8. Use deterministic sampling with logged frame, seed, strata, inclusion probabilities and checksums. Never cherry-pick replacements after sample selection.
9. Raw and frozen data are append-only in intention; ensure application code refuses overwrites. Filesystem permission alone is not a legally immutable audit store.
10. No outcome labels or future-market data in collector, extractor, verifier, reviewer or sampling paths.
11. Never quietly change `protocol/` rules once data collection begins. Record a versioned amendment and rerun the complete pipeline.
12. Run `python -m unittest discover -s tests -v` before declaring working software. Report *what was actually run*.

## Implementation workflow
- Claude Code is the main implementer. Codex performs an independent, adversarial audit through `.codex/prompts/independent-audit.md`.
- Each reviewer works on separate git branches/worktrees. Neither modifies `data/frozen/`.
- Prefer standard Python 3.11+ and reproducible fixtures. Network collectors need explicit rate limits and bounded pagination.
- Treat publication documents as historical evidence **only when** their original dated content/archival stability has been verified in review; a live updated web page isn't sufficient.
- Treat prompts, models and source schemas as versioned research instruments.

## Run commands
`python -m unittest discover -s tests -v`
`python -m radar --help` (after `python -m pip install -e .`)

## STOP conditions
Stop and report instead of inventing: inaccessible original source, ambiguous original date, unverifiable quotation, API terms uncertainty, failing tests, or missing source body. Report limitations instead of smoothing the dataset.
