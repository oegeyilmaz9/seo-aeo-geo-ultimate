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
VALIDATOR = ROOT / "scripts" / "validate_seo_geo.py"
FIXTURE = ROOT / "evals" / "fixtures" / "aeo-normal"


class SeoGeoValidatorTests(unittest.TestCase):
    def test_geo_brief_with_a_geo_owned_dimension_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(FIXTURE, bundle)
            artifact = bundle / "optimization-brief.json"
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            payload["optimization_domain"] = "geo"
            payload["producer_skill"] = "seo-geo"
            payload["findings"][0]["dimension"] = "entity_consistency"
            artifact.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            completed = subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-brief", str(artifact), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS: seo-geo", completed.stdout)

    def test_geo_rejects_artifact_outside_its_bundle(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
