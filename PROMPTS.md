# Copy-ready prompts

## First Claude Code session
"Read AGENTS.md, CLAUDE.md, PLANS.md and protocol/* first. Do NOT search for commercially successful examples or demand outcomes. Inspect the existing source collector, run all tests, and evaluate whether the pilot can be executed correctly. First propose any protocol or provenance corrections; then implement Phase A only. Report actual counts, API failures and test results. Do not change the sampling rules without recording an amendment."

## Claude Code: run pilot
"Use the bounded Federal Register source. Start with a narrow historical date window, not full years. Verify available source text; inspect false negatives among excluded documents; manually review 20 diverse candidates; create sample manifest and verify recreation. Provide a reproducible commands-and-observations report, not just a narrative."

## Codex independent audit
"Read AGENTS.md and .codex/prompts/independent-audit.md. Challenge the historical validity, source coverage, selection design, field-level evidence, deduplication, temporal leakage, deterministic sampling, and data immutability claims. Create adversarial unit tests on a separate branch. Do not edit data/frozen or declare evidence reviewed without inspection. Return severity-ranked findings with line references and exact reproduction steps."
