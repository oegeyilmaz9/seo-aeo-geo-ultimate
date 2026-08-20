from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "manage_orchestration_ledger.py"
MANIFEST = ROOT / "manifests" / "suite.json"


class OrchestrationLedgerTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), *args], check=False, capture_output=True, text=True)

    def initialized(self, root: Path, mode: str = "broad") -> tuple[Path, dict]:
        path = root / "orchestration-ledger.json"
        completed = self.run_cli(
            "init",
            "--output",
            str(path),
            "--request",
            "Improve organic and AI-search visibility end to end",
            "--mode",
            mode,
            "--authorized-boundary",
            "Research, audit, plan, and local implementation",
            "--created-at",
            "2026-08-20T12:00:00Z",
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return path, json.loads(path.read_text(encoding="utf-8"))

    def valid_payload(self, root: Path, mode: str = "broad") -> tuple[Path, dict]:
        path, payload = self.initialized(root, mode)
        for row in payload["skills"]:
            row["state"] = "not-applicable"
            row["reason"] = "Observed request scope does not activate this specialist lane."
        coordinator = next(row for row in payload["skills"] if row["skill"] == "seo")
        coordinator["state"] = "completed"
        coordinator["reason"] = "The router screened every current suite capability and consolidated the result."
        coordinator["output_refs"] = ["work/final-summary.md"]
        payload["overall_state"] = "completed"
        payload["coverage_summary"] = "All suite lanes were screened; only the coordinator was required for this bounded fixture."
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path, payload

    def test_init_uses_every_current_manifest_skill_and_is_explicitly_unassessed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path, payload = self.initialized(Path(temporary))
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            self.assertEqual([row["skill"] for row in payload["skills"]], list(manifest["skills"]))
            self.assertTrue(all(row["state"] == "unassessed" for row in payload["skills"]))
            completed = self.run_cli("validate", str(path))
            self.assertEqual(completed.returncode, 2)
            self.assertIn("state must be one of", completed.stderr)

    def test_complete_ledger_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path, _ = self.valid_payload(Path(temporary))
            completed = self.run_cli("validate", str(path))
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertIn("covers all 27 current suite skills", completed.stdout)

    def test_missing_duplicate_and_unknown_skill_rows_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, payload = self.valid_payload(root)
            payload["skills"].pop()
            payload["skills"][1]["skill"] = payload["skills"][0]["skill"]
            payload["skills"][2]["skill"] = "invented-specialist"
            path.write_text(json.dumps(payload), encoding="utf-8")
            completed = self.run_cli("validate", str(path))
            self.assertEqual(completed.returncode, 2)
            self.assertIn("duplicate suite rows", completed.stderr)
            self.assertIn("missing current suite rows", completed.stderr)
            self.assertIn("must name a current suite skill", completed.stderr)

    def test_final_ledger_rejects_unfinished_or_blocked_lanes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path, payload = self.valid_payload(Path(temporary))
            payload["skills"][1]["state"] = "active"
            payload["skills"][1]["reason"] = "Still running."
            payload["skills"][2]["state"] = "blocked"
            payload["skills"][2]["reason"] = "Provider access is missing."
            payload["skills"][2]["blocker"] = "Verified property access is unavailable."
            path.write_text(json.dumps(payload), encoding="utf-8")
            completed = self.run_cli("validate", str(path))
            self.assertEqual(completed.returncode, 2)
            self.assertIn("final ledger cannot contain required or active lanes", completed.stderr)
            self.assertIn("completed ledger cannot contain blocked lanes", completed.stderr)

    def test_completed_blocked_and_deferred_states_require_their_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path, payload = self.valid_payload(Path(temporary))
            completed_row = payload["skills"][1]
            completed_row["state"] = "completed"
            completed_row["reason"] = "Work was performed."
            blocked_row = payload["skills"][2]
            blocked_row["state"] = "blocked"
            blocked_row["reason"] = "Access was missing."
            deferred_row = payload["skills"][3]
            deferred_row["state"] = "deferred-by-owner"
            deferred_row["reason"] = "The owner deferred this lane."
            payload["overall_state"] = "blocked"
            path.write_text(json.dumps(payload), encoding="utf-8")
            completed = self.run_cli("validate", str(path))
            self.assertEqual(completed.returncode, 2)
            self.assertIn("completed state requires evidence_refs or output_refs", completed.stderr)
            self.assertIn("blocker must be a non-empty string", completed.stderr)
            self.assertIn("owner_decision_ref must be a non-empty string", completed.stderr)

    def test_broad_final_ledger_requires_coverage_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path, payload = self.valid_payload(Path(temporary))
            payload["coverage_summary"] = ""
            path.write_text(json.dumps(payload), encoding="utf-8")
            completed = self.run_cli("validate", str(path))
            self.assertEqual(completed.returncode, 2)
            self.assertIn("requires a compact coverage_summary", completed.stderr)

    def test_references_reject_credentials_absolute_paths_and_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path, payload = self.valid_payload(Path(temporary))
            coordinator = next(row for row in payload["skills"] if row["skill"] == "seo")
            coordinator["output_refs"] = [
                "https://alice:secret@example.com/report",
                "C:/private/report.json",
                "../outside.json",
            ]
            path.write_text(json.dumps(payload), encoding="utf-8")
            completed = self.run_cli("validate", str(path))
            self.assertEqual(completed.returncode, 2)
            self.assertIn("credential-free HTTPS URL", completed.stderr)
            self.assertIn("portable relative reference", completed.stderr)
            self.assertIn("must not be empty or traverse parent directories", completed.stderr)

    def test_init_refuses_overwrite_without_explicit_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, _ = self.initialized(root)
            before = path.read_bytes()
            completed = self.run_cli(
                "init",
                "--output",
                str(path),
                "--request",
                "A second request",
                "--mode",
                "narrow",
                "--authorized-boundary",
                "Read-only answer",
            )
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(path.read_bytes(), before)
            self.assertIn("--overwrite", completed.stderr)


if __name__ == "__main__":
    unittest.main()
