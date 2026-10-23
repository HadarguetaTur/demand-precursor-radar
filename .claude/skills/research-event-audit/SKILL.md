---
name: research-event-audit
description: Audit a candidate event using the immutable primary document and Stage-1 evidence rules.
---
# Research event audit
1. Read `protocol/research_protocol.yaml` and the record's source manifest.
2. Ensure original source body and metadata exist and hashes match.
3. Verify the exact quotation(s) from the body; map fields to quotations.
4. Distinguish original publication, page revision, extraction time, future effective date.
5. Inspect affected group and materiality without consulting later outcomes.
6. Identify duplicates across underlying announcements, not only exact document IDs.
7. Explain any uncertainty instead of guessing; do not make a human approval claim.
8. Output PASS/FAIL/UNVERIFIABLE and action items. Approval belongs to a real reviewer and must be logged.
