import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "seo-aeo"
CANON = ROOT / "manifests" / "artifact-schemas"


class SeoAeoSkillContractTests(unittest.TestCase):
    def test_frontmatter_has_exact_name_and_description_fields(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        self.assertIsNotNone(match)
        keys = [line.split(":", 1)[0] for line in match.group(1).splitlines() if re.match(r"^[a-z_]+:", line)]
        self.assertEqual(keys, ["name", "description"])
        self.assertNotIn("TODO", text)

    def test_aeo_geo_and_implementation_boundaries_are_explicit(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for phrase in ("Do not perform GEO", "ai-visibility-monitor", "ai-search-research", "seo-action-plan", "seo-content", "seo-schema", "seo-technical", "seo-hreflang", "optimise-seo"):
            self.assertIn(phrase, text)

    def test_myths_are_declined_not_prescribed(self):
        text = "\n".join(path.read_text(encoding="utf-8") for path in (SKILL / "SKILL.md", SKILL / "references" / "audit-protocol.md"))
        for forbidden in ("Optimal passage length:", "Brand Mentions > Backlinks", "llms.txt compliance", "AI crawlers do NOT execute JavaScript"):
            self.assertNotIn(forbidden, text)
        self.assertIn("Decline any requested mandatory rule", text)

    def test_contract_lock_matches_canonical_and_generated_bytes(self):
        lock = json.loads((SKILL / "references" / "contracts" / "contracts-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(len(lock["contracts"]), 3)
        for row in lock["contracts"]:
            canonical = ROOT / row["canonical_path"]
            generated = SKILL / row["generated_path"]
            canonical_hash = hashlib.sha256(canonical.read_bytes()).hexdigest()
            generated_hash = hashlib.sha256(generated.read_bytes()).hexdigest()
            self.assertEqual(canonical_hash, row["canonical_sha256"])
            self.assertEqual(generated_hash, row["generated_sha256"])
            self.assertEqual(canonical.read_bytes(), generated.read_bytes())


if __name__ == "__main__":
    unittest.main()
