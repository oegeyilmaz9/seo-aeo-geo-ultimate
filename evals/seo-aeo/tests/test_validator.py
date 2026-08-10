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
VALIDATOR = ROOT / "scripts" / "validate_seo_aeo.py"
FIXTURE = ROOT / "evals" / "fixtures" / "aeo-normal"


class SeoAeoValidatorTests(unittest.TestCase):
    def run_brief(self, mutator=None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(FIXTURE, bundle)
            artifact = bundle / "optimization-brief.json"
            if mutator:
                payload = json.loads(artifact.read_text(encoding="utf-8"))
                mutator(payload)
                artifact.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            return subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-brief", str(artifact), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_valid_optimization_brief_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(FIXTURE, bundle)
            completed = subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-brief", str(bundle / "optimization-brief.json"), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS: seo-aeo", completed.stdout)

    def test_artifact_cannot_live_outside_declared_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            shutil.copytree(FIXTURE, bundle)
            outside = root / "optimization-brief.json"
            outside.write_text((bundle / "optimization-brief.json").read_text(encoding="utf-8"), encoding="utf-8")
            completed = subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-brief", str(outside), "--bundle", str(bundle)],
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
            artifact = bundle / "optimization-brief.json"
            artifact.write_text("{not-json", encoding="utf-8")
            completed = subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-brief", str(artifact), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("optimization-brief.json is not valid JSON", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)

    def test_expanded_owner_passes_with_v1_1(self) -> None:
        def mutate(payload: dict) -> None:
            payload["schema_version"] = "1.1.0"
            payload["recommendations"][0]["owner_skill"] = "seo-commerce"
            for collection in (payload["findings"], payload["recommendations"]):
                for record in collection:
                    for ref in record["evidence_refs"]:
                        if ref["artifact_type"] == "optimization-brief":
                            ref["schema_version"] = "1.1.0"

        completed = self.run_brief(mutate)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_expanded_owner_rejects_legacy_version(self) -> None:
        completed = self.run_brief(
            lambda payload: payload["recommendations"][0].update({"owner_skill": "seo-commerce"})
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("expanded owner requires schema_version 1.1.0", completed.stderr)

    def test_expanded_target_rejects_legacy_version(self) -> None:
        completed = self.run_brief(
            lambda payload: payload["targets"][0].update({"target_type": "feed"})
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("expanded target type requires schema_version 1.1.0", completed.stderr)


if __name__ == "__main__":
    unittest.main()
