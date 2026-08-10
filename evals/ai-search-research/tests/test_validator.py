from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PYTHON = sys.executable
VALIDATOR = ROOT / "scripts" / "validate_ai_search_research.py"
FIXTURE = ROOT / "evals" / "fixtures" / "aeo-normal"
NOW = "2026-07-11T12:00:00Z"


class AiSearchResearchValidatorTests(unittest.TestCase):
    def run_pack(self, mutator=None, bundle_mutator=None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(FIXTURE, bundle)
            if bundle_mutator:
                bundle_mutator(bundle)
            artifact = bundle / "research-pack.json"
            if mutator:
                payload = json.loads(artifact.read_text(encoding="utf-8"))
                mutator(payload)
                artifact.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            return subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-pack", str(artifact), "--bundle", str(bundle), "--now", NOW],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_valid_research_pack_passes(self) -> None:
        completed = self.run_pack()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS: research-pack", completed.stdout)

    def test_artifact_cannot_live_outside_declared_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            shutil.copytree(FIXTURE, bundle)
            outside = root / "research-pack.json"
            outside.write_text((bundle / "research-pack.json").read_text(encoding="utf-8"), encoding="utf-8")
            completed = subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-pack", str(outside), "--bundle", str(bundle), "--now", NOW],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("artifact must be inside --bundle", completed.stderr)

    def test_invalid_json_is_reported_without_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(FIXTURE, bundle)
            artifact = bundle / "research-pack.json"
            artifact.write_text("{not-json", encoding="utf-8")
            completed = subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-pack", str(artifact), "--bundle", str(bundle), "--now", NOW],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("research-pack.json is not valid JSON", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)

    def test_v1_1_raw_evidence_hash_drift_fails(self) -> None:
        completed = self.run_pack(
            bundle_mutator=lambda bundle: (bundle / "raw" / "evidence.json").write_text(
                '{"unrelated": true}', encoding="utf-8"
            )
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("raw_evidence_ref hash mismatch", completed.stderr)

    def test_v1_1_requires_raw_evidence_hashes(self) -> None:
        completed = self.run_pack(
            lambda payload: payload["evidence"][0].pop("raw_evidence_sha256")
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("raw_evidence_sha256 is required", completed.stderr)

    def test_legacy_v1_0_without_raw_hashes_remains_supported(self) -> None:
        def mutate(payload: dict) -> None:
            payload["schema_version"] = "1.0.0"
            for record in payload["evidence"]:
                record.pop("raw_evidence_sha256", None)
            for observation in payload["competitor_observations"]:
                observation.pop("raw_observation_sha256", None)
            for fact in payload["ground_truth"]:
                fact.pop("provenance_sha256", None)

        completed = self.run_pack(mutate)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
