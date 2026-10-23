# Data contract

## Raw source directory (`data/raw/<source>/<document-id>/`)
- `source.json`: canonical JSON payload from primary API detail route.
- `document.txt`: retrieved official full text, or explicitly noted HTML fallback.
- `manifest.json`: source ID, URL, official publication date, fetch time, hashes, source-text mode, bounded collection window.

## Candidate (`data/candidates/<source>-<id>.json`)
- `event_id`, `source_id`, `source_document_id`, `publication_date`, `document_sha256`.
- `candidate_is_event`, `event_type`, `affected_group`, `change_summary`, `effective_at`.
- `evidence`: array of `{field,quote}`, with quote required to appear literally in source text.
- `uncertainties`, `extraction_backend`, `candidate_warning`.

## Review (`data/reviews/<event-id>.json`)
- named reviewer attestation, rationale, accept/reject, flags for dated original content/date, explicit `underlying_change_key` for dedup.
- immutable candidate checksum. Review files refuse overwrite.

## Sample (`data/samples/<name>.json`)
- count, seed, sampling algorithm, ordered strata and inclusion probabilities, accepted frame hash.
- selected event IDs, candidate/review/raw hash values.

## Freeze (`data/frozen/<name>.json`)
- sample snapshot, creation time and checksum. Refuses overwrite.
- Requires independent archival backup/WORM for serious studies.

## Future outcome storage
Not present in this repo on purpose. Stage 2 must run in a **different repository or access-controlled storage path** only after stage-1 freeze.
