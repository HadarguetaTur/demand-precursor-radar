"""Local evidence store helpers. All raw-source writes refuse overwrite."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha_json(value: object) -> str:
    return digest(stable_json(value))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as out:
        out.write(payload)


def write_json_once(path: Path, obj: object) -> None:
    write_once(path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n")


def write_json_replace_derived(path: Path, obj: object) -> None:
    """Derived reports can be regenerated; raw source, reviews and freeze cannot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def all_raw_dirs(root: Path):
    base = root / "data" / "raw"
    if not base.exists():
        return
    for manifest in sorted(base.glob("*/*/manifest.json")):
        yield manifest.parent


def safe_id(value: str) -> str:
    if not value or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for ch in value):
        raise ValueError("Unsafe document identifier")
    return value


def latest_source(root: Path, source_id: str, doc_id: str):
    p = root / "data" / "raw" / safe_id(source_id) / safe_id(doc_id)
    manifest = read_json(p / "manifest.json")
    text_bytes = (p / "document.txt").read_bytes()
    if digest(text_bytes) != manifest["document_sha256"]:
        raise ValueError(f"Raw text hash mismatch for {doc_id}")
    source_bytes = (p / "source.json").read_bytes()
    if digest(source_bytes) != manifest["source_sha256"]:
        raise ValueError(f"Raw JSON hash mismatch for {doc_id}")
    return manifest, text_bytes.decode("utf-8")
