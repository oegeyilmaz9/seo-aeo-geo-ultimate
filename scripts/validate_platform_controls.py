from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from bundle_safety import resolve_artifact_in_bundle, resolve_relative
from validate_ai_search_research import validate_schema_instance


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "manifests" / "artifact-schemas" / "platform-controls.schema.json"
SUITE_PATH = ROOT / "manifests" / "suite.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_time(value: object, field: str, errors: list[str]) -> dt.datetime | None:
    if not isinstance(value, str):
        errors.append(f"{field} must be a timestamp")
        return None
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        errors.append(f"{field} is not a valid timestamp")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field} must include a timezone")
        return None
    return parsed


def fail(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)


def validate_registry(path: Path, bundle: Path, as_of: dt.datetime, max_age_days: int) -> None:
    errors: list[str] = []
    artifact = resolve_artifact_in_bundle(path, bundle, errors)
    if artifact is None or errors:
        fail(errors)
    try:
        payload = load(artifact)
    except (OSError, json.JSONDecodeError):
        fail(["platform-controls.json is not valid JSON"])
    schema = load(SCHEMA_PATH)
    suite = load(SUITE_PATH)
    suite_skills = set(suite.get("skills", {})) if isinstance(suite, dict) and isinstance(suite.get("skills"), dict) else set()
    registry: dict[str, dict[str, Any]] = {schema["$id"]: schema}
    for name, definition in schema.get("$defs", {}).items():
        if isinstance(definition, dict):
            registry[f"#/$defs/{name}"] = definition
    validate_schema_instance(payload, schema, registry, "$", errors)
    if not isinstance(payload, dict):
        fail(errors or ["platform-controls.json must contain an object"])

    created_at = parse_time(payload.get("created_at"), "$.created_at", errors)
    review_due_at = parse_time(payload.get("review_due_at"), "$.review_due_at", errors)
    if created_at is not None and review_due_at is not None and review_due_at <= created_at:
        errors.append("review_due_at must be later than created_at")
    if created_at is not None and created_at > as_of:
        errors.append("platform controls registry cannot be created after --as-of")
    if review_due_at is not None and as_of > review_due_at:
        errors.append("platform controls registry is past review_due_at")

    seen_ids: set[str] = set()
    collections = (
        ("features", "feature_id"),
        ("crawlers", "control_id"),
        ("change_notifications", "integration_id"),
        ("protocol_capabilities", "capability_id"),
    )
    for collection, id_field in collections:
        for index, item in enumerate(payload.get(collection, []) if isinstance(payload.get(collection), list) else []):
            if not isinstance(item, dict):
                continue
            item_id = item.get(id_field)
            if isinstance(item_id, str) and item_id in seen_ids:
                errors.append(f"{collection}[{index}].{id_field} duplicates a registry ID")
            elif isinstance(item_id, str):
                seen_ids.add(item_id)
            verified = parse_time(item.get("last_verified_at"), f"{collection}[{index}].last_verified_at", errors)
            if verified is not None:
                if verified > as_of:
                    errors.append(f"{collection}[{index}] was verified after --as-of")
                if created_at is not None and verified > created_at:
                    errors.append(f"{collection}[{index}] was verified after registry creation")
                if as_of - verified > dt.timedelta(days=max_age_days):
                    errors.append(f"{collection}[{index}] verification is older than {max_age_days} days")

    for index, feature in enumerate(payload.get("features", []) if isinstance(payload.get("features"), list) else []):
        if not isinstance(feature, dict):
            continue
        if feature.get("status") in {"deprecated", "removed"} and feature.get("effective_at") is None:
            errors.append(f"features[{index}] deprecated/removed status requires effective_at")
        effective_at = parse_time(feature.get("effective_at"), f"features[{index}].effective_at", errors) if feature.get("effective_at") is not None else None
        if feature.get("status") in {"deprecated", "removed"} and effective_at is not None and effective_at > as_of:
            errors.append(f"features[{index}] deprecated/removed status cannot take effect after --as-of")
        unknown_skills = sorted(set(feature.get("affected_skills", [])) - suite_skills)
        if unknown_skills:
            errors.append(f"features[{index}].affected_skills references unknown suite skills: {unknown_skills}")

    crawler_signatures: set[tuple[object, object, object]] = set()
    for index, crawler in enumerate(payload.get("crawlers", []) if isinstance(payload.get("crawlers"), list) else []):
        if not isinstance(crawler, dict):
            continue
        signature = (crawler.get("vendor"), crawler.get("user_agent"), crawler.get("purpose"))
        if signature in crawler_signatures:
            errors.append(f"crawlers[{index}] duplicates vendor/user-agent/purpose")
        crawler_signatures.add(signature)
        if crawler.get("user_agent") == "*":
            errors.append(f"crawlers[{index}] blanket wildcard controls are not registry entries")
        if crawler.get("business_decision") != "undecided" and (not isinstance(crawler.get("decision_owner"), str) or not crawler.get("decision_owner", "").strip()):
            errors.append(f"crawlers[{index}] decided control requires decision_owner")
        if crawler.get("business_decision") == "undecided" and crawler.get("decision_owner") is not None:
            errors.append(f"crawlers[{index}] undecided control must not imply an approved owner decision")
        ref, sha = crawler.get("log_evidence_ref"), crawler.get("log_evidence_sha256")
        if (ref is None) != (sha is None):
            errors.append(f"crawlers[{index}] log evidence reference and hash must both be null or present")
        elif ref is not None:
            evidence = resolve_relative(bundle, ref, f"crawlers[{index}].log_evidence_ref", errors)
            if evidence is None or not evidence.is_file() or digest(evidence) != sha:
                errors.append(f"crawlers[{index}] log evidence hash mismatch")

    for index, item in enumerate(payload.get("change_notifications", []) if isinstance(payload.get("change_notifications"), list) else []):
        if not isinstance(item, dict):
            continue
        ref, sha = item.get("receipt_ref"), item.get("receipt_sha256")
        if (ref is None) != (sha is None):
            errors.append(f"change_notifications[{index}] receipt reference and hash must both be null or present")
        elif ref is not None:
            receipt = resolve_relative(bundle, ref, f"change_notifications[{index}].receipt_ref", errors)
            if receipt is None or not receipt.is_file() or digest(receipt) != sha:
                errors.append(f"change_notifications[{index}] receipt hash mismatch")
        if item.get("status") == "not-configured" and (item.get("endpoint") is not None or ref is not None):
            errors.append(f"change_notifications[{index}] not-configured integration cannot claim endpoint or receipt")

    if errors:
        fail(errors)
    print("PASS: platform feature lifecycle, crawler controls, notifications, and capabilities")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("validate-registry")
    command.add_argument("artifact", type=Path)
    command.add_argument("--bundle", type=Path, required=True)
    command.add_argument("--as-of", required=True)
    command.add_argument("--max-age-days", type=int, default=45)
    args = parser.parse_args()
    errors: list[str] = []
    as_of = parse_time(args.as_of, "--as-of", errors)
    if as_of is None:
        fail(errors)
    if args.max_age_days <= 0:
        fail(["--max-age-days must be positive"])
    validate_registry(args.artifact, args.bundle, as_of, args.max_age_days)


if __name__ == "__main__":
    main()
