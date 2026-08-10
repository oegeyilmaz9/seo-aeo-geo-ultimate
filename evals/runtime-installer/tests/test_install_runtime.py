from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
INSTALLER = ROOT / "scripts" / "install_runtime.py"
SPEC = importlib.util.spec_from_file_location("install_runtime_under_test", INSTALLER)
assert SPEC is not None and SPEC.loader is not None
INSTALLER_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER_MODULE)


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
            suite_root = Path(result["suite_root"])
            self.assertTrue((suite_root / "scripts" / "validate_seo_findings.py").is_file())
            self.assertTrue((suite_root / "manifests" / "suite.json").is_file())
            current = json.loads(Path(result["current_manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(Path(current["suite_root"]), suite_root)
            locator = json.loads((runtime / "seo-content" / ".seo-suite-runtime.json").read_text(encoding="utf-8"))
            self.assertEqual(Path(locator["suite_root"]), suite_root)
            self.assertEqual(locator["package_hash"], result["package_hash"])

            validation = subprocess.run(
                [sys.executable, str(suite_root / "scripts" / "validate_suite.py"), "--as-of", "2026-08-10"],
                check=False,
                capture_output=True,
                text=True,
                cwd=root,
            )
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)

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

    def test_verify_checks_support_locators_and_skill_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "runtime" / "skills"
            state = root / "state"
            installed = self.run_installer(runtime, state, "--skills", "seo")
            self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)

            verified = self.run_installer(runtime, state, "--skills", "seo", "--verify")
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
            result = json.loads(verified.stdout)
            self.assertTrue(result["verified"])
            self.assertEqual([item["name"] for item in result["skills"]], ["seo"])

            (runtime / "seo" / "SKILL.md").write_text("tampered", encoding="utf-8")
            drifted = self.run_installer(runtime, state, "--skills", "seo", "--verify")
            self.assertNotEqual(drifted.returncode, 0)
            self.assertIn("source hash mismatch", drifted.stderr)

    def test_support_package_is_reused_after_python_cache_files_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "runtime" / "skills"
            state = root / "state"
            first = self.run_installer(runtime, state, "--skills", "seo")
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            first_result = json.loads(first.stdout)
            suite_root = Path(first_result["suite_root"])
            subprocess.run(
                [sys.executable, str(suite_root / "scripts" / "validate_suite.py"), "--as-of", "2026-08-10"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue(any(suite_root.rglob("*.pyc")))

            second = self.run_installer(runtime, state, "--skills", "seo-page")
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            second_result = json.loads(second.stdout)
            self.assertEqual(second_result["suite_root"], first_result["suite_root"])
            self.assertTrue((runtime / "seo-page" / ".seo-suite-runtime.json").is_file())

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
                (ROOT / "skills", state, "runtime root must not overlap the source repository"),
                (runtime, ROOT / "skills", "state root must not overlap the source repository"),
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

    def test_metadata_failure_rolls_back_skill_and_partial_install_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / "runtime"
            state = root / "state"
            existing = runtime / "seo"
            existing.mkdir(parents=True)
            (existing / "legacy-marker.txt").write_text("restore me", encoding="utf-8")
            original_atomic_json = INSTALLER_MODULE.atomic_json

            def fail_current(path: Path, value: dict) -> None:
                if path.name == "current.json":
                    raise OSError("simulated current-manifest failure")
                original_atomic_json(path, value)

            with mock.patch.object(INSTALLER_MODULE, "atomic_json", side_effect=fail_current):
                with self.assertRaisesRegex(OSError, "simulated current-manifest failure"):
                    INSTALLER_MODULE.install(["seo"], runtime, state, False)

            self.assertEqual((runtime / "seo" / "legacy-marker.txt").read_text(encoding="utf-8"), "restore me")
            self.assertFalse((runtime / "seo" / "SKILL.md").exists())
            self.assertEqual(list((state / "installs").glob("*.json")), [])
            self.assertFalse((state / "current.json").exists())


if __name__ == "__main__":
    unittest.main()
