# Codex is the independent adversarial reviewer

Codex automatically reads the repository's `AGENTS.md` in supported workflows. Files under `.codex/prompts/` here are **reference prompts**, NOT automatically launched autonomous jobs. Paste the audit prompt into Codex or ask it to open the file. Separate working tree/branch recommended.

Codex should not share Claude's assumptions, edit `data/frozen`, or review outputs using future demand. Findings should be written to `reports/` or PR comments, not quietly incorporated into source records.
