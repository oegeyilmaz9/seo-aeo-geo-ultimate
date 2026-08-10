from __future__ import annotations

import importlib.util
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "scripts" / "validate_llms_txt.py"
SPEC = importlib.util.spec_from_file_location("validate_llms_txt_under_test", VALIDATOR)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR_MODULE
SPEC.loader.exec_module(VALIDATOR_MODULE)


def valid_text() -> str:
    return """# Example Site

> Public documentation and product guidance for Example Site.

Version 1.0. Public information only.

## Documentation

- [Quick start](https://example.com/docs/quick-start.md): Supported setup steps.
- [Reference](https://example.com/docs/reference): Canonical product reference.

## Optional

- [Changelog](https://example.com/changelog): Version history.
"""


class LlmsTxtValidatorTests(unittest.TestCase):
    def run_case(self, text: str, name: str = "llms.txt") -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / name
            path.write_text(text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), "validate-file", str(path)],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_repository_llms_txt_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR), "validate-file", str(ROOT / "llms.txt")],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS", completed.stdout)

    def test_valid_publisher_guide_passes(self) -> None:
        completed = self.run_case(valid_text())
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_bundled_template_renders_to_a_valid_candidate(self) -> None:
        template = (ROOT / "skills" / "seo-technical" / "assets" / "llms.txt.template").read_text(encoding="utf-8")
        replacements = {
            "{{SITE_OR_PROJECT_NAME}}": "Example Docs",
            "{{SHORT_TRUTHFUL_SUMMARY_FROM_THE_PUBLIC_SOURCE_OF_TRUTH}}": "Public product documentation for Example Docs.",
            "{{OPTIONAL_SCOPE_VERSION_OR_INTERPRETATION_NOTES}}": "Version 1.0. Public resources only.",
            "{{RESOURCE_NAME}}": "Getting started",
            "{{ABSOLUTE_HTTPS_CANONICAL_OR_MARKDOWN_URL}}": "https://docs.example.com/getting-started.md",
            "{{WHAT_THE_RESOURCE_COVERS}}": "Supported onboarding steps.",
            "{{SECONDARY_RESOURCE_NAME}}": "Changelog",
            "{{ABSOLUTE_HTTPS_URL}}": "https://docs.example.com/changelog",
            "{{WHY_A_CLIENT_MAY_SKIP_OR_USE_IT}}": "Version history for compatibility checks.",
        }
        for placeholder, value in replacements.items():
            template = template.replace(placeholder, value)
        completed = self.run_case(template)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_title_and_summary_are_required(self) -> None:
        completed = self.run_case("## Documentation\n\n- [Docs](https://example.com/docs)\n")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("first non-empty line", completed.stderr)
        self.assertIn("blockquote summary", completed.stderr)

    def test_links_must_be_public_https_urls(self) -> None:
        completed = self.run_case(valid_text().replace("https://example.com/docs/quick-start.md", "http://localhost/private"))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("absolute HTTPS URL", completed.stderr)
        self.assertIn("local hostname", completed.stderr)

    def test_private_ip_links_fail(self) -> None:
        completed = self.run_case(valid_text().replace("https://example.com/docs/quick-start.md", "https://127.0.0.1/private"))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("private or non-global IP", completed.stderr)

    def test_duplicate_urls_fail(self) -> None:
        completed = self.run_case(
            valid_text().replace("https://example.com/docs/reference", "https://example.com/docs/quick-start.md")
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("duplicate linked URL", completed.stderr)

    def test_file_list_sections_reject_free_text(self) -> None:
        completed = self.run_case(valid_text().replace("- [Reference]", "This is not a list item.\n- [Reference]"))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("every non-empty line in a file-list section", completed.stderr)

    def test_artifact_must_use_the_standard_filename(self) -> None:
        completed = self.run_case(valid_text(), name="ai-guide.txt")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("must be named llms.txt", completed.stderr)

    def test_default_validation_never_runs_a_live_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "llms.txt"
            path.write_text(valid_text(), encoding="utf-8")
            with mock.patch.object(
                VALIDATOR_MODULE,
                "check_live_urls",
                side_effect=AssertionError("offline validation attempted network work"),
            ):
                VALIDATOR_MODULE.validate_file(path)

    def test_live_check_accepts_bounded_https_redirect_and_text_content(self) -> None:
        calls: list[tuple[str, float, int]] = []

        def probe(url: str, timeout: float, max_redirects: int):
            calls.append((url, timeout, max_redirects))
            return VALIDATOR_MODULE.LiveProbe(
                requested_url=url,
                final_url="https://docs.example.com/final",
                status=200,
                content_type="text/html",
                redirect_count=1,
            )

        VALIDATOR_MODULE.check_live_urls(
            ["https://docs.example.com/start"],
            timeout=2.5,
            max_links=1,
            max_redirects=2,
            probe=probe,
        )
        self.assertEqual(calls, [("https://docs.example.com/start", 2.5, 2)])

    def test_live_check_rejects_insecure_redirect_target(self) -> None:
        def probe(url: str, timeout: float, max_redirects: int):
            return VALIDATOR_MODULE.LiveProbe(url, "http://example.com/final", 200, "text/plain", 1)

        with self.assertRaises(SystemExit):
            VALIDATOR_MODULE.check_live_urls(["https://example.com/start"], probe=probe)

    def test_live_check_rejects_error_status_and_binary_content(self) -> None:
        def probe(url: str, timeout: float, max_redirects: int):
            return VALIDATOR_MODULE.LiveProbe(url, url, 404, "application/octet-stream", 0)

        with self.assertRaises(SystemExit):
            VALIDATOR_MODULE.check_live_urls(["https://example.com/missing"], probe=probe)

    def test_live_check_rejects_missing_content_type(self) -> None:
        def probe(url: str, timeout: float, max_redirects: int):
            return VALIDATOR_MODULE.LiveProbe(url, url, 200, "", 0)

        with self.assertRaises(SystemExit):
            VALIDATOR_MODULE.check_live_urls(["https://example.com/no-content-type"], probe=probe)

    def test_live_check_enforces_link_bound_before_probing(self) -> None:
        probe = mock.Mock(side_effect=AssertionError("probe should not run after the bound fails"))
        with self.assertRaises(SystemExit):
            VALIDATOR_MODULE.check_live_urls(
                ["https://example.com/a", "https://example.com/b"],
                max_links=1,
                probe=probe,
            )
        probe.assert_not_called()

    def test_live_check_enforces_redirect_bound_from_probe_result(self) -> None:
        def probe(url: str, timeout: float, max_redirects: int):
            return VALIDATOR_MODULE.LiveProbe(url, url, 200, "application/pdf", 3)

        with self.assertRaises(SystemExit):
            VALIDATOR_MODULE.check_live_urls(
                ["https://example.com/guide.pdf"],
                max_redirects=2,
                probe=probe,
            )

    def test_live_resolver_rejects_private_dns_answers(self) -> None:
        private_answer = [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 443))
        ]
        with mock.patch.object(VALIDATOR_MODULE.socket, "getaddrinfo", return_value=private_answer):
            with self.assertRaisesRegex(ValueError, "private or non-global"):
                VALIDATOR_MODULE.resolved_public_addresses("https://docs.example.com/guide")

    def test_live_redirect_is_revalidated_and_re_resolved_before_following(self) -> None:
        class FakeResponse:
            status = 302
            headers = {"Content-Type": "text/html", "Location": "https://redirect.example/internal"}

            def close(self) -> None:
                pass

        connections: list[tuple[str, int, str, float]] = []

        class FakeConnection:
            def __init__(self, hostname: str, port: int, address: str, timeout: float) -> None:
                connections.append((hostname, port, address, timeout))

            def request(self, method: str, path: str, headers: dict[str, str]) -> None:
                self.requested = (method, path, headers)

            def getresponse(self) -> FakeResponse:
                return FakeResponse()

            def close(self) -> None:
                pass

        with (
            mock.patch.object(
                VALIDATOR_MODULE,
                "resolved_public_addresses",
                side_effect=[["93.184.216.34"], ValueError("hostname resolves to private or non-global address 127.0.0.1")],
            ) as resolver,
            mock.patch.object(VALIDATOR_MODULE, "PinnedHTTPSConnection", FakeConnection),
        ):
            with self.assertRaisesRegex(ValueError, "private or non-global"):
                VALIDATOR_MODULE._probe_live_url("https://docs.example.com/start", 2.0, 2)
        self.assertEqual(connections, [("docs.example.com", 443, "93.184.216.34", 2.0)])
        self.assertEqual(
            [call.args[0] for call in resolver.call_args_list],
            ["https://docs.example.com/start", "https://redirect.example/internal"],
        )


if __name__ == "__main__":
    unittest.main()
