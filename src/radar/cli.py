"""Research harness CLI. No outcomes or demand data are ever read in Stage 1."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .collector import collect_federal_register
from .evidence import accepted_frame, review, validate_candidate
from .extract import extract, screen
from .sampling import create_sample, freeze_sample, verify_freeze, verify_sample, draw_negative_audit
from .storage import all_raw_dirs, read_json, write_json_replace_derived


def report(root: Path) -> dict:
    raw = list(all_raw_dirs(root))
    candidates = sorted((root / "data" / "candidates").glob("*.json"))
    reviews = sorted((root / "data" / "reviews").glob("*.json"))
    screening_file = root / "data" / "reports" / "screening_frame.json"
    frame_rows = read_json(screening_file).get("rows", []) if screening_file.exists() else []
    invalid = []
    for p in candidates:
        c = read_json(p)
        errors = validate_candidate(root, c)
        if errors:
            invalid.append({"event_id": c.get("event_id"), "errors": errors})
    accepted = accepted_frame(root)
    result = {
        "raw_documents": len(raw), "screened_documents": len(frame_rows),
        "screened_candidates": sum(x["screen_decision"] == "candidate" for x in frame_rows),
        "screened_out_requiring_negative_audit": sum(x["screen_decision"] != "candidate" for x in frame_rows),
        "extracted_candidates": len(candidates), "candidate_validation_failures": len(invalid),
        "human_review_records": len(reviews), "human_accepted_events": len(accepted),
        "failure_details": invalid[:50],
        "source_counts_accepted": {source: sum(r["source_id"] == source for r in accepted) for source in sorted({r["source_id"] for r in accepted})},
        "interpretation": "These are Stage-1 provenance/screening metrics only, not demand prediction results.",
    }
    write_json_replace_derived(root / "data" / "reports" / "quality_report.json", result)
    return result


def main(argv: list[str] | None = None):
    p = argparse.ArgumentParser(prog="radar", description="Stage-1 auditable historical event sampling harness")
    p.add_argument("--root", type=Path, default=Path.cwd(), help="Repository directory (default: current working directory)")
    sub = p.add_subparsers(dest="command", required=True)
    col = sub.add_parser("collect", help="Download bounded original Federal Register documents")
    col.add_argument("--start", required=True, help="YYYY-MM-DD")
    col.add_argument("--end", required=True, help="YYYY-MM-DD")
    col.add_argument("--max-pages", type=int, default=2)
    col.add_argument("--max-docs", type=int, default=100)
    sub.add_parser("screen", help="Screen ALL raw documents, including rejected records")
    ext = sub.add_parser("extract", help="Extract candidate information; NEVER approves events")
    ext.add_argument("--backend", choices=["heuristic", "anthropic"], default="heuristic")
    ext.add_argument("--limit", type=int, default=30)
    val = sub.add_parser("validate", help="Check supporting exact quotes and source hashes")
    val.add_argument("--event-id", required=True)
    rev = sub.add_parser("review", help="Write one explicit human review decision")
    rev.add_argument("--event-id", required=True)
    rev.add_argument("--decision", required=True, choices=["accept", "reject"])
    rev.add_argument("--reviewer", required=True)
    rev.add_argument("--reason", required=True)
    rev.add_argument("--source-original-verified", action="store_true")
    rev.add_argument("--date-verified", action="store_true")
    rev.add_argument("--change-key")
    sub.add_parser("audit", help="Report Stage-1 quality, not prediction quality")
    neg = sub.add_parser("negative-sample", help="Randomly audit screened-OUT documents for missed events")
    neg.add_argument("--size", type=int, default=20)
    neg.add_argument("--seed", type=int, default=26023)
    neg.add_argument("--name", default="negative-audit-20")
    samp = sub.add_parser("sample", help="Draw a write-once reproducible PILOT sample")
    samp.add_argument("--size", type=int, default=20)
    samp.add_argument("--seed", type=int, default=26023)
    samp.add_argument("--name", default="pilot-20")
    samp.add_argument("--final", action="store_true", help="Intentional gate: blocked until multi-source coverage audit")
    vf = sub.add_parser("verify-sample")
    vf.add_argument("--name", default="pilot-20")
    fr = sub.add_parser("freeze")
    fr.add_argument("--name", default="pilot-20")
    vfr = sub.add_parser("verify-freeze")
    vfr.add_argument("--name", default="pilot-20")
    args = p.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "collect":
            result = collect_federal_register(root, start=args.start, end=args.end,
                max_pages=args.max_pages, max_docs=args.max_docs)
        elif args.command == "screen":
            result = screen(root)
        elif args.command == "extract":
            result = extract(root, backend=args.backend, limit=args.limit)
        elif args.command == "validate":
            result = {"event_id": args.event_id, "errors": validate_candidate(root, read_json(root / "data" / "candidates" / (args.event_id + ".json")))}
            result["valid_basic_evidence"] = not result["errors"]
        elif args.command == "review":
            result = review(root, event_id=args.event_id, decision=args.decision, reviewer=args.reviewer,
                reason=args.reason, source_original_verified=args.source_original_verified,
                date_verified=args.date_verified, change_key=args.change_key)
        elif args.command == "audit":
            result = report(root)
        elif args.command == "negative-sample":
            result = draw_negative_audit(root, name=args.name, n=args.size, seed=args.seed)
        elif args.command == "sample":
            result = create_sample(root, name=args.name, n=args.size, seed=args.seed, final=args.final)
        elif args.command == "verify-sample":
            result = verify_sample(root, args.name)
        elif args.command == "freeze":
            result = freeze_sample(root, args.name)
        elif args.command == "verify-freeze":
            result = verify_freeze(root, args.name)
        else:
            p.error("Unknown command")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, RuntimeError, FileNotFoundError, KeyError, FileExistsError) as exc:
        p.exit(2, f"ERROR: {exc}\n")

if __name__ == "__main__":
    main()
