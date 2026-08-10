from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONVENTIONAL = ROOT / "examples" / "conventional-seo-handoff"
AI_SEARCH = ROOT / "examples" / "ai-search-handoff"


class ArtifactExampleTests(unittest.TestCase):
    def run_command(self, *arguments: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *(str(argument) for argument in arguments)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_conventional_handoff_artifacts_validate(self) -> None:
        commands = [
            (
                ROOT / "scripts" / "validate_seo_findings.py",
                "validate-findings",
                CONVENTIONAL / "seo-findings.json",
                "--bundle",
                CONVENTIONAL,
            ),
            (
                ROOT / "scripts" / "validate_seo_performance.py",
                "validate-run",
                CONVENTIONAL / "seo-performance-run.json",
                "--bundle",
                CONVENTIONAL,
            ),
        ]
        for command in commands:
            with self.subTest(command=command[0].name):
                completed = self.run_command(*command)
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                self.assertIn("PASS:", completed.stdout)

    def test_ai_search_handoff_chain_validates(self) -> None:
        commands = [
            (
                ROOT / "scripts" / "validate_ai_search_research.py",
                "validate-pack",
                AI_SEARCH / "research-pack.json",
                "--bundle",
                AI_SEARCH,
                "--now",
                "2026-08-10T00:00:00Z",
            ),
            (
                ROOT / "scripts" / "validate_query_corpus.py",
                "validate-corpus",
                AI_SEARCH / "query-corpus.json",
                "--bundle",
                AI_SEARCH,
            ),
            (
                ROOT / "scripts" / "validate_seo_aeo.py",
                "validate-brief",
                AI_SEARCH / "optimization-brief-aeo.json",
                "--bundle",
                AI_SEARCH,
            ),
            (
                ROOT / "scripts" / "validate_seo_geo.py",
                "validate-brief",
                AI_SEARCH / "optimization-brief-geo.json",
                "--bundle",
                AI_SEARCH,
            ),
            (
                ROOT / "scripts" / "validate_ai_visibility_monitor.py",
                "validate-run",
                AI_SEARCH / "visibility-run.json",
                "--bundle",
                AI_SEARCH,
            ),
        ]
        for command in commands:
            with self.subTest(command=command[0].name):
                completed = self.run_command(*command)
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                self.assertIn("PASS:", completed.stdout)

    def test_examples_are_sanitized_and_have_no_draft_placeholders(self) -> None:
        forbidden = re.compile(r"(?:PENDING|TODO:|bearer\s|api[_-]?key|password|[A-Za-z]:\\)", re.IGNORECASE)
        for bundle in (CONVENTIONAL, AI_SEARCH):
            for path in bundle.rglob("*"):
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8")
                with self.subTest(path=path.relative_to(ROOT).as_posix()):
                    self.assertIsNone(forbidden.search(text))
                    self.assertNotIn(".draft.json", path.name)
                if path.suffix == ".json":
                    payload = json.loads(text)
                    serialized = json.dumps(payload)
                    urls = re.findall(r"https://[^\"\\s]+", serialized)
                    self.assertTrue(all(url.startswith("https://example.com") for url in urls), urls)

    def test_example_readmes_publish_exact_validation_commands_and_boundaries(self) -> None:
        conventional = (CONVENTIONAL / "README.md").read_text(encoding="utf-8")
        ai_search = (AI_SEARCH / "README.md").read_text(encoding="utf-8")
        self.assertIn("validate_seo_findings.py", conventional)
        self.assertIn("validate_seo_performance.py", conventional)
        self.assertIn("validate_ai_search_research.py", ai_search)
        self.assertIn("validate_seo_aeo.py", ai_search)
        self.assertIn("validate_seo_geo.py", ai_search)
        self.assertIn("validate_ai_visibility_monitor.py", ai_search)
        self.assertIn("does not guarantee retrieval, citation, ranking, traffic, revenue, or conversion", ai_search)


if __name__ == "__main__":
    unittest.main()
