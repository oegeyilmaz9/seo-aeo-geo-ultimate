from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILLS = ROOT / "skills"


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


class OperationalCloseoutContractTests(unittest.TestCase):
    def assert_markers(self, text: str, markers: tuple[str, ...]) -> None:
        for marker in markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_router_owns_the_complete_post_local_chain(self) -> None:
        router = read("skills", "seo", "SKILL.md")
        self.assert_markers(
            router,
            (
                "product-owner decision",
                "authorized release",
                "live delivery verification",
                "authorized provider operation",
                "delayed outcome follow-up",
                "authorization separately for implementation, release, and provider mutation",
                "resume the same decision and candidate chain",
            ),
        )

    def test_decision_contract_is_complete_without_redundant_bundle_ceremony(self) -> None:
        contract = read("skills", "seo", "references", "decision-and-release-contract.md")
        self.assert_markers(
            contract,
            (
                "decision owner",
                "desired end state",
                "affected surfaces",
                "acceptance criteria",
                "rollback",
                "do not require a redundant immutable bundle",
                "Implementation",
                "Release",
                "Provider operation",
            ),
        )

    def test_explicit_product_end_state_is_not_shrunk_by_smallest_change(self) -> None:
        implementation = read("skills", "optimise-seo", "SKILL.md")
        decision = read("skills", "seo", "references", "decision-and-release-contract.md")
        self.assertIn("cannot shrink or replace an explicit product-owner end state", implementation)
        self.assertIn("must not silently replace the approved end state", decision)

    def test_programmatic_editorial_and_search_states_are_independent(self) -> None:
        skill = read("skills", "seo-programmatic", "SKILL.md")
        protocol = read("skills", "seo-programmatic", "references", "editorial-vs-indexability.md")
        propagation = read("skills", "seo-programmatic", "references", "corpus-propagation-contract.md")
        self.assertIn("Record editorial readiness independently from search status/indexability", skill)
        self.assertIn("Never derive this field from an editorial flag alone", protocol)
        self.assertIn("unique canonical-owner page", protocol)
        self.assertIn("owner-linked duplicate source", protocol)
        for surface in ("detail", "search/browse", "hub/taxonomy", "sitemap", "hreflang", "llms.txt"):
            self.assertIn(surface, propagation)

    def test_verification_universe_and_redirect_contract_are_scope_matched(self) -> None:
        matrix = read("skills", "seo-technical", "references", "live-verification-matrix.md")
        self.assert_markers(
            matrix,
            (
                "Entire affected route class or a justified closed population",
                "Full declared URL corpus",
                "status, `Location`, sitemap exclusion, and the target's expected document state",
                "Do not require document-only title, canonical, robots-meta, description, or H1 fields from a bodyless redirect",
                "expected/passed/failed counts",
            ),
        )

    def test_provider_operation_is_separate_from_measurement_and_outcome(self) -> None:
        skill = read("skills", "seo-performance", "SKILL.md")
        protocol = read("skills", "seo-performance", "references", "provider-operations-protocol.md")
        self.assertIn("A receipt is not a Performance Run", skill)
        self.assertIn("separate `provider-operation-receipt.json`", protocol)
        self.assertIn("URL Inspection API reports inspection state", protocol)
        self.assertIn("Indexing API is limited", protocol)
        self.assertIn("Provider acceptance is not crawl, indexing", skill)

    def test_dirty_and_generated_candidate_identity_is_preserved(self) -> None:
        closeout = read("skills", "optimise-seo", "references", "external-closeout.md")
        self.assert_markers(
            closeout,
            (
                "staged/unstaged/untracked file hashes",
                "generated outputs",
                "gitDirty=1",
                "A dirty worktree is not automatically a blocker",
                "never reset, clean, substitute a clean checkout, or revert unrelated files",
                "If the candidate changes after acceptance, invalidate the prior acceptance",
            ),
        )

    def test_external_claims_are_adjudicated_before_becoming_required(self) -> None:
        protocol = read("skills", "seo-technical", "references", "external-claim-adjudication.md")
        for status in ("Confirmed defect", "Layer mismatch", "Supported opportunity", "False positive", "Unverified"):
            self.assertIn(status, protocol)
        self.assertIn("Only a confirmed defect becomes required automatically", protocol)
        self.assertIn("missing link `title` attribute", protocol)
        self.assertIn("arbitrary meta-description length limits", protocol)

    def test_batch_final_preserves_failed_attempts_and_reruns_complete_gate(self) -> None:
        modes = read("skills", "optimise-seo", "references", "verification-modes.md")
        self.assertIn("run one complete final gate", modes)
        self.assertIn("rerun the complete gate", modes)
        self.assertIn("Report every attempt honestly", modes)

    def test_tools_and_provider_contract_are_manifested_without_new_skill(self) -> None:
        manifest = json.loads(read("manifests", "suite.json"))
        self.assertEqual(len(manifest["skills"]), 27)
        self.assertIn("provider-operation-receipt", manifest["schemas"])
        self.assertIn("provider-operation-validate", manifest["tools"])
        self.assertIn("live-release-verify", manifest["tools"])
        self.assertIn("provider-operation-receipt", manifest["skills"]["seo-performance"]["produces"])

    def test_live_release_documentation_matches_candidate_contract(self) -> None:
        documentation = read("docs", "LIVE-RELEASE-VERIFICATION.md")
        blocks = re.findall(r"```json\n(.*?)\n```", documentation, flags=re.DOTALL)
        self.assertGreaterEqual(len(blocks), 2)
        candidate_manifest = json.loads(blocks[0])
        plan = json.loads(blocks[1])
        self.assertEqual(
            set(candidate_manifest),
            {
                "schema_version",
                "candidate_id",
                "candidate_sha256",
                "git_dirty",
                "source_files",
                "generated_files",
                "build_identity",
                "corpus",
            },
        )
        self.assertEqual(
            set(plan["candidate"]),
            {
                "candidate_id",
                "sha256",
                "git_dirty",
                "manifest_ref",
                "manifest_sha256",
                "deployment_id",
                "production_alias",
            },
        )
        self.assertEqual(
            set(plan["site_identity"]),
            {"homepage_url", "expected_favicon_url", "minimum_size_px", "require_recommended_size"},
        )


if __name__ == "__main__":
    unittest.main()
