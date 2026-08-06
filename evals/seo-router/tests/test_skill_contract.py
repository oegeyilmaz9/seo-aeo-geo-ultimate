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
        self.assertIn("route", match.group(1).lower())
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
        self.assertIn("default front door for every request", text)
        self.assertIn("Directly invoking that specialist remains available", text)
        self.assertIn("default entry point", interface)
        self.assertIn("recommended first call for any SEO, AEO, GEO, or AI-search request", matrix)
        self.assertIn("Optional `llms.txt` suitability", matrix)

    def test_mixed_work_is_phased_and_myths_are_not_router_defaults(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for phrase in ("research -> audit -> baseline measurement -> action planning -> approved implementation -> comparison measurement", "Do not create a universal SEO score", "mandatory `llms.txt`", "guarantee"):
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

    def test_contract_lock_binds_research_pack_only(self):
        lock = json.loads((SKILL / "references" / "contracts" / "contracts-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(len(lock["contracts"]), 1)
        row = lock["contracts"][0]
        self.assertTrue(row["generated_path"].endswith("research-pack.schema.json"))
        canonical = ROOT / row["canonical_path"]
        generated = SKILL / row["generated_path"]
        self.assertEqual(canonical.read_bytes(), generated.read_bytes())
        self.assertEqual(hashlib.sha256(canonical.read_bytes()).hexdigest(), row["canonical_sha256"])


if __name__ == "__main__":
    unittest.main()
