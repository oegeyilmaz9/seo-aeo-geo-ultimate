import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "seo"
MANIFEST = ROOT / "manifests" / "suite.json"


class SeoRouterSkillContractTests(unittest.TestCase):
    def test_frontmatter_is_router_specific(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        self.assertIsNotNone(match)
        keys = [line.split(":", 1)[0] for line in match.group(1).splitlines() if re.match(r"^[a-z_]+:", line)]
        self.assertEqual(keys, ["name", "description"])
        self.assertIn("orchestrator", match.group(1).lower())
        self.assertNotIn("TODO", text)

    def test_routes_every_declared_specialist_skill(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        specialists = set(manifest["skills"]) - {"seo"}
        self.assertTrue(specialists)
        for name in sorted(specialists):
            self.assertIn(name, text)

    def test_router_is_the_default_entry_point_without_hiding_specialists(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        interface = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
        matrix = (SKILL / "references" / "routing-matrix.md").read_text(encoding="utf-8")
        self.assertIn("default front door and user-facing owner for every request", text)
        self.assertIn("Directly invoking that specialist remains available", text)
        self.assertIn("screen all 27 skills", interface)
        self.assertIn("recommended first call and user-facing owner for any SEO, AEO, GEO, or AI-search request", matrix)
        self.assertIn("Optional `llms.txt` suitability", matrix)

    def test_router_owns_complete_coverage_without_user_coordination(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        contract = (SKILL / "references" / "autonomous-orchestration-contract.md").read_text(encoding="utf-8")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertIn("autonomous-orchestration-contract.md", text)
        self.assertIn("Never ask the user to choose a specialist, artifact, schema, validator, or phase order", text)
        self.assertIn("The router—not the user—invokes or performs the next specialist workflow", text)
        self.assertIn("one consolidated outcome", text)
        self.assertIn("Screening every capability is mandatory; executing every capability is not", contract)
        self.assertIn("The user must not be asked to invoke the next specialist manually", contract)
        self.assertIn("Do not dump 27 disconnected reports", contract)

        table_skills = {
            match.group(1)
            for line in contract.splitlines()
            if (match := re.match(r"^\|[^|]+\| `([^`]+)` \|", line))
        }
        self.assertEqual(table_skills, set(manifest["skills"]))

    def test_router_coverage_states_and_completion_bar_are_explicit(self):
        contract = (SKILL / "references" / "autonomous-orchestration-contract.md").read_text(encoding="utf-8")
        for state in ("`required`", "`active`", "`completed`", "`not-applicable`", "`blocked`", "`deferred-by-owner`"):
            self.assertIn(state, contract)
        for marker in (
            "Discover before asking",
            "Build the coverage ledger",
            "Load specialist instructions internally",
            "Execute and relay",
            "Continue to the authorized boundary",
            "Routing to a specialist is not completion",
            "A partial lane result cannot silently narrow an explicit end-to-end request",
        ):
            self.assertIn(marker, contract)

    def test_router_can_consume_every_formal_suite_artifact(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["skills"]["seo"]["consumes"]), set(manifest["schemas"]))

    def test_broad_coverage_is_manifest_derived_and_executable(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        contract = (SKILL / "references" / "autonomous-orchestration-contract.md").read_text(encoding="utf-8")
        documentation = (ROOT / "docs" / "AUTONOMOUS-ORCHESTRATION.md").read_text(encoding="utf-8")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["tools"]["orchestration-ledger"]["path"], "scripts/manage_orchestration_ledger.py")
        self.assertIn("manage_orchestration_ledger.py", text)
        self.assertIn("Do not expose this internal bookkeeping as user homework", text)
        self.assertIn("manifest-derived initializer and validator", contract)
        self.assertIn("missing, duplicate, invented, or unfinished lanes", documentation)

    def test_mixed_work_is_phased_and_myths_are_not_router_defaults(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for phrase in ("research -> audit -> baseline measurement -> product-owner decision -> action planning -> authorized implementation -> local acceptance -> authorized release -> live delivery verification -> authorized provider operation -> delayed outcome follow-up", "Do not create a universal SEO score", "mandatory `llms.txt`", "guarantee"):
            self.assertIn(phrase, text)

    def test_answer_audit_is_distinct_from_rewrite_implementation(self):
        text = (SKILL / "references" / "routing-matrix.md").read_text(encoding="utf-8")
        self.assertIn("Audit answer readiness", text)
        self.assertIn("Rewrite or implement an answer change", text)
        self.assertIn("validated AEO finding", text)
        self.assertIn("Validated Action Plan item", text)
        for owner in ("seo-content", "seo-schema", "seo-technical", "seo-hreflang", "optimise-seo"):
            self.assertIn(owner, text)

    def test_research_handoff_distinguishes_aeo_from_geo(self):
        text = (ROOT / "skills" / "ai-search-research" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("direct-answer completeness", text)
        self.assertIn("audits to `seo-aeo`", text)
        self.assertIn("citation, and documented engine-control audits to `seo-geo`", text)

    def test_contract_lock_binds_router_handoff_artifacts(self):
        lock = json.loads((SKILL / "references" / "contracts" / "contracts-lock.json").read_text(encoding="utf-8"))
        expected = {
            "evidence-record.schema.json",
            "research-pack.schema.json",
            "query-corpus.schema.json",
            "optimization-brief.schema.json",
            "visibility-run.schema.json",
            "seo-performance-run.schema.json",
            "site-graph.schema.json",
            "platform-controls.schema.json",
            "seo-findings.schema.json",
            "action-plan.schema.json",
            "provider-operation-receipt.schema.json",
        }
        self.assertEqual({Path(row["generated_path"]).name for row in lock["contracts"]}, expected)
        for row in lock["contracts"]:
            canonical = ROOT / row["canonical_path"]
            generated = SKILL / row["generated_path"]
            self.assertEqual(canonical.read_bytes(), generated.read_bytes())
            self.assertEqual(hashlib.sha256(canonical.read_bytes()).hexdigest(), row["canonical_sha256"])


if __name__ == "__main__":
    unittest.main()
