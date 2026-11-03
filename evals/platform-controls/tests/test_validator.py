from __future__ import annotations

import json
import datetime as dt
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "scripts" / "validate_platform_controls.py"
REGISTRY = ROOT / "manifests" / "platform-controls.json"


class PlatformControlsValidatorTests(unittest.TestCase):
    def run_case(self, mutate=None, as_of: str | None = None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
            if as_of is None:
                as_of = payload["created_at"][:10] + "T23:59:59Z"
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
        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
        expired = dt.datetime.fromisoformat(payload["review_due_at"].replace("Z", "+00:00")) + dt.timedelta(days=1)
        completed = self.run_case(as_of=expired.isoformat())
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("past review_due_at", completed.stderr)

    def test_extending_review_deadline_does_not_refresh_old_entries(self) -> None:
        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
        future = dt.datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00")) + dt.timedelta(days=46)
        completed = self.run_case(
            lambda row: row.update(review_due_at=(future + dt.timedelta(days=30)).isoformat()),
            as_of=future.isoformat(),
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("verification is older than 45 days", completed.stderr)
        self.assertNotIn("past review_due_at", completed.stderr)

    def test_active_openai_controls_use_crawler_sources_and_independent_purposes(self) -> None:
        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
        controls = {row["control_id"]: row for row in payload["crawlers"]}
        for control_id, agent, purpose, ip in (
            ("openai-searchbot", "OAI-SearchBot", "ai-search", "searchbot"),
            ("openai-gptbot", "GPTBot", "training", "gptbot"),
        ):
            with self.subTest(control_id=control_id):
                row = controls[control_id]
                self.assertEqual((row["user_agent"], row["purpose"]), (agent, purpose))
                self.assertEqual(row["documentation_url"], "https://developers.openai.com/api/docs/bots")
                self.assertEqual(row["published_ip_source_url"], f"https://openai.com/{ip}.json")
                self.assertEqual(row["business_decision"], "undecided")
        self.assertIn("navigational links", " ".join(controls["openai-searchbot"]["limitations"]))

    def test_google_visibility_is_a_feature_with_rollout_distinct_from_source_update(self) -> None:
        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
        feature = next(row for row in payload["features"] if row["feature_id"] == "google-search-generative-ai-control")
        self.assertEqual(feature["documentation_url"], "https://support.google.com/webmasters/answer/16908024")
        self.assertEqual(feature["status"], "current")
        self.assertEqual(feature["effective_at"][:10], "2026-08-31")
        self.assertTrue({"search-console", "google-search-ai-overviews", "google-search-ai-mode", "google-discover-generative-ai"} <= set(feature["surfaces"]))
        self.assertFalse(any(row["control_id"] == feature["feature_id"] for row in payload["crawlers"]))
        manifest = json.loads((ROOT / "manifests/suite.json").read_text(encoding="utf-8"))
        sources = json.loads((ROOT / manifest["source_registry"]).read_text(encoding="utf-8"))["sources"]
        sharing = next(row for row in sources if row["id"] == "google-control-what-you-share")
        self.assertEqual(sharing["updated_at"], "2026-10-21")
        self.assertNotEqual(sharing["updated_at"], feature["effective_at"][:10])

    def test_every_active_control_source_is_in_the_reviewed_source_registry(self) -> None:
        manifest = json.loads((ROOT / "manifests/suite.json").read_text(encoding="utf-8"))
        sources = json.loads((ROOT / manifest["source_registry"]).read_text(encoding="utf-8"))["sources"]
        urls = {row["url"] for row in sources}
        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
        for group in ("features", "crawlers", "change_notifications", "protocol_capabilities"):
            for row in payload[group]:
                with self.subTest(group=group, url=row["documentation_url"]):
                    self.assertIn(row["documentation_url"], urls)
                    if row.get("published_ip_source_url"):
                        self.assertIn(row["published_ip_source_url"], urls)

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
