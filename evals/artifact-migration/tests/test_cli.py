from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "scripts" / "migrate_artifact.py"
AI_EXAMPLE = ROOT / "examples" / "ai-search-handoff"
CONVENTIONAL_EXAMPLE = ROOT / "examples" / "conventional-seo-handoff"
LEGACY_AEO_FIXTURE = ROOT / "evals" / "fixtures" / "aeo-normal"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def legacy_action_plan(bundle: Path) -> Path:
    input_bundle = bundle / "inputs" / "conventional"
    shutil.copytree(CONVENTIONAL_EXAMPLE, input_bundle)
    findings_path = input_bundle / "seo-findings.json"
    findings = json.loads(findings_path.read_text(encoding="utf-8"))
    findings["schema_version"] = "1.0.0"
    findings["evidence"][0].pop("raw_evidence_sha256", None)
    write_json(findings_path, findings)
    plan = {
        "schema_version": "1.1.0",
        "plan_id": "example-legacy-action-plan",
        "created_at": "2026-08-08T13:00:00Z",
        "producer_skill": "seo-action-plan",
        "input_findings": [
            {
                "finding_set_id": findings["finding_set_id"],
                "schema_version": findings["schema_version"],
                "producer_skill": findings["producer_skill"],
                "bundle_ref": "inputs/conventional",
                "artifact_ref": "inputs/conventional/seo-findings.json",
                "artifact_sha256": sha256(findings_path),
            }
        ],
        "scope": {
            "objective": "Prepare the captured title-delivery correction for explicit review.",
            "target_ids": ["example-homepage"],
            "locales": ["en-US"],
        },
        "actions": [
            {
                "action_id": "add-example-homepage-title",
                "title": "Add an approved descriptive title to the rendered homepage",
                "finding_refs": [
                    {
                        "finding_set_id": findings["finding_set_id"],
                        "finding_id": "homepage-title-missing",
                    }
                ],
                "evidence_refs": [
                    {
                        "finding_set_id": findings["finding_set_id"],
                        "artifact_type": "seo-findings",
                        "collection": "evidence",
                        "record_id": "homepage-title-observation",
                    }
                ],
                "change_type": "technical",
                "owner": {"team": "Engineering", "role": "web developer", "approval_role": "engineering lead"},
                "approval": {"required": True, "status": "pending"},
                "priority": "now",
                "risk": "low",
                "effort": "small",
                "confidence": "high",
                "rationale": "The requested correction is bound to one immutable page capture.",
                "execution_outline": ["Implement the approved title in the rendered document."],
                "acceptance_criteria": ["A fresh capture contains one approved descriptive title."],
                "verification": {
                    "method": "Recapture the rendered page and review the title.",
                    "metric_type": "recrawl",
                    "success_condition": "The approved title is present once.",
                    "guardrail": "Reject unsupported ranking or traffic claims.",
                },
                "rollback": {"required": True, "method": "Restore the previously approved title."},
                "dependencies": [],
                "claim_boundary": {
                    "statement": "This corrects a captured delivery issue and does not guarantee a search outcome.",
                    "no_guarantee": True,
                },
            }
        ],
        "declined_actions": [],
        "limitations": ["Human approval is required before implementation."],
    }
    path = bundle / "action-plan-legacy.json"
    write_json(path, plan)
    return path


