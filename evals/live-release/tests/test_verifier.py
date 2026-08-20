from __future__ import annotations

import json
import hashlib
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VERIFIER = ROOT / "scripts" / "verify_live_release.py"


def png_bytes(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw_scanline = b"\x00" + b"\x00\x00\x00\xff" * width
    image_data = raw_scanline * height
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(image_data))
        + chunk(b"IEND", b"")
    )


class ReleaseHandler(BaseHTTPRequestHandler):
    sitemap_paths = ["/page"]
    wrong_canonical_paths: set[str] = set()
    redirect_target = "/page"
    transient_paths: set[str] = set()
    noindex_paths: set[str] = set()
    hits: dict[str, int] = {}
    homepage_has_favicon = True
    favicon_size = 96
    favicon_status = 200
    favicon_content_type = "image/png"

    def log_message(self, format: str, *args) -> None:
        return

    def base(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def do_GET(self) -> None:
        self.__class__.hits[self.path] = self.__class__.hits.get(self.path, 0) + 1
        if self.path == "/sitemap.xml":
            rows = "".join(f"<url><loc>{self.base()}{path}</loc></url>" for path in self.__class__.sitemap_paths)
            body = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{rows}</urlset>'.encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/":
            icon = '<link rel="icon" href="/favicon.png">' if self.__class__.homepage_has_favicon else ""
            body = f"<!doctype html><html><head><title>Home</title>{icon}</head><body><h1>Home</h1></body></html>".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/favicon.png":
            body = png_bytes(self.__class__.favicon_size, self.__class__.favicon_size)
            self.send_response(self.__class__.favicon_status)
            self.send_header("Content-Type", self.__class__.favicon_content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/old":
            self.send_response(308)
            self.send_header("Location", self.__class__.redirect_target)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path == "/robots.txt":
            body = b"User-agent: *\nAllow: /\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path in self.__class__.transient_paths and self.__class__.hits[self.path] == 1:
            self.send_response(503)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path in {"/page", "/transient", "/unexpected", "/missing", "/noindex"}:
            canonical_path = "/wrong" if self.path in self.__class__.wrong_canonical_paths else self.path
            robots = '<meta name="robots" content="noindex">' if self.path in self.__class__.noindex_paths else ""
            body = (
                "<!doctype html><html><head>"
                f"<title>{self.path} title</title>"
                '<meta name="description" content="Useful description">'
                f"{robots}"
                f'<link rel="canonical" href="{self.base()}{canonical_path}">'
                "</head><body><h1>Useful heading</h1></body></html>"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()


class LiveReleaseVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        ReleaseHandler.sitemap_paths = ["/page"]
        ReleaseHandler.wrong_canonical_paths = set()
        ReleaseHandler.redirect_target = "/page"
        ReleaseHandler.transient_paths = set()
        ReleaseHandler.noindex_paths = set()
        ReleaseHandler.hits = {}
        ReleaseHandler.homepage_has_favicon = True
        ReleaseHandler.favicon_size = 96
        ReleaseHandler.favicon_status = 200
        ReleaseHandler.favicon_content_type = "image/png"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ReleaseHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def plan(self, paths: list[str] | None = None, redirects: bool = True) -> dict:
        paths = paths or ["/page"]
        expected_urls = [f"{self.base}{path}" for path in paths]
        (self.root / "expected.txt").write_text("".join(f"{url}\n" for url in expected_urls), encoding="utf-8")
        corpus_sha256 = hashlib.sha256(("\n".join(sorted(expected_urls)) + "\n").encode()).hexdigest()
        candidate_manifest = {
            "schema_version": "1.0.0",
            "candidate_id": "build-123",
            "candidate_sha256": "0" * 64,
            "git_dirty": True,
            "source_files": [{"path": "src/pages.ts", "sha256": "1" * 64}],
            "generated_files": [],
            "build_identity": "local-test-build",
            "corpus": {"kind": "url-set", "expected_count": len(expected_urls), "sha256": corpus_sha256},
        }
        manifest_path = self.root / "candidate-manifest.json"
        manifest_path.write_text(json.dumps(candidate_manifest, indent=2) + "\n", encoding="utf-8")
        manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        return {
            "schema_version": "1.0.0",
            "release_id": "candidate-release-001",
            "candidate": {
                "candidate_id": "build-123",
                "sha256": "0" * 64,
                "git_dirty": True,
                "manifest_ref": "candidate-manifest.json",
                "manifest_sha256": manifest_sha256,
                "deployment_id": "deployment-test-123",
                "production_alias": self.base,
            },
            "origin": self.base,
            "expected_inventory_ref": "expected.txt",
            "live_sitemap_url": f"{self.base}/sitemap.xml",
            "sitemap_mode": "exact",
            "document_defaults": {
                "allowed_status": [200],
                "indexable": True,
                "canonical": "self",
                "require_title": True,
                "require_description": True,
                "require_h1": True,
            },
            "document_overrides": [],
            "redirects": [
                {"source": f"{self.base}/old", "target": f"{self.base}/page", "allowed_status": [301, 308]}
            ] if redirects else [],
            "surfaces": [
                {
                    "surface_id": "robots",
                    "url": f"{self.base}/robots.txt",
                    "allowed_status": [200],
                    "content_type_prefix": "text/plain",
                    "required_text": "User-agent:",
                }
            ],
            "network": {"concurrency": 4, "retries": 2, "timeout_seconds": 3},
            "rendered_required": False,
            "site_identity": {
                "homepage_url": self.base,
                "expected_favicon_url": f"{self.base}/favicon.png",
                "minimum_size_px": 8,
                "require_recommended_size": True,
            },
        }

    def invoke(self, payload: dict) -> tuple[subprocess.CompletedProcess[str], dict | None]:
        plan = self.root / "plan.json"
        output = self.root / "report.json"
        plan.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                str(VERIFIER),
                "verify",
                "--plan",
                str(plan),
                "--output",
                str(output),
                "--allow-private-targets",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        return completed, json.loads(output.read_text(encoding="utf-8")) if output.exists() else None

    def test_complete_raw_release_contract_passes(self) -> None:
        completed, report = self.invoke(self.plan())
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["counts"]["indexable"], {"expected": 1, "passed": 1, "failed": 0})
        self.assertEqual(report["counts"]["redirects"], {"expected": 1, "passed": 1, "failed": 0})
        self.assertEqual(report["counts"]["surfaces"], {"expected": 1, "passed": 1, "failed": 0})
        self.assertEqual(report["counts"]["site_identity"], {"expected": 1, "passed": 1, "failed": 0})
        self.assertEqual(report["site_identity"]["observed"]["dimensions"], [96.0, 96.0])

    def test_missing_homepage_favicon_link_returns_nonzero(self) -> None:
        ReleaseHandler.homepage_has_favicon = False
        completed, report = self.invoke(self.plan())
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(any(row["check"] == "homepage-favicon-link" for row in report["failures"]))

    def test_tiny_favicon_fails_owned_quality_floor(self) -> None:
        ReleaseHandler.favicon_size = 32
        completed, report = self.invoke(self.plan())
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(any(row["check"] == "favicon-recommended-size" for row in report["failures"]))

    def test_wrong_canonical_returns_nonzero(self) -> None:
        ReleaseHandler.wrong_canonical_paths = {"/page"}
        completed, report = self.invoke(self.plan())
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(any(row["check"] == "canonical" for row in report["failures"]))

    def test_expected_search_copy_must_reach_the_live_document(self) -> None:
        payload = self.plan()
        payload["document_overrides"] = [
            {
                "url": f"{self.base}/page",
                "expected_title": "/page title",
                "expected_description": "A specific, approved description that was not deployed.",
                "expected_h1": "Useful heading",
            }
        ]
        completed, report = self.invoke(payload)
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(any(row["check"] == "description-copy" for row in report["failures"]))

        payload["document_overrides"][0]["expected_description"] = "Useful description"
        (self.root / "report.json").unlink()
        completed, report = self.invoke(payload)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(report["result"], "pass")

    def test_wrong_redirect_target_returns_nonzero(self) -> None:
        ReleaseHandler.redirect_target = "/unexpected"
        completed, report = self.invoke(self.plan())
        self.assertEqual(completed.returncode, 1)
        self.assertTrue(any(row["kind"] == "redirect" and row["check"] == "location" for row in report["failures"]))

    def test_transient_recovery_is_visible_but_not_permanent_failure(self) -> None:
        ReleaseHandler.sitemap_paths = ["/transient"]
        ReleaseHandler.transient_paths = {"/transient"}
        completed, report = self.invoke(self.plan(["/transient"], redirects=False))
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(len(report["recovered_transient_requests"]), 1)
        self.assertEqual(report["permanent_failures"], [])

    def test_bodyless_redirect_does_not_require_document_metadata(self) -> None:
        completed, report = self.invoke(self.plan())
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(report["redirects"][0]["failures"], [])
        self.assertNotIn("title", report["redirects"][0]["observed"])

    def test_sitemap_missing_and_unexpected_counts_are_distinct(self) -> None:
        ReleaseHandler.sitemap_paths = ["/unexpected"]
        completed, report = self.invoke(self.plan(["/page"], redirects=False))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(report["sitemap"]["missing_count"], 1)
        self.assertEqual(report["sitemap"]["unexpected_count"], 1)
        self.assertEqual(report["sitemap"]["missing_urls"], [f"{self.base}/page"])
        self.assertEqual(report["sitemap"]["unexpected_urls"], [f"{self.base}/unexpected"])

    def test_scoped_sitemap_ignores_unrelated_urls_and_enforces_nonindex_exclusion(self) -> None:
        ReleaseHandler.sitemap_paths = ["/page", "/unexpected"]
        ReleaseHandler.noindex_paths = {"/noindex"}
        payload = self.plan(["/page", "/noindex"], redirects=False)
        payload["sitemap_mode"] = "scoped"
        payload["document_overrides"] = [{"url": f"{self.base}/noindex", "indexable": False}]
        completed, report = self.invoke(payload)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(report["sitemap"]["unexpected_count"], 0)
        self.assertEqual(report["counts"]["indexable"], {"expected": 1, "passed": 1, "failed": 0})
        self.assertEqual(report["counts"]["nonindex"], {"expected": 1, "passed": 1, "failed": 0})

        ReleaseHandler.sitemap_paths.append("/noindex")
        (self.root / "report.json").unlink()
        completed, report = self.invoke(payload)
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(report["sitemap"]["excluded_present_urls"], [f"{self.base}/noindex"])

    def test_rendered_requirement_fails_closed(self) -> None:
        payload = self.plan()
        payload["rendered_required"] = True
        completed, report = self.invoke(payload)
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(report["rendered_verification"], "required-but-unsupported")
        self.assertTrue(any(row["kind"] == "rendered" for row in report["failures"]))

    def test_candidate_manifest_hash_mismatch_fails_before_network(self) -> None:
        payload = self.plan()
        payload["candidate"]["manifest_sha256"] = "f" * 64
        completed, report = self.invoke(payload)
        self.assertEqual(completed.returncode, 2)
        self.assertIsNone(report)
        self.assertIn("candidate manifest hash mismatch", completed.stderr)

    def test_dirty_candidate_cannot_omit_changed_file_identity(self) -> None:
        payload = self.plan()
        manifest_path = self.root / "candidate-manifest.json"
        candidate_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        candidate_manifest["source_files"] = []
        candidate_manifest["generated_files"] = []
        manifest_path.write_text(json.dumps(candidate_manifest, indent=2) + "\n", encoding="utf-8")
        payload["candidate"]["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        completed, report = self.invoke(payload)
        self.assertEqual(completed.returncode, 2)
        self.assertIsNone(report)
        self.assertIn("dirty candidate manifest must preserve", completed.stderr)

    def test_malformed_plan_fails_without_report(self) -> None:
        payload = self.plan()
        del payload["candidate"]
        completed, report = self.invoke(payload)
        self.assertEqual(completed.returncode, 2)
        self.assertIsNone(report)
        self.assertIn("plan is missing", completed.stderr)


if __name__ == "__main__":
    unittest.main()
