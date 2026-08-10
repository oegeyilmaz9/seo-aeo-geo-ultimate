from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "scripts" / "validate_platform_controls.py"
REGISTRY = ROOT / "manifests" / "platform-controls.json"


class PlatformControlsValidatorTests(unittest.TestCase):
    def run_case(self, mutate=None, as_of: str = "2026-08-10T18:00:00Z") -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
            if mutate is not None:
                mutate(payload)
            artifact = bundle / "platform-controls.json"
            artifact.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), "validate-registry", str(artifact), "--bundle", str(bundle), "--as-of", as_of],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_current_registry_passes(self) -> None:
        completed = self.run_case()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_removed_feature_requires_effective_date(self) -> None:
        def remove_effective_date(payload: dict[str, object]) -> None:
            removed = next(
                feature
                for feature in payload["features"]
                if feature["feature_id"] == "google-faq-rich-results"
            )
            removed["effective_at"] = None

        completed = self.run_case(remove_effective_date)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("requires effective_at", completed.stderr)

    def test_removed_feature_cannot_take_effect_after_validation_time(self) -> None:
        def move_effective_date(payload: dict[str, object]) -> None:
            removed = next(
                feature
                for feature in payload["features"]
                if feature["feature_id"] == "google-faq-rich-results"
            )
            removed["effective_at"] = "2030-01-01T00:00:00Z"

        completed = self.run_case(move_effective_date)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("cannot take effect after --as-of", completed.stderr)

    def test_blanket_crawler_wildcard_fails(self) -> None:
        completed = self.run_case(lambda payload: payload["crawlers"][0].update({"user_agent": "*"}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("wildcard", completed.stderr)

    def test_expired_registry_fails(self) -> None:
        completed = self.run_case(as_of="2026-10-10T18:00:00Z")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("past review_due_at", completed.stderr)

    def test_backdated_validation_cannot_use_future_registry_evidence(self) -> None:
        completed = self.run_case(as_of="2026-08-01T23:59:59Z")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("after --as-of", completed.stderr)

    def test_feature_affected_skills_must_resolve(self) -> None:
        completed = self.run_case(
            lambda payload: payload["features"][0]["affected_skills"].append("seo-does-not-exist")
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unknown suite skills", completed.stderr)


if __name__ == "__main__":
    unittest.main()