class ArtifactMigrationTests(unittest.TestCase):
    def run_cli(self, *arguments: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *(str(argument) for argument in arguments)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_paths_disclose_automatic_and_manual_only_migrations(self) -> None:
        completed = self.run_cli("--json", "paths")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("1.0.0->1.1.0", payload["automatic"]["research-pack"])
        self.assertIn("1.0.0/1.1.0->1.2.0", payload["manual_only"]["action-plan"]["path"])
        self.assertIn("risk_flags", payload["manual_only"]["action-plan"]["reason"])
        self.assertIn("cannot be inferred safely", payload["manual_only"]["visibility-run"]["reason"])

    def test_research_pack_migration_hashes_raw_inputs_and_preserves_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(AI_EXAMPLE, bundle)
            source = bundle / "research-pack-legacy.json"
            payload = json.loads((bundle / "research-pack.json").read_text(encoding="utf-8"))
            payload["schema_version"] = "1.0.0"
            for record in payload["evidence"]:
                record.pop("raw_evidence_sha256", None)
            for record in payload["competitor_observations"]:
                record.pop("raw_observation_sha256", None)
            for record in payload["ground_truth"]:
                record.pop("provenance_sha256", None)
            write_json(source, payload)
            before = source.read_bytes()
            completed = self.run_cli(
                "migrate", source, "--bundle", bundle, "--as-of", "2026-08-10T00:00:00Z"
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            destination = bundle / "research-pack-legacy.v1.1.0.json"
            migrated = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(migrated["schema_version"], "1.1.0")
            self.assertEqual(migrated["evidence"][0]["raw_evidence_sha256"], sha256(bundle / "raw/research-source.json"))
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(list(bundle.glob(".*.tmp")), [])

    def test_findings_migration_infers_unique_target_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(CONVENTIONAL_EXAMPLE, bundle)
            source = bundle / "seo-findings-legacy.json"
            payload = json.loads((bundle / "seo-findings.json").read_text(encoding="utf-8"))
            payload["schema_version"] = "1.0.0"
            payload["evidence"][0].pop("raw_evidence_sha256", None)
            payload["evidence"][0].pop("target_id", None)
            write_json(source, payload)
            completed = self.run_cli("migrate", source, "--bundle", bundle)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            migrated = json.loads((bundle / "seo-findings-legacy.v1.1.0.json").read_text(encoding="utf-8"))
            self.assertEqual(migrated["evidence"][0]["target_id"], "example-homepage")
            self.assertEqual(migrated["evidence"][0]["raw_evidence_sha256"], sha256(bundle / "raw/homepage.html"))

    def test_brief_migration_updates_self_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(AI_EXAMPLE, bundle)
            source = bundle / "optimization-brief-legacy.json"
            payload = json.loads((bundle / "optimization-brief-aeo.json").read_text(encoding="utf-8"))
            payload["schema_version"] = "1.0.0"
            for collection in ("findings", "recommendations"):
                for item in payload[collection]:
                    for reference in item["evidence_refs"]:
                        if reference["artifact_type"] == "optimization-brief":
                            reference["schema_version"] = "1.0.0"
            write_json(source, payload)
            completed = self.run_cli("migrate", source, "--bundle", bundle)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            migrated = json.loads((bundle / "optimization-brief-legacy.v1.1.0.json").read_text(encoding="utf-8"))
            self.assertEqual(migrated["schema_version"], "1.1.0")
            self.assertTrue(
                all(
                    reference["schema_version"] == "1.1.0"
                    for item in migrated["findings"] + migrated["recommendations"]
                    for reference in item["evidence_refs"]
                    if reference["artifact_type"] == "optimization-brief"
                )
            )

    def test_action_plan_with_actions_requires_manual_current_risk_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            bundle.mkdir()
            source = legacy_action_plan(bundle)
            completed = self.run_cli("migrate", source, "--bundle", bundle)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("manual-only", completed.stderr)
            self.assertIn("risk_flags", completed.stderr)
            self.assertFalse((bundle / "action-plan-legacy.v1.2.0.json").exists())

    def test_declined_only_action_plan_still_requires_manual_current_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(LEGACY_AEO_FIXTURE, bundle)
            brief = json.loads((bundle / "optimization-brief.json").read_text(encoding="utf-8"))
            self.assertEqual(brief["schema_version"], "1.0.0")
            plan = {
                "schema_version": "1.0.0",
                "plan_id": "example-declined-legacy-plan",
                "created_at": "2026-07-10T23:40:00Z",
                "producer_skill": "seo-action-plan",
                "input_briefs": [
                    {
                        "brief_id": brief["brief_id"],
                        "schema_version": brief["schema_version"],
                        "producer_skill": brief["producer_skill"],
                        "optimization_domain": brief["optimization_domain"],
                        "bundle_ref": ".",
                        "artifact_ref": "optimization-brief.json",
                        "artifact_sha256": sha256(bundle / "optimization-brief.json"),
                    }
                ],
                "scope": {
                    "objective": "Record why an unsupported guaranteed-outcome request was declined.",
                    "target_ids": ["homepage-tr"],
                    "locales": ["tr-TR"],
                },
                "actions": [],
                "declined_actions": [
                    {
                        "declined_id": "decline-ranking-guarantee",
                        "request": "Guarantee ranking from the proposed content change.",
                        "reason": "The supplied evidence does not establish a guaranteed search outcome.",
                        "revisit_when": "Never as a guarantee; evaluate observed outcomes separately.",
                    }
                ],
                "limitations": ["No implementation action is authorized by this declined-only plan."],
            }
            source = bundle / "action-plan-v1.json"
            write_json(source, plan)
            completed = self.run_cli("migrate", source, "--bundle", bundle)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("manual-only", completed.stderr)
            self.assertFalse((bundle / "action-plan-v1.v1.2.0.json").exists())

    def test_visibility_v2_evidence_is_never_fabricated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(AI_EXAMPLE, bundle)
            source = bundle / "visibility-legacy.json"
            payload = json.loads((bundle / "visibility-run.json").read_text(encoding="utf-8"))
            payload["schema_version"] = "1.0.0"
            write_json(source, payload)
            completed = self.run_cli("migrate", source, "--bundle", bundle)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("manual-only", completed.stderr)
            self.assertFalse((bundle / "visibility-legacy.v2.0.0.json").exists())

    def test_existing_destination_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(CONVENTIONAL_EXAMPLE, bundle)
            source = bundle / "seo-findings-legacy.json"
            payload = json.loads((bundle / "seo-findings.json").read_text(encoding="utf-8"))
            payload["schema_version"] = "1.0.0"
            write_json(source, payload)
            destination = bundle / "seo-findings-legacy.v1.1.0.json"
            destination.write_text("user-owned\n", encoding="utf-8")
            completed = self.run_cli("migrate", source, "--bundle", bundle)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("refusing to overwrite", completed.stderr)
            self.assertEqual(destination.read_text(encoding="utf-8"), "user-owned\n")

    def test_source_cannot_be_used_as_destination_even_with_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(CONVENTIONAL_EXAMPLE, bundle)
            source = bundle / "seo-findings-legacy.json"
            payload = json.loads((bundle / "seo-findings.json").read_text(encoding="utf-8"))
            payload["schema_version"] = "1.0.0"
            write_json(source, payload)
            before = source.read_bytes()
            completed = self.run_cli(
                "migrate", source, "--bundle", bundle, "--out", source, "--overwrite"
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("must differ from the immutable source", completed.stderr)
            self.assertEqual(source.read_bytes(), before)

    def test_non_regular_destination_is_rejected_even_with_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(CONVENTIONAL_EXAMPLE, bundle)
            source = bundle / "seo-findings-legacy.json"
            payload = json.loads((bundle / "seo-findings.json").read_text(encoding="utf-8"))
            payload["schema_version"] = "1.0.0"
            write_json(source, payload)
            destination = bundle / "directory-output.json"
            destination.mkdir()
            completed = self.run_cli(
                "migrate", source, "--bundle", bundle, "--out", destination, "--overwrite"
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("destination is a directory", completed.stderr)
            self.assertTrue(destination.is_dir())

    def test_symlink_destination_is_rejected_even_with_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(CONVENTIONAL_EXAMPLE, bundle)
            source = bundle / "seo-findings-legacy.json"
            payload = json.loads((bundle / "seo-findings.json").read_text(encoding="utf-8"))
            payload["schema_version"] = "1.0.0"
            write_json(source, payload)
            target = bundle / "target.json"
            target.write_text("user-owned\n", encoding="utf-8")
            link = bundle / "linked-output.json"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            completed = self.run_cli(
                "migrate", source, "--bundle", bundle, "--out", link, "--overwrite"
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("reparse", completed.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "user-owned\n")

    def test_malformed_legacy_collections_fail_without_traceback_or_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(AI_EXAMPLE, bundle)
            source = bundle / "research-pack-malformed.json"
            payload = json.loads((bundle / "research-pack.json").read_text(encoding="utf-8"))
            payload["schema_version"] = "1.0.0"
            payload["evidence"] = None
            write_json(source, payload)
            completed = self.run_cli(
                "migrate", source, "--bundle", bundle, "--as-of", "2026-08-10T00:00:00Z"
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("evidence must be an array", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)
            self.assertFalse((bundle / "research-pack-malformed.v1.1.0.json").exists())


if __name__ == "__main__":
    unittest.main()
