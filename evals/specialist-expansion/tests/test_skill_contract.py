from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILLS = ROOT / "skills"


class SpecialistExpansionContractTests(unittest.TestCase):
    def test_new_specialists_are_packaged_and_formally_handoff_findings(self) -> None:
        manifest = json.loads((ROOT / "manifests" / "suite.json").read_text(encoding="utf-8"))
        markers = {
            "seo-agentic": ("task_flow", "agentic"),
            "seo-architecture": ("site_graph", "architecture"),
            "seo-authority": ("backlink_profile", "authority"),
            "seo-commerce": ("feed", "commerce"),
            "seo-local": ("business_profile", "local"),
            "seo-news-discover": ("news_property", "news-discover"),
            "seo-video": ("video", "video"),
        }
        for skill, (target, category) in markers.items():
            with self.subTest(skill=skill):
                text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
                interface = (SKILLS / skill / "agents" / "openai.yaml").read_text(encoding="utf-8")
                self.assertRegex(text, rf"^---\nname: {re.escape(skill)}\n", skill)
                self.assertIn("SEO Findings `1.1.0`", text)
                self.assertIn(f"`{target}`", text)
                self.assertIn(f"`{category}`", text)
                self.assertIn("${CLAUDE_PLUGIN_ROOT}", text)
                self.assertRegex(text, r'validate_seo_findings\.py"? validate-findings')
                self.assertIn(f"${skill}", interface)
                self.assertIn("seo-findings", manifest["skills"][skill]["produces"])

    def test_measurement_and_architecture_commands_match_the_validator_clis(self) -> None:
        performance = (SKILLS / "seo-performance" / "SKILL.md").read_text(encoding="utf-8")
        architecture = (SKILLS / "seo-architecture" / "SKILL.md").read_text(encoding="utf-8")
        query_protocol = (ROOT / "docs" / "QUERY-CORPUS-PROTOCOL.md").read_text(encoding="utf-8")
        controls = (ROOT / "docs" / "PLATFORM-CONTROLS.md").read_text(encoding="utf-8")
        self.assertRegex(performance, r"validate_seo_performance\.py\"? validate-run")
        self.assertRegex(architecture, r"validate_site_graph\.py\"? validate-graph")
        self.assertIn("validate_query_corpus.py validate-corpus", query_protocol)
        self.assertIn("validate_platform_controls.py validate-registry", controls)

    def test_performance_stays_separate_from_ai_visibility(self) -> None:
        performance = (SKILLS / "seo-performance" / "SKILL.md").read_text(encoding="utf-8")
        router = (SKILLS / "seo" / "SKILL.md").read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "manifests" / "suite.json").read_text(encoding="utf-8"))
        self.assertIn("never merge the two reports into one score", performance)
        self.assertIn("Use `seo-performance` for conventional first-party search/site metrics", router)
        self.assertEqual(
            manifest["skills"]["seo-performance"]["produces"],
            ["seo-performance-run", "provider-operation-receipt"],
        )
        self.assertNotIn("visibility-run", manifest["skills"]["seo-performance"]["produces"])
        self.assertEqual(manifest["skills"]["ai-visibility-monitor"]["produces"], ["visibility-run"])

    def test_skill_validator_commands_are_not_cwd_relative(self) -> None:
        for skill_path in SKILLS.glob("*/SKILL.md"):
            text = skill_path.read_text(encoding="utf-8")
            with self.subTest(skill=skill_path.parent.name):
                self.assertNotIn("python scripts/", text)
                if 'python "<suite-root>/scripts/' in text:
                    self.assertIn("${CLAUDE_PLUGIN_ROOT}", text)
                    self.assertIn(".seo-suite-runtime.json", text)
                    self.assertIn("suite_root", text)

    def test_technical_skill_can_generate_and_validate_llms_txt(self) -> None:
        technical = (SKILLS / "seo-technical" / "SKILL.md").read_text(encoding="utf-8")
        protocol = (SKILLS / "seo-technical" / "references" / "llms-txt-protocol.md").read_text(encoding="utf-8")
        template = SKILLS / "seo-technical" / "assets" / "llms.txt.template"
        router = (SKILLS / "seo" / "SKILL.md").read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "manifests" / "suite.json").read_text(encoding="utf-8"))
        self.assertIn("suitability, generation, validation, or publishing", technical)
        self.assertIn("low-cost future-readiness", technical)
        self.assertIn("validate_llms_txt.py", technical)
        self.assertIn("llms.txt.template", technical)
        self.assertIn("documented consumer strengthens the case but is not mandatory", protocol)
        self.assertTrue(template.is_file())
        self.assertIn("Optional `llms.txt` suitability, generation, validation", router)
        self.assertEqual(manifest["skills"]["seo-technical"]["produces_files"], ["llms-txt"])
        self.assertEqual(manifest["file_outputs"]["llms-txt"]["validator"], "scripts/validate_llms_txt.py")


if __name__ == "__main__":
    unittest.main()
