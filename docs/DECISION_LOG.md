# Methodology decision log

| Date | Decision | Rationale | Status |
|---|---|---|---|
| 2026-10-23 | Start with bounded Federal Register official-document collector | Test end-to-end source provenance with an accessible primary archive | Draft pilot choice |
| 2026-10-23 | No outcome analysis during collection | Reduce selection and hindsight bias | Draft protocol |
| 2026-10-23 | Require independent human verification before acceptance | Quote matching alone does not prove historical/semantic correctness | Draft protocol |
| 2026-10-23 | Prohibit 150 final freeze until >=3 source families and frame audit | One-source sample cannot generalize to global markets | Technical gate |
| 2026-10-23 | Keep current source/record output empty | Avoid fictional sample or implied verification | Implemented |
| 2026-10-23 | Run 1 snapshots quarantined; full text now from GPO govinfo.gov `<pre>` HTML when federalregister.gov blocks; off-host redirects and HTML-in-text are retrieval failures | federalregister.gov full-text URLs 302 to an access-block page; GPO is the statutory FR publisher and the API itself links govinfo pdf/mods | Implemented in code; AWAITING researcher ratification (protocol still DRAFT) |

A protocol amendment must be dated, numbered, describe the impact on already-collected data, and be approved before code changes.
