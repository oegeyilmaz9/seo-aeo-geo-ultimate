#!/usr/bin/env python3
"""Validate a versioned SEO / AI-search source registry.

The registry records what supports a suite rule and when that support was last
checked. It deliberately validates structure and freshness metadata only; it
does not fetch a URL or claim that a remote page still says the same thing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SOURCE_KINDS = {
    "vendor_documentation",
    "standard",
    "original_research",
    "direct_observation",
    "secondary_context",
}

REQUIRED_ROOT_FIELDS = {
    "registry_version",
    "observed_on",
    "purpose",
    "freshness_policy",
    "sources",
}

REQUIRED_POLICY_FIELDS = {
    "vendor_documentation_days",
    "standards_days",
    "original_research_days",
    "direct_observation_days",
    "collection_or_access_policy",
}

REQUIRED_SOURCE_FIELDS = {
    "id",
    "title",
    "publisher",
    "url",
    "source_kind",
    "updated_at",
    "observed_at",
    "scopes",
    "design_effect",
}

SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,127}$")


@dataclass
class Result:
    errors: list[str]
    warnings: list[str]
    checked: int
    stale: int


def parse_day(value: Any, label: str, result: Result) -> date | None:
    if not isinstance(value, str):
        result.errors.append(f"{label} must be an ISO date string.")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        result.errors.append(f"{label} must use YYYY-MM-DD.")
        return None


def require_nonempty_string(value: Any, label: str, result: Result) -> None:
    if not isinstance(value, str) or not value.strip():
        result.errors.append(f"{label} must be a non-empty string.")


def freshness_days(kind: str, policy: dict[str, Any]) -> int:
    if kind == "standard":
        return policy["standards_days"]
    if kind == "original_research":
        return policy["original_research_days"]
    if kind == "direct_observation":
        return policy["direct_observation_days"]
    return policy["vendor_documentation_days"]


def validate_policy(policy: Any, result: Result) -> dict[str, Any] | None:
    if not isinstance(policy, dict):
        result.errors.append("freshness_policy must be an object.")
        return None

    missing = REQUIRED_POLICY_FIELDS - policy.keys()
    if missing:
        result.errors.append(
            "freshness_policy is missing fields: " + ", ".join(sorted(missing))
        )
        return None

    for field in (
        "vendor_documentation_days",
        "standards_days",
        "original_research_days",
        "direct_observation_days",
    ):
        value = policy[field]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            result.errors.append(f"freshness_policy.{field} must be a positive integer.")
    require_nonempty_string(
        policy["collection_or_access_policy"],
        "freshness_policy.collection_or_access_policy",
        result,
    )
    return policy


def validate_url(value: Any, label: str, result: Result) -> None:
    if not isinstance(value, str):
        result.errors.append(f"{label} must be an HTTPS URL.")
        return
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        result.errors.append(f"{label} must be an HTTPS URL with a host.")


def validate_source(
    source: Any,
    index: int,
    policy: dict[str, Any],
    as_of: date,
    allow_stale: bool,
    seen_ids: set[str],
    result: Result,
) -> None:
    label = f"sources[{index}]"
    if not isinstance(source, dict):
        result.errors.append(f"{label} must be an object.")
        return

    missing = REQUIRED_SOURCE_FIELDS - source.keys()
    if missing:
        result.errors.append(
            f"{label} is missing fields: " + ", ".join(sorted(missing))
        )
        return

    source_id = source["id"]
    if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
        result.errors.append(f"{label}.id must be a lowercase kebab-case identifier.")
    elif source_id in seen_ids:
        result.errors.append(f"{label}.id duplicates {source_id}.")
    else:
        seen_ids.add(source_id)

    for field in ("title", "publisher", "design_effect"):
        require_nonempty_string(source[field], f"{label}.{field}", result)
    validate_url(source["url"], f"{label}.url", result)

    kind = source["source_kind"]
    if kind not in SOURCE_KINDS:
        result.errors.append(
            f"{label}.source_kind must be one of: {', '.join(sorted(SOURCE_KINDS))}."
        )
        return

    if not isinstance(source["scopes"], list) or not source["scopes"]:
        result.errors.append(f"{label}.scopes must be a non-empty array.")
    elif any(not isinstance(scope, str) or not scope.strip() for scope in source["scopes"]):
        result.errors.append(f"{label}.scopes must contain non-empty strings only.")

    observed = parse_day(source["observed_at"], f"{label}.observed_at", result)
    updated_value = source["updated_at"]
    updated = None
    if updated_value is not None:
        updated = parse_day(updated_value, f"{label}.updated_at", result)

    if observed is None:
        return
    if observed > as_of:
        result.errors.append(f"{label}.observed_at cannot be later than --as-of.")
        return
    if updated is not None and updated > observed:
        result.errors.append(f"{label}.updated_at cannot be later than observed_at.")
        return

    # Freshness is the date the suite last re-checked the source, not the
    # publisher's last modification date. A stable standard can be old while
    # its current applicability was verified today.
    age_days = (as_of - observed).days
    allowed_days = freshness_days(kind, policy)
    result.checked += 1
    if age_days > allowed_days:
        result.stale += 1
        message = (
            f"{label} is stale by {age_days - allowed_days} day(s): "
            f"{source_id} is {age_days} day(s) old; limit is {allowed_days}."
        )
        if allow_stale:
            result.warnings.append(message)
        else:
            result.errors.append(message)


def validate_registry(
    payload: Any, as_of: date, allow_stale: bool
) -> Result:
    result = Result(errors=[], warnings=[], checked=0, stale=0)
    if not isinstance(payload, dict):
        result.errors.append("Registry root must be an object.")
        return result

    missing = REQUIRED_ROOT_FIELDS - payload.keys()
    if missing:
        result.errors.append("Registry root is missing fields: " + ", ".join(sorted(missing)))
        return result

    require_nonempty_string(payload["registry_version"], "registry_version", result)
    require_nonempty_string(payload["purpose"], "purpose", result)
    observed_on = parse_day(payload["observed_on"], "observed_on", result)
    if observed_on is not None and observed_on > as_of:
        result.errors.append("observed_on cannot be later than --as-of.")

    policy = validate_policy(payload["freshness_policy"], result)
    sources = payload["sources"]
    if not isinstance(sources, list) or not sources:
        result.errors.append("sources must be a non-empty array.")
        return result
    if policy is None:
        return result

    seen_ids: set[str] = set()
    for index, source in enumerate(sources):
        validate_source(source, index, policy, as_of, allow_stale, seen_ids, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate source-registry structure and freshness metadata."
    )
    parser.add_argument("registry", type=Path)
    parser.add_argument(
        "--as-of",
        default=date.today().isoformat(),
        help="ISO date used for freshness checks; defaults to today.",
    )
    parser.add_argument(
        "--allow-stale",
        action="store_true",
        help="Report stale registry entries as warnings instead of errors.",
    )
    args = parser.parse_args()

    result = Result(errors=[], warnings=[], checked=0, stale=0)
    as_of = parse_day(args.as_of, "--as-of", result)
    if as_of is None:
        print(json.dumps({"status": "FAIL", "errors": result.errors}, indent=2))
        return 2

    try:
        payload = json.loads(args.registry.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(json.dumps({"status": "FAIL", "errors": ["Registry file not found."]}, indent=2))
        return 2
    except json.JSONDecodeError as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "errors": [f"Registry is not valid JSON: line {exc.lineno} column {exc.colno}."],
                },
                indent=2,
            )
        )
        return 2

    result = validate_registry(payload, as_of, args.allow_stale)
    output = {
        "status": "PASS" if not result.errors else "FAIL",
        "checked_sources": result.checked,
        "stale_sources": result.stale,
        "errors": result.errors,
        "warnings": result.warnings,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not result.errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
