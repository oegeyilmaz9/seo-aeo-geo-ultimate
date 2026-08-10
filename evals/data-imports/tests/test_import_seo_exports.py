from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
IMPORTER = ROOT / "scripts" / "import_seo_exports.py"
PERFORMANCE_VALIDATOR = ROOT / "scripts" / "validate_seo_performance.py"
SPEC = importlib.util.spec_from_file_location("import_seo_exports_under_test", IMPORTER)
assert SPEC is not None and SPEC.loader is not None
IMPORTER_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORTER_MODULE)


class DataImportAdapterTests(unittest.TestCase):
    def invoke(self, *args: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(IMPORTER), *(str(arg) for arg in args)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def performance_args(self, command: str, source: Path, output: Path) -> list[object]:
        return [
            command,
            source,
            "--output",
            output,
            "--property",
            "sc-domain:example.com" if command != "ga4-csv" else "properties/123456",
            "--window-start",
            "2026-08-01T00:00:00Z",
            "--window-end",
            "2026-08-04T00:00:00Z",
            "--timezone",
            "UTC",
        ]

    def test_gsc_emits_deterministic_performance_envelope_and_hash_bound_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            source = bundle / "gsc.csv"
            source.write_text(
                "Query,Page,Date,Clicks,Impressions,CTR,Position,Unmapped note\n"
                "seo tools,https://example.com/tools,2026-08-02,10,100,10%,4.5,kept only in raw\n",
                encoding="utf-8",
            )
            first = bundle / "first.json"
            second = bundle / "second.json"
            one = self.invoke(*self.performance_args("gsc-csv", source, first))
            two = self.invoke(*self.performance_args("gsc-csv", source, second))
            self.assertEqual(one.returncode, 0, one.stdout + one.stderr)
            self.assertEqual(two.returncode, 0, two.stdout + two.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())

            payload = json.loads(first.read_text(encoding="utf-8"))
            self.assertEqual(
                set(payload),
                {
                    "schema_version", "source_type", "property", "search_type", "filters",
                    "export_method", "window", "dimensions", "rows", "indexation", "web_vitals",
                },
            )
            self.assertEqual(payload["source_type"], "google-search-console")
            self.assertEqual(payload["dimensions"], ["date", "query", "page"])
            self.assertEqual(payload["rows"][0]["ctr"], 0.1)
            self.assertIsNone(payload["rows"][0]["organic_sessions"])

            provenance = json.loads((bundle / "first.json.provenance.json").read_text(encoding="utf-8"))
            self.assertEqual(provenance["source"]["raw_source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(provenance["result"]["normalized_output_sha256"], hashlib.sha256(first.read_bytes()).hexdigest())
            self.assertEqual(provenance["source"]["ignored_headers"], ["Unmapped note"])

    def test_gsc_output_is_accepted_as_seo_performance_raw_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            raw_dir = bundle / "raw"
            raw_dir.mkdir()
            source = raw_dir / "gsc.csv"
            source.write_text(
                "Query,Page,Date,Clicks,Impressions,CTR,Average Position\n"
                "adapter test,HTTPS://EXAMPLE.COM/test,2026-08-02,3,12,25%,2.5\n",
                encoding="utf-8",
            )
            normalized = raw_dir / "gsc.normalized.json"
            imported = self.invoke(*self.performance_args("gsc-csv", source, normalized))
            self.assertEqual(imported.returncode, 0, imported.stdout + imported.stderr)
            source_envelope = json.loads(normalized.read_text(encoding="utf-8"))
            self.assertEqual(source_envelope["rows"][0]["page"], "https://example.com/test")
            run = {
                "schema_version": "1.0.0",
                "run_id": "adapter-performance-run",
                "created_at": "2026-08-05T00:00:00Z",
                "mode": "baseline",
                "interpretation_type": "observational_association",
                "causal_claim": False,
                **{
                    key: source_envelope[key]
                    for key in (
                        "source_type", "property", "search_type", "filters", "export_method",
                        "window", "dimensions", "rows", "indexation", "web_vitals",
                    )
                },
                "raw_source_ref": "raw/gsc.normalized.json",
                "raw_source_sha256": hashlib.sha256(normalized.read_bytes()).hexdigest(),
                "query_corpus_id": None,
                "query_corpus_ref": None,
                "query_corpus_sha256": None,
                "prior_run_id": None,
                "prior_run_ref": None,
                "prior_run_sha256": None,
                "data_quality": {
                    "sampling_status": "unknown",
                    "anonymized_queries": "unknown",
                    "row_limit": None,
                    "canonical_aggregation": "unknown",
                    "notes": ["The CSV export does not disclose these provider quality settings."],
                },
                "drift": [],
                "limitations": ["Credential-free user-supplied export."],
            }
            run_path = bundle / "seo-performance-run.json"
            run_path.write_text(json.dumps(run), encoding="utf-8")
            checked = subprocess.run(
                [
                    sys.executable,
                    str(PERFORMANCE_VALIDATOR),
                    "validate-run",
                    str(run_path),
                    "--bundle",
                    str(bundle),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertIn("PASS", checked.stdout)

    def test_search_csv_rejects_two_headers_for_one_dimension(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "ambiguous.csv"
            source.write_text("Page,URL,Clicks,Impressions\nhttps://example.com/a,https://example.com/b,1,2\n", encoding="utf-8")
            result = self.invoke(*self.performance_args("gsc-csv", source, root / "out.json"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ambiguous headers", result.stderr)
            self.assertFalse((root / "out.json").exists())

    def test_search_csv_rejects_malformed_row_and_conflicting_ctr(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            malformed = root / "malformed.csv"
            malformed.write_text("Query,Clicks,Impressions\nexample,1\n", encoding="utf-8")
            malformed_result = self.invoke(*self.performance_args("gsc-csv", malformed, root / "malformed.json"))
            self.assertNotEqual(malformed_result.returncode, 0)
            self.assertIn("different column count", malformed_result.stderr)

            conflicting = root / "conflicting.csv"
            conflicting.write_text("Query,Clicks,Impressions,CTR\nexample,1,10,90%\n", encoding="utf-8")
            conflict_result = self.invoke(*self.performance_args("gsc-csv", conflicting, root / "conflicting.json"))
            self.assertNotEqual(conflict_result.returncode, 0)
            self.assertIn("conflicts with clicks/impressions", conflict_result.stderr)

            impossible = root / "impossible.csv"
            impossible.write_text("Query,Clicks,Impressions\nexample,11,10\n", encoding="utf-8")
            impossible_result = self.invoke(*self.performance_args("gsc-csv", impossible, root / "impossible.json"))
            self.assertNotEqual(impossible_result.returncode, 0)
            self.assertIn("clicks cannot exceed impressions", impossible_result.stderr)
            self.assertFalse((root / "impossible.json").exists())

    def test_bing_export_preserves_provider_and_does_not_fill_absent_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "bing.csv"
            source.write_text("Keywords,Page,Clicks,Impressions\nseo,https://example.com/,2,20\n", encoding="utf-8")
            output = root / "bing.json"
            result = self.invoke(*self.performance_args("bing-csv", source, output))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["source_type"], "bing-webmaster-tools")
            self.assertEqual(payload["rows"][0]["ctr"], 0.1)
            self.assertIsNone(payload["rows"][0]["average_position"])
            self.assertIsNone(payload["rows"][0]["conversions"])

    def test_ga4_requires_explicit_organic_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "ga4.csv"
            source.write_text("Landing Page,Sessions\n/pricing,10\n", encoding="utf-8")
            output = root / "ga4.json"
            result = self.invoke(*self.performance_args("ga4-csv", source, output), "--origin", "https://example.com")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not assumed organic", result.stderr)

    def test_ga4_filters_declared_channel_and_does_not_relabel_key_events(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "ga4.csv"
            source.write_text(
                "Landing Page,Sessions,Session default channel group,Key events,Total Revenue\n"
                "/pricing,10,Organic Search,4,5.5\n"
                "/pricing,20,Direct,8,9.5\n",
                encoding="utf-8",
            )
            output = root / "ga4.json"
            result = self.invoke(*self.performance_args("ga4-csv", source, output), "--origin", "https://example.com")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["rows"]), 1)
            self.assertEqual(payload["rows"][0]["page"], "https://example.com/pricing")
            self.assertEqual(payload["rows"][0]["organic_sessions"], 10)
            self.assertIsNone(payload["rows"][0]["conversions"])
            self.assertEqual(payload["rows"][0]["revenue"], 5.5)
            self.assertIn(
                {"dimension": "sessionDefaultChannelGroup", "operator": "equals", "value": "Organic Search"},
                payload["filters"],
            )
            provenance = json.loads((root / "ga4.json.provenance.json").read_text(encoding="utf-8"))
            self.assertEqual(provenance["result"]["skipped_row_count"], 1)
            self.assertIn("Key events", provenance["source"]["ignored_headers"])

    def test_ga4_rejects_numbers_outside_finite_json_range(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "ga4.csv"
            huge = "9" * 400 + ".5"
            source.write_text(
                "Landing Page,Sessions,Session default channel group,Total Revenue\n"
                f"/pricing,10,Organic Search,{huge}\n",
                encoding="utf-8",
            )
            output = root / "ga4.json"
            result = self.invoke(*self.performance_args("ga4-csv", source, output), "--origin", "https://example.com")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("finite numeric range", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(output.exists())
            self.assertFalse((root / "ga4.json.provenance.json").exists())

    def test_relative_page_and_country_name_are_never_guessed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            relative = root / "relative.csv"
            relative.write_text("Page,Clicks,Impressions\n/a,1,2\n", encoding="utf-8")
            relative_result = self.invoke(*self.performance_args("gsc-csv", relative, root / "relative.json"))
            self.assertNotEqual(relative_result.returncode, 0)
            self.assertIn("requires --origin", relative_result.stderr)

            country = root / "country.csv"
            country.write_text("Country,Clicks,Impressions\nUnited States,1,2\n", encoding="utf-8")
            country_result = self.invoke(*self.performance_args("gsc-csv", country, root / "country.json"))
            self.assertNotEqual(country_result.returncode, 0)
            self.assertIn("names are not guessed", country_result.stderr)

    def test_malformed_url_is_a_clean_validation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "invalid-url.csv"
            source.write_text("Page,Clicks,Impressions\nhttps://[invalid,1,2\n", encoding="utf-8")
            result = self.invoke(*self.performance_args("gsc-csv", source, root / "out.json"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not a valid URL", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_crawler_csv_emits_candidates_without_fabricating_site_graph_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "crawl.csv"
            source.write_text(
                "Address,Status Code,Content Type,Title 1,Canonical Link Element 1,Indexability,Crawl Depth,Extra\n"
                "https://example.com/,200,text/html,Home,https://example.com/,Indexable,0,raw-only\n",
                encoding="utf-8",
            )
            output = root / "crawl.json"
            result = self.invoke("crawler-csv", source, "--output", output)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["provenance"]["raw_source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(payload["records"][0]["http_status"], 200)
            self.assertEqual(payload["records"][0]["indexability"], "Indexable")
            self.assertNotIn("index_intent", payload["records"][0])
            self.assertEqual(payload["workflow_compatibility"]["site_graph"]["not_emitted"], "site-graph.json")
            self.assertIn("Extra", payload["provenance"]["ignored_headers"])

    def test_crawler_csv_rejects_duplicate_urls_and_ambiguous_headers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            duplicate = root / "duplicate.csv"
            duplicate.write_text(
                "URL,Status Code\nhttps://example.com/,200\nhttps://example.com/,301\n",
                encoding="utf-8",
            )
            duplicate_result = self.invoke("crawler-csv", duplicate, "--output", root / "duplicate.json")
            self.assertNotEqual(duplicate_result.returncode, 0)
            self.assertIn("duplicate URL", duplicate_result.stderr)

            ambiguous = root / "ambiguous.csv"
            ambiguous.write_text(
                "URL,Address,Status Code\nhttps://example.com/,https://example.com/,200\n",
                encoding="utf-8",
            )
            ambiguous_result = self.invoke("crawler-csv", ambiguous, "--output", root / "ambiguous.json")
            self.assertNotEqual(ambiguous_result.returncode, 0)
            self.assertIn("ambiguous headers", ambiguous_result.stderr)

    def test_server_log_preserves_line_provenance_but_redacts_ip_and_query(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "access.log"
            line = '203.0.113.7 - - [10/Oct/2000:13:55:36 -0700] "GET /private?token=secret HTTP/1.1" 200 2326 "https://ref.example/" "ExampleBot/1.0"'
            source.write_text(line + "\n", encoding="utf-8")
            output = root / "access.json"
            result = self.invoke("server-log", source, "--output", output, "--origin", "https://example.com")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            record = payload["records"][0]
            self.assertEqual(payload["provenance"]["format"], "combined")
            self.assertEqual(payload["provenance"]["raw_source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(record["path"], "/private")
            self.assertTrue(record["query_present"])
            self.assertEqual(record["target_url"], "https://example.com/private")
            self.assertEqual(record["decoded_line_sha256"], hashlib.sha256(line.encode("utf-8")).hexdigest())
            self.assertEqual(record["request_target_sha256"], hashlib.sha256(b"/private?token=secret").hexdigest())
            serialized = output.read_text(encoding="utf-8")
            self.assertNotIn("203.0.113.7", serialized)
            self.assertNotIn("token=secret", serialized)
            self.assertNotIn("verified_crawler", serialized)

    def test_server_log_rejects_mixed_or_malformed_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mixed = root / "mixed.log"
            mixed.write_text(
                '127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET /a HTTP/1.0" 200 10\n'
                '127.0.0.1 - - [10/Oct/2000:13:55:37 -0700] "GET /b HTTP/1.1" 200 20 "-" "Agent"\n',
                encoding="utf-8",
            )
            mixed_result = self.invoke("server-log", mixed, "--output", root / "mixed.json")
            self.assertNotEqual(mixed_result.returncode, 0)
            self.assertIn("mixed Common and Combined", mixed_result.stderr)

            malformed = root / "malformed.log"
            malformed.write_text("this is not an access log\n", encoding="utf-8")
            malformed_result = self.invoke("server-log", malformed, "--output", root / "malformed.json")
            self.assertNotEqual(malformed_result.returncode, 0)
            self.assertIn("malformed or unsupported", malformed_result.stderr)

            bad_offset = root / "bad-offset.log"
            bad_offset.write_text(
                '127.0.0.1 - - [10/Oct/2000:13:55:37 +2460] "GET / HTTP/1.1" 200 20\n',
                encoding="utf-8",
            )
            offset_result = self.invoke("server-log", bad_offset, "--output", root / "bad-offset.json")
            self.assertNotEqual(offset_result.returncode, 0)
            self.assertIn("invalid access-log UTC offset", offset_result.stderr)
            self.assertNotIn("Traceback", offset_result.stderr)

    def test_server_log_rejects_credentials_in_absolute_request_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "credentials.log"
            source.write_text(
                '127.0.0.1 - - [10/Oct/2000:13:55:37 +0000] "GET https://alice:supersecret@example.com/private?token=abc HTTP/1.1" 200 20\n',
                encoding="utf-8",
            )
            output = root / "credentials.json"
            result = self.invoke("server-log", source, "--output", output)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cannot contain credentials", result.stderr)
            self.assertNotIn("supersecret", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(output.exists())

    def test_utf16_csv_is_supported_only_when_bom_marked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "gsc-utf16.csv"
            source.write_text("Query,Clicks,Impressions\nexample,1,2\n", encoding="utf-16")
            output = root / "gsc.json"
            result = self.invoke(*self.performance_args("gsc-csv", source, output))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            provenance = json.loads((root / "gsc.json.provenance.json").read_text(encoding="utf-8"))
            self.assertEqual(provenance["source"]["encoding"], "utf-16")

    def test_output_target_must_be_a_regular_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "gsc.csv"
            source.write_text("Query,Clicks,Impressions\nexample,1,2\n", encoding="utf-8")
            output = root / "output.json"
            output.mkdir()
            result = self.invoke(*self.performance_args("gsc-csv", source, output), "--overwrite")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("regular file", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_raw_source_reference_rejects_windows_drive_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "gsc.csv"
            source.write_text("Query,Clicks,Impressions\nexample,1,2\n", encoding="utf-8")
            output = root / "output.json"
            result = self.invoke(
                *self.performance_args("gsc-csv", source, output),
                "--raw-source-ref",
                "C:/secret.csv",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must be relative", result.stderr)
            self.assertFalse(output.exists())

    def test_two_file_output_failure_restores_both_previous_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "normalized.json"
            second = root / "normalized.json.provenance.json"
            first.write_bytes(b"old-normalized")
            second.write_bytes(b"old-provenance")
            real_replace = os.replace

            def fail_second_promotion(source: object, destination: object) -> None:
                source_path = Path(source)
                destination_path = Path(destination)
                if source_path.suffix == ".tmp" and destination_path == second:
                    raise OSError("simulated second-output failure")
                real_replace(source_path, destination_path)

            with mock.patch.object(IMPORTER_MODULE.os, "replace", side_effect=fail_second_promotion):
                with self.assertRaisesRegex(IMPORTER_MODULE.ImportFailure, "atomically write"):
                    IMPORTER_MODULE.staged_write_bytes(
                        [(first, b"new-normalized"), (second, b"new-provenance")]
                    )

            self.assertEqual(first.read_bytes(), b"old-normalized")
            self.assertEqual(second.read_bytes(), b"old-provenance")
            self.assertEqual(
                [path for path in root.iterdir() if path.name.startswith(".")],
                [],
            )


if __name__ == "__main__":
    unittest.main()
