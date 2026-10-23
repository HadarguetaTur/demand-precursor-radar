"""Review-aid document selection (type-stratified, seeded). Reproduces data/reports/agent_extraction_selection.json.
Usage: python scripts/select_review_aid_docs.py <repo-root>. Not part of production sampling."""
﻿import json, random, sys
from pathlib import Path
root = Path(sys.argv[1]); frame = json.loads((root/"data/reports/screening_frame.json").read_text(encoding="utf-8"))["rows"]
cands = [r for r in frame if r["screen_decision"]=="candidate"]
bytype = {}
for r in cands:
    s = json.loads((root/"data/raw/federal-register"/r["source_document_id"]/"source.json").read_text(encoding="utf-8"))
    bytype.setdefault(s["type"], []).append(r["source_document_id"])
quota = {"Rule": 7, "Proposed Rule": 7, "Notice": 6}
sel = {}
for t, q in quota.items():
    pool = sorted(bytype.get(t, []))
    sel[t] = sorted(random.Random(f"26023:{t}").sample(pool, min(q, len(pool))))
out = {"purpose":"Documents handed to Claude Code event-extractor subagent as REVIEW AID (not production extraction)",
       "rule":"type-stratified quota Rule7/ProposedRule7/Notice6 from keyword candidates; random.Random('26023:<type>').sample over sorted ids; chosen before reading any body",
       "pool_sizes":{t:len(v) for t,v in bytype.items()}, "selected":sel}
p = root/"data/reports/agent_extraction_selection.json"; p.write_text(json.dumps(out, indent=2)+"\n", encoding="utf-8")
print(json.dumps(out, indent=1))
