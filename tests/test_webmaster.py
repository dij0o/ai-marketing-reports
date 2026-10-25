"""Contract and failure-boundary tests. No real credentials or network calls."""
import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import bing_pull
import google_webmaster_pull
import requests
import scan_for_private_data as scanner
import webmaster_clients as wc
import webmaster_report as wr
import yandex_pull

PERIOD = {"start": "2026-10-01", "end": "2026-10-24", "timezone": "Asia/Karachi"}
SETTINGS = {"site": "example.com", "bing": {"site_url": "https://example.com/"}, "yandex": {"host_id": "https:example.com:443"}}


class Response:
    def __init__(self, data, status=200):
        self.data, self.status_code = data, status

    def json(self):
        if isinstance(self.data, Exception):
            raise self.data
        return self.data


class Session:
    def __init__(self, respond):
        self.respond, self.calls = respond, []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.respond(url, kwargs)


def bing_response(url, options):
    method = url.rsplit("/", 1)[-1]
    if method == "GetUserSites":
        return Response({"d": [{"Url": "https://example.com/", "IsVerified": True}]})
    if method == "GetUrlInfo":
        return Response({"d": {"HttpStatus": 0, "LastCrawledDate": "/Date(1792281600000)/"}})
    if method == "GetFeeds":
        return Response({"d": [{"Url": "https://example.com/sitemap-index.xml", "UrlCount": 1, "Status": "Success"}]})
    return Response({"d": []})


def yandex_response(url, options):
    path = unquote(urlparse(url).path)
    if path.endswith("/v4/user"):
        return Response({"user_id": 1})
    if path.endswith("/hosts"):
        return Response({"hosts": [{"host_id": "https:example.com:443", "host_url": "https://example.com/", "verified": True}]})
    if path.endswith("/search-queries/popular"):
        return Response({"queries": [{"query_text": "example", "indicators": {"TOTAL_CLICKS": 0}}], "date_from": "2026-10-18", "date_to": "2026-10-24", "count": 1})
    if path.endswith("/diagnostics"):
        return Response({"problems": {"NO_SITEMAPS": {"state": "UNDEFINED", "severity": "CRITICAL"}}})
    return Response({"sitemaps": []})


