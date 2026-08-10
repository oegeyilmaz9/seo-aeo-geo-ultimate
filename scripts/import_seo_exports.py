#!/usr/bin/env python3
"""Normalize credential-free SEO exports without inventing observations.

The performance adapters emit the exact source-envelope shape consumed by
``validate_seo_performance.py`` plus a hash-bound provenance sidecar. Crawler
and access-log adapters emit observation envelopes because those exports do not
contain the raw HTML, metadata captures, or metric definitions required to
pretend they are a Site Graph or SEO Performance Run.
"""

from __future__ import annotations

import argparse
import codecs
import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
import re
import stat
import sys
import tempfile
import unicodedata
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import SplitResult, urljoin, urlsplit, urlunsplit

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover - Python 3.9+ is required by the suite.
    ZoneInfo = None  # type: ignore[assignment]
    ZoneInfoNotFoundError = Exception  # type: ignore[assignment]


ADAPTER_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"
DELIMITERS = {"comma": ",", "tab": "\t", "semicolon": ";"}
DIMENSION_ORDER = ("date", "query", "page", "country", "device", "search_appearance")
PERFORMANCE_ROW_FIELDS = (
    "row_id", "date", "query", "page", "country", "device", "search_appearance",
    "clicks", "impressions", "ctr", "average_position", "organic_sessions",
    "conversions", "revenue",
)


class ImportFailure(ValueError):
    """A user-facing import validation error."""


