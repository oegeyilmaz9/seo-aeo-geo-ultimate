from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_suite  # noqa: E402


class ReleaseMetadataTests(unittest.TestCase):
    def run_case(self, citation_version: str, changelog_version: str, llms_version: str) -> list[str]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "suite.json"
            citation = root / "CITATION.cff"
            changelog = root / "CHANGELOG.md"
            llms = root / "llms.txt"
            manifest.write_text(json.dumps({"suite_version": "3.1.0"}), encoding="utf-8")
            citation.write_text(f'version: "{citation_version}"\n', encoding="utf-8")
            changelog.write_text(f"## [{changelog_version}] - 2026-08-10\n", encoding="utf-8")
            llms.write_text(f"Version {llms_version}.\n", encoding="utf-8")
            errors: list[str] = []
            with (
                patch.object(validate_suite, "MANIFEST", manifest),
                patch.object(validate_suite, "CITATION", citation),
                patch.object(validate_suite, "CHANGELOG", changelog),
                patch.object(validate_suite, "LLMS_TXT", llms),
            ):
                validate_suite.validate_release_metadata(errors)
            return errors

    def test_release_metadata_versions_match(self) -> None:
        self.assertEqual(self.run_case("3.1.0", "3.1.0", "3.1.0"), [])

    def test_release_metadata_drift_is_reported(self) -> None:
        errors = self.run_case("2.2.0", "2.2.0", "2.2.0")
        self.assertEqual(len(errors), 3)
        self.assertTrue(any("CITATION.cff" in error for error in errors))
        self.assertTrue(any("CHANGELOG.md" in error for error in errors))
        self.assertTrue(any("llms.txt" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
