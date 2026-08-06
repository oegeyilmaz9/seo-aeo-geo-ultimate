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
PYTHON = sys.executable
VALIDATOR = ROOT / "scripts" / "validate_seo_action_plan.py"
UPSTREAM_BUNDLE = ROOT / "evals" / "fixtures" / "aeo-normal"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_plan(bundle: Path) -> dict:
    brief = json.loads((bundle / "optimization-brief.json").read_text(encoding="utf-8"))
    return {
        "schema_version": "1.0.0",
        "plan_id": "example-action-plan",
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
            "objective": "Make the supported availability answer reviewable on the tr-TR page.",
            "target_ids": ["homepage-tr"],
            "locales": ["tr-TR"],
        },
        "actions": [
            {
                "action_id": "add-supported-availability-answer",
                "title": "Add the approved availability answer to the visible page",
                "finding_refs": [{"brief_id": brief["brief_id"], "finding_id": "availability-answer-missing"}],
                "evidence_refs": [
                    {
                        "brief_id": brief["brief_id"],
                        "artifact_type": "optimization-brief",
                        "collection": "audit_evidence",
                        "record_id": "homepage-tr-answer-observation",
                    }
                ],
                "change_type": "content",
                "owner": {"team": "Content", "role": "editor", "approval_role": "content lead"},
                "approval": {"required": True, "status": "pending"},
                "priority": "now",
                "risk": "low",
                "effort": "small",
                "confidence": "high",
                "rationale": "The captured page lacks a direct answer to the supported availability question.",
                "execution_outline": [
                    "Draft a concise visible answer using only the pinned supported fact.",
                    "Do not add a broad availability, citation, or ranking claim beyond the evidence scope.",
                ],
                "acceptance_criteria": [
                    "A reviewer can find the supported answer in the rendered tr-TR page.",
                    "The answer scope matches the pinned source and does not introduce a new claim.",
                ],
                "verification": {
                    "method": "Recapture the rendered page and have a content reviewer compare it with the pinned fact.",
                    "metric_type": "manual-review",
                    "success_condition": "The visible answer is present and factually aligned with the approved source.",
                    "guardrail": "Reject the change if it adds an unsupported availability or performance claim.",
                },
                "rollback": {"required": True, "method": "Restore the previously approved page copy."},
                "dependencies": [],
                "claim_boundary": {
                    "statement": "This improves direct-answer completeness only; it does not guarantee retrieval, citation, ranking, traffic, or conversion.",
                    "no_guarantee": True,
                },
            }
        ],
        "declined_actions": [],
        "limitations": [
            "The plan is based on the supplied point-in-time capture and requires human approval before publication."
        ],
    }


def base_standard_findings() -> dict:
    return {
        "schema_version": "1.0.0",
        "finding_set_id": "homepage-technical-findings",
        "created_at": "2026-07-10T23:30:00Z",
        "producer_skill": "seo-technical",
        "scope": {
            "objective": "Record a reviewable title delivery observation for the Turkish homepage.",
            "targets": [
                {
                    "target_id": "homepage-tr",
                    "target_type": "web_page",
                    "locale": "tr-TR",
                    "source_url": "https://example.test/tr",
                }
            ],
        },
        "evidence": [
            {
                "claim_id": "homepage-title-observation",
                "claim": "The rendered Turkish homepage has no descriptive title element.",
                "classification": "confirmed",
                "source_kind": "direct_observation",
                "engine": "not_applicable",
                "surface": "rendered-page",
                "locale": "tr-TR",
                "source_title": "Turkish homepage capture",
                "source_url": "https://example.test/tr",
                "source_published_or_updated_at": None,
                "accessed_at": "2026-07-10T23:20:00Z",
                "raw_evidence_ref": "raw/homepage-tr.html",
                "observation_method": "Rendered page capture reviewed by an analyst.",
                "limitations": ["The capture is point in time and does not establish indexing or ranking."],
            }
        ],
        "findings": [
            {
                "finding_id": "homepage-title-missing",
                "target_id": "homepage-tr",
                "title": "The rendered homepage title is missing",
                "observation": "The captured HTML contains no descriptive title element.",
                "category": "technical",
                "classification": "confirmed",
                "severity": "important",
                "evidence_ids": ["homepage-title-observation"],
                "candidate_owner": "seo-technical",
                "desired_outcome": "Deliver one accurate, descriptive title in the rendered document.",
                "verification_method": "Recapture the rendered page and compare its title to the approved content brief.",
                "limitations": ["A title correction does not guarantee indexing, ranking, or traffic."],
            }
        ],
        "declined_claims": [],
        "limitations": ["The finding is limited to the supplied rendered capture."],
    }