def digest_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def normalized_header(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().casefold()
    return " ".join(value.split())


def decode_text(path: Path) -> tuple[str, str, bytes]:
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ImportFailure(f"cannot read source file: {exc}") from exc
    if not content:
        raise ImportFailure("source file is empty")
    if content.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        encoding = "utf-16"
    else:
        encoding = "utf-8-sig"
    try:
        text = content.decode(encoding)
    except UnicodeDecodeError as exc:
        raise ImportFailure("source must be UTF-8 (optional BOM) or BOM-marked UTF-16") from exc
    if "\x00" in text:
        raise ImportFailure("decoded source contains NUL characters")
    return text, encoding, content


def alias_lookup(aliases: dict[str, set[str]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical, names in aliases.items():
        for name in names | {canonical}:
            key = normalized_header(name)
            if key in lookup and lookup[key] != canonical:
                raise RuntimeError(f"internal alias collision for {name!r}")
            lookup[key] = canonical
    return lookup


def map_headers(headers: list[str], aliases: dict[str, set[str]], required: set[str]) -> tuple[dict[str, int], list[str]]:
    if not headers or any(not header.strip() for header in headers):
        raise ImportFailure("CSV header contains an empty column name")
    normalized = [normalized_header(header) for header in headers]
    if len(normalized) != len(set(normalized)):
        raise ImportFailure("CSV header contains duplicate column names")
    lookup = alias_lookup(aliases)
    mapped: dict[str, int] = {}
    ignored: list[str] = []
    for index, (header, key) in enumerate(zip(headers, normalized)):
        canonical = lookup.get(key)
        if canonical is None:
            ignored.append(header)
            continue
        if canonical in mapped:
            first = headers[mapped[canonical]]
            raise ImportFailure(
                f"ambiguous headers {first!r} and {header!r} both map to {canonical!r}"
            )
        mapped[canonical] = index
    missing = sorted(required - set(mapped))
    if missing:
        raise ImportFailure("missing required header(s): " + ", ".join(missing))
    return mapped, ignored


def parsed_csv(
    path: Path,
    aliases: dict[str, set[str]],
    required: set[str],
    delimiter_name: str,
) -> tuple[list[str], list[list[str]], dict[str, int], list[str], str, str, bytes]:
    text, encoding, content = decode_text(path)
    choices = DELIMITERS if delimiter_name == "auto" else {delimiter_name: DELIMITERS[delimiter_name]}
    candidates: list[tuple[str, list[list[str]], dict[str, int], list[str]]] = []
    failures: list[str] = []
    for name, delimiter in choices.items():
        try:
            rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True))
        except csv.Error as exc:
            failures.append(f"{name}: malformed CSV ({exc})")
            continue
        rows = [row for row in rows if any(cell.strip() for cell in row)]
        if not rows:
            failures.append(f"{name}: no non-empty CSV rows")
            continue
        width = len(rows[0])
        if width < 2:
            failures.append(f"{name}: header has fewer than two columns")
            continue
        malformed_index = next((index for index, row in enumerate(rows[1:], start=2) if len(row) != width), None)
        if malformed_index is not None:
            failures.append(f"{name}: row {malformed_index} has a different column count")
            continue
        try:
            mapped, ignored = map_headers(rows[0], aliases, required)
        except ImportFailure as exc:
            failures.append(f"{name}: {exc}")
            continue
        candidates.append((name, rows, mapped, ignored))
    if not candidates:
        raise ImportFailure("could not identify a valid CSV delimiter/header mapping; " + "; ".join(failures))
    if len(candidates) > 1:
        names = ", ".join(candidate[0] for candidate in candidates)
        raise ImportFailure(f"ambiguous CSV delimiter; valid interpretations: {names}; pass --delimiter")
    name, rows, mapped, ignored = candidates[0]
    if len(rows) == 1:
        raise ImportFailure("CSV contains a header but no data rows")
    return rows[0], rows[1:], mapped, ignored, name, encoding, content


def raw_value(row: list[str], mapping: dict[str, int], field: str) -> str | None:
    if field not in mapping:
        return None
    value = row[mapping[field]].strip()
    return value if value else None


INTEGER_RE = re.compile(r"^\d+$")
DECIMAL_RE = re.compile(r"^(?:\d+(?:\.\d+)?|\.\d+)$")


def parse_nonnegative_int(value: str | None, field: str, row_number: int, *, required: bool = False) -> int | None:
    if value is None:
        if required:
            raise ImportFailure(f"row {row_number}: {field} is required")
        return None
    if not INTEGER_RE.fullmatch(value):
        raise ImportFailure(f"row {row_number}: {field} must be a non-negative integer without grouping separators")
    return int(value)


def parse_nonnegative_number(value: str | None, field: str, row_number: int) -> int | float | None:
    if value is None:
        return None
    if not DECIMAL_RE.fullmatch(value):
        raise ImportFailure(f"row {row_number}: {field} must be a non-negative base-10 number")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:  # defensive; the regex already limits input.
        raise ImportFailure(f"row {row_number}: {field} is not numeric") from exc
    if not parsed.is_finite():
        raise ImportFailure(f"row {row_number}: {field} must be finite")
    if parsed == parsed.to_integral_value():
        return int(parsed)
    converted = float(parsed)
    if not math.isfinite(converted):
        raise ImportFailure(f"row {row_number}: {field} is outside the supported finite numeric range")
    return converted


def validate_exported_ctr(value: str | None, clicks: int, impressions: int, row_number: int) -> float | None:
    if clicks > impressions:
        raise ImportFailure(f"row {row_number}: clicks cannot exceed impressions")
    if impressions == 0:
        if clicks != 0:
            raise ImportFailure(f"row {row_number}: clicks cannot be positive when impressions are zero")
        if value is not None:
            raw = value[:-1] if value.endswith("%") else value
            if not DECIMAL_RE.fullmatch(raw) or Decimal(raw) != 0:
                raise ImportFailure(f"row {row_number}: CTR conflicts with zero impressions")
        return None
    expected = Decimal(clicks) / Decimal(impressions)
    if value is not None:
        percent = value.endswith("%")
        raw = value[:-1].strip() if percent else value
        if not DECIMAL_RE.fullmatch(raw):
            raise ImportFailure(f"row {row_number}: CTR must be a decimal fraction or percentage")
        observed = Decimal(raw) / (Decimal(100) if percent else Decimal(1))
        decimal_places = max(0, -Decimal(raw).as_tuple().exponent)
        unit = Decimal(10) ** (-decimal_places)
        tolerance = unit / (Decimal(200) if percent else Decimal(2))
        if abs(observed - expected) > tolerance + Decimal("1e-12"):
            raise ImportFailure(f"row {row_number}: exported CTR conflicts with clicks/impressions")
    return float(expected)


def parse_instant(value: str, field: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise ImportFailure(f"{field} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ImportFailure(f"{field} must include a UTC offset or Z")
    return parsed


def reporting_tz(value: str) -> dt.tzinfo:
    if value.casefold() == "utc":
        return dt.timezone.utc
    if re.fullmatch(r"[+-]\d{2}:\d{2}", value):
        sign = 1 if value[0] == "+" else -1
        hours, minutes = (int(part) for part in value[1:].split(":"))
        if hours > 23 or minutes > 59:
            raise ImportFailure("timezone offset is out of range")
        return dt.timezone(sign * dt.timedelta(hours=hours, minutes=minutes))
    if ZoneInfo is None:
        raise ImportFailure("named timezones are unavailable; use UTC or an explicit offset")
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ImportFailure(f"unknown timezone {value!r}; use UTC or an explicit offset") from exc


def parse_row_date(value: str | None, timezone: str, row_number: int) -> str | None:
    if value is None:
        return None
    try:
        if re.fullmatch(r"\d{8}", value):
            parsed_date = dt.datetime.strptime(value, "%Y%m%d").date()
            parsed = dt.datetime.combine(parsed_date, dt.time.min, reporting_tz(timezone))
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            parsed_date = dt.date.fromisoformat(value)
            parsed = dt.datetime.combine(parsed_date, dt.time.min, reporting_tz(timezone))
        else:
            parsed = parse_instant(value, f"row {row_number}: date")
    except ValueError as exc:
        raise ImportFailure(f"row {row_number}: date is invalid") from exc
    return parsed.isoformat()


def validate_country(value: str | None, row_number: int) -> str | None:
    if value is None:
        return None
    country = value.upper()
    if not re.fullmatch(r"[A-Z]{2}", country):
        raise ImportFailure(
            f"row {row_number}: country must be an ISO 3166-1 alpha-2 code; names are not guessed"
        )
    return country


def validate_device(value: str | None, row_number: int) -> str | None:
    if value is None:
        return None
    device = value.casefold()
    if device not in {"desktop", "mobile", "tablet", "other"}:
        raise ImportFailure(f"row {row_number}: unsupported device value {value!r}")
    return device


def split_url(value: str, context: str) -> SplitResult:
    try:
        return urlsplit(value)
    except ValueError as exc:
        raise ImportFailure(f"{context} is not a valid URL") from exc


def normalized_authority(parsed: SplitResult, context: str) -> str:
    if parsed.username is not None or parsed.password is not None:
        raise ImportFailure(f"{context} cannot contain credentials")
    hostname = parsed.hostname
    if hostname is None:
        raise ImportFailure(f"{context} must include a hostname")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ImportFailure(f"{context} contains an invalid port") from exc
    host = hostname.casefold()
    if ":" in host:
        host = f"[{host}]"
    return f"{host}:{port}" if port is not None else host


def validate_url(value: str | None, field: str, row_number: int, *, origin: str | None, https_only: bool) -> str | None:
    if value is None:
        return None
    candidate = value
    parsed = split_url(candidate, f"row {row_number}: {field}")
    if not parsed.scheme:
        if origin is None:
            raise ImportFailure(f"row {row_number}: relative {field} requires --origin")
        candidate = urljoin(origin.rstrip("/") + "/", candidate)
        parsed = split_url(candidate, f"row {row_number}: {field}")
    allowed = {"https"} if https_only else {"http", "https"}
    if parsed.scheme.casefold() not in allowed or not parsed.hostname:
        protocols = "HTTPS" if https_only else "HTTP(S)"
        raise ImportFailure(f"row {row_number}: {field} must be an absolute {protocols} URL")
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise ImportFailure(f"row {row_number}: {field} cannot contain credentials or a fragment")
    authority = normalized_authority(parsed, f"row {row_number}: {field}")
    return urlunsplit((parsed.scheme.casefold(), authority, parsed.path, parsed.query, ""))


def validate_origin(value: str | None) -> str | None:
    if value is None:
        return None
    parsed = split_url(value, "--origin")
    if (
        parsed.scheme.casefold() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ImportFailure("--origin must be an HTTPS origin with no path, query, fragment, or credentials")
    return urlunsplit(("https", normalized_authority(parsed, "--origin"), "", "", ""))


def stable_row_id(index: int, row: dict[str, Any]) -> str:
    canonical = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"row-{index:06d}-{digest_bytes(canonical)[:10]}"


def parse_filters(values: list[str]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for value in values:
        if "=" not in value:
            raise ImportFailure("--filter must use DIMENSION=VALUE")
        dimension, expected = (part.strip() for part in value.split("=", 1))
        if not dimension or not expected:
            raise ImportFailure("--filter requires non-empty DIMENSION and VALUE")
        key = (dimension, expected)
        if key in seen:
            raise ImportFailure(f"duplicate filter {value!r}")
        seen.add(key)
        result.append({"dimension": dimension, "operator": "equals", "value": expected})
    return result


SEARCH_ALIASES = {
    "date": {"date"},
    "query": {"query", "queries", "top queries", "keyword", "keywords"},
    "page": {"page", "pages", "top pages", "url"},
    "country": {"country"},
    "device": {"device"},
    "search_appearance": {"search appearance", "search appearance type"},
    "clicks": {"clicks"},
    "impressions": {"impressions"},
    "ctr": {"ctr", "click through rate", "click-through rate"},
    "average_position": {"position", "average position", "avg. position", "avg position"},
}

GA4_ALIASES = {
    "date": {"date"},
    "page": {"landing page", "landing page + query string", "landing page plus query string"},
    "country": {"country"},
    "device": {"device", "device category"},
    "channel": {"session default channel group", "default channel group"},
    "organic_sessions": {"sessions", "organic sessions"},
    "conversions": {"conversions"},
    "revenue": {"total revenue", "revenue"},
}

CRAWLER_ALIASES = {
    "url": {"url", "address"},
    "http_status": {"status code", "status", "http status", "http status code"},
    "content_type": {"content type", "mime type"},
    "title": {"title", "title 1", "page title"},
    "canonical_url": {"canonical", "canonical url", "canonical link element 1"},
    "indexability": {"indexability"},
    "indexability_status": {"indexability status", "index status"},
    "depth": {"crawl depth", "depth"},
    "inlinks": {"inlinks", "unique inlinks"},
    "outlinks": {"outlinks", "unique outlinks"},
    "redirect_url": {"redirect url", "redirect target", "redirect url 1"},
}


def performance_envelope(args: argparse.Namespace, adapter: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if not args.property.strip():
        raise ImportFailure("--property must be non-empty")
    aliases = GA4_ALIASES if adapter == "ga4-csv" else SEARCH_ALIASES
    required = {"page", "organic_sessions"} if adapter == "ga4-csv" else {"clicks", "impressions"}
    headers, source_rows, mapping, ignored, delimiter, encoding, raw_content = parsed_csv(
        args.source, aliases, required, args.delimiter
    )
    origin = validate_origin(args.origin)
    window_start = parse_instant(args.window_start, "--window-start")
    window_end = parse_instant(args.window_end, "--window-end")
    if window_start >= window_end:
        raise ImportFailure("--window-start must be before --window-end")
    reporting_tz(args.timezone)
    filters = parse_filters(args.filter)
    if adapter == "ga4-csv":
        if "channel" not in mapping and not args.organic_filter_asserted:
            raise ImportFailure(
                "GA4 sessions are not assumed organic; include a channel column or pass --organic-filter-asserted"
            )
        organic_filter = {"dimension": "sessionDefaultChannelGroup", "operator": "equals", "value": "Organic Search"}
        channel_filters = [item for item in filters if item["dimension"].casefold() == "sessiondefaultchannelgroup"]
        if channel_filters and channel_filters != [organic_filter]:
            raise ImportFailure("GA4 channel filter conflicts with the required Organic Search scope")
        if organic_filter not in filters:
            filters.append(organic_filter)
    dimensions = [field for field in DIMENSION_ORDER if field in mapping]
    if adapter != "ga4-csv" and not dimensions:
        raise ImportFailure("search-performance CSV requires at least one recognized dimension header")
    rows: list[dict[str, Any]] = []
    skipped = 0
    for source_index, source_row in enumerate(source_rows, start=2):
        if adapter == "ga4-csv" and "channel" in mapping:
            channel = raw_value(source_row, mapping, "channel")
            if channel is None:
                raise ImportFailure(f"row {source_index}: channel is empty")
            if channel.casefold() != "organic search":
                skipped += 1
                continue
        date = parse_row_date(raw_value(source_row, mapping, "date"), args.timezone, source_index)
        if date is not None:
            observed = parse_instant(date, f"row {source_index}: date")
            if not window_start <= observed < window_end:
                raise ImportFailure(f"row {source_index}: date falls outside the declared half-open window")
        page = validate_url(
            raw_value(source_row, mapping, "page"), "page", source_index, origin=origin, https_only=True
        )
        row: dict[str, Any] = {
            "date": date,
            "query": raw_value(source_row, mapping, "query"),
            "page": page,
            "country": validate_country(raw_value(source_row, mapping, "country"), source_index),
            "device": validate_device(raw_value(source_row, mapping, "device"), source_index),
            "search_appearance": raw_value(source_row, mapping, "search_appearance"),
            "clicks": None,
            "impressions": None,
            "ctr": None,
            "average_position": None,
            "organic_sessions": None,
            "conversions": None,
            "revenue": None,
        }
        if adapter == "ga4-csv":
            row["organic_sessions"] = parse_nonnegative_int(
                raw_value(source_row, mapping, "organic_sessions"), "sessions", source_index, required=True
            )
            row["conversions"] = parse_nonnegative_number(
                raw_value(source_row, mapping, "conversions"), "conversions", source_index
            )
            row["revenue"] = parse_nonnegative_number(
                raw_value(source_row, mapping, "revenue"), "revenue", source_index
            )
        else:
            clicks = parse_nonnegative_int(raw_value(source_row, mapping, "clicks"), "clicks", source_index, required=True)
            impressions = parse_nonnegative_int(
                raw_value(source_row, mapping, "impressions"), "impressions", source_index, required=True
            )
            assert clicks is not None and impressions is not None
            row["clicks"] = clicks
            row["impressions"] = impressions
            row["ctr"] = validate_exported_ctr(raw_value(source_row, mapping, "ctr"), clicks, impressions, source_index)
            row["average_position"] = parse_nonnegative_number(
                raw_value(source_row, mapping, "average_position"), "average position", source_index
            )
        row["row_id"] = stable_row_id(len(rows) + 1, row)
        row = {field: row[field] for field in PERFORMANCE_ROW_FIELDS}
        rows.append(row)
    if not rows:
        raise ImportFailure("no rows remain after applying the declared source scope")
    source_type = {
        "gsc-csv": "google-search-console",
        "bing-csv": "bing-webmaster-tools",
        "ga4-csv": "analytics",
    }[adapter]
    search_type = "not-applicable" if adapter == "ga4-csv" else args.search_type
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "source_type": source_type,
        "property": args.property,
        "search_type": search_type,
        "filters": filters,
        "export_method": f"credential-free {adapter} adapter {ADAPTER_VERSION}",
        "window": {
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
            "timezone": args.timezone,
        },
        "dimensions": dimensions,
        "rows": rows,
        "indexation": [],
        "web_vitals": [],
    }
    transformations = ["Whitespace around CSV cell values was removed."]
    if adapter != "ga4-csv":
        transformations.append("CTR was recomputed exactly as clicks divided by impressions; any exported CTR was used only as a consistency check.")
    else:
        transformations.append("Only explicitly identified Organic Search rows were retained; no total-session row was relabeled as organic.")
        transformations.append("Relative landing-page values were resolved only when an explicit HTTPS --origin was supplied.")
    provenance = {
        "schema_version": SCHEMA_VERSION,
        "envelope_type": "seo-data-import-provenance",
        "adapter": {"id": adapter, "version": ADAPTER_VERSION},
        "source": {
            "provider": source_type,
            "raw_source_ref": validate_raw_source_ref(args.raw_source_ref or args.source.name),
            "raw_source_sha256": digest_bytes(raw_content),
            "raw_source_size_bytes": len(raw_content),
            "encoding": encoding,
            "delimiter": delimiter,
            "original_headers": headers,
            "header_map": {field: headers[index] for field, index in sorted(mapping.items())},
            "ignored_headers": ignored,
        },
        "import_parameters": {
            "property": args.property,
            "search_type": search_type,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "timezone": args.timezone,
            "origin": origin,
            "filters": filters,
        },
        "result": {
            "input_row_count": len(source_rows),
            "output_row_count": len(rows),
            "skipped_row_count": skipped,
        },
        "transformations": transformations,
        "limitations": [
            "The adapter preserves supplied observations; it does not establish sampling, anonymized-query, canonical-aggregation, attribution, or consent status.",
            "Unknown columns are listed in ignored_headers and are not converted into metrics.",
        ],
    }
    return envelope, provenance


def validate_raw_source_ref(value: str) -> str:
    if "\\" in value:
        raise ImportFailure("raw source reference must use forward slashes")
    if re.match(r"^[A-Za-z]:", value) or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", value):
        raise ImportFailure("raw source reference must be relative, not a drive path or URL")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not value.strip():
        raise ImportFailure("raw source reference must be a non-empty relative path without parent traversal")
    return value


def crawler_envelope(args: argparse.Namespace) -> dict[str, Any]:
    headers, source_rows, mapping, ignored, delimiter, encoding, raw_content = parsed_csv(
        args.source, CRAWLER_ALIASES, {"url", "http_status"}, args.delimiter
    )
    records: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for source_index, source_row in enumerate(source_rows, start=2):
        url = validate_url(raw_value(source_row, mapping, "url"), "url", source_index, origin=None, https_only=False)
        assert url is not None
        if url in seen_urls:
            raise ImportFailure(f"row {source_index}: duplicate URL {url!r} is ambiguous")
        seen_urls.add(url)
        status = parse_nonnegative_int(
            raw_value(source_row, mapping, "http_status"), "http status", source_index, required=True
        )
        if status is None or not 100 <= status <= 599:
            raise ImportFailure(f"row {source_index}: HTTP status must be between 100 and 599")
        canonical = validate_url(
            raw_value(source_row, mapping, "canonical_url"), "canonical URL", source_index, origin=None, https_only=False
        )
        redirect = validate_url(
            raw_value(source_row, mapping, "redirect_url"), "redirect URL", source_index, origin=None, https_only=False
        )
        record: dict[str, Any] = {
            "url": url,
            "http_status": status,
            "content_type": raw_value(source_row, mapping, "content_type"),
            "title": raw_value(source_row, mapping, "title"),
            "canonical_url": canonical,
            "indexability": raw_value(source_row, mapping, "indexability"),
            "indexability_status": raw_value(source_row, mapping, "indexability_status"),
            "depth": parse_nonnegative_int(raw_value(source_row, mapping, "depth"), "depth", source_index),
            "inlinks": parse_nonnegative_int(raw_value(source_row, mapping, "inlinks"), "inlinks", source_index),
            "outlinks": parse_nonnegative_int(raw_value(source_row, mapping, "outlinks"), "outlinks", source_index),
            "redirect_url": redirect,
        }
        record["record_id"] = stable_row_id(len(records) + 1, record)
        records.append({"record_id": record.pop("record_id"), **record})
    https_candidate_ids = [record["record_id"] for record in records if record["url"].startswith("https://")]
    return {
        "schema_version": SCHEMA_VERSION,
        "envelope_type": "seo-data-import",
        "adapter": {"id": "crawler-csv", "version": ADAPTER_VERSION},
        "source_type": "crawler-export",
        "provenance": {
            "raw_source_ref": validate_raw_source_ref(args.raw_source_ref or args.source.name),
            "raw_source_sha256": digest_bytes(raw_content),
            "raw_source_size_bytes": len(raw_content),
            "encoding": encoding,
            "delimiter": delimiter,
            "original_headers": headers,
            "header_map": {field: headers[index] for field, index in sorted(mapping.items())},
            "ignored_headers": ignored,
            "input_row_count": len(source_rows),
        },
        "records": records,
        "workflow_compatibility": {
            "site_graph": {
                "candidate_record_ids": https_candidate_ids,
                "compatible_observed_fields": ["url", "http_status", "canonical_url", "title"],
                "not_emitted": "site-graph.json",
                "missing_requirements": [
                    "hash-pinned raw HTML capture per node",
                    "hash-pinned node metadata envelope",
                    "locale, business role, target type, and index intent decisions",
                    "captured anchor evidence for every edge",
                ],
            },
            "evidence": {
                "observation_record_ids": [record["record_id"] for record in records],
                "classification": "direct_observation",
                "claim_generation": "not_performed",
            },
        },
        "transformations": ["Whitespace around CSV cell values was removed; observed crawler labels were otherwise preserved."],
        "limitations": [
            "A crawler export is not proof of indexation, ranking, retrieval, citation, referral, or conversion.",
            "No index intent, locale, page type, business role, completeness, or graph edge was inferred.",
            "Unknown columns are listed in ignored_headers and are not converted into observations.",
        ],
    }


LOG_RE = re.compile(
    r'^(?P<client>\S+) (?P<ident>\S+) (?P<auth>\S+) \[(?P<time>[^\]]+)\] '
    r'"(?P<request>[^"]*)" (?P<status>\d{3}) (?P<size>\d+|-)'
    r'(?: "(?P<referrer>[^"]*)" "(?P<agent>[^"]*)")?$'
)
LOG_TIME_RE = re.compile(
    r"^(?P<day>\d{2})/(?P<month>[A-Za-z]{3})/(?P<year>\d{4}):"
    r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}) (?P<offset>[+-]\d{4})$"
)
MONTHS = {month: index for index, month in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), start=1
)}


def parse_log_time(value: str, line_number: int) -> str:
    match = LOG_TIME_RE.fullmatch(value)
    if match is None or match.group("month") not in MONTHS:
        raise ImportFailure(f"line {line_number}: unsupported access-log timestamp")
    offset_raw = match.group("offset")
    sign = 1 if offset_raw[0] == "+" else -1
    offset_hours, offset_minutes = int(offset_raw[1:3]), int(offset_raw[3:5])
    if offset_hours > 23 or offset_minutes > 59:
        raise ImportFailure(f"line {line_number}: invalid access-log UTC offset")
    offset = dt.timezone(sign * dt.timedelta(hours=offset_hours, minutes=offset_minutes))
    try:
        parsed = dt.datetime(
            int(match.group("year")), MONTHS[match.group("month")], int(match.group("day")),
            int(match.group("hour")), int(match.group("minute")), int(match.group("second")), tzinfo=offset,
        )
    except ValueError as exc:
        raise ImportFailure(f"line {line_number}: invalid access-log timestamp") from exc
    return parsed.isoformat()


def server_log_envelope(args: argparse.Namespace) -> dict[str, Any]:
    text, encoding, raw_content = decode_text(args.source)
    origin = validate_origin(args.origin)
    lines = [(number, line.rstrip("\r")) for number, line in enumerate(text.splitlines(), start=1) if line.strip()]
    if not lines:
        raise ImportFailure("access log has no non-empty lines")
    records: list[dict[str, Any]] = []
    formats: set[str] = set()
    for line_number, line in lines:
        match = LOG_RE.fullmatch(line)
        if match is None:
            raise ImportFailure(f"line {line_number}: malformed or unsupported Common/Combined access-log record")
        combined = match.group("referrer") is not None
        formats.add("combined" if combined else "common")
        request_parts = match.group("request").split()
        if len(request_parts) != 3:
            raise ImportFailure(f"line {line_number}: request must contain method, target, and protocol")
        method, target, protocol = request_parts
        if not re.fullmatch(r"[A-Z]+", method) or not re.fullmatch(r"HTTP/\d(?:\.\d)?", protocol):
            raise ImportFailure(f"line {line_number}: malformed HTTP request line")
        target_parts = split_url(target, f"line {line_number}: request target")
        if target_parts.scheme:
            if target_parts.scheme.casefold() not in {"http", "https"} or not target_parts.hostname:
                raise ImportFailure(f"line {line_number}: unsupported absolute request target")
            if target_parts.username is not None or target_parts.password is not None or target_parts.fragment:
                raise ImportFailure(f"line {line_number}: absolute request target cannot contain credentials or a fragment")
            path = target_parts.path or "/"
        else:
            if not target.startswith("/"):
                raise ImportFailure(f"line {line_number}: request target must be origin-form or HTTP(S)")
            path = target_parts.path or "/"
        query_present = bool(target_parts.query)
        if origin is not None:
            origin_host = split_url(origin, "--origin").hostname
            if target_parts.hostname is not None and origin_host is not None and target_parts.hostname.casefold() != origin_host.casefold():
                raise ImportFailure(f"line {line_number}: absolute request target is outside --origin")
            target_url = urljoin(origin.rstrip("/") + "/", path.lstrip("/"))
        elif target_parts.scheme.casefold() == "https":
            target_url = urlunsplit(
                ("https", normalized_authority(target_parts, f"line {line_number}: request target"), path, "", "")
            )
        else:
            target_url = None
        status = int(match.group("status"))
        if not 100 <= status <= 599:
            raise ImportFailure(f"line {line_number}: HTTP status must be between 100 and 599")
        size_raw = match.group("size")
        referrer_raw = match.group("referrer")
        referrer_url: str | None = None
        referrer_query_present = False
        referrer_sha256: str | None = None
        if referrer_raw not in {None, "-"}:
            referrer_sha256 = digest_bytes(referrer_raw.encode("utf-8"))
            referrer_parts = split_url(referrer_raw, f"line {line_number}: referrer")
            if (
                referrer_parts.scheme.casefold() in {"http", "https"}
                and referrer_parts.hostname
                and referrer_parts.username is None
                and referrer_parts.password is None
            ):
                referrer_url = urlunsplit(
                    (referrer_parts.scheme.casefold(), referrer_parts.netloc, referrer_parts.path, "", "")
                )
                referrer_query_present = bool(referrer_parts.query)
        record: dict[str, Any] = {
            "observed_at": parse_log_time(match.group("time"), line_number),
            "method": method,
            "path": path,
            "query_present": query_present,
            "request_target_sha256": digest_bytes(target.encode("utf-8")),
            "protocol": protocol,
            "http_status": status,
            "response_bytes": None if size_raw == "-" else int(size_raw),
            "referrer_url": referrer_url,
            "referrer_query_present": referrer_query_present,
            "referrer_sha256": referrer_sha256,
            "user_agent": None if match.group("agent") in {None, "-"} else match.group("agent"),
            "client_address_sha256": digest_bytes(match.group("client").encode("utf-8")),
            "target_url": target_url,
            "decoded_line_sha256": digest_bytes(line.encode("utf-8")),
        }
        record["record_id"] = stable_row_id(len(records) + 1, record)
        records.append({"record_id": record.pop("record_id"), **record})
    if len(formats) != 1:
        raise ImportFailure("mixed Common and Combined access-log formats are ambiguous; split the source file")
    log_format = next(iter(formats))
    return {
        "schema_version": SCHEMA_VERSION,
        "envelope_type": "seo-data-import",
        "adapter": {"id": "server-access-log", "version": ADAPTER_VERSION},
        "source_type": "server-logs",
        "provenance": {
            "raw_source_ref": validate_raw_source_ref(args.raw_source_ref or args.source.name),
            "raw_source_sha256": digest_bytes(raw_content),
            "raw_source_size_bytes": len(raw_content),
            "encoding": encoding,
            "format": log_format,
            "input_line_count": len(lines),
        },
        "records": records,
        "workflow_compatibility": {
            "seo_performance": {
                "not_emitted": "seo-performance source envelope",
                "reason": "Request rows do not define sessions, conversions, rankings, citations, or other performance metrics.",
            },
            "site_graph": {
                "not_emitted": "site-graph.json",
                "reason": "Requests do not capture page bodies, canonical metadata, or anchor edges.",
            },
            "evidence": {
                "observation_record_ids": [record["record_id"] for record in records],
                "classification": "direct_observation",
                "claim_generation": "not_performed",
            },
        },
        "transformations": [
            "Client addresses were replaced by unsalted SHA-256 values.",
            "Query strings were removed from normalized paths; request_target_sha256 binds the exact observed target.",
            "Referrer query strings and fragments were removed; referrer_sha256 binds the exact non-empty referrer value.",
            "No user-agent string was classified as a verified crawler identity.",
        ],
        "limitations": [
            "An access-log request is not proof of indexing, ranking, retrieval, citation, referral, session, or conversion.",
            "IP hashing is pseudonymization, not anonymization; retain and process the envelope under the site's privacy policy.",
            "Paths and user-agent strings can still contain personal or sensitive data and require project-specific retention review.",
            "Crawler identity requires separate verification against current vendor guidance and network evidence.",
        ],
    }


def json_bytes(payload: dict[str, Any]) -> bytes:
    try:
        rendered = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)
    except ValueError as exc:
        raise ImportFailure(f"normalized output contains a non-finite number: {exc}") from exc
    return (rendered + "\n").encode("utf-8")


