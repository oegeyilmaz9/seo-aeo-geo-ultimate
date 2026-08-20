from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILLS = ROOT / "skills"


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


class SearchFundamentalsContractTests(unittest.TestCase):
    def test_broad_growth_route_cannot_skip_baseline_surfaces(self) -> None:
        router = read("skills", "seo", "SKILL.md")
        matrix = read("skills", "seo", "references", "routing-matrix.md")
        for marker in (
            "intended query families with `seo-research`",
            "search-result presentation with `seo-page` and `seo-content`",
            "favicon/site identity with `seo-technical`",
            "title, descriptive meta description, favicon, canonical/indexability, or query-to-page ownership",
            "A deliberately narrow request remains narrow",
        ):
            self.assertIn(marker, router)
        self.assertIn("Broad rank-higher or organic-growth request", matrix)
        self.assertIn("Missing or incorrect favicon in search presentation", matrix)

    def test_meta_copy_uses_semantic_completeness_without_a_fake_length_rule(self) -> None:
        page = read("skills", "seo-page", "references", "search-result-presentation.md")
        content = read("skills", "seo-content", "references", "snippet-copy-protocol.md")
        combined = page + content
        for marker in (
            "page identity or subject",
            "useful outcome",
            "concrete differentiator",
            "material qualifier",
            "actual proposed title and description",
            "too short to explain why the result fits the query",
            "Do not add filler to reach a fixed character count",
        ):
            self.assertIn(marker, combined)
        self.assertNotIn("120-160", combined)
        self.assertNotIn("150-160", combined)

    def test_query_opportunity_protocol_keeps_every_decision_dimension_visible(self) -> None:
        protocol = read("skills", "seo-research", "references", "query-opportunity-protocol.md")
        for marker in (
            "query, canonical page, country, device, search type, window, clicks, impressions, CTR, and average position",
            "Dated result-set evidence",
            "Defend",
            "Near win",
            "Snippet/CTR",
            "Coverage gap",
            "Consolidate",
            "Strategic build",
            "Head-term leadership",
            "Defer",
            "cannot be reported as a universal keyword score",
            "one primary need/query family per page",
        ):
            self.assertIn(marker, protocol)

    def test_head_term_leadership_is_mandatory_and_cannot_be_replaced_by_quick_wins(self) -> None:
        router = read("skills", "seo", "SKILL.md")
        matrix = read("skills", "seo", "references", "routing-matrix.md")
        research = read("skills", "seo-research", "SKILL.md")
        protocol = read("skills", "seo-research", "references", "query-opportunity-protocol.md")
        plan = read("skills", "seo-plan", "SKILL.md")
        implementation = read("skills", "optimise-seo", "references", "implementation-gate.md")
        performance = read("skills", "seo-performance", "references", "performance-measurement-protocol.md")
        combined = router + matrix + research + protocol + plan + implementation + performance
        for marker in (
            "two concurrent opportunity tracks",
            "every owner-declared relevant high-volume family",
            "nearer-term capture track",
            "head-term leadership track",
            "Difficulty, weak current visibility, or an authority gap",
            "Cost, difficulty, weak authority, or current absence alone do not qualify",
            "top-20, top-10, and top-3",
            "position 1 as an explicit stretch objective",
            "cannot silently remove that strategic target",
        ):
            self.assertIn(marker, combined)
        self.assertIn("does not sacrifice category ambition to quick wins", matrix)

    def test_favicon_protocol_is_executable_and_does_not_claim_display(self) -> None:
        technical = read("skills", "seo-technical", "SKILL.md")
        protocol = read("skills", "seo-technical", "references", "favicon-search-protocol.md")
        verifier = read("scripts", "verify_live_release.py")
        self.assertIn("favicon-search-protocol.md", technical)
        self.assertIn("one favicon per hostname", protocol)
        self.assertIn("larger than 48x48", protocol)
        self.assertIn("does not guarantee", protocol)
        self.assertIn('"site_identity"', verifier)
        self.assertIn("homepage-favicon-link", verifier)
        self.assertIn("favicon-recommended-size", verifier)

    def test_current_primary_sources_back_the_new_rules(self) -> None:
        registry = json.loads(read("docs", "research", "2026-08-06-source-registry.json"))
        sources = {row["id"]: row for row in registry["sources"]}
        expected = {
            "google-search-essentials-2026": "https://developers.google.com/search/docs/essentials",
            "google-search-snippet-meta-description-2026": "https://developers.google.com/search/docs/appearance/snippet",
            "google-search-title-links-2026": "https://developers.google.com/search/docs/appearance/title-link",
            "google-search-favicon-2026": "https://developers.google.com/search/docs/appearance/favicon-in-search",
            "google-search-console-query-opportunities-2026": "https://support.google.com/webmasters/answer/17010961",
        }
        for source_id, url in expected.items():
            with self.subTest(source_id=source_id):
                self.assertEqual(sources[source_id]["url"], url)
                self.assertEqual(sources[source_id]["source_kind"], "vendor_documentation")
                self.assertEqual(sources[source_id]["observed_at"], "2026-08-20")


if __name__ == "__main__":
    unittest.main()