class SeoActionPlanValidatorTests(unittest.TestCase):
    def run_plan(self, mutator=None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(UPSTREAM_BUNDLE, bundle)
            plan = base_plan(bundle)
            if mutator:
                mutator(plan)
            artifact = bundle / "action-plan.json"
            artifact.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
            return subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-plan", str(artifact), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )

    def run_standard_findings_plan(self, mutator=None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            input_bundle = bundle / "inputs" / "technical-homepage"
            raw = input_bundle / "raw"
            raw.mkdir(parents=True)
            (raw / "homepage-tr.html").write_text("<html><head></head><body>Example</body></html>", encoding="utf-8")
            finding_artifact = input_bundle / "seo-findings.json"
            finding_artifact.write_text(json.dumps(base_standard_findings(), indent=2) + "\n", encoding="utf-8")
            plan = {
                "schema_version": "1.1.0",
                "plan_id": "technical-action-plan",
                "created_at": "2026-07-10T23:40:00Z",
                "producer_skill": "seo-action-plan",
                "input_findings": [
                    {
                        "finding_set_id": "homepage-technical-findings",
                        "schema_version": "1.0.0",
                        "producer_skill": "seo-technical",
                        "bundle_ref": "inputs/technical-homepage",
                        "artifact_ref": "inputs/technical-homepage/seo-findings.json",
                        "artifact_sha256": sha256(finding_artifact),
                    }
                ],
                "scope": {
                    "objective": "Make rendered title delivery reviewable on the Turkish homepage.",
                    "target_ids": ["homepage-tr"],
                    "locales": ["tr-TR"],
                },
                "actions": [
                    {
                        "action_id": "add-homepage-title",
                        "title": "Add an approved descriptive title to the rendered homepage",
                        "finding_refs": [{"finding_set_id": "homepage-technical-findings", "finding_id": "homepage-title-missing"}],
                        "evidence_refs": [
                            {
                                "finding_set_id": "homepage-technical-findings",
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
                        "rationale": "The finding is tied to a reviewed rendered capture and can be verified by recapture.",
                        "execution_outline": [
                            "Implement the approved descriptive title in the rendering path.",
                            "Do not add an indexing, ranking, citation, or traffic claim.",
                        ],
                        "acceptance_criteria": [
                            "A fresh rendered capture has one accurate descriptive title.",
                            "The title remains aligned with the approved content brief.",
                        ],
                        "verification": {
                            "method": "Recapture the rendered page and have an engineering reviewer compare the title with the approved brief.",
                            "metric_type": "recrawl",
                            "success_condition": "The expected title is present in the rendered document.",
                            "guardrail": "Reject the change if the deployed title adds an unsupported business or performance claim.",
                        },
                        "rollback": {"required": True, "method": "Restore the previously approved title."},
                        "dependencies": [],
                        "claim_boundary": {
                            "statement": "This corrects a captured delivery issue only; it does not guarantee indexing, ranking, citation, traffic, or conversion.",
                            "no_guarantee": True,
                        },
                    }
                ],
                "declined_actions": [],
                "limitations": ["The plan requires human approval before deployment."],
            }
            if mutator:
                mutator(plan)
            artifact = bundle / "action-plan.json"
            artifact.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
            return subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-plan", str(artifact), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_valid_plan_passes_and_revalidates_input_bundle(self) -> None:
        completed = self.run_plan()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS: seo-action-plan", completed.stdout)

    def test_standard_seo_findings_can_drive_a_formal_plan(self) -> None:
        completed = self.run_standard_findings_plan()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS: seo-action-plan", completed.stdout)

    def test_standard_seo_findings_require_action_plan_v1_1(self) -> None:
        completed = self.run_standard_findings_plan(lambda plan: plan.update({"schema_version": "1.0.0"}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("schema_version", completed.stderr)

    def test_input_hash_drift_fails(self) -> None:
        completed = self.run_plan(lambda plan: plan["input_briefs"][0].update({"artifact_sha256": "0" * 64}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("artifact_sha256 does not match", completed.stderr)

    def test_plan_artifact_cannot_live_outside_declared_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            shutil.copytree(UPSTREAM_BUNDLE, bundle)
            outside = root / "action-plan.json"
            outside.write_text(json.dumps(base_plan(bundle), indent=2) + "\n", encoding="utf-8")
            completed = subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-plan", str(outside), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("artifact must be inside --bundle", completed.stderr)

    def test_unresolved_finding_fails(self) -> None:
        def mutate(plan: dict) -> None:
            plan["actions"][0]["finding_refs"][0]["finding_id"] = "missing-finding"

        completed = self.run_plan(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("finding_refs[0] does not resolve", completed.stderr)

    def test_disconnected_evidence_fails(self) -> None:
        def mutate(plan: dict) -> None:
            plan["actions"][0]["evidence_refs"][0]["record_id"] = "missing-evidence"

        completed = self.run_plan(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("record does not resolve", completed.stderr)

    def test_planner_cannot_own_implementation(self) -> None:
        def mutate(plan: dict) -> None:
            plan["actions"][0]["owner"]["team"] = "SEO Action Plan"

        completed = self.run_plan(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("cannot assign implementation", completed.stderr)

    def test_high_risk_requires_rollback(self) -> None:
        def mutate(plan: dict) -> None:
            plan["actions"][0]["risk"] = "high"
            plan["actions"][0]["rollback"]["required"] = False

        completed = self.run_plan(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("high-risk changes require", completed.stderr)

    def test_skill_contract_passes(self) -> None:
        completed = subprocess.run(
            [PYTHON, str(VALIDATOR), "validate-skill"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
