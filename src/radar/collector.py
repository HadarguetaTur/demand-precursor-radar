"""Bounded official Federal Register API collector. Network needed for real research."""
from __future__ import annotations

import json
import re
import time
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from .storage import digest, safe_id, stable_json, utcnow, write_json_once, write_once

API = "https://www.federalregister.gov/api/v1/documents.json"
DETAIL_API = "https://www.federalregister.gov/api/v1/documents/{}.json"
HEADERS = {"User-Agent": "DemandPrecursorRadar-Research/0.1 (historical source provenance)", "Accept": "application/json,text/plain,text/html"}


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "nav", "footer"}:
            self.ignored += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "nav", "footer"}:
            self.ignored = max(0, self.ignored - 1)

    def handle_data(self, data):
        if self.ignored == 0 and data.strip():
            self.parts.append(data.strip())


def fetch_detailed(url: str, *, max_bytes: int = 3_000_000, attempts: int = 3) -> tuple[bytes, str, str]:
    """Fetch over HTTPS. Returns (body, final_url, content_type).

    An off-host redirect (e.g. federalregister.gov -> unblock.federalregister.gov access-block
    page) is a retrieval FAILURE, never a source document.
    """
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS source retrieval is permitted")
    requested_host = urlparse(url).netloc
    last_exc = None
    for attempt in range(attempts):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=30) as response:
                final_url = response.geturl()
                if urlparse(final_url).netloc != requested_host:
                    raise RuntimeError(f"Off-host redirect {url} -> {final_url}; treated as access block, not source")
                blob = response.read(max_bytes + 1)
                if len(blob) > max_bytes:
                    raise ValueError(f"Source exceeded {max_bytes} bytes: {url}")
                return blob, final_url, response.headers.get("Content-Type", "")
        except (HTTPError, URLError, TimeoutError) as exc:
            last_exc = exc
            if isinstance(exc, HTTPError) and exc.code not in (429, 500, 502, 503, 504):
                break
            if attempt < attempts - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not fetch {url}: {last_exc}")


def fetch(url: str, *, max_bytes: int = 3_000_000, attempts: int = 3) -> bytes:
    return fetch_detailed(url, max_bytes=max_bytes, attempts=attempts)[0]


def fetch_json(url: str) -> dict:
    return json.loads(fetch(url).decode("utf-8"))


def looks_like_html(text: str) -> bool:
    head = text.lstrip()[:300].lower()
    return head.startswith("<!doctype html") or head.startswith("<html") or "<head>" in head


def govinfo_html_url(record: dict) -> str | None:
    """Derive the GPO official HTML rendering from the API's own govinfo pdf_url field."""
    pdf_url = record.get("pdf_url") or ""
    parsed = urlparse(pdf_url)
    if parsed.netloc != "www.govinfo.gov" or "/pdf/" not in parsed.path or not parsed.path.endswith(".pdf"):
        return None
    return "https://www.govinfo.gov" + parsed.path.replace("/pdf/", "/html/", 1)[:-4] + ".htm"


def decode_cfemail(hex_value: str) -> str:
    """Reverse Cloudflare's email obfuscation: first byte is the XOR key for the rest."""
    data = bytes.fromhex(hex_value)
    if len(data) < 2:
        raise ValueError("Malformed data-cfemail value")
    key = data[0]
    return bytes(b ^ key for b in data[1:]).decode("utf-8")


_CF_EMAIL = re.compile(
    r"<(?:a|span)\b[^>]*class=\"__cf_email__\"[^>]*data-cfemail=\"([0-9a-fA-F]+)\"[^>]*>.*?</(?:a|span)>",
    flags=re.IGNORECASE | re.DOTALL,
)


