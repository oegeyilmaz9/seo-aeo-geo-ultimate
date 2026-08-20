from __future__ import annotations

import subprocess
import sys
import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "scripts" / "validate_suite.py"


class SuiteValidatorTests(unittest.TestCase):
    def test_suite_passes_on_review_date(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR), "--as-of", "2026-08-20"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("27 skills", completed.stdout)

    def test_manifest_registers_supported_repository_tools(self) -> None:
        manifest = json.loads((ROOT / "manifests" / "suite.json").read_text(encoding="utf-8"))
        self.assertEqual(
            set(manifest["tools"]),
            {
                "artifact-scaffold",
                "artifact-migrate",
                "artifact-report",
                "data-import",
                "runtime-install",
                "provider-operation-validate",
                "live-release-verify",
                "orchestration-ledger",
            },
        )
        for entry in manifest["tools"].values():
            self.assertTrue((ROOT / entry["path"]).is_file())


if __name__ == "__main__":
    unittest.main()
