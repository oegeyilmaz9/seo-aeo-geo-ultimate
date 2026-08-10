from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "scripts" / "init_artifact.py"
SUITE = json.loads((ROOT / "manifests" / "suite.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("init_artifact_under_test", CLI)
assert SPEC is not None and SPEC.loader is not None
INIT_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INIT_MODULE)


class ArtifactScaffoldTests(unittest.TestCase):
    def run_cli(self, *arguments: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *(str(argument) for argument in arguments)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_list_is_derived_from_suite_manifest(self) -> None:
        completed = self.run_cli("--json", "list")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["artifact_types"], sorted(SUITE["schemas"]))
        self.assertEqual(set(payload["bundle_profiles"]["all"]), set(SUITE["schemas"]))

    def test_all_bundle_is_deterministic_and_explicitly_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first"
            second = Path(temporary) / "second"
            arguments = ("bundle", "all", "--seed", "example-project", "--created-at", "2026-08-10T00:00:00Z")
            one = self.run_cli(*arguments, "--out", first)
            two = self.run_cli(*arguments, "--out", second)
            self.assertEqual(one.returncode, 0, one.stderr)
            self.assertEqual(two.returncode, 0, two.stderr)

            first_files = {path.relative_to(first).as_posix(): path.read_bytes() for path in first.rglob("*") if path.is_file()}
            second_files = {path.relative_to(second).as_posix(): path.read_bytes() for path in second.rglob("*") if path.is_file()}
            self.assertEqual(first_files, second_files)
            self.assertEqual(len(list(first.glob("*.draft.json"))), len(SUITE["schemas"]))
            self.assertNotIn("research-pack.json", first_files)
            self.assertIn("Status: **draft / not validated**", (first / "DRAFT.md").read_text(encoding="utf-8"))
            manifest = json.loads((first / "draft-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "draft")
            self.assertEqual(manifest["validation_status"], "not_run")
            self.assertEqual(list(first.rglob("*.tmp")), [])

    def test_every_contract_can_be_scaffolded_individually(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for artifact_type in SUITE["schemas"]:
                with self.subTest(artifact_type=artifact_type):
                    output = root / f"{artifact_type}.draft.json"
                    completed = self.run_cli(
                        "artifact",
                        artifact_type,
                        "--out",
                        output,
                        "--seed",
                        "example-project",
                        "--created-at",
                        "2026-08-10T00:00:00Z",
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    payload = json.loads(output.read_text(encoding="utf-8"))
                    schema = json.loads(
                        (ROOT / "manifests" / "artifact-schemas" / SUITE["schemas"][artifact_type]).read_text(
                            encoding="utf-8"
                        )
                    )
                    self.assertTrue(set(schema.get("required", [])) <= set(payload))

    def test_no_overwrite_is_the_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "research-pack.draft.json"
            output.write_text("user-owned\n", encoding="utf-8")
            completed = self.run_cli(
                "artifact",
                "research-pack",
                "--out",
                output,
                "--seed",
                "example-project",
                "--created-at",
                "2026-08-10T00:00:00Z",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("refusing to overwrite", completed.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "user-owned\n")

    def test_artifact_output_must_keep_draft_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "research-pack.json"
            completed = self.run_cli(
                "artifact",
                "research-pack",
                "--out",
                output,
                "--seed",
                "example-project",
                "--created-at",
                "2026-08-10T00:00:00Z",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("must end with .draft.json", completed.stderr)
            self.assertFalse(output.exists())

    def test_bundle_preflight_prevents_partial_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "bundle"
            output.mkdir()
            blocker = output / "seo-findings.draft.json"
            blocker.write_text("user-owned\n", encoding="utf-8")
            completed = self.run_cli(
                "bundle",
                "conventional",
                "--out",
                output,
                "--seed",
                "example-project",
                "--created-at",
                "2026-08-10T00:00:00Z",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(blocker.read_text(encoding="utf-8"), "user-owned\n")
            self.assertFalse((output / "query-corpus.draft.json").exists())

    def test_overwrite_failure_restores_every_existing_bundle_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "a.draft.json"
            second = root / "b.draft.json"
            first.write_text("OLD-A", encoding="utf-8")
            second.write_text("OLD-B", encoding="utf-8")
            real_replace = os.replace
            promotion_count = 0

            def fail_second_promotion(source: object, destination: object) -> None:
                nonlocal promotion_count
                source_path = Path(source)
                destination_path = Path(destination)
                if source_path.suffix == ".tmp" and destination_path in {first, second}:
                    promotion_count += 1
                    if promotion_count == 2:
                        raise OSError("simulated second promotion failure")
                real_replace(source_path, destination_path)

            with mock.patch.object(INIT_MODULE.os, "replace", side_effect=fail_second_promotion):
                with self.assertRaisesRegex(INIT_MODULE.ScaffoldError, "atomically replace"):
                    INIT_MODULE.write_files({first: "NEW-A", second: "NEW-B"}, overwrite=True)

            self.assertEqual(first.read_text(encoding="utf-8"), "OLD-A")
            self.assertEqual(second.read_text(encoding="utf-8"), "OLD-B")
            self.assertEqual([path for path in root.iterdir() if path.name.startswith(".")], [])

    def test_non_regular_output_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "research-pack.draft.json"
            directory.mkdir()
            completed = self.run_cli(
                "artifact",
                "research-pack",
                "--out",
                directory,
                "--seed",
                "example-project",
                "--created-at",
                "2026-08-10T00:00:00Z",
                "--overwrite",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("directory", completed.stderr)

    def test_symlink_output_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.json"
            target.write_text("user-owned\n", encoding="utf-8")
            link = root / "linked.draft.json"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            completed = self.run_cli(
                "artifact",
                "research-pack",
                "--out",
                link,
                "--seed",
                "example-project",
                "--created-at",
                "2026-08-10T00:00:00Z",
                "--overwrite",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("reparse", completed.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "user-owned\n")

    def test_impossible_calendar_timestamp_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "research-pack.draft.json"
            completed = self.run_cli(
                "artifact",
                "research-pack",
                "--out",
                output,
                "--seed",
                "example-project",
                "--created-at",
                "2026-99-99T00:00:00Z",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("real UTC calendar timestamp", completed.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
