"""Collector provenance guards. All responses here are synthetic; no network is used."""
import unittest
from unittest import mock

from radar import collector


BLOCK_PAGE = "<!DOCTYPE html>\n<html><head><title>Federal Register :: Request Access</title></head><body>You must request access. It will be granted later.</body></html>"
GOVINFO_PAGE = (
    "<html>\n<head>\n<title>Federal Register, Volume 87 Issue 63</title>\n</head>\n<body><pre>\n"
    "[Federal Register Volume 87, Number 63 (Friday, April 1, 2022)]\n[Rules and Regulations]\n"
    "From the Federal Register Online via the Government Publishing Office [<a href=\"http://www.gpo.gov\">www.gpo.gov</a>]\n"
    "[FR Doc No: 2022-00000]\n\nSynthetic fixture text &amp; entity. Not a real document.\n"
    "</pre><script src=\"/x.js\"></script></body>\n</html>"
)
RECORD = {
    "raw_text_url": "https://www.federalregister.gov/documents/full_text/text/2022/04/01/2022-00000.txt",
    "pdf_url": "https://www.govinfo.gov/content/pkg/FR-2022-04-01/pdf/2022-00000.pdf",
    "html_url": "https://www.federalregister.gov/documents/2022/04/01/2022-00000/synthetic",
}


class CollectorProvenanceTests(unittest.TestCase):
    def test_off_host_redirect_is_failure_not_source(self):
        response = mock.MagicMock()
        response.geturl.return_value = "https://unblock.federalregister.gov/"
        response.read.return_value = BLOCK_PAGE.encode()
        response.headers = {"Content-Type": "text/html; charset=utf-8"}
        response.__enter__.return_value = response
        with mock.patch.object(collector, "urlopen", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "Off-host redirect"):
                collector.fetch_detailed("https://www.federalregister.gov/documents/full_text/text/x.txt")

    def test_html_served_as_raw_text_is_rejected_and_govinfo_used(self):
        calls = []

        def fake_fetch(url, **kwargs):
            calls.append(url)
            if "full_text/text" in url:
                return BLOCK_PAGE.encode(), url, "text/html; charset=utf-8"
            if url.startswith("https://www.govinfo.gov/"):
                return GOVINFO_PAGE.encode(), url, "text/html"
            raise AssertionError("unexpected url " + url)

        with mock.patch.object(collector, "fetch_detailed", side_effect=fake_fetch):
            text, url, mode = collector.get_primary_text(RECORD)
        self.assertEqual(mode, "govinfo_gpo_html_pre_text")
        self.assertEqual(url, "https://www.govinfo.gov/content/pkg/FR-2022-04-01/html/2022-00000.htm")
        self.assertIn("[FR Doc No: 2022-00000]", text)
        self.assertIn("Synthetic fixture text & entity.", text)
        self.assertNotIn("<a href", text)
        self.assertNotIn("<script", text)
        self.assertFalse(collector.looks_like_html(text))

    def test_all_paths_blocked_raises(self):
        def fake_fetch(url, **kwargs):
            raise RuntimeError(f"Off-host redirect {url} -> https://unblock.federalregister.gov/")

        with mock.patch.object(collector, "fetch_detailed", side_effect=fake_fetch):
            with self.assertRaisesRegex(RuntimeError, "All full-text retrieval paths failed"):
                collector.get_primary_text(RECORD)

    def test_govinfo_url_only_derived_from_official_govinfo_pdf(self):
        self.assertIsNone(collector.govinfo_html_url({"pdf_url": "https://evil.example/content/pkg/x/pdf/y.pdf"}))
        self.assertIsNone(collector.govinfo_html_url({}))
        self.assertEqual(collector.govinfo_html_url(RECORD),
                         "https://www.govinfo.gov/content/pkg/FR-2022-04-01/html/2022-00000.htm")

    def test_govinfo_page_without_pre_is_refused(self):
        with self.assertRaisesRegex(ValueError, "no <pre> body"):
            collector.govinfo_pre_text("<html><body>Access denied</body></html>")

    def test_cloudflare_obfuscated_email_is_decoded_to_printed_address(self):
        # "ab@cd.ef" XOR-encoded with key 0x10, as Cloudflare does for govinfo pages.
        encoded = "10" + "".join(f"{b ^ 0x10:02x}" for b in b"ab@cd.ef")
        html = ('<html><body><pre>Contact: <a href="/cdn-cgi/l/email-protection" class="__cf_email__" '
                f'data-cfemail="{encoded}">[email&#160;protected]</a> for details.</pre></body></html>')
        self.assertEqual(collector.decode_cfemail(encoded), "ab@cd.ef")
        self.assertEqual(collector.govinfo_pre_text(html), "Contact: ab@cd.ef for details.")

    def test_block_page_detected_as_html(self):
        self.assertTrue(collector.looks_like_html(BLOCK_PAGE))
        self.assertFalse(collector.looks_like_html("DEPARTMENT OF X\n\nFinal rule text."))


if __name__ == "__main__":
    unittest.main()