def is_reparse(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    attributes = getattr(metadata, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def assert_safe_output_path(path: Path) -> None:
    current = path.parent.absolute()
    while current != current.parent:
        if current.exists() and is_reparse(current):
            raise ImportFailure(f"output path must not traverse a symlink or reparse point: {current}")
        current = current.parent
    if path.exists() and (is_reparse(path) or not path.is_file()):
        raise ImportFailure(f"output path must be a regular file and not a reparse point when it exists: {path}")


def ensure_output_targets(source: Path, targets: list[Path], overwrite: bool) -> None:
    for target in targets:
        assert_safe_output_path(target)
    resolved_source = source.resolve()
    resolved_targets = [target.resolve() for target in targets]
    if len(resolved_targets) != len(set(resolved_targets)):
        raise ImportFailure("output and provenance paths must be distinct")
    if resolved_source in resolved_targets:
        raise ImportFailure("an output path cannot overwrite the raw source")
    existing = [str(target) for target in targets if target.exists()]
    if existing and not overwrite:
        raise ImportFailure("output already exists; pass --overwrite to replace: " + ", ".join(existing))
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        if is_reparse(target.parent):
            raise ImportFailure(f"output parent must not be a symlink or reparse point: {target.parent}")


def staged_write_bytes(outputs: list[tuple[Path, bytes]]) -> None:
    staged: list[tuple[Path, Path]] = []
    installed: list[tuple[Path, Path | None]] = []
    backups: list[Path] = []
    try:
        for target, content in outputs:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
            )
            temporary = Path(temporary_name)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            staged.append((temporary, target))
        for temporary, target in staged:
            backup: Path | None = None
            if target.exists():
                backup = target.with_name(f".{target.name}.{uuid.uuid4().hex}.backup")
                os.replace(target, backup)
                backups.append(backup)
            installed.append((target, backup))
            os.replace(temporary, target)
    except OSError as exc:
        rollback_errors: list[str] = []
        for target, backup in reversed(installed):
            try:
                if target.exists() and target.is_file() and not is_reparse(target):
                    target.unlink()
                if backup is not None and backup.exists():
                    os.replace(backup, target)
            except OSError as rollback_exc:
                rollback_errors.append(f"{target}: {rollback_exc}")
        detail = f"cannot atomically write normalized output set: {exc}"
        if rollback_errors:
            detail += "; rollback incomplete: " + "; ".join(rollback_errors)
        raise ImportFailure(detail) from exc
    finally:
        for temporary, _ in staged:
            if temporary.exists() and temporary.is_file() and not is_reparse(temporary):
                temporary.unlink()
    cleanup_errors: list[str] = []
    for backup in backups:
        if backup.exists() and backup.is_file() and not is_reparse(backup):
            try:
                backup.unlink()
            except OSError as exc:
                cleanup_errors.append(f"{backup}: {exc}")
    if cleanup_errors:
        raise ImportFailure(
            "normalized outputs were written, but prior-output backup cleanup failed: " + "; ".join(cleanup_errors)
        )


def write_performance_outputs(
    source: Path,
    output: Path,
    provenance_output: Path,
    envelope: dict[str, Any],
    provenance: dict[str, Any],
    overwrite: bool,
) -> None:
    if output.parent.resolve() != provenance_output.parent.resolve():
        raise ImportFailure("--provenance-output must be in the same directory as --output")
    ensure_output_targets(source, [output, provenance_output], overwrite)
    normalized = json_bytes(envelope)
    provenance["result"].update(
        {
            "normalized_output_ref": output.name,
            "normalized_output_sha256": digest_bytes(normalized),
        }
    )
    staged_write_bytes(
        [
            (output, normalized),
            (provenance_output, json_bytes(provenance)),
        ]
    )


def write_observation_output(source: Path, output: Path, envelope: dict[str, Any], overwrite: bool) -> None:
    ensure_output_targets(source, [output], overwrite)
    staged_write_bytes([(output, json_bytes(envelope))])


def add_csv_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--delimiter", choices=["auto", *DELIMITERS], default="auto")
    parser.add_argument("--raw-source-ref")
    parser.add_argument("--overwrite", action="store_true")


def add_performance_options(parser: argparse.ArgumentParser, *, analytics: bool = False) -> None:
    add_csv_options(parser)
    parser.add_argument("--property", required=True, help="Exact provider property or data-stream identifier.")
    parser.add_argument("--window-start", required=True, help="Inclusive ISO 8601 timestamp with offset.")
    parser.add_argument("--window-end", required=True, help="Exclusive ISO 8601 timestamp with offset.")
    parser.add_argument("--timezone", default="UTC", help="Reporting timezone: UTC, +/-HH:MM, or an available IANA name.")
    parser.add_argument("--origin", help="HTTPS origin used only to resolve relative page values.")
    parser.add_argument("--filter", action="append", default=[], metavar="DIMENSION=VALUE")
    parser.add_argument("--provenance-output", type=Path)
    if analytics:
        parser.add_argument(
            "--organic-filter-asserted",
            action="store_true",
            help="Assert that an export without a channel column was filtered to Organic Search upstream.",
        )
    else:
        parser.add_argument(
            "--search-type",
            choices=["web", "image", "video", "news", "discover", "google-news", "other"],
            default="web",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_performance_options(subparsers.add_parser("gsc-csv", help="Normalize a Google Search Console CSV export."))
    add_performance_options(subparsers.add_parser("bing-csv", help="Normalize a Bing Webmaster Tools CSV export."))
    add_performance_options(
        subparsers.add_parser("ga4-csv", help="Normalize an organic GA4 landing-page CSV export."), analytics=True
    )
    add_csv_options(subparsers.add_parser("crawler-csv", help="Normalize an SEO crawler CSV export."))
    logs = subparsers.add_parser("server-log", help="Normalize Apache/Nginx Common or Combined access logs.")
    logs.add_argument("source", type=Path)
    logs.add_argument("--output", type=Path, required=True)
    logs.add_argument("--origin", help="Optional HTTPS origin used to form target_url values from paths.")
    logs.add_argument("--raw-source-ref")
    logs.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command in {"gsc-csv", "bing-csv", "ga4-csv"}:
            envelope, provenance = performance_envelope(args, args.command)
            provenance_output = args.provenance_output or args.output.with_name(args.output.name + ".provenance.json")
            write_performance_outputs(
                args.source, args.output, provenance_output, envelope, provenance, args.overwrite
            )
            print(
                f"PASS: {args.command} normalized {len(envelope['rows'])} row(s); "
                f"wrote {args.output} and {provenance_output}"
            )
        elif args.command == "crawler-csv":
            envelope = crawler_envelope(args)
            write_observation_output(args.source, args.output, envelope, args.overwrite)
            print(f"PASS: crawler-csv normalized {len(envelope['records'])} observation(s); wrote {args.output}")
        else:
            envelope = server_log_envelope(args)
            write_observation_output(args.source, args.output, envelope, args.overwrite)
            print(f"PASS: server-log normalized {len(envelope['records'])} observation(s); wrote {args.output}")
    except ImportFailure as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
