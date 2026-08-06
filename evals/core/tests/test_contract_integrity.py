from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class ContractIntegrityTests(unittest.TestCase):
    def test_every_checked_in_contract_copy_matches_its_canonical_schema(self) -> None:
        for lock_path in ROOT.glob("skills/*/references/contracts/contracts-lock.json"):
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            self.assertIn("contracts", lock, lock_path)
            for row in lock["contracts"]:
                canonical = ROOT / row["canonical_path"]
                generated = lock_path.parents[2] / row["generated_path"]
                self.assertTrue(canonical.is_file(), canonical)
                self.assertTrue(generated.is_file(), generated)
                self.assertEqual(canonical.read_bytes(), generated.read_bytes(), generated)
                self.assertEqual(hashlib.sha256(canonical.read_bytes()).hexdigest(), row["canonical_sha256"])
                self.assertEqual(hashlib.sha256(generated.read_bytes()).hexdigest(), row["generated_sha256"])

    def test_primary_artifact_skill_validators_accept_their_own_skill_contracts(self) -> None:
        commands = (
            ["scripts/validate_ai_search_research.py", "validate-skill"],
            ["scripts/validate_seo_action_plan.py", "validate-skill"],
        )
        for command in commands:
            completed = subprocess.run(
                [sys.executable, str(ROOT / command[0]), *command[1:]],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