def govinfo_pre_text(html: str) -> str:
    """GovInfo FR documents are a single <pre> block of the printed issue text.

    GovInfo is served through Cloudflare, which rewrites e-mail addresses into
    `__cf_email__` elements; they are decoded back to the printed address so the stored
    text matches the official document rather than a CDN artifact.
    """
    match = re.search(r"<pre[^>]*>(.*?)</pre>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("GovInfo page has no <pre> body; refusing to treat as source text")
    body = _CF_EMAIL.sub(lambda m: decode_cfemail(m.group(1)), match.group(1))
    body = re.sub(r"<a\b[^>]*>|</a>", "", body)
    return unescape(body)


def get_primary_text(record: dict) -> tuple[str, str, str]:
    """Prefer official raw_text; then GPO govinfo rendering; HTML scrape is the weakest mode.

    Every path rejects HTML served where plain text was expected and off-host redirects.
    """
    failures: list[str] = []
    raw_url = record.get("raw_text_url")
    if raw_url:
        try:
            raw, final_url, ctype = fetch_detailed(raw_url)
            text = raw.decode("utf-8-sig", errors="replace")
            if "text/html" in ctype.lower() or looks_like_html(text):
                raise RuntimeError(f"raw_text_url served HTML instead of text ({final_url})")
            return text, raw_url, "raw_text"
        except (RuntimeError, ValueError) as exc:
            failures.append(str(exc))
    gov_url = govinfo_html_url(record)
    if gov_url:
        try:
            raw, final_url, _ = fetch_detailed(gov_url)
            text = govinfo_pre_text(raw.decode("utf-8", errors="replace"))
            return text, gov_url, "govinfo_gpo_html_pre_text"
        except (RuntimeError, ValueError) as exc:
            failures.append(str(exc))
    html_url = record.get("html_url")
    if html_url:
        try:
            raw, final_url, _ = fetch_detailed(html_url)
            parser = _VisibleText()
            parser.feed(raw.decode("utf-8", errors="replace"))
            return "\n".join(parser.parts), html_url, "rendered_html_fallback_requires_manual_check"
        except (RuntimeError, ValueError) as exc:
            failures.append(str(exc))
    if failures:
        raise RuntimeError("All full-text retrieval paths failed: " + " | ".join(failures))
    raise ValueError("Official full-text URL missing; cannot treat summary as source")


def collect_federal_register(root: Path, *, start: str, end: str, max_pages: int, max_docs: int) -> dict:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", start) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", end) or start > end:
        raise ValueError("Use YYYY-MM-DD dates with start <= end")
    if max_pages < 1 or max_docs < 1:
        raise ValueError("max-pages and max-docs must be > 0")
    # Intentionally no outcome-specific terms, popularity score or document-type filtering.
    query = urlencode({
        "conditions[publication_date][gte]": start,
        "conditions[publication_date][lte]": end,
        "per_page": 100,
        "order": "oldest",
    })
    url = API + "?" + query
    found = 0
    new = 0
    errors: list[dict] = []
    visited_pages: list[str] = []
    remaining = True
    limit_hit = False
    api_total_count = None
    for _ in range(max_pages):
        if not url or found >= max_docs:
            limit_hit = bool(url)
            break
        visited_pages.append(url)
        page = fetch_json(url)
        if api_total_count is None:
            api_total_count = page.get("count")
        results = page.get("results", [])
        if not isinstance(results, list):
            raise ValueError("Unexpected Federal Register response shape")
        for item in results:
            if found >= max_docs:
                limit_hit = True
                break
            found += 1
            doc_id = safe_id(str(item.get("document_number", "")))
            out = root / "data" / "raw" / "federal-register" / doc_id
            if (out / "manifest.json").exists():
                continue
            try:
                # Detail endpoint supplies full-text URLs reliably regardless of search fields.
                detail = fetch_json(DETAIL_API.format(doc_id))
                published = detail.get("publication_date") or item.get("publication_date")
                if not published or not (start <= published <= end):
                    raise ValueError("Document publication date missing or outside window")
                text, original_url, text_mode = get_primary_text(detail)
                if len(text.strip()) < 150:
                    raise ValueError("Source body too short to be useful")
                # Download into memory before write so failed retrieval creates no half-document.
                source_data = stable_json(detail)
                text_data = text.encode("utf-8")
                manifest = {
                    "source_id": "federal-register",
                    "source_document_id": doc_id,
                    "source_url": detail.get("html_url") or original_url,
                    "original_text_url": original_url,
                    "source_text_mode": text_mode,
                    "publication_date": published,
                    "fetched_at": utcnow(),
                    "source_sha256": digest(source_data),
                    "document_sha256": digest(text_data),
                    "historical_date_approved": False,
                    "coverage_source_search_start": start,
                    "coverage_source_search_end": end,
                }
                # Avoid accidental overwrite; source snapshots are write-once.
                write_once(out / "source.json", source_data)
                write_once(out / "document.txt", text_data)
                write_json_once(out / "manifest.json", manifest)
                new += 1
            except Exception as exc:
                errors.append({"document_number": doc_id, "error": str(exc)})
        if found >= max_docs:
            limit_hit = True
            break
        url = page.get("next_page_url")
        if not url:
            remaining = False
            break
        time.sleep(0.25)
    else:
        limit_hit = bool(url)
    report = {
        "run_at": utcnow(), "source": "federal-register", "start": start, "end": end,
        "api_reported_total_in_window": api_total_count,
        "retrieved_items": found, "new_snapshots": new, "failed_documents": errors,
        "search_pages": visited_pages, "frame_complete": (not remaining and not limit_hit and not errors),
        "warning": "If frame_complete=false, do not draw representativeness conclusions or freeze a FINAL frame.",
    }
    # Collection reports are append only, keyed by run identifier, no false claim about coverage.
    key = utcnow().replace(":", "-").replace("+", "_")
    write_json_once(root / "data" / "reports" / f"collect-{key}.json", report)
    return report