class WebmasterTests(unittest.TestCase):
    def setUp(self):
        self.keys = patch.dict(os.environ, {"BING_API_KEY": "b" * 32, "YANDEX_TOKEN": "y" * 32})
        self.keys.start()
        self.addCleanup(self.keys.stop)

    def test_bing_empty_data_is_not_zero_but_property_and_sitemap_survive(self):
        session = Session(bing_response)
        report = bing_pull.collect(SETTINGS, PERIOD, session)
        self.assertEqual(report["status"], "connected")
        self.assertEqual(report["datasets"]["traffic"]["returned_rows"], 0)
        self.assertEqual(wr.overview({"providers": {"bing": report}}, "bing"), {})
        self.assertTrue(report["datasets"]["property"]["rows"][0]["verified"])
        self.assertEqual(report["datasets"]["sitemaps"]["rows"][0]["url_count"], 1)
        self.assertIsNone(report["datasets"]["url_info"]["rows"][0]["http_status"])
        self.assertEqual(len(session.calls), 7)
        for url, options in session.calls:
            self.assertIn(url.rsplit("/", 1)[-1], bing_pull.METHODS)
            self.assertFalse(options["allow_redirects"])
            self.assertEqual(options["timeout"], (8, 25))

    def test_bing_filtering_missing_metrics_and_provider_buckets(self):
        def respond(url, options):
            if url.endswith("GetRankAndTrafficStats"):
                return Response({"d": [{"Date": "2026-10-10", "Clicks": 0}, {"Date": "2026-09-10", "Clicks": 7, "Impressions": 10}, {"Clicks": 9}]})
            return bing_response(url, options)
        report = bing_pull.collect(SETTINGS, PERIOD, Session(respond))
        data = report["datasets"]["traffic"]
        self.assertEqual(data["returned_rows"], 3)
        self.assertEqual(data["undated_rows"], 1)
        self.assertEqual(data["rows"][0]["clicks"], 0)
        self.assertIsNone(data["rows"][0]["impressions"])
        totals = wr.overview({"providers": {"bing": report}}, "bing")
        self.assertEqual(totals["clicks"], 0)
        self.assertIsNone(totals["impressions"])
        self.assertIn("weekly", report["datasets"]["queries"]["source"]["grain"])

    def test_bing_partial_failure_redacts_raw_provider_body(self):
        secret = os.environ["BING_API_KEY"]
        def respond(url, options):
            return Response({"error": secret}, 403) if url.endswith("GetQueryStats") else bing_response(url, options)
        report = bing_pull.collect(SETTINGS, PERIOD, Session(respond))
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["datasets"]["queries"]["status"], "error")
        self.assertNotIn(secret, json.dumps(report))

    def test_wrong_bing_property_is_an_error(self):
        def respond(url, options):
            return Response({"d": []}) if url.endswith("GetUserSites") else bing_response(url, options)
        report = bing_pull.collect(SETTINGS, PERIOD, Session(respond))
        self.assertEqual(report["datasets"]["property"]["status"], "error")
        self.assertEqual(report["status"], "partial")

    def test_yandex_sample_dates_nulls_diagnostics_and_encoded_host(self):
        session = Session(yandex_response)
        report = yandex_pull.collect(SETTINGS, PERIOD, session)
        data = report["datasets"]["queries"]
        self.assertEqual(report["status"], "connected")
        self.assertEqual(data["actual_range"]["start"], "2026-10-18")
        self.assertIsNone(data["rows"][0]["impressions"])
        self.assertEqual(data["rows"][0]["clicks"], 0)
        self.assertEqual(wr.overview({"providers": {"yandex": report}}, "yandex"), {})
        self.assertEqual(report["datasets"]["diagnostics"]["rows"][0]["state"], "UNDEFINED")
        self.assertTrue(any("https%3Aexample.com%3A443" in url for url, _ in session.calls))
        self.assertTrue(all(options["headers"]["Authorization"].startswith("OAuth ") for _, options in session.calls))

    def test_yandex_can_discover_host_from_exact_site_url(self):
        report = yandex_pull.collect({"site": "example.com"}, PERIOD, Session(yandex_response))
        self.assertEqual(report["host_id"], "https:example.com:443")

    def test_yandex_timeout_is_not_invalid_token_and_stops_host_calls(self):
        def respond(url, options):
            raise requests.ConnectTimeout("private URL and token must never be printed")
        session = Session(respond)
        report = yandex_pull.collect(SETTINGS, PERIOD, session)
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(report["status"], "error")
        self.assertIn("credential validity is unverified", report["datasets"]["user"]["error"])
        self.assertNotIn("private URL", json.dumps(report))

    def test_yandex_sitemap_cursor_and_query_cap(self):
        pages = []
        def respond(url, options):
            if url.endswith("/sitemaps"):
                pages.append(options["params"])
                return Response({"sitemaps": [{"sitemap_id": str(i)} for i in range(100)] if len(pages) == 1 else []})
            if url.endswith("/search-queries/popular"):
                self.assertEqual(options["params"]["limit"], 500)
                return Response({"queries": [{"query_text": "x", "indicators": {}}], "count": 3000})
            return yandex_response(url, options)
        report = yandex_pull.collect(SETTINGS, PERIOD, Session(respond))
        self.assertEqual(pages[1]["from"], "99")
        self.assertEqual(len(report["datasets"]["sitemaps"]["rows"]), 100)
        self.assertTrue(report["datasets"]["queries"]["truncated"])

    def test_malformed_http_responses_fail_closed(self):
        for response in (Response({"d": {"ErrorCode": 5}}), Response(ValueError()), Response({}, 302), Response({}, 429)):
            with self.subTest(response=response), self.assertRaises(wc.ReportError):
                wc.get_json(Session(lambda u, o: response), "https://example.com/api")

    def test_missing_credential_makes_no_requests_or_google_imports(self):
        session = Session(lambda u, o: self.fail("Network must not be called"))
        with patch.dict(os.environ, {"BING_API_KEY": "", "YANDEX_TOKEN": ""}):
            for collector in (bing_pull.collect, yandex_pull.collect):
                self.assertEqual(collector({}, PERIOD, session)["status"], "not_configured")

    def test_dates_and_numbers_preserve_missing_values(self):
        self.assertEqual(wc.day("/Date(0-0700)/"), "1969-12-31")
        self.assertIsNone(wc.day("not-a-date"))
        self.assertIsNone(wc.number(float("nan")))
        self.assertIsNone(wc.number(None))
        self.assertEqual(wc.number("0"), 0)
        self.assertIsNone(wc.ratio(1, 0))

    def test_invalid_and_incomplete_windows_are_rejected(self):
        opts = argparse.Namespace(days=0, start=None, end=None, timezone="UTC")
        with self.assertRaises(wc.ReportError):
            wc.window(opts)
        opts.days, opts.end = 28, date.today() + timedelta(days=1)
        with self.assertRaises(wc.ReportError):
            wc.window(opts)

    def test_one_failed_provider_does_not_discard_other_results(self):
        with patch.dict(wr.COLLECTORS, {"bing": lambda *_: {"status": "connected", "datasets": {}}, "yandex": lambda *_: (_ for _ in ()).throw(RuntimeError("private"))}):
            report = wr.collect({}, PERIOD, ["bing", "yandex"])
        self.assertEqual(report["providers"]["bing"]["status"], "connected")
        self.assertEqual(report["providers"]["yandex"]["status"], "error")
        self.assertNotIn("private", json.dumps(report))

    def test_markdown_contains_all_dataset_metadata_and_limits_display_only(self):
        source = wc.envelope("yandex", PERIOD)
        source.update(status="connected")
        wc.capture(source, "queries", "popular", lambda: {"rows": [{"query": "<script>|[link](x)", "clicks": 1}] * 25, "actual_range": PERIOD, "truncated": True}, grain="sample", note="not site totals")
        report = {"requested": PERIOD, "generated_at": "test", "providers": {"yandex": source}}
        rendered = wr.markdown(report, "test.json")
        self.assertIn("Showing 20 of 25", rendered)
        self.assertIn("actual_range", rendered)
        self.assertIn("providers.yandex.datasets.queries", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("[link]", rendered)
        self.assertEqual(len(source["datasets"]["queries"]["rows"]), 25)

    def test_saved_output_redacts_credentials(self):
        with tempfile.TemporaryDirectory(dir=wc.ROOT) as folder, patch.object(wc, "SNAPSHOTS", Path(folder)):
            path = wc.save_json("test.json", {"nested": [os.environ["YANDEX_TOKEN"], os.environ["BING_API_KEY"]]})
            self.assertEqual(json.loads(path.read_text())["nested"], ["[REDACTED]", "[REDACTED]"])

    def test_google_missing_config_is_separate_from_other_sources(self):
        self.assertEqual(google_webmaster_pull.collect_gsc({}, PERIOD)["status"], "not_configured")
        self.assertEqual(google_webmaster_pull.collect_ga4({}, PERIOD)["status"], "not_configured")

    def test_ga4_uses_readonly_scope_and_preserves_privacy_metadata(self):
        class API:
            def properties(self): return self
            def runReport(self, **kwargs): return self
            def execute(self):
                return {"rows": [], "rowCount": 2000, "metadata": {"timeZone": "Asia/Karachi", "subjectToThresholding": True}}
        with patch.object(google_webmaster_pull, "client", return_value=API()) as factory:
            report = google_webmaster_pull.collect_ga4({"ga4": {"property_id": "123"}}, PERIOD)
        self.assertEqual(factory.call_args.args[2], "https://www.googleapis.com/auth/analytics.readonly")
        self.assertTrue(report["datasets"]["totals"]["subject_to_thresholding"])
        self.assertTrue(report["datasets"]["pages"]["truncated"])

    def test_offline_render_needs_no_config_and_retains_failure_exit(self):
        with tempfile.TemporaryDirectory(dir=wc.ROOT) as folder:
            path = Path(folder) / "report.json"
            report = {"schema_version": 1, "requested": PERIOD, "generated_at": "test", "providers": {"yandex": {"status": "error", "datasets": {}}}}
            path.write_text(json.dumps(report), encoding="utf-8")
            with patch.object(sys, "argv", ["webmaster_report.py", "--from-json", str(path)]), patch.object(wc, "config", side_effect=AssertionError("No configuration read")), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(wr.main(), 1)
            self.assertIn("yandex", path.with_suffix(".md").read_text())

    def test_scanner_recognises_bare_and_quoted_new_credentials(self):
        import re
        pattern = scanner.PATTERNS["Bing or Yandex credential assigned"]
        for name in ("BING_API_KEY", "YANDEX_TOKEN"):
            for quote in ("", "'", '"'):
                assignment = name + "=" + quote + "x" * 32 + quote
                self.assertIsNotNone(re.search(pattern, assignment))
            self.assertIsNone(re.search(pattern, name + "='<PLACEHOLDER>'"))


if __name__ == "__main__":
    unittest.main()
