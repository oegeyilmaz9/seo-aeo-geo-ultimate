#!/usr/bin/env python3
"""Validate a mutation-time, evidence-bound search-provider operation receipt."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from bundle_safety import resolve_artifact_in_bundle, resolve_relative
from validate_ai_search_research import validate_schema_instance


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "manifests" / "artifact-schemas" / "provider-operation-receipt.schema.json"


def fail(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        fail([f"cannot read JSON {path}: {exc}"])


def parse_time(value: object, field: str, errors: list[str]) -> dt.datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        errors.append(f"{field} must be an ISO 8601 UTC timestamp ending in Z")
        return None
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        errors.append(f"{field} is not a valid timestamp")
        return None
    return parsed


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_hash_ref(bundle: Path, ref: object, sha: object, field: str, errors: list[str]) -> None:
    path = resolve_relative(bundle, ref, f"{field}.evidence_ref", errors)
    if path is None:
        return
    if not path.is_file():
        errors.append(f"{field}.evidence_ref must resolve to a regular file")
        return
    if not isinstance(sha, str) or digest(path) != sha:
        errors.append(f"{field}.evidence_ref hash mismatch")


def https_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme == "https" and bool(parsed.hostname) and parsed.username is None and parsed.password is None


def target_in_property(provider: str, property_value: str, target: str) -> bool:
    if not https_url(target):
        return False
    host = (urlsplit(target).hostname or "").lower()
    if property_value.startswith("sc-domain:"):
        domain = property_value.removeprefix("sc-domain:").lower().rstrip(".")
        return host == domain or host.endswith("." + domain)
    if https_url(property_value):
        if provider == "indexnow":
            return host == (urlsplit(property_value).hostname or "").lower()
        return target.startswith(property_value)
    return provider == "other-documented"


def validate_capability(payload: dict[str, Any], errors: list[str]) -> None:
    provider = payload["provider"]["provider_id"]
    operation = payload["operation"]
    op_type = operation["operation_type"]
    access = operation["access_path"]
    matrix: dict[str, dict[str, set[str]]] = {
        "google-search-console": {
            "submit-sitemap": {"api", "cli", "mcp", "isolated-browser-ui", "named-user-browser-ui"},
            "request-indexing": {"isolated-browser-ui", "named-user-browser-ui"},
            "validate-fix": {"isolated-browser-ui", "named-user-browser-ui"},
        },
        "google-indexing-api": {"submit-url": {"api", "cli", "mcp"}},
        "bing-webmaster-tools": {
            "submit-sitemap": {"api", "cli", "mcp", "isolated-browser-ui", "named-user-browser-ui"},
            "submit-url": {"api", "cli", "mcp", "isolated-browser-ui", "named-user-browser-ui"},
        },
        "indexnow": {"indexnow-notify": {"api", "cli", "mcp"}},
        "other-documented": {"other-documented-mutation": {"api", "cli", "mcp", "isolated-browser-ui", "named-user-browser-ui"}},
    }
    allowed = matrix.get(provider, {}).get(op_type)
    if allowed is None or access not in allowed:
        errors.append(f"operation {op_type!r} via {access!r} is not declared for provider {provider!r}")

    targets = operation["targets"]
    expected_type = {
        "submit-sitemap": "sitemap",
        "submit-url": "url",
        "request-indexing": "url",
        "validate-fix": "issue-cohort",
        "indexnow-notify": "url",
    }.get(op_type)
    if expected_type is not None:
        for index, target in enumerate(targets):
            if target["target_type"] != expected_type:
                errors.append(f"operation.targets[{index}].target_type must be {expected_type!r} for {op_type}")

    if provider == "google-indexing-api":
        eligible = {"job-posting", "livestream-broadcast-event"}
        for index, target in enumerate(targets):
            if target["eligibility"] not in eligible:
                errors.append(
                    f"operation.targets[{index}].eligibility must be job-posting or livestream-broadcast-event for Google Indexing API"
                )
    else:
        for index, target in enumerate(targets):
            if target["eligibility"] in {"job-posting", "livestream-broadcast-event"}:
                errors.append(f"operation.targets[{index}].eligibility is specific to Google Indexing API")


def validate_receipt(path: Path, bundle: Path) -> None:
    errors: list[str] = []
    artifact = resolve_artifact_in_bundle(path, bundle, errors)
    if artifact is None:
        fail(errors)
    payload = load(artifact)
    schema = load(SCHEMA)
    registry = {schema["$id"]: schema, "#/$defs/capture": schema["$defs"]["capture"]}
    validate_schema_instance(payload, schema, registry, "$", errors)
    if errors or not isinstance(payload, dict):
        fail(errors)

    provider = payload["provider"]
    authorization = payload["authorization"]
    operation = payload["operation"]
    result = payload["result"]
    pre_state = payload["pre_state"]
    post_state = payload["post_state"]

    times = {
        "authorization.authorized_at": parse_time(authorization["authorized_at"], "authorization.authorized_at", errors),
        "provider.property_verified_at": parse_time(provider["property_verified_at"], "provider.property_verified_at", errors),
        "provider.capability_verified_at": parse_time(provider["capability_verified_at"], "provider.capability_verified_at", errors),
        "pre_state.captured_at": parse_time(pre_state["captured_at"], "pre_state.captured_at", errors),
        "operation.started_at": parse_time(operation["started_at"], "operation.started_at", errors),
        "result.completed_at": parse_time(result["completed_at"], "result.completed_at", errors),
        "post_state.captured_at": parse_time(post_state["captured_at"], "post_state.captured_at", errors),
        "recorded_at": parse_time(payload["recorded_at"], "recorded_at", errors),
    }
    if all(value is not None for value in times.values()):
        authorized = times["authorization.authorized_at"]
        property_verified = times["provider.property_verified_at"]
        capability_verified = times["provider.capability_verified_at"]
        pre = times["pre_state.captured_at"]
        started = times["operation.started_at"]
        completed = times["result.completed_at"]
        post = times["post_state.captured_at"]
        recorded = times["recorded_at"]
        assert authorized and property_verified and capability_verified and pre and started and completed and post and recorded
        if not (authorized <= started and pre <= started <= completed <= post <= recorded):
            errors.append("authorization, pre-state, operation, result, post-state, and receipt timestamps are not chronological")
        if not (property_verified <= started and started - property_verified <= dt.timedelta(hours=1)):
            errors.append("provider property must be verified no more than one hour before mutation")
        if not (capability_verified <= started and started - capability_verified <= dt.timedelta(days=30)):
            errors.append("provider capability must be verified no more than 30 days before mutation")

    check_hash_ref(bundle, authorization["evidence_ref"], authorization["evidence_sha256"], "authorization", errors)
    check_hash_ref(bundle, pre_state["evidence_ref"], pre_state["evidence_sha256"], "pre_state", errors)
    check_hash_ref(bundle, result["evidence_ref"], result["evidence_sha256"], "result", errors)
    check_hash_ref(bundle, post_state["evidence_ref"], post_state["evidence_sha256"], "post_state", errors)

    target_ids = [target["target_id"] for target in operation["targets"]]
    if len(target_ids) != len(set(target_ids)):
        errors.append("operation.targets target_id values must be unique")
    if set(authorization["target_ids"]) != set(target_ids):
        errors.append("authorization.target_ids must exactly match operation target IDs")
    if operation["operation_type"] not in authorization["operation_types"]:
        errors.append("authorization.operation_types does not authorize this operation type")
    succeeded = set(result["succeeded_target_ids"])
    failed = set(result["failed_target_ids"])
    if succeeded & failed:
        errors.append("result succeeded and failed target IDs must be disjoint")
    if succeeded | failed != set(target_ids):
        errors.append("result target IDs must exactly partition the operation targets")
    status = result["status"]
    if status == "accepted" and (not succeeded or failed):
        errors.append("accepted result must succeed every target")
    if status == "partial" and (not succeeded or not failed):
        errors.append("partial result must contain both succeeded and failed targets")
    if status in {"rejected", "failed"} and succeeded:
        errors.append(f"{status} result cannot contain succeeded targets")
    if status in {"accepted", "partial"} and not result["provider_receipt"]:
        errors.append(f"{status} result requires a provider receipt")

    validate_capability(payload, errors)
    provider_id = provider["provider_id"]
    property_value = provider["property"]
    for index, target in enumerate(operation["targets"]):
        if target["target_type"] in {"url", "sitemap"} and not target_in_property(provider_id, property_value, target["value"]):
            errors.append(f"operation.targets[{index}].value must be an HTTPS target inside the verified property")

    seen_outcomes: set[str] = set()
    completed_at = times["result.completed_at"]
    recorded_at = times["recorded_at"]
    for index, outcome in enumerate(payload["outcomes"]):
        kind = outcome["kind"]
        if kind in seen_outcomes:
            errors.append(f"outcomes[{index}].kind is duplicated")
        seen_outcomes.add(kind)
        observed_at = outcome["observed_at"]
        evidence_ref = outcome["evidence_ref"]
        evidence_sha = outcome["evidence_sha256"]
        if outcome["state"] in {"observed", "not-observed"}:
            parsed = parse_time(observed_at, f"outcomes[{index}].observed_at", errors)
            if evidence_ref is None or evidence_sha is None:
                errors.append(f"outcomes[{index}] observed state requires hash-bound evidence")
            else:
                check_hash_ref(bundle, evidence_ref, evidence_sha, f"outcomes[{index}]", errors)
            if parsed is not None and completed_at is not None and recorded_at is not None and not (completed_at <= parsed <= recorded_at):
                errors.append(f"outcomes[{index}].observed_at must follow the operation and precede the receipt")
        elif any(value is not None for value in (observed_at, evidence_ref, evidence_sha)):
            errors.append(f"outcomes[{index}] pending/unknown/not-applicable state must not claim observation evidence")

    if errors:
        fail(errors)
    print(f"PASS: provider operation receipt {payload['receipt_id']} with {len(target_ids)} target(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate provider-operation receipts without performing provider mutations.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("validate-receipt")
    command.add_argument("receipt", type=Path)
    command.add_argument("--bundle", required=True, type=Path)
    args = parser.parse_args()
    validate_receipt(args.receipt.resolve(), args.bundle.resolve())


if __name__ == "__main__":
    main()
