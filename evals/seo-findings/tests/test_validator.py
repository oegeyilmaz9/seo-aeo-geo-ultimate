from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PYTHON = sys.executable
VALIDATOR = ROOT / "scripts" / "validate_seo_findings.py"
RAW_CAPTURE = b"<html><head></head><body>Example</body></html>"
RAW_CAPTURE_SHA256 = hashlib.sha256(RAW_CAPTURE).hexdigest()


def base_findings() -> dict:
    return {
        "schema_version": "1.0.0",
        "finding_set_id": "homepage-technical-findings",
        "created_at": "2026-07-10T23:30:00Z",
        "producer_skill": "seo-technical",
        "scope": {
            "objective": "Record a reviewable title delivery observation for the Turkish homepage.",
            "targets": [
                {
                    "target_id": "homepage-tr",
                    "target_type": "web_page",
                    "locale": "tr-TR",
                    "source_url": "https://example.test/tr",
                }
            ],
        },
        "evidence": [
            {
                "claim_id": "homepage-title-observation",
                "target_id": "homepage-tr",
                "claim": "The rendered Turkish homepage has no descriptive title element.",
                "classification": "confirmed",
                "source_kind": "direct_observation",
                "engine": "not_applicable",
                "surface": "rendered-page",
                "locale": "tr-TR",
                "source_title": "Turkish homepage capture",
                "source_url": "https://example.test/tr",
                "source_published_or_updated_at": None,
                "accessed_at": "2026-07-10T23:20:00Z",
                "raw_evidence_ref": "raw/homepage-tr.html",
                "raw_evidence_sha256": RAW_CAPTURE_SHA256,
                "observation_method": "Rendered page capture reviewed by an analyst.",
                "limitations": ["The capture is point in time and does not establish indexing or ranking."],
            }
        ],
        "findings": [
            {
                "finding_id": "homepage-title-missing",
                "target_id": "homepage-tr",
                "title": "The rendered homepage title is missing",
                "observation": "The captured HTML contains no descriptive title element.",
                "category": "technical",
                "classification": "confirmed",
                "severity": "important",
                "evidence_ids": ["homepage-title-observation"],
                "candidate_owner": "seo-technical",
                "desired_outcome": "Deliver one accurate, descriptive title in the rendered document.",
                "verification_method": "Recapture the rendered page and compare its title to the approved content brief.",
                "limitations": ["A title correction does not guarantee indexing, ranking, or traffic."],
            }
        ],
        "declined_claims": [],
        "limitations": ["The finding is limited to the supplied rendered capture."],
    }


class SeoFindingsValidatorTests(unittest.TestCase):
    def run_findings(self, mutator=None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            raw = bundle / "raw"
            raw.mkdir(parents=True)
            (raw / "homepage-tr.html").write_bytes(RAW_CAPTURE)
            artifact = bundle / "seo-findings.json"
            payload = base_findings()
            if mutator:
                mutator(payload)
            artifact.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            return subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-findings", str(artifact), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_valid_findings_pass(self) -> None:
        completed = self.run_findings()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS: seo-findings", completed.stdout)

    def test_expanded_specialist_findings_pass_with_v1_1(self) -> None:
        def mutate(payload: dict) -> None:
            payload["schema_version"] = "1.1.0"
            payload["producer_skill"] = "seo-commerce"
            payload["scope"]["targets"][0]["target_type"] = "feed"
            payload["findings"][0]["category"] = "commerce"
            payload["findings"][0]["candidate_owner"] = "seo-commerce"

        completed = self.run_findings(mutate)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_expanded_specialist_findings_reject_legacy_version(self) -> None:
        def mutate(payload: dict) -> None:
            payload["producer_skill"] = "seo-commerce"
            payload["findings"][0]["category"] = "commerce"
            payload["findings"][0]["candidate_owner"] = "seo-commerce"

        completed = self.run_findings(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("schema_version 1.1.0 is required", completed.stderr)

    def test_v1_1_requires_hash_pinned_raw_evidence(self) -> None:
        def mutate(payload: dict) -> None:
            payload["schema_version"] = "1.1.0"
            payload["evidence"][0].pop("raw_evidence_sha256")

        completed = self.run_findings(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("raw_evidence_sha256 is required", completed.stderr)

    def test_v1_1_evidence_must_bind_a_scope_target(self) -> None:
        def mutate(payload: dict) -> None:
            payload["schema_version"] = "1.1.0"
            payload["evidence"][0]["target_id"] = "unrelated-target"

        completed = self.run_findings(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("target_id must resolve", completed.stderr)

    def test_v1_1_direct_observation_url_and_locale_must_match_target(self) -> None:
        def mutate(payload: dict) -> None:
            payload["schema_version"] = "1.1.0"
            payload["evidence"][0].update(
                {"source_url": "https://unrelated.example/other", "locale": "en-US"}
            )

        completed = self.run_findings(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("source_url must match its scope target URL", completed.stderr)
        self.assertIn("locale must match its scope target locale", completed.stderr)

    def test_v1_1_url_less_target_requires_a_target_specific_envelope(self) -> None:
        def mutate(payload: dict) -> None:
            payload["schema_version"] = "1.1.0"
            payload["producer_skill"] = "seo-architecture"
            payload["scope"]["targets"][0].update({"target_type": "site_graph", "source_url": None})
            payload["findings"][0].update({"category": "architecture", "candidate_owner": "seo-architecture"})

        completed = self.run_findings(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("URL-less target evidence must be a hash-pinned JSON target envelope", completed.stderr)

    def test_raw_evidence_hash_drift_fails(self) -> None:
        completed = self.run_findings(
            lambda payload: payload["evidence"][0].update({"raw_evidence_sha256": "0" * 64})
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("raw evidence hash mismatch", completed.stderr)

    def test_finding_requires_direct_observation_for_target(self) -> None:
        def mutate(payload: dict) -> None:
            payload["evidence"][0]["source_kind"] = "vendor_documentation"

        completed = self.run_findings(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("requires capture-tied direct observation", completed.stderr)

    def test_finding_cannot_overstate_weakest_evidence_classification(self) -> None:
        def mutate(payload: dict) -> None:
            payload["evidence"][0]["classification"] = "vendor-recommended"

        completed = self.run_findings(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("classification exceeds its weakest evidence premise", completed.stderr)

    def test_raw_evidence_path_cannot_escape_bundle(self) -> None:
        def mutate(payload: dict) -> None:
            payload["evidence"][0]["raw_evidence_ref"] = "raw/../outside.html"

        completed = self.run_findings(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("raw_evidence_ref", completed.stderr)

    def test_artifact_cannot_live_outside_declared_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            (bundle / "raw").mkdir(parents=True)
            (bundle / "raw" / "homepage-tr.html").write_bytes(RAW_CAPTURE)
            outside = root / "seo-findings.json"
            outside.write_text(json.dumps(base_findings(), indent=2) + "\n", encoding="utf-8")
            completed = subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-findings", str(outside), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("artifact must be inside --bundle", completed.stderr)


if __name__ == "__main__":
    unittest.main()
