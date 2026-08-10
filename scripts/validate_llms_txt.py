from __future__ import annotations

import argparse
import http.client
import ipaddress
import re
import socket
import ssl
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit


H1_RE = re.compile(r"^#\s+(.+\S)\s*$")
H2_RE = re.compile(r"^##\s+(.+\S)\s*$")
LINK_RE = re.compile(r"^-\s+\[([^\]]+)]\(([^\s)]+)\)(?::\s*(.*))?\s*$")
DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_MAX_LIVE_LINKS = 25
DEFAULT_MAX_REDIRECTS = 5
MAX_TIMEOUT_SECONDS = 30.0
MAX_LIVE_LINKS = 100
MAX_REDIRECTS = 10


@dataclass(frozen=True)
class LiveProbe:
    requested_url: str
    final_url: str
    status: int
    content_type: str
    redirect_count: int


def fail(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)


def public_https_url(value: str, label: str, errors: list[str]) -> None:
    parsed = urlsplit(value)
    if not parsed.hostname:
        errors.append(f"{label} must be an absolute HTTPS URL")
        return
    if parsed.scheme != "https":
        errors.append(f"{label} must be an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        errors.append(f"{label} must not contain credentials")
    host = parsed.hostname.casefold().rstrip(".")
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        errors.append(f"{label} must not expose a local hostname")
        return
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if not address.is_global:
        errors.append(f"{label} must not expose a private or non-global IP address")


def resolve_public_host(
    value: str,
    label: str,
    errors: list[str],
    resolver: Callable[..., list[tuple]] = socket.getaddrinfo,
) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        return
    try:
        results = resolver(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        errors.append(f"{label} hostname could not be resolved: {exc}")
        return
    addresses = {result[4][0] for result in results if result[4]}
    if not addresses:
        errors.append(f"{label} hostname resolved to no addresses")
        return
    for raw_address in sorted(addresses):
        address = ipaddress.ip_address(raw_address.split("%", 1)[0])
        if not address.is_global:
            errors.append(f"{label} resolves to private or non-global address {raw_address}")


def resolved_public_addresses(value: str) -> list[str]:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("live-check URL must be absolute HTTPS")
    try:
        results = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError(f"hostname could not be resolved: {exc}") from exc
    addresses = sorted({result[4][0].split("%", 1)[0] for result in results if result[4]})
    if not addresses:
        raise ValueError("hostname resolved to no addresses")
    for raw_address in addresses:
        if not ipaddress.ip_address(raw_address).is_global:
            raise ValueError(f"hostname resolves to private or non-global address {raw_address}")
    return addresses


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to an already-vetted address while retaining hostname TLS checks."""

    def __init__(self, hostname: str, port: int, address: str, timeout: float) -> None:
        super().__init__(hostname, port=port, timeout=timeout, context=ssl.create_default_context())
        self._pinned_address = address

    def connect(self) -> None:
        raw_socket = socket.create_connection(
            (self._pinned_address, self.port),
            self.timeout,
            self.source_address,
        )
        self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)


def _content_type(headers) -> str:  # type: ignore[no-untyped-def]
    raw = headers.get("Content-Type")
    if not raw:
        return ""
    if hasattr(headers, "get_content_type"):
        return str(headers.get_content_type()).casefold()
    return str(raw).split(";", 1)[0].strip().casefold()


def acceptable_content_type(value: str) -> bool:
    if value.startswith("text/"):
        return True
    return value in {
        "application/json",
        "application/ld+json",
        "application/pdf",
        "application/xml",
        "application/xhtml+xml",
    } or value.endswith("+json") or value.endswith("+xml")


def _probe_live_url(url: str, timeout: float, max_redirects: int) -> LiveProbe:
    current = url
    redirect_count = 0
    redirect_statuses = {301, 302, 303, 307, 308}
    headers = {
        "Accept": "text/html,text/plain,application/json,application/xml,application/pdf;q=0.9,*/*;q=0.1",
        "Range": "bytes=0-0",
        "User-Agent": "seo-aeo-geo-ultimate-llms-validator/3.0",
    }
    while True:
        policy_errors: list[str] = []
        public_https_url(current, "live-check URL", policy_errors)
        if policy_errors:
            raise ValueError("; ".join(policy_errors))
        parsed = urlsplit(current)
        assert parsed.hostname is not None
        addresses = resolved_public_addresses(current)
        path = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        response: http.client.HTTPResponse | None = None
        last_error: OSError | ssl.SSLError | None = None
        for address in addresses:
            connection = PinnedHTTPSConnection(parsed.hostname, parsed.port or 443, address, timeout)
            try:
                connection.request("GET", path, headers=headers)
                response = connection.getresponse()
                break
            except (OSError, ssl.SSLError) as exc:
                last_error = exc
                connection.close()
        if response is None:
            raise OSError(f"all vetted addresses failed: {last_error}")
        try:
            status = int(response.status)
            content_type = _content_type(response.headers)
            location = response.headers.get("Location")
        finally:
            response.close()
            connection.close()  # close the pinned connection without reading a large body
        if status not in redirect_statuses:
            return LiveProbe(
                requested_url=url,
                final_url=current,
                status=status,
                content_type=content_type,
                redirect_count=redirect_count,
            )
        redirect_count += 1
        if redirect_count > max_redirects:
            raise ValueError(f"redirect limit exceeded ({max_redirects})")
        if not location:
            raise ValueError(f"HTTP {status} redirect is missing Location")
        current = urljoin(current, location)


def check_live_urls(
    urls: Iterable[str],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_links: int = DEFAULT_MAX_LIVE_LINKS,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    probe: Callable[[str, float, int], LiveProbe] | None = None,
) -> None:
    targets = list(urls)
    if len(targets) > max_links:
        fail([f"live check is bounded to {max_links} link(s), but llms.txt contains {len(targets)}"])
    live_errors: list[str] = []
    probe_url = probe or _probe_live_url
    for url in targets:
        try:
            result = probe_url(url, timeout, max_redirects)
        except (OSError, ValueError) as exc:
            live_errors.append(f"{url} live check failed: {exc}")
            continue

        final_errors: list[str] = []
        public_https_url(result.final_url, f"{url} final URL", final_errors)
        if final_errors:
            live_errors.extend(final_errors)
        if not 200 <= result.status < 300:
            live_errors.append(f"{url} returned non-success HTTP status {result.status}")
        if result.redirect_count > max_redirects:
            live_errors.append(f"{url} exceeded redirect limit {max_redirects}")
        if not acceptable_content_type(result.content_type):
            shown = result.content_type or "missing"
            live_errors.append(f"{url} returned unsupported Content-Type {shown!r}")
    if live_errors:
        fail(live_errors)
    print(
        f"PASS: live-checked {len(targets)} llms.txt link(s) "
        f"with timeout={timeout:g}s and max_redirects={max_redirects}"
    )


def validate_file(
    path: Path,
    *,
    check_live: bool = False,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_links: int = DEFAULT_MAX_LIVE_LINKS,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
) -> None:
    errors: list[str] = []
    if path.name.casefold() != "llms.txt":
        errors.append("publisher guide must be named llms.txt")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        fail(["llms.txt does not exist"])
    except UnicodeDecodeError:
        fail(["llms.txt must be valid UTF-8 text"])
    if "\x00" in text:
        errors.append("llms.txt must not contain NUL bytes")

    lines = text.splitlines()
    meaningful = [index for index, line in enumerate(lines) if line.strip()]
    if not meaningful:
        fail(errors + ["llms.txt must not be empty"])
    first = meaningful[0]
    if H1_RE.fullmatch(lines[first].strip()) is None:
        errors.append("the first non-empty line must be one H1 project/site title")

    h1_count = sum(1 for line in lines if H1_RE.fullmatch(line.strip()) is not None)
    if h1_count != 1:
        errors.append("llms.txt must contain exactly one H1 title")

    first_h2 = next((index for index, line in enumerate(lines) if H2_RE.fullmatch(line.strip())), len(lines))
    summary_lines = [line for line in lines[first + 1:first_h2] if line.strip().startswith(">")]
    if not summary_lines or not any(line.lstrip("> ").strip() for line in summary_lines):
        errors.append("llms.txt requires a non-empty blockquote summary before its file lists")

    sections: dict[str, int] = {}
    current_section: str | None = None
    seen_urls: set[str] = set()
    linked_urls: list[str] = []
    link_count = 0
    primary_link_count = 0
    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("###"):
            errors.append(f"line {index + 1}: use H2 headings only for file-list sections")
            continue
        section_match = H2_RE.fullmatch(line)
        if section_match is not None:
            current_section = section_match.group(1).strip()
            key = current_section.casefold()
            if key in sections:
                errors.append(f"line {index + 1}: duplicate section heading {current_section!r}")
            sections[key] = 0
            continue
        if current_section is None:
            continue
        link_match = LINK_RE.fullmatch(line)
        if link_match is None:
            errors.append(f"line {index + 1}: every non-empty line in a file-list section must be a Markdown link item")
            continue
        label, url = link_match.group(1).strip(), link_match.group(2)
        if not label:
            errors.append(f"line {index + 1}: link label must not be empty")
        public_https_url(url, f"line {index + 1} URL", errors)
        normalized = url.casefold()
        if normalized in seen_urls:
            errors.append(f"line {index + 1}: duplicate linked URL")
        seen_urls.add(normalized)
        linked_urls.append(url)
        sections[current_section.casefold()] += 1
        link_count += 1
        if current_section.casefold() != "optional":
            primary_link_count += 1

    if not sections:
        errors.append("llms.txt requires at least one H2 file-list section")
    for section, count in sections.items():
        if count == 0:
            errors.append(f"section {section!r} must contain at least one valid link item")
    if primary_link_count == 0:
        errors.append("llms.txt requires at least one non-optional public resource link")

    if errors:
        fail(errors)
    print(f"PASS: llms.txt publisher guide with {len(sections)} section(s) and {link_count} public link(s)")
    if check_live:
        check_live_urls(
            linked_urls,
            timeout=timeout,
            max_links=max_links,
            max_redirects=max_redirects,
        )


def positive_float(value: str) -> float:
    parsed = float(value)
    if not 0 < parsed <= MAX_TIMEOUT_SECONDS:
        raise argparse.ArgumentTypeError(f"must be greater than 0 and no more than {MAX_TIMEOUT_SECONDS:g}")
    return parsed


def bounded_int(value: str, maximum: int) -> int:
    parsed = int(value)
    if not 1 <= parsed <= maximum:
        raise argparse.ArgumentTypeError(f"must be between 1 and {maximum}")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the suite's maintained llms.txt publication profile.")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("validate-file")
    command.add_argument("artifact", type=Path)
    command.add_argument(
        "--check-live",
        action="store_true",
        help="also make bounded HTTPS requests to validate redirects, success status, and Content-Type",
    )
    command.add_argument("--timeout", type=positive_float, default=DEFAULT_TIMEOUT_SECONDS)
    command.add_argument(
        "--max-links",
        type=lambda value: bounded_int(value, MAX_LIVE_LINKS),
        default=DEFAULT_MAX_LIVE_LINKS,
    )
    command.add_argument(
        "--max-redirects",
        type=lambda value: bounded_int(value, MAX_REDIRECTS),
        default=DEFAULT_MAX_REDIRECTS,
    )
    args = parser.parse_args()
    validate_file(
        args.artifact,
        check_live=args.check_live,
        timeout=args.timeout,
        max_links=args.max_links,
        max_redirects=args.max_redirects,
    )


if __name__ == "__main__":
    main()
