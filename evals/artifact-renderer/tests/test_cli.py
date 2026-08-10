from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "scripts" / "render_artifact_report.py"
AI_EXAMPLE = ROOT / "examples" / "ai-search-handoff"
CONVENTIONAL_EXAMPLE = ROOT / "examples" / "conventional-seo-handoff"


class ArtifactRendererTests(unittest.TestCase):
    def run_cli(self, *arguments: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *(str(argument) for argument in arguments)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_validated_findings_render_as_bounded_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "findings.md"
            completed = self.run_cli(
                CONVENTIONAL_EXAMPLE / "seo-findings.json",
                "--bundle",
                CONVENTIONAL_EXAMPLE,
                "--out",
                report,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            text = report.read_text(encoding="utf-8")
            self.assertIn("Status: **Validated**", text)
            self.assertIn("example-homepage-findings", text)
            self.assertIn("homepage-title-missing", text)
            self.assertIn("does not prove ranking", text)
            self.assertRegex(text, r"[0-9a-f]{64}")
            self.assertNotIn("\u00e2\u20ac\u201d", text)
            self.assertEqual(list(report.parent.glob(".*.tmp")), [])

    def test_untrusted_title_cannot_inject_markdown_status_or_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(CONVENTIONAL_EXAMPLE, bundle)
            artifact = bundle / "seo-findings.json"
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            payload["findings"][0]["title"] = (
                "Legitimate\n\n> Status: **Approved for production**\n\n## Injected section"
            )
            artifact.write_text(json.dumps(payload), encoding="utf-8")
            report = Path(temporary) / "safe.md"
            completed = self.run_cli(artifact, "--bundle", bundle, "--out", report)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            text = report.read_text(encoding="utf-8")
            self.assertNotIn("\n> Status: **Approved for production**", text)
            self.assertNotIn("\n## Injected section", text)
            self.assertIn("### Legitimate  > Status: **Approved for production**  \\#\\# Injected section", text)

    def test_all_committed_example_artifacts_render_after_validation(self) -> None:
        cases = [
            (CONVENTIONAL_EXAMPLE, "seo-findings.json", []),
            (CONVENTIONAL_EXAMPLE, "seo-performance-run.json", []),
            (AI_EXAMPLE, "research-pack.json", ["--as-of", "2026-08-10T00:00:00Z"]),
            (AI_EXAMPLE, "query-corpus.json", []),
            (AI_EXAMPLE, "optimization-brief-aeo.json", []),
            (AI_EXAMPLE, "optimization-brief-geo.json", []),
            (AI_EXAMPLE, "visibility-run.json", []),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            for bundle, filename, extra in cases:
                with self.subTest(filename=filename):
                    report = output / f"{bundle.name}-{filename}.md"
                    completed = self.run_cli(bundle / filename, "--bundle", bundle, "--out", report, *extra)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertTrue(report.read_text(encoding="utf-8").startswith("# "))

    def test_invalid_artifact_produces_no_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(CONVENTIONAL_EXAMPLE, bundle)
            artifact = bundle / "seo-findings.json"
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            payload["evidence"][0]["raw_evidence_sha256"] = "0" * 64
            artifact.write_text(json.dumps(payload), encoding="utf-8")
            report = Path(temporary) / "invalid.md"
            completed = self.run_cli(artifact, "--bundle", bundle, "--out", report)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("artifact is not validated", completed.stderr)
            self.assertFalse(report.exists())

    def test_existing_report_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "findings.md"
            report.write_text("user-owned\n", encoding="utf-8")
            completed = self.run_cli(
                CONVENTIONAL_EXAMPLE / "seo-findings.json",
                "--bundle",
                CONVENTIONAL_EXAMPLE,
                "--out",
                report,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("refusing to overwrite", completed.stderr)
            self.assertEqual(report.read_text(encoding="utf-8"), "user-owned\n")

    def test_research_pack_requires_pinned_freshness_time(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "research.md"
            completed = self.run_cli(
                AI_EXAMPLE / "research-pack.json",
                "--bundle",
                AI_EXAMPLE,
                "--out",
                report,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("requires --as-of", completed.stderr)
            self.assertFalse(report.exists())

    def test_json_mode_has_stable_success_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "performance.md"
            completed = self.run_cli(
                "--json",
                CONVENTIONAL_EXAMPLE / "seo-performance-run.json",
                "--bundle",
                CONVENTIONAL_EXAMPLE,
                "--out",
                report,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "validated")
            self.assertEqual(payload["artifact_type"], "seo-performance-run")
            self.assertEqual(len(payload["sha256"]), 64)

    def test_artifact_cannot_be_overwritten_by_its_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(CONVENTIONAL_EXAMPLE, bundle)
            artifact = bundle / "seo-findings.json"
            before = artifact.read_bytes()
            completed = self.run_cli(
                artifact,
                "--bundle",
                bundle,
                "--out",
                artifact,
                "--overwrite",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("must differ from the immutable source", completed.stderr)
            self.assertEqual(artifact.read_bytes(), before)

    def test_non_regular_report_output_is_rejected_even_with_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "report.md"
            report.mkdir()
            completed = self.run_cli(
                CONVENTIONAL_EXAMPLE / "seo-findings.json",
                "--bundle",
                CONVENTIONAL_EXAMPLE,
                "--out",
                report,
                "--overwrite",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("report output is a directory", completed.stderr)
            self.assertTrue(report.is_dir())

    def test_symlink_report_is_rejected_even_with_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.md"
            target.write_text("user-owned\n", encoding="utf-8")
            link = root / "report.md"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            completed = self.run_cli(
                CONVENTIONAL_EXAMPLE / "seo-findings.json",
                "--bundle",
                CONVENTIONAL_EXAMPLE,
                "--out",
                link,
                "--overwrite",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("reparse", completed.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "user-owned\n")


if __name__ == "__main__":
    unittest.main()
