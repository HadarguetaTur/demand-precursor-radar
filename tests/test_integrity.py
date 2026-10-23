import json
import tempfile
import unittest
from pathlib import Path

from radar.storage import digest, stable_json, write_once, write_json_once
from radar.evidence import validate_candidate, review, accepted_frame
from radar.sampling import draw, create_sample, verify_sample, freeze_sample, verify_freeze, draw_negative_audit
from radar.extract import screen, heuristic


class ResearchIntegrityTests(unittest.TestCase):
    """All fixtures are synthetic and must NOT be represented as collected historical events."""

    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        self.addCleanup(self.t.cleanup)
        for folder in ("raw", "candidates", "reviews", "samples", "frozen", "reports"):
            (self.root / "data" / folder).mkdir(parents=True)

    def create_test_event(self, id_number: int, year="2022", review_it=False, change_key=None):
        doc_id = f"synthetic-{id_number}"
        raw_dir = self.root / "data" / "raw" / "federal-register" / doc_id
        text = ("A newly announced compliance requirement affects producers of test widgets. "
                "Manufacturers of these widgets must submit the required report by the published date.\n")
        body = text.encode()
        source = {"title": "Synthetic fixtures are NOT actual regulatory events", "publication_date": f"{year}-05-12"}
        source_bytes = stable_json(source)
        manifest = {
            "source_id": "federal-register", "source_document_id": doc_id,
            "publication_date": f"{year}-05-12", "document_sha256": digest(body), "source_sha256": digest(source_bytes),
        }
        write_once(raw_dir / "document.txt", body)
        write_once(raw_dir / "source.json", source_bytes)
        write_json_once(raw_dir / "manifest.json", manifest)
        candidate = {
            "event_id": f"federal-register-{doc_id}", "source_id": "federal-register", "source_document_id": doc_id,
            "publication_date": f"{year}-05-12", "document_sha256": digest(body),
            "candidate_is_event": True, "event_type": "new_legal_requirement",
            "affected_group": "Manufacturers of test widgets",
            "change_summary": "New reporting requirement",
            "effective_at": None,
            "evidence": [
                {"field": "change_summary", "quote": "A newly announced compliance requirement affects producers of test widgets."},
                {"field": "affected_group", "quote": "Manufacturers of these widgets must submit the required report by the published date."},
            ],
        }
        write_json_once(self.root / "data" / "candidates" / f"{candidate['event_id']}.json", candidate)
        if review_it:
            review(self.root, event_id=candidate["event_id"], decision="accept", reviewer="Fixture Researcher",
                   reason="Verified the original synthetic fixture and both factual supporting quotations.",
                   source_original_verified=True, date_verified=True,
                   change_key=change_key or f"synthetic-event-{id_number}")
        return candidate, raw_dir

    def test_quote_validated_against_raw(self):
        candidate, _ = self.create_test_event(1)
        self.assertEqual(validate_candidate(self.root, candidate), [])
        candidate["evidence"][0]["quote"] = "Invented quotation absent from primary source."
        self.assertTrue(any("QUOTE_NOT_IN_SOURCE" in x for x in validate_candidate(self.root, candidate)))

    def test_raw_tamper_detected(self):
        candidate, p = self.create_test_event(1)
        (p / "document.txt").write_text("tampered source", encoding="utf-8")
        self.assertTrue(any("RAW_SOURCE_INVALID" in x for x in validate_candidate(self.root, candidate)))

    def test_accept_needs_human_date_checks(self):
        candidate, _ = self.create_test_event(1)
        with self.assertRaisesRegex(ValueError, "explicit review"):
            review(self.root, event_id=candidate["event_id"], decision="accept", reviewer="Human Reviewer",
                   reason="I assessed the original publication and original wording.", change_key="distinct-change-1")

    def test_duplicate_change_key_rejected(self):
        self.create_test_event(1, review_it=True, change_key="same-change")
        self.create_test_event(2, review_it=True, change_key="same-change")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            accepted_frame(self.root)

    def test_random_sampling_order_independent(self):
        rows = [{"event_id": f"evt-{i}", "source_id": "source-A" if i < 7 else "source-B",
                 "publication_date": "2021-06-01" if i % 2 else "2022-07-01",
                 "candidate_sha256": "c", "review_sha256": "r", "source_text_sha256": "h"}
                for i in range(12)]
        s1 = draw(rows, 5, 26023)
        s2 = draw(list(reversed(rows)), 5, 26023)
        self.assertEqual(s1, s2)
        self.assertEqual(sum(s["sampled"] for s in s1["strata"]), 5)
        self.assertEqual(len(set(r["event_id"] for r in s1["sample"])), 5)

    def test_zero_allocation_stratum_is_refused(self):
        # 100 events in stratum A, 1 in stratum B, n=20: largest remainder gives B zero -> pi=0.
        rows = [{"event_id": f"a-{i}", "source_id": "source-A", "publication_date": "2021-01-01",
                 "candidate_sha256": "c", "review_sha256": "r", "source_text_sha256": "h"} for i in range(100)]
        rows.append({"event_id": "b-0", "source_id": "source-B", "publication_date": "2021-01-01",
                     "candidate_sha256": "c", "review_sha256": "r", "source_text_sha256": "h"})
        with self.assertRaisesRegex(ValueError, "inclusion probability 0"):
            draw(rows, 20, 26023)

    def test_pilot_freeze_and_reproduce(self):
        for i in range(4):
            self.create_test_event(i, review_it=True)
        m = create_sample(self.root, name="synthetic-pilot", n=3, seed=5, final=False)
        self.assertEqual(m["n"], 3)
        self.assertTrue(verify_sample(self.root, "synthetic-pilot")["valid"])
        result = freeze_sample(self.root, "synthetic-pilot")
        self.assertEqual(result["frozen_event_count"], 3)
        self.assertTrue(verify_freeze(self.root, "synthetic-pilot")["matches_current_sample"])
        with self.assertRaises(FileExistsError):
            freeze_sample(self.root, "synthetic-pilot")

    def test_final_requires_additional_coverage_audit(self):
        for i in range(4):
            self.create_test_event(i, review_it=True)
        with self.assertRaisesRegex(ValueError, "source families"):
            create_sample(self.root, name="invalid-final", n=3, seed=1, final=True)

    def test_screen_captures_negative_frame(self):
        self.create_test_event(1)
        result = screen(self.root)
        self.assertEqual(result["screened"], 1)
        self.assertEqual(result["possible_candidates"], 1)
        self.assertEqual(heuristic("nothing changed" )["is_event"], False)

    def test_negative_audit_requires_excluded_documents(self):
        self.create_test_event(1)
        screen(self.root)
        with self.assertRaisesRegex(ValueError, "only 0 exist"):
            draw_negative_audit(self.root, "synthetic-negative", 1, 26023)

    def test_cannot_overwrite_raw(self):
        c, d = self.create_test_event(1)
        with self.assertRaises(FileExistsError):
            write_once(d / "document.txt", b"new document")


if __name__ == "__main__":
    unittest.main()
