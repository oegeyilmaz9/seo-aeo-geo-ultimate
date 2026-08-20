from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILLS = ROOT / "skills"


def skill_text(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def reference_text(skill: str, name: str) -> str:
    return (SKILLS / skill / "references" / name).read_text(encoding="utf-8")


class SpecialistDepthContractTests(unittest.TestCase):
    def assert_markers(self, text: str, markers: tuple[str, ...]) -> None:
        for marker in markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_seo_audit_preserves_scope_evidence_and_approval_boundaries(self) -> None:
        text = skill_text("seo-audit")
        self.assert_markers(
            text,
            (
                "representative URLs/templates",
                "Preserve their artifacts and disagreements",
                "validated findings",
                "not by one blended SEO number",
                "pending approval",
            ),
        )
        protocol = reference_text("seo-audit", "audit-scope-protocol.md")
        self.assertIn("Report site-wide conclusions only when the evidence truly covers the population", protocol)

    def test_competitor_pages_require_dated_attributable_and_reviewed_claims(self) -> None:
        text = skill_text("seo-competitor-pages")
        self.assert_markers(
            text,
            (
                "Every material row gets a source",
                "label it unknown, omit it, or ask for an approved source",
                "legal/brand",
                "Never fabricate rankings",
                "Unverified rows are explicit gaps",
            ),
        )
        protocol = reference_text("seo-competitor-pages", "comparison-evidence-protocol.md")
        self.assertIn("market/plan/version scope", protocol)

    def test_images_separate_accessibility_delivery_discovery_and_rights(self) -> None:
        text = skill_text("seo-images")
        self.assert_markers(
            text,
            (
                "Mark decorative images as decorative",
                "Alt text explains the image",
                "actual LCP/CLS/interaction evidence",
                "owner/license",
                "Keep image discovery, user accessibility, and rendering performance as separate verifications",
            ),
        )

    def test_page_review_uses_a_page_contract_and_routes_real_owners(self) -> None:
        text = skill_text("seo-page")
        self.assert_markers(
            text,
            (
                "Declare the page contract",
                "raw and rendered capture",
                "Route content usefulness and drafts to `seo-content`",
                "Avoid arbitrary meta-length",
                "Do not change a page, deploy markup, submit URLs, or claim approval",
            ),
        )

    def test_plan_uses_only_validated_approved_owned_work(self) -> None:
        text = skill_text("seo-plan")
        self.assert_markers(
            text,
            (
                "validated audit/research artifacts",
                "approved action-plan items",
                "Keep experimental work in a separate learning track",
                "owner, acceptance criteria, verification method, guardrail, and review date",
                "cannot forecast rankings, citations, traffic, or revenue as a guarantee",
            ),
        )
        protocol = reference_text("seo-plan", "roadmap-protocol.md")
        self.assertIn("rollback", protocol)

    def test_programmatic_pages_require_provenance_failure_samples_and_reversible_rollout(self) -> None:
        text = skill_text("seo-programmatic")
        self.assert_markers(
            text,
            (
                "data dictionary and provenance",
                "normal, sparse-data, conflicting-data, locale, outlier, and deprecation cases",
                "explicit index/noindex/redirect/withhold conditions",
                "owned reversible cohort",
                "Do not use word counts",
            ),
        )

    def test_research_preserves_query_kinds_provenance_and_ai_boundary(self) -> None:
        text = skill_text("seo-research")
        self.assert_markers(
            text,
            (
                "Separate user needs, observed search queries, AI prompts, and engine-executed subqueries",
                "Treat volume/difficulty/vendor metrics as dated estimates, never ground truth",
                "create `query-corpus.json`",
                "validate_query_corpus.py",
                "AI-specific formal work to `ai-search-research`",
            ),
        )
        protocol = reference_text("seo-research", "research-evidence-protocol.md")
        self.assertIn("Do not invent engine-executed queries", protocol)

    def test_sitemap_requires_verified_inventory_and_truthful_lastmod(self) -> None:
        text = skill_text("seo-sitemap")
        self.assert_markers(
            text,
            (
                "verified canonical URL inventory",
                "Include `lastmod` only when it is a truthful",
                "redirecting, error, duplicate, blocked, noindex",
                "neither forces crawling nor guarantees indexation",
                "test/rollback instructions",
            ),
        )
        protocol = reference_text("seo-sitemap", "sitemap-inventory-protocol.md")
        self.assertIn("Create four explicit sets", protocol)

    def test_technical_routes_migrations_incidents_and_recovery_to_full_recipe(self) -> None:
        text = skill_text("seo-technical")
        protocol = reference_text("seo-technical", "migration-and-recovery-protocol.md")
        self.assertIn("migration-and-recovery-protocol.md", text)
        self.assert_markers(
            protocol,
            (
                "old-to-new URL map",
                "last known-good time",
                "Manual Actions report",
                "Security Issues report",
                "security/incident owner",
                "Do not submit repeated requests",
            ),
        )
        llms_protocol = reference_text("seo-technical", "llms-txt-protocol.md")
        self.assertIn(".seo-suite-runtime.json", llms_protocol)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", llms_protocol)
        self.assertNotIn("or the absolute repository checkout in Codex", llms_protocol)

    def test_performance_routes_experiments_to_predeclared_search_safe_recipe(self) -> None:
        text = skill_text("seo-performance")
        protocol = reference_text("seo-performance", "controlled-seo-experiment-protocol.md")
        self.assertIn("controlled-seo-experiment-protocol.md", text)
        self.assert_markers(
            protocol,
            (
                "falsifiable hypothesis",
                "primary outcome",
                "use a holdout",
                "do not cloak a test",
                "verified delivery",
                "label any post-result analysis exploratory",
                "observational association",
            ),
        )

    def test_import_adapters_are_routed_as_evidence_preparation_not_outcomes(self) -> None:
        router = skill_text("seo")
        performance = skill_text("seo-performance")
        architecture = skill_text("seo-architecture")
        technical = skill_text("seo-technical")
        matrix = reference_text("seo", "routing-matrix.md")
        self.assertIn("import_seo_exports.py", performance)
        self.assertIn("imported envelope is evidence input, not a validated Performance Run", performance)
        self.assertIn("import_seo_exports.py", architecture)
        self.assertIn("observation envelope is not a Site Graph", architecture)
        self.assertIn("import_seo_exports.py", technical)
        self.assertIn("do not fabricate HTML captures", technical)
        self.assertIn("import is evidence preparation, not a validated finding or outcome", router)
        self.assertIn("Normalize an authorized GSC, Bing, organic GA4, crawler CSV, or server log", matrix)

    def test_router_exposes_operational_recipes_without_new_specialists(self) -> None:
        router = skill_text("seo")
        matrix = reference_text("seo", "routing-matrix.md")
        self.assert_markers(
            router,
            (
                "Site migration/replatforming, sudden traffic/indexation incident",
                "Controlled SEO experiment design, baseline, or evaluation",
            ),
        )
        self.assert_markers(
            matrix,
            (
                "| Site migration or replatforming | `seo-technical` |",
                "| Sudden traffic/indexation incident | `seo-technical` |",
                "| Manual action or hacked-site recovery | `seo-technical`",
                "| Controlled SEO experiment | `seo-performance` |",
            ),
        )

    def test_claude_distribution_docs_use_official_and_direct_marketplaces(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        submission = (ROOT / "docs" / "CLAUDE-PLUGIN-SUBMISSION.md").read_text(encoding="utf-8")
        for text in (readme, submission):
            with self.subTest(document="README" if text is readme else "submission"):
                self.assertIn("seo-aeo-geo-ultimate@claude-plugins-official", text)
                self.assertIn("seo-aeo-geo-ultimate@oegeyilmaz9-skills", text)
                self.assertNotIn("claude-plugins-community", text)
                self.assertNotIn("@claude-community", text)
        self.assertIn("https://claude.ai/settings/plugins/submit", submission)
        self.assertIn("https://platform.claude.com/plugins/submit", submission)

    def test_weekly_freshness_alert_is_deduplicated_and_permission_scoped(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8")
        self.assert_markers(
            workflow,
            (
                "push:",
                "pull_request:",
                "workflow_dispatch:",
                "schedule:",
                "cron: '17 6 * * 1'",
                "github.event_name == 'schedule'",
                "[automation] Source and platform review required",
                "state: 'closed'",
            ),
        )
        self.assertEqual(workflow.count("issues: write"), 1)


if __name__ == "__main__":
    unittest.main()
