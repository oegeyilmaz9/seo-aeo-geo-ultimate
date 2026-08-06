from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SYNC = ROOT / "scripts" / "sync_contracts.py"


class ContractSyncTests(unittest.TestCase):
    def test_checked_in_generated_contracts_match_the_canonical_source(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SYNC), "--check"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS: verified", completed.stdout)


if __name__ == "__main__":
    unittest.main()
