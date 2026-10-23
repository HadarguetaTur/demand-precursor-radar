"""Evidence validation, explicit independent human review and audit traces."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .storage import digest, latest_source, read_json, sha_json, utcnow, write_json_once

ALLOWED_EVENT_TYPES = {
    "new_legal_requirement", "compliance_deadline", "end_of_support",
    "platform_policy_change", "price_or_terms_change", "new_program_or_eligibility",
    "infrastructure_constraint", "other_identifiable_change",
}


def date_ok(value: object) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def validate_candidate(root: Path, candidate: dict) -> list[str]:
    errors = []
    source_id = candidate.get("source_id", "")
    doc_id = candidate.get("source_document_id", "")
    try:
        manifest, text = latest_source(root, source_id, doc_id)
    except (OSError, ValueError, KeyError) as exc:
        return [f"RAW_SOURCE_INVALID:{exc}"]
    if manifest["document_sha256"] != candidate.get("document_sha256"):
        errors.append("HASH_MISMATCH")
    if manifest["publication_date"] != candidate.get("publication_date"):
        errors.append("PUB_DATE_MISMATCH")
    published = candidate.get("publication_date")
    if not date_ok(published) or not ("2020-01-01" <= published <= "2025-12-31"):
        errors.append("DATE_OUT_OF_PROTOCOL")
    if not candidate.get("candidate_is_event"):
        errors.append("NOT_MARKED_AS_EVENT")
    if candidate.get("event_type") not in ALLOWED_EVENT_TYPES:
        errors.append("UNKNOWN_EVENT_TYPE")
    if not candidate.get("affected_group") or not isinstance(candidate["affected_group"], str):
        errors.append("AFFECTED_GROUP_MISSING")
    if not candidate.get("change_summary") or not isinstance(candidate["change_summary"], str):
        errors.append("CHANGE_SUMMARY_MISSING")
    if candidate.get("effective_at") is not None and not date_ok(candidate["effective_at"]):
        errors.append("EFFECTIVE_DATE_INVALID")
    quotations = candidate.get("evidence", [])
    if not isinstance(quotations, list):
        return errors + ["EVIDENCE_MALFORMED"]
    cited_fields = set()
    for idx, proof in enumerate(quotations):
        if not isinstance(proof, dict) or proof.get("field") not in ("change_summary", "affected_group"):
            errors.append(f"EVIDENCE_{idx}_MALFORMED")
            continue
        quote = proof.get("quote", "")
        # Substring match: prevents fabricated quotations but NOT mistaken semantic inferences.
        if not isinstance(quote, str) or len(quote.strip()) < 20 or quote not in text:
            errors.append(f"EVIDENCE_{idx}_QUOTE_NOT_IN_SOURCE")
        else:
            cited_fields.add(proof["field"])
    for field in ("change_summary", "affected_group"):
        if field not in cited_fields:
            errors.append(f"NO_SUPPORTED_QUOTE_FOR_{field.upper()}")
    return errors


def review(root: Path, *, event_id: str, decision: str, reviewer: str, reason: str,
           source_original_verified: bool = False, date_verified: bool = False,
           change_key: str | None = None) -> dict:
    if decision not in ("accept", "reject"):
        raise ValueError("Decision must be accept or reject")
    if len(reviewer.strip()) < 2 or len(reason.strip()) < 15:
        raise ValueError("Review must name a person and give an explanatory reason (>=15 chars)")
    path = root / "data" / "candidates" / f"{event_id}.json"
    candidate = read_json(path)
    errors = validate_candidate(root, candidate)
    if decision == "accept":
        if errors:
            raise ValueError(f"Candidate fails evidence/date checks: {errors}")
        if not source_original_verified or not date_verified:
            raise ValueError("Acceptance requires explicit review of original source AND historical publication date")
        if not change_key or len(change_key.strip()) < 5:
            raise ValueError("Provide underlying change key after dedup review (--change-key)")
    verdict = {
        "event_id": event_id, "candidate_sha256": sha_json(candidate),
        "decision": decision, "reviewer": reviewer.strip(), "reason": reason.strip(),
        "reviewed_at": utcnow(), "source_original_verified": bool(source_original_verified),
        "date_verified": bool(date_verified), "underlying_change_key": change_key,
        "validator_errors": errors,
        "statement": "Human reviewer attestation only; CLI does not independently verify claimed identity.",
    }
    write_json_once(root / "data" / "reviews" / f"{event_id}.json", verdict)
    return verdict


def accepted_frame(root: Path) -> list[dict]:
    accepted = []
    seen_change: dict[str, str] = {}
    for file in sorted((root / "data" / "reviews").glob("*.json")):
        verdict = read_json(file)
        if verdict.get("decision") != "accept":
            continue
        event_id = verdict["event_id"]
        candidate = read_json(root / "data" / "candidates" / f"{event_id}.json")
        if sha_json(candidate) != verdict.get("candidate_sha256"):
            raise ValueError(f"Reviewed candidate was modified: {event_id}")
        errors = validate_candidate(root, candidate)
        if errors:
            raise ValueError(f"Accepted event now fails validation: {event_id}: {errors}")
        if not verdict.get("source_original_verified") or not verdict.get("date_verified"):
            raise ValueError(f"Temporal attestation missing: {event_id}")
        change_key = verdict.get("underlying_change_key")
        if not change_key:
            raise ValueError(f"Underlying change key missing: {event_id}")
        if change_key in seen_change:
            raise ValueError(f"Possible duplicate event: {event_id} vs {seen_change[change_key]} ({change_key})")
        seen_change[change_key] = event_id
        accepted.append({
            "event_id": event_id, "source_id": candidate["source_id"],
            "source_document_id": candidate["source_document_id"],
            "publication_date": candidate["publication_date"],
            "event_type": candidate["event_type"],
            "candidate_sha256": sha_json(candidate), "review_sha256": sha_json(verdict),
            "source_text_sha256": candidate["document_sha256"],
            "underlying_change_key": change_key,
        })
    return accepted
