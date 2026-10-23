"""Documented proportional stratified SRS without replacement, deterministic seed."""
from __future__ import annotations

import random
import sys
from collections import defaultdict
from pathlib import Path

from .evidence import accepted_frame
from .storage import read_json, sha_json, utcnow, write_json_once


def draw(frame: list[dict], n: int, seed: int) -> dict:
    if n < 1 or len(frame) < n:
        raise ValueError(f"Insufficient accepted events: requested {n}, have {len(frame)}")
    ids = [r["event_id"] for r in frame]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate event IDs in sampling frame")
    populations: dict[str, list[dict]] = defaultdict(list)
    for row in frame:
        k = f"{row['source_id']}|{row['publication_date'][:4]}"
        populations[k].append(row)
    total = len(frame)
    allocations = {k: (n * len(rows)) // total for k, rows in populations.items()}
    remainder = n - sum(allocations.values())
    # largest remainder, tie-broken lexically; nonnegative and capacity-safe.
    priority = sorted(populations, key=lambda k: (-((n * len(populations[k])) % total), k))
    for k in priority[:remainder]:
        allocations[k] += 1
    # Protocol: a stratum shortage must be recorded and amended, never silently sampled with pi=0.
    empty = sorted(k for k, count in allocations.items() if count == 0)
    if empty:
        raise ValueError(f"Stratum allocation is zero (inclusion probability 0) for {empty}; "
                         "amend the sampling plan or increase n before drawing")
    selected: list[dict] = []
    strata = []
    for k in sorted(populations):
        pop = sorted(populations[k], key=lambda r: r["event_id"])
        count = allocations[k]
        chosen = random.Random(f"{seed}:{k}").sample(pop, count)
        pi = count / len(pop)
        for r in chosen:
            selected.append({"event_id": r["event_id"], "stratum": k, "inclusion_probability": pi,
                "candidate_sha256": r["candidate_sha256"], "review_sha256": r["review_sha256"],
                "source_text_sha256": r["source_text_sha256"]})
        strata.append({"stratum": k, "eligible": len(pop), "sampled": count, "inclusion_probability": pi})
    selected.sort(key=lambda r: r["event_id"])
    return {
        "protocol_id": "DPR-HIST-EVENTS-001", "selection_algorithm": "proportional-largest-remainder-v0.1",
        "seed": seed, "n": n, "frame_n": total, "frame_hash": sha_json(sorted(frame, key=lambda r: r["event_id"])),
        "strata": strata, "sample": selected, "selection_uses_outcome_data": False,
    }


def create_sample(root: Path, *, name: str, n: int, seed: int, final: bool) -> dict:
    if any(x not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for x in name):
        raise ValueError("Unsafe sample name")
    frame = accepted_frame(root)
    if final:
        source_families = len(set(r["source_id"] for r in frame))
        if source_families < 3:
            raise ValueError("Final N=150 cannot use fewer than 3 source families; see protocol")
        # All collection reports covering sampled source periods must also demonstrate coverage
        # and final reviewer must separately attest sampling-frame sufficiency.
        raise ValueError("FINAL freeze intentionally disabled until a frame-coverage audit and protocol approval are implemented")
    manifest = draw(frame, n, seed)
    manifest["created_at"] = utcnow()
    # random.Random(...).sample is only guaranteed stable within an interpreter version.
    manifest["python_version"] = sys.version
    manifest["study_stage"] = "pilot_only_not_generalizable"
    manifest["sampling_frame_warning"] = "Pilot may use incomplete API pagination and one source; cannot claim representative coverage."
    write_json_once(root / "data" / "samples" / f"{name}.json", manifest)
    return manifest


def verify_sample(root: Path, name: str) -> dict:
    manifest = read_json(root / "data" / "samples" / f"{name}.json")
    frame = accepted_frame(root)
    reproduced = draw(frame, manifest["n"], manifest["seed"])
    fields = ("selection_algorithm", "seed", "n", "frame_n", "frame_hash", "strata", "sample")
    mismatches = [k for k in fields if reproduced[k] != manifest.get(k)]
    return {"sample": name, "valid": not mismatches, "mismatches": mismatches,
        "sample_n": len(manifest.get("sample", [])), "recomputed_frame_n": len(frame)}


def freeze_sample(root: Path, name: str) -> dict:
    verification = verify_sample(root, name)
    if not verification["valid"]:
        raise ValueError("Cannot freeze: sample failed reproduction " + str(verification))
    sample = read_json(root / "data" / "samples" / f"{name}.json")
    freeze = {"sample": sample, "freeze_recorded_at": utcnow(),
        "sample_checksum": sha_json(sample), "warning": "Filesystem write-once is not WORM storage; archive SHA-256 separately."}
    write_json_once(root / "data" / "frozen" / f"{name}.json", freeze)
    return {"name": name, "checksum": sha_json(freeze), "reproducible": True,
        "frozen_event_count": len(sample["sample"])}


def verify_freeze(root: Path, name: str) -> dict:
    freeze = read_json(root / "data" / "frozen" / f"{name}.json")
    sample = read_json(root / "data" / "samples" / f"{name}.json")
    reproduced = verify_sample(root, name)
    return {"name": name, "sample_checksum_valid": freeze["sample_checksum"] == sha_json(sample),
            "sample_reproducible": reproduced["valid"], "frozen_n": len(freeze["sample"]["sample"]),
            "matches_current_sample": freeze["sample"] == sample}


def draw_negative_audit(root: Path, name: str, n: int, seed: int) -> dict:
    """Random sample of screened-out original documents, to detect missed events."""
    path = root / "data" / "reports" / "screening_frame.json"
    if not path.exists():
        raise ValueError("Run screen first")
    frame = read_json(path).get("rows", [])
    excluded = sorted((r for r in frame if r["screen_decision"] == "excluded_by_rule"),
                      key=lambda r: (r["source_id"], r["source_document_id"]))
    if n < 1 or n > len(excluded):
        raise ValueError(f"Requested {n} negative cases but only {len(excluded)} exist")
    sample = random.Random(seed).sample(excluded, n)
    result = {
        "kind": "negative_screening_audit", "name": name, "seed": seed,
        "screen_version": "keyword-v0.1", "total_screened_out": len(excluded),
        "inclusion_probability": n / len(excluded),
        "excluded_frame_hash": sha_json(excluded),
        "cases": sorted(sample, key=lambda r: (r["source_id"], r["source_document_id"])),
        "instruction": "Manually read each original document, label missed eligible event YES/NO/UNCLEAR, and report denominator and missingness. No future outcomes.",
    }
    write_json_once(root / "data" / "samples" / f"{name}.json", result)
    return {"negative_case_count": n, "excluded_pool": len(excluded), "manifest": str(root / "data" / "samples" / f"{name}.json")}
