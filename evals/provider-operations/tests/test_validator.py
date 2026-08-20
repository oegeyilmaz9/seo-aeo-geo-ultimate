from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "scripts" / "validate_provider_operation.py"
RENDERER = ROOT / "scripts" / "render_artifact_report.py"


class ProviderOperationValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.bundle = Path(self.temporary.name)
        (self.bundle / "raw").mkdir()
        for name in ("authorization.txt", "pre.json", "response.json", "post.json", "outcome.json"):
            (self.bundle / "raw" / name).write_text(f"evidence: {name}\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def hash(self, name: str) -> str:
        return hashlib.sha256((self.bundle / "raw" / name).read_bytes()).hexdigest()

    def payload(self) -> dict:
        return {
            "schema_version": "1.0.0",
            "receipt_id": "gsc-sitemap-001",
            "recorded_at": "2026-08-20T11:03:00Z",
            "provider": {
                "provider_id": "google-search-console",
                "property": "sc-domain:example.test",
                "property_verified_at": "2026-08-20T10:55:00Z",
                "capability_documentation_url": "https://developers.google.com/webmaster-tools/v1/sitemaps/submit",
                "capability_verified_at": "2026-08-20T10:50:00Z",
            },
            "authorization": {
                "authorized_by": "product owner",
                "authorized_at": "2026-08-20T10:00:00Z",
                "mutation_allowed": True,
                "operation_types": ["submit-sitemap"],
                "target_ids": ["sitemap-main"],
                "evidence_ref": "raw/authorization.txt",
                "evidence_sha256": self.hash("authorization.txt"),
            },
            "pre_state": {
                "captured_at": "2026-08-20T10:56:00Z",
                "evidence_ref": "raw/pre.json",
                "evidence_sha256": self.hash("pre.json"),
                "summary": "Property and sitemap pre-state captured.",
            },
            "operation": {
                "operation_id": "submit-main-sitemap",
                "operation_type": "submit-sitemap",
                "access_path": "api",
                "endpoint_or_surface": "Search Console sitemaps.submit",
                "mutation": True,
                "started_at": "2026-08-20T11:00:00Z",
                "targets": [
                    {
                        "target_id": "sitemap-main",
                        "target_type": "sitemap",
                        "value": "https://example.test/sitemap.xml",
                        "eligibility": "not-applicable",
                    }
                ],
            },
            "result": {
                "completed_at": "2026-08-20T11:01:00Z",
                "status": "accepted",
                "provider_receipt": "HTTP 204",
                "succeeded_target_ids": ["sitemap-main"],
                "failed_target_ids": [],
                "evidence_ref": "raw/response.json",
                "evidence_sha256": self.hash("response.json"),
                "errors": [],
            },
            "post_state": {
                "captured_at": "2026-08-20T11:02:00Z",
                "evidence_ref": "raw/post.json",
                "evidence_sha256": self.hash("post.json"),
                "summary": "Submission response and post-state captured.",
            },
            "outcomes": [
                {
                    "kind": "indexing",
                    "state": "pending",
                    "observed_at": None,
                    "evidence_ref": None,
                    "evidence_sha256": None,
                    "note": "Sitemap acceptance is not an indexing observation.",
                }
            ],
            "limitations": ["Provider processing and reporting lag remain."],
        }

    def invoke(self, payload: dict) -> subprocess.CompletedProcess[str]:
        path = self.bundle / "provider-operation-receipt.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "validate-receipt", str(path), "--bundle", str(self.bundle)],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_valid_sitemap_submission_keeps_indexing_pending(self) -> None:
        completed = self.invoke(self.payload())
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS: provider operation receipt", completed.stdout)

    def test_property_mismatch_is_rejected(self) -> None:
        payload = self.payload()
        payload["operation"]["targets"][0]["value"] = "https://unrelated.test/sitemap.xml"
        completed = self.invoke(payload)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("inside the verified property", completed.stderr)

    def test_authorized_targets_must_exactly_match_operation(self) -> None:
        payload = self.payload()
        payload["authorization"]["target_ids"] = ["different-target"]
        completed = self.invoke(payload)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("must exactly match operation target IDs", completed.stderr)

    def test_property_must_be_verified_immediately_before_mutation(self) -> None:
        payload = self.payload()
        payload["provider"]["property_verified_at"] = "2026-08-19T10:55:00Z"
        completed = self.invoke(payload)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("no more than one hour", completed.stderr)

    def test_search_console_request_indexing_cannot_claim_api_path(self) -> None:
        payload = self.payload()
        payload["authorization"]["operation_types"] = ["request-indexing"]
        payload["operation"]["operation_type"] = "request-indexing"
        payload["operation"]["targets"][0]["target_type"] = "url"
        payload["operation"]["targets"][0]["value"] = "https://example.test/page"
        completed = self.invoke(payload)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("not declared for provider", completed.stderr)

    def test_google_indexing_api_requires_documented_page_eligibility(self) -> None:
        payload = self.payload()
        payload["provider"]["provider_id"] = "google-indexing-api"
        payload["provider"]["property"] = "https://example.test/"
        payload["provider"]["capability_documentation_url"] = "https://developers.google.com/search/apis/indexing-api/v3/using-api"
        payload["authorization"]["operation_types"] = ["submit-url"]
        payload["operation"]["operation_type"] = "submit-url"
        payload["operation"]["targets"][0].update(
            {"target_type": "url", "value": "https://example.test/page", "eligibility": "not-applicable"}
        )
        completed = self.invoke(payload)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("must be job-posting or livestream-broadcast-event", completed.stderr)

    def test_observed_outcome_requires_separate_hash_bound_evidence(self) -> None:
        payload = self.payload()
        payload["outcomes"][0].update({"state": "observed", "observed_at": "2026-08-20T11:02:30Z"})
        completed = self.invoke(payload)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("requires hash-bound evidence", completed.stderr)

    def test_observed_outcome_with_later_evidence_passes(self) -> None:
        payload = self.payload()
        payload["outcomes"][0].update(
            {
                "state": "observed",
                "observed_at": "2026-08-20T11:02:30Z",
                "evidence_ref": "raw/outcome.json",
                "evidence_sha256": self.hash("outcome.json"),
            }
        )
        completed = self.invoke(payload)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_hash_tampering_is_rejected(self) -> None:
        payload = self.payload()
        (self.bundle / "raw" / "response.json").write_text("tampered\n", encoding="utf-8")
        completed = self.invoke(payload)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("result.evidence_ref hash mismatch", completed.stderr)

    def test_valid_receipt_can_render_a_readable_validated_report(self) -> None:
        payload = self.payload()
        receipt = self.bundle / "provider-operation-receipt.json"
        report = self.bundle / "provider-operation-report.md"
        receipt.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                str(RENDERER),
                str(receipt),
                "--bundle",
                str(self.bundle),
                "--out",
                str(report),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        text = report.read_text(encoding="utf-8")
        self.assertIn("Provider Operation Receipt", text)
        self.assertIn("Sitemap acceptance is not an indexing observation", text)


if __name__ == "__main__":
    unittest.main()
