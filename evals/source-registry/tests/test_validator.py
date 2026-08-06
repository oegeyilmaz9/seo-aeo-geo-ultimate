from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PYTHON = sys.executable
VALIDATOR = ROOT / "scripts" / "validate_source_registry.py"
REGISTRY = ROOT / "docs" / "research" / "2026-08-06-source-registry.json"


class SourceRegistryValidatorTests(unittest.TestCase):
    def load_registry(self) -> dict:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))

    def run_validator(self, payload: dict, *extra: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                [PYTHON, str(VALIDATOR), str(path), "--as-of", "2026-08-06", *extra],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_current_registry_passes(self) -> None:
        completed = subprocess.run(
            [
                PYTHON,
                str(VALIDATOR),
                str(REGISTRY),
                "--as-of",
                "2026-08-06",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["checked_sources"], 26)

    def test_stale_source_fails_by_default(self) -> None:
        payload = self.load_registry()
        payload["sources"][0]["updated_at"] = "2026-05-01"
        payload["sources"][0]["observed_at"] = "2026-06-01"
        completed = self.run_validator(payload)
        self.assertEqual(completed.returncode, 2)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["stale_sources"], 1)

    def test_stale_source_can_be_reported_as_warning(self) -> None:
        payload = self.load_registry()
        payload["sources"][0]["updated_at"] = "2026-05-01"
        payload["sources"][0]["observed_at"] = "2026-06-01"
        completed = self.run_validator(payload, "--allow-stale")
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["stale_sources"], 1)
        self.assertEqual(len(result["warnings"]), 1)

    def test_non_https_source_fails(self) -> None:
        payload = self.load_registry()
        payload["sources"][0]["url"] = "http://example.com/source"
        completed = self.run_validator(payload)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("HTTPS URL", completed.stdout)


if __name__ == "__main__":
    unittest.main()
