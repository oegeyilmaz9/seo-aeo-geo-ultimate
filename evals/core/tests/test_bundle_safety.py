from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from bundle_safety import resolve_artifact_in_bundle, resolve_relative  # noqa: E402


class BundleSafetyTests(unittest.TestCase):
    def test_regular_artifact_inside_bundle_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            artifact = bundle / "raw" / "record.json"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("{}", encoding="utf-8")
            errors: list[str] = []

            resolved = resolve_artifact_in_bundle(artifact, bundle, errors)

        self.assertEqual(errors, [])
        self.assertEqual(resolved, artifact)

    def test_external_artifact_and_parent_traversal_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            bundle.mkdir()
            outside = root / "outside.json"
            outside.write_text("{}", encoding="utf-8")

            outside_errors: list[str] = []
            escaped = resolve_artifact_in_bundle(outside, bundle, outside_errors)
            traversal_errors: list[str] = []
            traversed = resolve_relative(bundle, "raw/../outside.json", "raw_ref", traversal_errors)

        self.assertIsNone(escaped)
        self.assertIn("artifact must be inside --bundle", outside_errors)
        self.assertIsNone(traversed)
        self.assertTrue(any("bundle-relative" in error for error in traversal_errors))

    def test_reparse_artifact_is_rejected_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            raw = bundle / "raw"
            raw.mkdir(parents=True)
            target = raw / "record.json"
            target.write_text("{}", encoding="utf-8")
            alias = bundle / "artifact-link.json"
            try:
                alias.symlink_to(target)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"Symlinks are unavailable in this environment: {exc}")
            errors: list[str] = []

            resolved = resolve_artifact_in_bundle(alias, bundle, errors)

        self.assertIsNone(resolved)
        self.assertTrue(any("symlink or reparse point" in error for error in errors))

    def test_reparse_guard_branch_is_covered_without_symlink_privileges(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            artifact = bundle / "raw" / "record.json"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("{}", encoding="utf-8")
            errors: list[str] = []

            with patch("bundle_safety.is_reparse", side_effect=lambda path: path.name == "raw"):
                resolved = resolve_artifact_in_bundle(artifact, bundle, errors)

        self.assertIsNone(resolved)
        self.assertTrue(any("symlink or reparse point" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
