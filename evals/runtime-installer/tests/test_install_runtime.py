from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INSTALLER = ROOT / "scripts" / "install_runtime.py"


class RuntimeInstallerTests(unittest.TestCase):
    def run_installer(self, runtime: Path, state: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(INSTALLER),
                "--runtime-root",
                str(runtime),
                "--state-root",
                str(state),
                *extra,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_install_preserves_existing_skill_in_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "runtime" / "skills"
            existing = runtime / "seo-content"
            existing.mkdir(parents=True)
            (existing / "legacy-marker.txt").write_text("preserve me", encoding="utf-8")
            completed = self.run_installer(runtime, root / "state", "--skills", "seo-content", "seo-action-plan")
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            result = json.loads(completed.stdout)
            self.assertTrue((runtime / "seo-content" / "SKILL.md").is_file())
            self.assertTrue((runtime / "seo-action-plan" / "SKILL.md").is_file())
            content = next(item for item in result["skills"] if item["name"] == "seo-content")
            self.assertIsNotNone(content["backup"])
            self.assertEqual((Path(content["backup"]) / "legacy-marker.txt").read_text(encoding="utf-8"), "preserve me")
            self.assertTrue(Path(result["manifest"]).is_file())

    def test_dry_run_does_not_create_runtime_or_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "runtime" / "skills"
            state = root / "state"
            completed = self.run_installer(runtime, state, "--skills", "seo", "--dry-run")
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            result = json.loads(completed.stdout)
            self.assertTrue(result["dry_run"])
            self.assertFalse(runtime.exists())
            self.assertFalse(state.exists())

    def test_unknown_skill_is_rejected_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "runtime" / "skills"
            state = root / "state"
            completed = self.run_installer(runtime, state, "--skills", "not-a-skill")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("unknown skills", completed.stderr)
            self.assertFalse(runtime.exists())
            self.assertFalse(state.exists())

    def test_runtime_and_state_paths_cannot_overlap_source_or_each_other(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "runtime"
            state = root / "state"
            cases = (
                (ROOT / "skills", state, "runtime root must not overlap the source skills directory"),
                (runtime, ROOT / "skills", "state root must not overlap the source skills directory"),
                (runtime, runtime, "runtime root and state root must not overlap"),
            )
            for candidate_runtime, candidate_state, expected in cases:
                completed = self.run_installer(candidate_runtime, candidate_state, "--skills", "seo", "--dry-run")
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn(expected, completed.stderr)

    def test_existing_runtime_target_must_be_a_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "runtime"
            runtime.mkdir()
            target = runtime / "seo-content"
            target.write_text("do not replace a file", encoding="utf-8")
            completed = self.run_installer(runtime, root / "state", "--skills", "seo-content")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("runtime target must be a directory", completed.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "do not replace a file")


if __name__ == "__main__":
    unittest.main()
