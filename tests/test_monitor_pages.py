import os
import tempfile
import unittest

import monitor_pages


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, payloads):
        self.payloads = payloads

    def get(self, url, timeout=None):
        payload = self.payloads[url]
        if isinstance(payload, Exception):
            raise payload
        return FakeResponse(payload)


class MonitorPagesTests(unittest.TestCase):
    def test_unchanged_page_writes_no_change_marker(self):
        url = "https://example.com/a"
        html_doc = "<html><body><h1>Stable</h1></body></html>"
        normalised = monitor_pages.normalise_content(html_doc)
        stable_hash = monitor_pages.hashlib.sha256(normalised.encode("utf-8")).hexdigest()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "change_log.txt")
            session = FakeSession({url: html_doc})

            current_hashes, changed_pages = monitor_pages.process_urls(
                urls=[url],
                url_to_title={url: "Page A"},
                previous_hashes={url: stable_hash},
                session=session,
                log_file=log_file,
            )
            monitor_pages.write_no_changes_marker_if_needed(log_file, changed_pages)

            self.assertEqual(changed_pages, [])
            self.assertEqual(current_hashes[url], stable_hash)
            with open(log_file, "r", encoding="utf-8") as file_obj:
                log_text = file_obj.read()
            self.assertIn("NO CHANGES THIS RUN", log_text)
            self.assertNotIn("CHANGE DETECTED", log_text)

    def test_changed_page_logged_and_summary_written(self):
        url = "https://example.com/b"
        html_doc = "<html><body><p>New content</p></body></html>"

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "change_log.txt")
            summary_file = os.path.join(tmpdir, "changes_summary.html")
            session = FakeSession({url: html_doc})

            current_hashes, changed_pages = monitor_pages.process_urls(
                urls=[url],
                url_to_title={url: "Page B"},
                previous_hashes={url: "oldhash"},
                session=session,
                log_file=log_file,
            )
            monitor_pages.write_changes_summary(summary_file, changed_pages)

            self.assertEqual(len(current_hashes), 1)
            self.assertEqual(changed_pages, [("Page B", url)])
            with open(log_file, "r", encoding="utf-8") as file_obj:
                log_text = file_obj.read()
            self.assertIn("CHANGE DETECTED: Page B", log_text)

            with open(summary_file, "r", encoding="utf-8") as file_obj:
                summary_text = file_obj.read()
            self.assertIn("<h2>The following pages have been updated:</h2>", summary_text)
            self.assertIn(url, summary_text)
            self.assertIn("Page B", summary_text)

    def test_fetch_exception_logs_error_and_skips_hash(self):
        url = "https://example.com/c"

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "change_log.txt")
            session = FakeSession({url: RuntimeError("network timeout")})

            current_hashes, changed_pages = monitor_pages.process_urls(
                urls=[url],
                url_to_title={url: "Page C"},
                previous_hashes={},
                session=session,
                log_file=log_file,
            )

            self.assertEqual(current_hashes, {})
            self.assertEqual(changed_pages, [])
            with open(log_file, "r", encoding="utf-8") as file_obj:
                log_text = file_obj.read()
            self.assertIn("ERROR FETCHING", log_text)
            self.assertIn(url, log_text)

    def test_new_url_logs_new_url_monitored(self):
        url = "https://example.com/d"
        html_doc = "<html><body><p>First run</p></body></html>"

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "change_log.txt")
            session = FakeSession({url: html_doc})

            current_hashes, changed_pages = monitor_pages.process_urls(
                urls=[url],
                url_to_title={url: "Page D"},
                previous_hashes={},
                session=session,
                log_file=log_file,
            )

            self.assertIn(url, current_hashes)
            self.assertEqual(changed_pages, [])
            with open(log_file, "r", encoding="utf-8") as file_obj:
                log_text = file_obj.read()
            self.assertIn("NEW URL MONITORED: Page D", log_text)


if __name__ == "__main__":
    unittest.main()
