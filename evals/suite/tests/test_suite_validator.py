from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "scripts" / "validate_suite.py"


class SuiteValidatorTests(unittest.TestCase):
    def test_suite_passes_on_review_date(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR), "--as-of", "2026-08-06"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("19 skills", completed.stdout)


if __name__ == "__main__":
    unittest.main()
