"""Pre-specified coarse screening + conservative AI extraction (optional)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .storage import all_raw_dirs, digest, latest_source, read_json, sha_json, utcnow, write_json_replace_derived

PATTERNS = [
    r"\brequire[ds]?\b", r"\bmandatory\b", r"\bcompliance\b", r"\bprohibit(?:ed|ion)?\b",
    r"\beffective\b", r"\bdeadline\b", r"\bfinal rule\b", r"\bnew rule\b",
    r"\bno longer\b", r"\bend of support\b", r"\bapplications? open\b",
    r"\bmust\b", r"\bwill be\b", r"\bnew requirement\b",
]
REGEX = re.compile("|".join(PATTERNS), flags=re.IGNORECASE)

SYSTEM = """You are an archival research event extractor. You see ONLY an original primary document and publication metadata. Do not use knowledge of events after publication. DO NOT predict commercial demand or mention subsequent success. Return strict JSON with keys is_event (boolean), event_type (string from new_legal_requirement, compliance_deadline, end_of_support, platform_policy_change, price_or_terms_change, new_program_or_eligibility, infrastructure_constraint, other_identifiable_change), affected_group (string or null), change_summary (string or null), effective_at (YYYY-MM-DD or null), evidence (array of objects: field ('change_summary' or 'affected_group'), quote (EXACT SOURCE TEXT substring)), uncertainties (array of strings). Only a newly announced behavior-changing event is eligible; if no such event return is_event=false and empty evidence. Do not invent quotes or infer an affected population without supporting source text. Do not transform a proposed change into an enacted rule. No markdown."""


def screen(root: Path) -> dict:
    rows: list[dict] = []
    for d in all_raw_dirs(root):
        manifest, text = latest_source(root, d.parent.name, d.name)
        source_data = read_json(d / "source.json")
        title = str(source_data.get("title", ""))
        matches = sorted(set(m.group().lower() for m in REGEX.finditer(title + "\n" + text)))
        rows.append({
            "source_id": manifest["source_id"], "source_document_id": manifest["source_document_id"],
            "publication_date": manifest["publication_date"], "document_sha256": manifest["document_sha256"],
            "screen_decision": "candidate" if matches else "excluded_by_rule",
            "matched_signals": matches, "screening_rule": "keyword-v0.1",
        })
    path = root / "data" / "reports" / "screening_frame.json"
    write_json_replace_derived(path, {
        "screening_version": "keyword-v0.1",
        "screened_at": utcnow(),
        "patterns_sha256": digest("\n".join(PATTERNS).encode("utf-8")),
        "raw_document_count": len(rows),
        "rows": rows,
    })
    return {"screened": len(rows), "possible_candidates": sum(x["screen_decision"] == "candidate" for x in rows),
            "excluded_need_false_negative_audit": sum(x["screen_decision"] != "candidate" for x in rows), "file": str(path)}


def heuristic(text: str) -> dict:
    for line in re.split(r"(?<=[.!?])\s+|\n+", text):
        match = REGEX.search(line)
        if match and 25 <= len(line.strip()) <= 650:
            return {"is_event": True, "event_type": "other_identifiable_change",
                "affected_group": None, "change_summary": None, "effective_at": None,
                "evidence": [{"field": "change_summary", "quote": line.strip()}],
                "uncertainties": ["Heuristic signal only. Human/LLM must supply independently supported change and affected group."]}
    return {"is_event": False, "event_type": "other_identifiable_change", "affected_group": None,
            "change_summary": None, "effective_at": None, "evidence": [], "uncertainties": ["No rule signal"]}


def anthropic_extract(text: str, published: str) -> dict:
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("Install optional AI dependency: pip install -e '.[ai]'") from exc
    model = os.getenv("ANTHROPIC_MODEL")
    if not model or not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("Set ANTHROPIC_MODEL and ANTHROPIC_API_KEY in your environment (not in source code).")
    # Long bodies are truncated to bound cost; truncated extraction cannot prove document completeness.
    excerpt = text[:90_000]
    client = anthropic.Anthropic()
    response = client.messages.create(model=model, max_tokens=2500, temperature=0,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"Official publication date: {published}\nSource body (possibly truncated):\n{excerpt}"}])
    raw = "".join(getattr(block, "text", "") for block in response.content).strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    result = json.loads(raw)
    result.setdefault("uncertainties", [])
    if len(text) > len(excerpt):
        result["uncertainties"].append("Document truncated at 90k chars for model extraction; manual full-source review required")
    return result


def extract(root: Path, *, backend: str, limit: int = 30) -> dict:
    path = root / "data" / "reports" / "screening_frame.json"
    if not path.exists():
        raise ValueError("Run screen before extract")
    frame = read_json(path)["rows"]
    candidates = [r for r in frame if r["screen_decision"] == "candidate"]
    done = 0
    skipped = 0
    rejected = 0
    for row in candidates[:limit]:
        source_id, doc_id = row["source_id"], row["source_document_id"]
        target = root / "data" / "candidates" / f"{source_id}-{doc_id}.json"
        if target.exists():
            skipped += 1
            continue
        manifest, text = latest_source(root, source_id, doc_id)
        payload = heuristic(text) if backend == "heuristic" else anthropic_extract(text, manifest["publication_date"])
        event_id = f"{source_id}-{doc_id}"
        candidate = {
            "event_id": event_id, "source_id": source_id, "source_document_id": doc_id,
            "publication_date": manifest["publication_date"],
            "document_sha256": manifest["document_sha256"],
            "event_type": payload.get("event_type"), "affected_group": payload.get("affected_group"),
            "change_summary": payload.get("change_summary"), "effective_at": payload.get("effective_at"),
            "evidence": payload.get("evidence", []), "uncertainties": payload.get("uncertainties", []),
            "candidate_is_event": payload.get("is_event", False), "extraction_backend": backend,
            "extraction_protocol": "extraction-v0.1",
            "candidate_warning": "Unreviewed AI/heuristic output. Not an approved event.",
        }
        # Derived candidate still write-once: after a changed prompt use a separately named run/branch.
        from .storage import write_json_once
        write_json_once(target, candidate)
        if not payload.get("is_event", False):
            rejected += 1
        done += 1
    return {"possible_candidates": len(candidates), "new_extracted": done, "skipped_existing": skipped,
            "agent_rejected": rejected, "remaining_not_attempted": max(0, len(candidates) - limit)}
