#!/usr/bin/env python3
"""Verify a declared live SEO release against a local expected URL inventory.

The verifier is deliberately read-only. It checks raw HTTP/HTML, sitemap,
redirect, and shared-surface contracts. It does not render JavaScript, deploy a
candidate, mutate a provider, or claim crawl/index/search outcomes.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import ipaddress
import json
import os
import re
import socket
import struct
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from bundle_safety import is_reparse, resolve_relative


TRANSIENT_STATUSES = {408, 425, 429, 500, 502, 503, 504}
MAX_BODY_BYTES = 5_000_000
MAX_SITEMAP_FILES = 50
MAX_URLS = 100_000
HEX_64 = re.compile(r"^[a-f0-9]{64}$")


class VerificationError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self._in_title = False
        self._h1_depth = 0
        self.description: str | None = None
        self.meta_robots: list[str] = []
        self.canonicals: list[str] = []
        self.hreflang: dict[str, list[str]] = {}
        self.icons: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): (value or "") for name, value in attrs}
        lowered = tag.lower()
        if lowered == "title":
            self._in_title = True
        elif lowered == "h1":
            self._h1_depth += 1
        elif lowered == "meta":
            name = values.get("name", "").lower()
            if name == "description" and self.description is None:
                self.description = values.get("content", "").strip()
            if name in {"robots", "googlebot", "bingbot"}:
                self.meta_robots.append(values.get("content", "").lower())
        elif lowered == "link":
            rel = {token.lower() for token in values.get("rel", "").split()}
            href = values.get("href", "").strip()
            if "canonical" in rel and href:
                self.canonicals.append(href)
            if "alternate" in rel and href and values.get("hreflang"):
                self.hreflang.setdefault(values["hreflang"].lower(), []).append(href)
            if href and ("icon" in rel or "apple-touch-icon" in rel or "apple-touch-icon-precomposed" in rel):
                self.icons.append(href)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "title":
            self._in_title = False
        elif lowered == "h1" and self._h1_depth:
            self._h1_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._h1_depth:
            self.h1_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())

    @property
    def h1(self) -> str:
        return " ".join("".join(self.h1_parts).split())


@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int | None
    headers: dict[str, str]
    body: bytes
    attempts: int
    transient_failures: tuple[str, ...]
    error: str | None


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def digest_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8-sig"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite {value}")),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise VerificationError(f"cannot read plan JSON: {exc}") from exc


def require_keys(value: object, required: set[str], allowed: set[str], field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VerificationError(f"{field} must be an object")
    missing = required - value.keys()
    extra = value.keys() - allowed
    if missing:
        raise VerificationError(f"{field} is missing {sorted(missing)}")
    if extra:
        raise VerificationError(f"{field} has unsupported fields {sorted(extra)}")
    return value


def absolute_url(value: object, field: str, origin: str | None = None) -> str:
    if not isinstance(value, str) or not value:
        raise VerificationError(f"{field} must be a non-empty URL")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise VerificationError(f"{field} must be an HTTP(S) URL without credentials")
    if parsed.fragment:
        raise VerificationError(f"{field} must not contain a fragment")
    if origin is not None:
        expected = urllib.parse.urlsplit(origin)
        if (parsed.scheme.lower(), parsed.hostname.lower(), parsed.port) != (
            expected.scheme.lower(),
            expected.hostname.lower(),
            expected.port,
        ):
            raise VerificationError(f"{field} must use the declared origin")
    return value


def integer(value: object, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise VerificationError(f"{field} must be an integer from {minimum} through {maximum}")
    return value


def boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise VerificationError(f"{field} must be boolean")
    return value


def validate_plan(payload: object, plan: Path) -> dict[str, Any]:
    required = {
        "schema_version",
        "release_id",
        "candidate",
        "origin",
        "expected_inventory_ref",
        "live_sitemap_url",
        "sitemap_mode",
        "document_defaults",
        "document_overrides",
        "redirects",
        "surfaces",
        "network",
        "rendered_required",
    }
    root = require_keys(payload, required, required | {"site_identity"}, "plan")
    if root["schema_version"] != "1.0.0":
        raise VerificationError("plan.schema_version must be 1.0.0")
    if not isinstance(root["release_id"], str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", root["release_id"]):
        raise VerificationError("plan.release_id has invalid format")
    candidate_fields = {
        "candidate_id",
        "sha256",
        "git_dirty",
        "manifest_ref",
        "manifest_sha256",
        "deployment_id",
        "production_alias",
    }
    candidate = require_keys(root["candidate"], candidate_fields, candidate_fields, "plan.candidate")
    if not isinstance(candidate["candidate_id"], str) or not candidate["candidate_id"].strip():
        raise VerificationError("plan.candidate.candidate_id must be non-empty")
    if not isinstance(candidate["sha256"], str) or HEX_64.fullmatch(candidate["sha256"]) is None:
        raise VerificationError("plan.candidate.sha256 must be lowercase SHA-256")
    boolean(candidate["git_dirty"], "plan.candidate.git_dirty")
    if not isinstance(candidate["manifest_sha256"], str) or HEX_64.fullmatch(candidate["manifest_sha256"]) is None:
        raise VerificationError("plan.candidate.manifest_sha256 must be lowercase SHA-256")
    if not isinstance(candidate["deployment_id"], str) or not candidate["deployment_id"].strip():
        raise VerificationError("plan.candidate.deployment_id must be non-empty")
    candidate_manifest = resolve_relative(plan.parent, candidate["manifest_ref"], "plan.candidate.manifest_ref", [])
    if candidate_manifest is None or not candidate_manifest.is_file() or is_reparse(candidate_manifest):
        raise VerificationError("plan.candidate.manifest_ref must resolve to a regular in-bundle file")
    if digest_bytes(candidate_manifest.read_bytes()) != candidate["manifest_sha256"]:
        raise VerificationError("plan.candidate manifest hash mismatch")
    manifest_payload = load_json(candidate_manifest)
    manifest_fields = {
        "schema_version",
        "candidate_id",
        "candidate_sha256",
        "git_dirty",
        "source_files",
        "generated_files",
        "build_identity",
        "corpus",
    }
    candidate_record = require_keys(manifest_payload, manifest_fields, manifest_fields, "candidate manifest")
    if candidate_record["schema_version"] != "1.0.0":
        raise VerificationError("candidate manifest schema_version must be 1.0.0")
    if candidate_record["candidate_id"] != candidate["candidate_id"]:
        raise VerificationError("candidate manifest candidate_id mismatch")
    if candidate_record["candidate_sha256"] != candidate["sha256"] or HEX_64.fullmatch(str(candidate_record["candidate_sha256"])) is None:
        raise VerificationError("candidate manifest candidate_sha256 mismatch")
    if candidate_record["git_dirty"] is not candidate["git_dirty"]:
        raise VerificationError("candidate manifest git_dirty mismatch")
    if not isinstance(candidate_record["build_identity"], str) or not candidate_record["build_identity"].strip():
        raise VerificationError("candidate manifest build_identity must be non-empty")
    all_candidate_paths: set[str] = set()
    candidate_file_count = 0
    for collection in ("source_files", "generated_files"):
        rows = candidate_record[collection]
        if not isinstance(rows, list):
            raise VerificationError(f"candidate manifest {collection} must be an array")
        seen_paths: set[str] = set()
        for index, row in enumerate(rows):
            item = require_keys(row, {"path", "sha256"}, {"path", "sha256"}, f"candidate manifest {collection}[{index}]")
            path_value = item["path"]
            if (
                not isinstance(path_value, str)
                or not path_value
                or "\\" in path_value
                or path_value.startswith("/")
                or re.match(r"^[A-Za-z]:", path_value)
                or ".." in Path(path_value).parts
            ):
                raise VerificationError(f"candidate manifest {collection}[{index}].path must be portable and relative")
            if path_value in seen_paths:
                raise VerificationError(f"candidate manifest {collection} paths must be unique")
            if path_value in all_candidate_paths:
                raise VerificationError("candidate manifest paths cannot appear in both source_files and generated_files")
            seen_paths.add(path_value)
            all_candidate_paths.add(path_value)
            candidate_file_count += 1
            if not isinstance(item["sha256"], str) or HEX_64.fullmatch(item["sha256"]) is None:
                raise VerificationError(f"candidate manifest {collection}[{index}].sha256 must be lowercase SHA-256")
    if candidate["git_dirty"] and candidate_file_count == 0:
        raise VerificationError("a dirty candidate manifest must preserve at least one source or generated file hash")
    corpus = require_keys(candidate_record["corpus"], {"kind", "expected_count", "sha256"}, {"kind", "expected_count", "sha256"}, "candidate manifest corpus")
    if not isinstance(corpus["kind"], str) or not corpus["kind"].strip():
        raise VerificationError("candidate manifest corpus.kind must be non-empty")
    integer(corpus["expected_count"], "candidate manifest corpus.expected_count", 1, MAX_URLS)
    if not isinstance(corpus["sha256"], str) or HEX_64.fullmatch(corpus["sha256"]) is None:
        raise VerificationError("candidate manifest corpus.sha256 must be lowercase SHA-256")
    root["_candidate_manifest_path"] = candidate_manifest
    root["_candidate_manifest"] = candidate_record
    origin = absolute_url(root["origin"], "plan.origin")
    parsed_origin = urllib.parse.urlsplit(origin)
    if parsed_origin.path not in {"", "/"} or parsed_origin.query:
        raise VerificationError("plan.origin must contain only scheme and authority")
    root["origin"] = origin.rstrip("/")
    candidate["production_alias"] = absolute_url(candidate["production_alias"], "plan.candidate.production_alias")
    if candidate["production_alias"].rstrip("/") != root["origin"]:
        raise VerificationError("plan.candidate.production_alias must equal the declared origin")
    root["live_sitemap_url"] = absolute_url(root["live_sitemap_url"], "plan.live_sitemap_url", root["origin"])
    if root["sitemap_mode"] not in {"exact", "scoped"}:
        raise VerificationError("plan.sitemap_mode must be exact or scoped")
    inventory = resolve_relative(plan.parent, root["expected_inventory_ref"], "plan.expected_inventory_ref", [])
    if inventory is None or not inventory.is_file() or is_reparse(inventory):
        raise VerificationError("plan.expected_inventory_ref must resolve to a regular in-bundle file")
    root["_inventory_path"] = inventory

    defaults = require_keys(
        root["document_defaults"],
        {"allowed_status", "indexable", "canonical", "require_title", "require_description", "require_h1"},
        {"allowed_status", "indexable", "canonical", "require_title", "require_description", "require_h1"},
        "plan.document_defaults",
    )
    defaults["allowed_status"] = status_list(defaults["allowed_status"], "plan.document_defaults.allowed_status")
    boolean(defaults["indexable"], "plan.document_defaults.indexable")
    if defaults["canonical"] not in {"self", "none"}:
        raise VerificationError("plan.document_defaults.canonical must be self or none")
    for field in ("require_title", "require_description", "require_h1"):
        boolean(defaults[field], f"plan.document_defaults.{field}")

    if not isinstance(root["document_overrides"], list):
        raise VerificationError("plan.document_overrides must be an array")
    override_urls: set[str] = set()
    for index, raw in enumerate(root["document_overrides"]):
        allowed = {
            "url",
            "allowed_status",
            "indexable",
            "canonical",
            "require_title",
            "require_description",
            "require_h1",
            "expected_title",
            "expected_description",
            "expected_h1",
            "expected_hreflang",
        }
        row = require_keys(raw, {"url"}, allowed, f"plan.document_overrides[{index}]")
        row["url"] = absolute_url(row["url"], f"plan.document_overrides[{index}].url", root["origin"])
        if row["url"] in override_urls:
            raise VerificationError("plan.document_overrides URLs must be unique")
        override_urls.add(row["url"])
        if "allowed_status" in row:
            row["allowed_status"] = status_list(row["allowed_status"], f"plan.document_overrides[{index}].allowed_status")
        for field in ("indexable", "require_title", "require_description", "require_h1"):
            if field in row:
                boolean(row[field], f"plan.document_overrides[{index}].{field}")
        for field in ("expected_title", "expected_description", "expected_h1"):
            if field in row and (not isinstance(row[field], str) or not row[field].strip()):
                raise VerificationError(f"plan.document_overrides[{index}].{field} must be a non-empty string")
        if "canonical" in row and row["canonical"] not in {"self", "none"}:
            row["canonical"] = absolute_url(row["canonical"], f"plan.document_overrides[{index}].canonical", root["origin"])
        if "expected_hreflang" in row:
            if not isinstance(row["expected_hreflang"], dict) or not row["expected_hreflang"]:
                raise VerificationError(f"plan.document_overrides[{index}].expected_hreflang must be a non-empty object")
            for locale, url in row["expected_hreflang"].items():
                if not isinstance(locale, str) or not locale:
                    raise VerificationError(f"plan.document_overrides[{index}].expected_hreflang has invalid locale")
                row["expected_hreflang"][locale] = absolute_url(
                    url, f"plan.document_overrides[{index}].expected_hreflang.{locale}", root["origin"]
                )

    if not isinstance(root["redirects"], list):
        raise VerificationError("plan.redirects must be an array")
    redirect_sources: set[str] = set()
    for index, raw in enumerate(root["redirects"]):
        row = require_keys(raw, {"source", "target", "allowed_status"}, {"source", "target", "allowed_status"}, f"plan.redirects[{index}]")
        row["source"] = absolute_url(row["source"], f"plan.redirects[{index}].source", root["origin"])
        row["target"] = absolute_url(row["target"], f"plan.redirects[{index}].target", root["origin"])
        row["allowed_status"] = status_list(row["allowed_status"], f"plan.redirects[{index}].allowed_status")
        if row["source"] in redirect_sources:
            raise VerificationError("plan.redirects source URLs must be unique")
        redirect_sources.add(row["source"])

    if not isinstance(root["surfaces"], list):
        raise VerificationError("plan.surfaces must be an array")
    surface_urls: set[str] = set()
    for index, raw in enumerate(root["surfaces"]):
        allowed = {"surface_id", "url", "allowed_status", "content_type_prefix", "required_text"}
        row = require_keys(raw, {"surface_id", "url", "allowed_status"}, allowed, f"plan.surfaces[{index}]")
        if not isinstance(row["surface_id"], str) or not row["surface_id"]:
            raise VerificationError(f"plan.surfaces[{index}].surface_id must be non-empty")
        row["url"] = absolute_url(row["url"], f"plan.surfaces[{index}].url", root["origin"])
        row["allowed_status"] = status_list(row["allowed_status"], f"plan.surfaces[{index}].allowed_status")
        for optional in ("content_type_prefix", "required_text"):
            if optional in row and (not isinstance(row[optional], str) or not row[optional]):
                raise VerificationError(f"plan.surfaces[{index}].{optional} must be non-empty")
        if row["url"] in surface_urls:
            raise VerificationError("plan.surfaces URLs must be unique")
        surface_urls.add(row["url"])

    network = require_keys(root["network"], {"concurrency", "retries", "timeout_seconds"}, {"concurrency", "retries", "timeout_seconds"}, "plan.network")
    network["concurrency"] = integer(network["concurrency"], "plan.network.concurrency", 1, 32)
    network["retries"] = integer(network["retries"], "plan.network.retries", 0, 5)
    network["timeout_seconds"] = integer(network["timeout_seconds"], "plan.network.timeout_seconds", 1, 30)
    boolean(root["rendered_required"], "plan.rendered_required")
    if "site_identity" in root:
        identity_fields = {
            "homepage_url",
            "expected_favicon_url",
            "minimum_size_px",
            "require_recommended_size",
        }
        identity = require_keys(root["site_identity"], identity_fields, identity_fields, "plan.site_identity")
        identity["homepage_url"] = absolute_url(identity["homepage_url"], "plan.site_identity.homepage_url", root["origin"])
        identity["expected_favicon_url"] = absolute_url(
            identity["expected_favicon_url"], "plan.site_identity.expected_favicon_url"
        )
        identity["minimum_size_px"] = integer(identity["minimum_size_px"], "plan.site_identity.minimum_size_px", 8, 4096)
        boolean(identity["require_recommended_size"], "plan.site_identity.require_recommended_size")
    return root


def status_list(value: object, field: str) -> list[int]:
    if not isinstance(value, list) or not value or len(value) != len(set(value)):
        raise VerificationError(f"{field} must be a non-empty unique array")
    return [integer(item, f"{field}[]", 100, 599) for item in value]


def ensure_network_target(url: str, allow_private: bool) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme == "http" and not allow_private:
        raise VerificationError(f"refusing non-HTTPS target: {url}")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except OSError as exc:
        raise VerificationError(f"DNS resolution failed for {url}: {exc}") from exc
    for row in addresses:
        address = ipaddress.ip_address(row[4][0])
        unsafe = not address.is_global
        if unsafe and not allow_private:
            raise VerificationError(f"refusing private, loopback, reserved, or non-global target: {url}")


def fetch(url: str, retries: int, timeout: int, allow_private: bool) -> FetchResult:
    transient: list[str] = []
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    for attempt in range(1, retries + 2):
        try:
            ensure_network_target(url, allow_private)
            request = urllib.request.Request(url, headers={"User-Agent": "SEO-AEO-GEO-Ultimate-LiveVerifier/1.0"})
            try:
                response = opener.open(request, timeout=timeout)
            except urllib.error.HTTPError as exc:
                response = exc
            status = int(response.getcode())
            headers = {name.lower(): value for name, value in response.headers.items()}
            body = response.read(MAX_BODY_BYTES + 1)
            if len(body) > MAX_BODY_BYTES:
                return FetchResult(url, status, headers, b"", attempt, tuple(transient), "response exceeds 5 MB limit")
            if status in TRANSIENT_STATUSES and attempt <= retries:
                transient.append(f"HTTP {status}")
                time.sleep(min(0.05 * attempt, 0.2))
                continue
            error = f"transient HTTP {status} exhausted" if status in TRANSIENT_STATUSES else None
            return FetchResult(url, status, headers, body, attempt, tuple(transient), error)
        except (urllib.error.URLError, TimeoutError, socket.timeout, VerificationError, OSError) as exc:
            if attempt <= retries:
                transient.append(type(exc).__name__)
                time.sleep(min(0.05 * attempt, 0.2))
                continue
            return FetchResult(url, None, {}, b"", attempt, tuple(transient), f"{type(exc).__name__}: {exc}")
    raise AssertionError("fetch retry loop exhausted unexpectedly")


def normalize_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value.strip())
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))


def parse_inventory(path: Path, origin: str) -> set[str]:
    content = path.read_bytes()
    suffix = path.suffix.lower()
    values: list[str]
    try:
        if suffix == ".json":
            payload = json.loads(content.decode("utf-8-sig"))
            values = payload if isinstance(payload, list) else payload.get("urls") if isinstance(payload, dict) else None
            if not isinstance(values, list):
                raise VerificationError("expected inventory JSON must be an array or an object with urls")
        elif suffix == ".xml" or content.lstrip().startswith(b"<"):
            root = ET.fromstring(content)
            if root.tag.rsplit("}", 1)[-1] != "urlset":
                raise VerificationError("expected inventory XML must be one urlset, not a sitemap index")
            values = [element.text.strip() for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "loc" and element.text]
        else:
            values = [line.strip() for line in content.decode("utf-8-sig").splitlines() if line.strip() and not line.lstrip().startswith("#")]
    except (UnicodeDecodeError, json.JSONDecodeError, ET.ParseError) as exc:
        raise VerificationError(f"cannot parse expected inventory: {exc}") from exc
    if not values or len(values) > MAX_URLS or any(not isinstance(value, str) for value in values):
        raise VerificationError("expected inventory must contain 1 through 100000 URLs")
    normalized = {normalize_url(absolute_url(value, "expected inventory URL", origin)) for value in values}
    if len(normalized) != len(values):
        raise VerificationError("expected inventory contains duplicate URLs after normalization")
    return normalized


def parse_sitemap_body(body: bytes, source_url: str, origin: str) -> tuple[str, list[str]]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise VerificationError(f"live sitemap XML is invalid at {source_url}: {exc}") from exc
    kind = root.tag.rsplit("}", 1)[-1]
    if kind not in {"urlset", "sitemapindex"}:
        raise VerificationError(f"live sitemap root must be urlset or sitemapindex at {source_url}")
    values = [element.text.strip() for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "loc" and element.text]
    return kind, [absolute_url(value, f"live sitemap loc in {source_url}", origin) for value in values]


def fetch_live_inventory(plan: dict[str, Any], allow_private: bool, fetch_records: dict[str, FetchResult]) -> set[str]:
    pending = [plan["live_sitemap_url"]]
    visited: set[str] = set()
    urls: set[str] = set()
    network = plan["network"]
    while pending:
        sitemap_url = pending.pop(0)
        if sitemap_url in visited:
            continue
        if len(visited) >= MAX_SITEMAP_FILES:
            raise VerificationError("live sitemap index exceeds 50 files")
        visited.add(sitemap_url)
        result = fetch(sitemap_url, network["retries"], network["timeout_seconds"], allow_private)
        fetch_records[sitemap_url] = result
        if result.error or result.status != 200:
            raise VerificationError(f"live sitemap fetch failed at {sitemap_url}: {result.error or 'HTTP ' + str(result.status)}")
        kind, values = parse_sitemap_body(result.body, sitemap_url, plan["origin"])
        if kind == "sitemapindex":
            pending.extend(values)
        else:
            urls.update(normalize_url(value) for value in values)
        if len(urls) > MAX_URLS:
            raise VerificationError("live sitemap inventory exceeds 100000 URLs")
    return urls


def merged_expectation(plan: dict[str, Any], url: str) -> dict[str, Any]:
    expected = dict(plan["document_defaults"])
    for row in plan["document_overrides"]:
        if normalize_url(row["url"]) == url:
            expected.update({key: value for key, value in row.items() if key != "url"})
            break
    return expected


def document_checks(url: str, expected: dict[str, Any], result: FetchResult) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    observed: dict[str, Any] = {"status": result.status, "attempts": result.attempts, "transient_failures": list(result.transient_failures)}
    if result.error:
        failures.append({"check": "fetch", "expected": "successful final response", "actual": result.error, "classification": "transient-exhausted" if result.status in TRANSIENT_STATUSES or result.transient_failures else "permanent"})
        return failures, observed
    if result.status not in expected["allowed_status"]:
        failures.append({"check": "status", "expected": expected["allowed_status"], "actual": result.status, "classification": "permanent"})
    content_type = result.headers.get("content-type", "").lower()
    observed["content_type"] = content_type
    parser = PageParser()
    try:
        parser.feed(result.body.decode("utf-8", errors="replace"))
    except Exception as exc:  # HTMLParser should be tolerant; retain any exceptional parser failure.
        failures.append({"check": "html-parse", "expected": "parseable HTML", "actual": str(exc), "classification": "permanent"})
        return failures, observed
    canonical_values = [normalize_url(urllib.parse.urljoin(url, value)) for value in parser.canonicals]
    x_robots = result.headers.get("x-robots-tag", "").lower()
    robots = ",".join([*parser.meta_robots, x_robots])
    observed.update(
        {
            "title": parser.title,
            "description": parser.description,
            "h1": parser.h1,
            "canonical": canonical_values,
            "robots": robots,
            "hreflang": {key: [normalize_url(urllib.parse.urljoin(url, value)) for value in values] for key, values in parser.hreflang.items()},
        }
    )
    if expected["indexable"] and "noindex" in robots:
        failures.append({"check": "indexability", "expected": "no noindex directive", "actual": robots, "classification": "permanent"})
    if not expected["indexable"] and "noindex" not in robots:
        failures.append({"check": "indexability", "expected": "noindex directive", "actual": robots or "absent", "classification": "permanent"})
    canonical = expected["canonical"]
    if canonical == "self":
        expected_canonical: str | None = url
    elif canonical == "none":
        expected_canonical = None
    else:
        expected_canonical = normalize_url(canonical)
    if expected_canonical is None and canonical_values:
        failures.append({"check": "canonical", "expected": "absent", "actual": canonical_values, "classification": "permanent"})
    elif expected_canonical is not None and canonical_values != [expected_canonical]:
        failures.append({"check": "canonical", "expected": [expected_canonical], "actual": canonical_values, "classification": "permanent"})
    for field, actual in (("title", parser.title), ("description", parser.description or ""), ("h1", parser.h1)):
        if expected[f"require_{field}"] and not actual.strip():
            failures.append({"check": field, "expected": "non-empty", "actual": "absent", "classification": "permanent"})
        expected_copy = expected.get(f"expected_{field}")
        if expected_copy is not None:
            normalized_expected = " ".join(expected_copy.split())
            normalized_actual = " ".join(actual.split())
            if normalized_actual != normalized_expected:
                failures.append(
                    {
                        "check": f"{field}-copy",
                        "expected": normalized_expected,
                        "actual": normalized_actual or "absent",
                        "classification": "permanent",
                    }
                )
    for locale, href in expected.get("expected_hreflang", {}).items():
        actual = observed["hreflang"].get(locale.lower(), [])
        normalized_expected = normalize_url(href)
        if normalized_expected not in actual:
            failures.append({"check": f"hreflang:{locale}", "expected": normalized_expected, "actual": actual, "classification": "permanent"})
    return failures, observed


def redirect_checks(row: dict[str, Any], result: FetchResult, live_inventory: set[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    observed = {"status": result.status, "location": result.headers.get("location"), "attempts": result.attempts, "transient_failures": list(result.transient_failures)}
    if result.error:
        failures.append({"check": "fetch", "expected": "redirect response", "actual": result.error, "classification": "transient-exhausted" if result.transient_failures else "permanent"})
        return failures, observed
    if result.status not in row["allowed_status"]:
        failures.append({"check": "status", "expected": row["allowed_status"], "actual": result.status, "classification": "permanent"})
    location = result.headers.get("location")
    actual_target = normalize_url(urllib.parse.urljoin(row["source"], location)) if location else None
    expected_target = normalize_url(row["target"])
    if actual_target != expected_target:
        failures.append({"check": "location", "expected": expected_target, "actual": actual_target, "classification": "permanent"})
    if normalize_url(row["source"]) in live_inventory:
        failures.append({"check": "sitemap-exclusion", "expected": "source absent", "actual": "source present", "classification": "permanent"})
    return failures, observed


def numeric_svg_dimension(value: str | None) -> float | None:
    if value is None:
        return None
    matched = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)(?:px)?\s*", value, flags=re.IGNORECASE)
    return float(matched.group(1)) if matched else None


def image_dimensions(body: bytes, content_type: str) -> tuple[float, float] | None:
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        offset = 8
        dimensions: tuple[float, float] | None = None
        while offset + 12 <= len(body):
            length = struct.unpack(">I", body[offset : offset + 4])[0]
            chunk_type = body[offset + 4 : offset + 8]
            end = offset + 12 + length
            if end > len(body):
                return None
            data = body[offset + 8 : offset + 8 + length]
            expected_crc = struct.unpack(">I", body[offset + 8 + length : end])[0]
            if zlib.crc32(chunk_type + data) & 0xFFFFFFFF != expected_crc:
                return None
            if chunk_type == b"IHDR":
                if offset != 8 or length != 13:
                    return None
                width, height = struct.unpack(">II", data[:8])
                if width == 0 or height == 0:
                    return None
                dimensions = (float(width), float(height))
            if chunk_type == b"IEND":
                return dimensions if length == 0 and end == len(body) else None
            offset = end
        return None
    if body[:6] in {b"GIF87a", b"GIF89a"} and len(body) >= 14 and body.endswith(b";"):
        width, height = struct.unpack("<HH", body[6:10])
        return (float(width), float(height)) if width and height else None
    if body.startswith(b"\x00\x00\x01\x00") and len(body) >= 8:
        count = struct.unpack("<H", body[4:6])[0]
        if count and len(body) >= 6 + count * 16:
            sizes: list[tuple[float, float]] = []
            for index in range(count):
                start = 6 + index * 16
                size, offset = struct.unpack("<II", body[start + 8 : start + 16])
                if size == 0 or offset < 6 + count * 16 or offset + size > len(body):
                    return None
                sizes.append((float(body[start] or 256), float(body[start + 1] or 256)))
            return max(sizes, key=lambda pair: min(pair))
    if content_type.lower().startswith("image/svg+xml") or body.lstrip().startswith(b"<svg"):
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            return None
        if root.tag.rsplit("}", 1)[-1].lower() != "svg":
            return None
        width = numeric_svg_dimension(root.attrib.get("width"))
        height = numeric_svg_dimension(root.attrib.get("height"))
        if width is not None and height is not None:
            return width, height
        view_box = root.attrib.get("viewBox") or root.attrib.get("viewbox")
        if view_box:
            values = view_box.replace(",", " ").split()
            if len(values) == 4:
                try:
                    return float(values[2]), float(values[3])
                except ValueError:
                    return None
    return None


def site_identity_checks(
    row: dict[str, Any], homepage: FetchResult, favicon: FetchResult
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    failures: list[dict[str, Any]] = []
    warnings: list[str] = []
    expected_icon = normalize_url(row["expected_favicon_url"])
    observed: dict[str, Any] = {
        "homepage_status": homepage.status,
        "favicon_status": favicon.status,
        "favicon_content_type": favicon.headers.get("content-type", ""),
        "favicon_url": expected_icon,
        "declared_icon_urls": [],
        "dimensions": None,
    }
    if homepage.error or homepage.status != 200:
        failures.append({
            "check": "homepage-fetch",
            "expected": "HTTP 200 home page",
            "actual": homepage.error or homepage.status,
            "classification": "transient-exhausted" if homepage.transient_failures else "permanent",
        })
    else:
        parser = PageParser()
        parser.feed(homepage.body.decode("utf-8", errors="replace"))
        declared = sorted({normalize_url(urllib.parse.urljoin(row["homepage_url"], href)) for href in parser.icons})
        observed["declared_icon_urls"] = declared
        if expected_icon not in declared:
            failures.append({
                "check": "homepage-favicon-link",
                "expected": expected_icon,
                "actual": declared or "absent",
                "classification": "permanent",
            })
    if favicon.error or favicon.status != 200:
        failures.append({
            "check": "favicon-fetch",
            "expected": "HTTP 200 favicon",
            "actual": favicon.error or favicon.status,
            "classification": "transient-exhausted" if favicon.transient_failures else "permanent",
        })
        return failures, observed, warnings
    content_type = favicon.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if not content_type.startswith("image/"):
        failures.append({
            "check": "favicon-content-type",
            "expected": "image/*",
            "actual": content_type or "absent",
            "classification": "permanent",
        })
    dimensions = image_dimensions(favicon.body, content_type)
    observed["dimensions"] = list(dimensions) if dimensions is not None else None
    if dimensions is None:
        failures.append({
            "check": "favicon-dimensions",
            "expected": "verifiable square image dimensions",
            "actual": "unrecognized or invalid image bytes",
            "classification": "permanent",
        })
    else:
        width, height = dimensions
        if width != height:
            failures.append({
                "check": "favicon-aspect-ratio",
                "expected": "1:1 square",
                "actual": f"{width:g}x{height:g}",
                "classification": "permanent",
            })
        if min(width, height) < row["minimum_size_px"]:
            failures.append({
                "check": "favicon-minimum-size",
                "expected": f"at least {row['minimum_size_px']}x{row['minimum_size_px']}",
                "actual": f"{width:g}x{height:g}",
                "classification": "permanent",
            })
        if max(width, height) <= 48:
            message = "favicon meets the declared minimum but is not larger than Google's 48x48 quality recommendation"
            if row["require_recommended_size"]:
                failures.append({
                    "check": "favicon-recommended-size",
                    "expected": "square image larger than 48x48",
                    "actual": f"{width:g}x{height:g}",
                    "classification": "permanent",
                })
            else:
                warnings.append(message)
    return failures, observed, warnings


def surface_checks(row: dict[str, Any], result: FetchResult) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    content_type = result.headers.get("content-type", "")
    observed = {"status": result.status, "content_type": content_type, "attempts": result.attempts, "transient_failures": list(result.transient_failures)}
    if result.error:
        failures.append({"check": "fetch", "expected": "successful final response", "actual": result.error, "classification": "transient-exhausted" if result.transient_failures else "permanent"})
        return failures, observed
    if result.status not in row["allowed_status"]:
        failures.append({"check": "status", "expected": row["allowed_status"], "actual": result.status, "classification": "permanent"})
    prefix = row.get("content_type_prefix")
    if prefix and not content_type.lower().startswith(prefix.lower()):
        failures.append({"check": "content-type", "expected": prefix, "actual": content_type, "classification": "permanent"})
    required = row.get("required_text")
    if required and required not in result.body.decode("utf-8", errors="replace"):
        failures.append({"check": "required-text", "expected": required, "actual": "absent", "classification": "permanent"})
    return failures, observed


def run_verification(plan: dict[str, Any], plan_path: Path, allow_private: bool) -> dict[str, Any]:
    inventory_path: Path = plan["_inventory_path"]
    expected = parse_inventory(inventory_path, plan["origin"])
    expected_set_sha256 = digest_bytes(("\n".join(sorted(expected)) + "\n").encode("utf-8"))
    candidate_corpus = plan["_candidate_manifest"]["corpus"]
    if candidate_corpus["expected_count"] != len(expected) or candidate_corpus["sha256"] != expected_set_sha256:
        raise VerificationError("candidate manifest corpus identity does not match the expected inventory")
    override_urls = {normalize_url(row["url"]) for row in plan["document_overrides"]}
    if override_urls - expected:
        raise VerificationError("document override URLs must belong to the expected inventory")
    expectations = {url: merged_expectation(plan, url) for url in expected}
    expected_indexable = {url for url, row in expectations.items() if row["indexable"]}
    expected_nonindex = expected - expected_indexable
    fetch_records: dict[str, FetchResult] = {}
    failures: list[dict[str, Any]] = []
    try:
        live = fetch_live_inventory(plan, allow_private, fetch_records)
    except VerificationError as exc:
        live = set()
        failures.append({"kind": "sitemap", "url": plan["live_sitemap_url"], "check": "fetch-or-parse", "expected": "valid complete live sitemap", "actual": str(exc), "classification": "permanent"})
    missing = sorted(expected_indexable - live)
    unexpected = sorted(live - expected_indexable) if plan["sitemap_mode"] == "exact" else []
    excluded_present = sorted(expected_nonindex & live)
    if missing:
        failures.append({"kind": "sitemap", "url": plan["live_sitemap_url"], "check": "missing-urls", "expected": 0, "actual": len(missing), "classification": "permanent"})
    if unexpected:
        failures.append({"kind": "sitemap", "url": plan["live_sitemap_url"], "check": "unexpected-urls", "expected": 0, "actual": len(unexpected), "classification": "permanent"})
    if excluded_present:
        failures.append({"kind": "sitemap", "url": plan["live_sitemap_url"], "check": "nonindex-urls-present", "expected": 0, "actual": len(excluded_present), "classification": "permanent"})

    identity_urls: set[str] = set()
    if "site_identity" in plan:
        identity_urls = {
            normalize_url(plan["site_identity"]["homepage_url"]),
            normalize_url(plan["site_identity"]["expected_favicon_url"]),
        }
    urls_to_fetch = sorted(
        expected
        | {normalize_url(row["source"]) for row in plan["redirects"]}
        | {normalize_url(row["url"]) for row in plan["surfaces"]}
        | identity_urls
    )
    network = plan["network"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=network["concurrency"]) as executor:
        future_map = {
            executor.submit(fetch, url, network["retries"], network["timeout_seconds"], allow_private): url
            for url in urls_to_fetch
            if url not in fetch_records
        }
        for future in concurrent.futures.as_completed(future_map):
            fetch_records[future_map[future]] = future.result()

    documents: list[dict[str, Any]] = []
    for url in sorted(expected):
        expectation = expectations[url]
        item_failures, observed = document_checks(url, expectation, fetch_records[url])
        kind = "indexable-document" if expectation["indexable"] else "nonindex-document"
        documents.append({"url": url, "kind": kind, "status": "fail" if item_failures else "pass", "observed": observed, "failures": item_failures})
        failures.extend({"kind": kind, "url": url, **failure} for failure in item_failures)

    redirects: list[dict[str, Any]] = []
    for row in plan["redirects"]:
        source = normalize_url(row["source"])
        item_failures, observed = redirect_checks(row, fetch_records[source], live)
        target = normalize_url(row["target"])
        if target not in expected:
            item_failures.append({"check": "target-contract", "expected": "target present in expected indexable inventory", "actual": "absent", "classification": "permanent"})
        redirects.append({"source": source, "target": target, "status": "fail" if item_failures else "pass", "observed": observed, "failures": item_failures})
        failures.extend({"kind": "redirect", "url": source, **failure} for failure in item_failures)

    surfaces: list[dict[str, Any]] = []
    for row in plan["surfaces"]:
        url = normalize_url(row["url"])
        item_failures, observed = surface_checks(row, fetch_records[url])
        surfaces.append({"surface_id": row["surface_id"], "url": url, "status": "fail" if item_failures else "pass", "observed": observed, "failures": item_failures})
        failures.extend({"kind": "surface", "url": url, **failure} for failure in item_failures)

    site_identity: dict[str, Any] | None = None
    identity_warnings: list[str] = []
    if "site_identity" in plan:
        identity = plan["site_identity"]
        homepage_url = normalize_url(identity["homepage_url"])
        favicon_url = normalize_url(identity["expected_favicon_url"])
        item_failures, observed, identity_warnings = site_identity_checks(
            identity, fetch_records[homepage_url], fetch_records[favicon_url]
        )
        site_identity = {
            "homepage_url": homepage_url,
            "expected_favicon_url": favicon_url,
            "status": "fail" if item_failures else "pass",
            "observed": observed,
            "warnings": identity_warnings,
            "failures": item_failures,
        }
        failures.extend({"kind": "site-identity", "url": homepage_url, **failure} for failure in item_failures)

    if plan["rendered_required"]:
        failures.append({"kind": "rendered", "url": plan["origin"], "check": "hydrated-ui", "expected": "separate rendered verification", "actual": "unsupported by raw verifier", "classification": "permanent"})

    attempts = [
        {
            "url": url,
            "attempts": result.attempts,
            "transient_failures": list(result.transient_failures),
            "recovered": bool(result.transient_failures) and result.error is None and result.status not in TRANSIENT_STATUSES,
            "final_status": result.status,
            "final_error": result.error,
        }
        for url, result in sorted(fetch_records.items())
    ]
    recovered = [row for row in attempts if row["recovered"]]
    permanent = [row for row in failures if row["classification"] == "permanent"]
    transient_exhausted = [row for row in failures if row["classification"] == "transient-exhausted"]
    normalized_plan = {key: value for key, value in plan.items() if not key.startswith("_")}
    return {
        "schema_version": "1.0.0",
        "release_id": plan["release_id"],
        "candidate": {
            **plan["candidate"],
            "manifest_file_sha256": digest_bytes(plan["_candidate_manifest_path"].read_bytes()),
            "build_identity": plan["_candidate_manifest"]["build_identity"],
        },
        "verified_at": now_utc(),
        "result": "fail" if failures else "pass",
        "plan_sha256": digest_bytes(plan_path.read_bytes()),
        "expected_inventory": {
            "ref": plan["expected_inventory_ref"],
            "file_sha256": digest_bytes(inventory_path.read_bytes()),
            "set_sha256": expected_set_sha256,
        },
        "sitemap": {
            "url": plan["live_sitemap_url"],
            "mode": plan["sitemap_mode"],
            "expected_indexable": len(expected_indexable),
            "expected_excluded": len(expected_nonindex),
            "live": len(live),
            "missing_count": len(missing),
            "unexpected_count": len(unexpected),
            "excluded_present_count": len(excluded_present),
            "missing_urls": missing,
            "unexpected_urls": unexpected,
            "excluded_present_urls": excluded_present,
        },
        "counts": {
            "indexable": {"expected": len(expected_indexable), "passed": sum(row["kind"] == "indexable-document" and row["status"] == "pass" for row in documents), "failed": sum(row["kind"] == "indexable-document" and row["status"] == "fail" for row in documents)},
            "nonindex": {"expected": len(expected_nonindex), "passed": sum(row["kind"] == "nonindex-document" and row["status"] == "pass" for row in documents), "failed": sum(row["kind"] == "nonindex-document" and row["status"] == "fail" for row in documents)},
            "redirects": {"expected": len(redirects), "passed": sum(row["status"] == "pass" for row in redirects), "failed": sum(row["status"] == "fail" for row in redirects)},
            "surfaces": {"expected": len(surfaces), "passed": sum(row["status"] == "pass" for row in surfaces), "failed": sum(row["status"] == "fail" for row in surfaces)},
            "site_identity": {
                "expected": 1 if site_identity is not None else 0,
                "passed": 1 if site_identity is not None and site_identity["status"] == "pass" else 0,
                "failed": 1 if site_identity is not None and site_identity["status"] == "fail" else 0,
            },
        },
        "documents": documents,
        "redirects": redirects,
        "surfaces": surfaces,
        "site_identity": site_identity,
        "attempts": attempts,
        "recovered_transient_requests": recovered,
        "permanent_failures": permanent,
        "transient_exhausted_failures": transient_exhausted,
        "failures": failures,
        "rendered_verification": "required-but-unsupported" if plan["rendered_required"] else "not-required-by-plan",
        "limitations": [
            "Raw HTTP/HTML and sitemap verification only; JavaScript hydration is not rendered.",
            *(identity_warnings if identity_warnings else []),
            *([] if site_identity is not None else ["Hostname favicon/site identity was not declared in this release plan."]),
            "The report does not deploy, mutate a search provider, or prove crawl, indexing, ranking, retrieval, citation, referral, traffic, or conversion.",
        ],
        "normalized_plan": normalized_plan,
    }


def safe_output(path: Path, overwrite: bool) -> None:
    if path.exists():
        if is_reparse(path) or not path.is_file():
            raise VerificationError("output must be a regular non-reparse file")
        if not overwrite:
            raise VerificationError("output exists; pass --overwrite to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    if is_reparse(path.parent):
        raise VerificationError("output parent must not be a symlink or reparse point")


def write_report(path: Path, report: dict[str, Any], overwrite: bool) -> None:
    safe_output(path, overwrite)
    content = (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify an exact live SEO release without deploying or mutating providers.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--plan", required=True, type=Path)
    verify.add_argument("--output", required=True, type=Path)
    verify.add_argument("--overwrite", action="store_true")
    verify.add_argument("--allow-private-targets", action="store_true", help="allow HTTP/private targets for controlled local testing")
    args = parser.parse_args()
    try:
        plan_path = args.plan.resolve()
        if not plan_path.is_file() or is_reparse(plan_path):
            raise VerificationError("plan must be a regular non-reparse file")
        plan = validate_plan(load_json(plan_path), plan_path)
        report = run_verification(plan, plan_path, args.allow_private_targets)
        write_report(args.output.resolve(), report, args.overwrite)
    except VerificationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if report["result"] != "pass":
        print(
            f"FAIL: live release {report['release_id']} with {len(report['failures'])} failure(s); report={args.output}",
            file=sys.stderr,
        )
        return 1
    print(f"PASS: live release {report['release_id']}; report={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
