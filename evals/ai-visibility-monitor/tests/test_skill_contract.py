import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "ai-visibility-monitor"


class AiVisibilityMonitorSkillContractTests(unittest.TestCase):
    def test_frontmatter_and_trigger_boundary_are_exact(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        self.assertIsNotNone(match)
        keys = [line.split(":", 1)[0] for line in match.group(1).splitlines() if re.match(r"^[a-z_]+:", line)]
        self.assertEqual(keys, ["name", "description"])
        for phrase in ("frozen", "hash-pinned", "Do not use for live research", "causal attribution"):
            self.assertIn(phrase, match.group(1))
        self.assertNotIn("TODO", text)

    def test_measurement_only_boundaries_and_handoffs_are_present(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for phrase in ("does not prescribe", "Never bypass", "ai-search-research", "seo-aeo", "seo-geo", "Backlog minor", "at most twice"):
            self.assertIn(phrase, text)

    def test_contract_lock_matches_canonical_and_generated_bytes(self):
        lock = json.loads((SKILL / "references" / "contracts" / "contracts-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(len(lock["contracts"]), 2)
        for row in lock["contracts"]:
            canonical = ROOT / row["canonical_path"]
            generated = SKILL / row["generated_path"]
            self.assertEqual(hashlib.sha256(canonical.read_bytes()).hexdigest(), row["canonical_sha256"])
            self.assertEqual(hashlib.sha256(generated.read_bytes()).hexdigest(), row["generated_sha256"])
            self.assertEqual(canonical.read_bytes(), generated.read_bytes())


if __name__ == "__main__":
    unittest.main()
