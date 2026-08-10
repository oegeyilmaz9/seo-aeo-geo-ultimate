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
SCHEMA_ROOT = ROOT / "manifests" / "artifact-schemas"
CLASSIFICATION_RANK = {"speculative": 0, "experimental": 1, "vendor-recommended": 2, "confirmed": 3}
LEGACY_PRODUCERS = {"seo-audit", "seo-competitor-pages", "seo-content", "seo-hreflang", "seo-images", "seo-page", "seo-programmatic", "seo-research", "seo-schema", "seo-sitemap", "seo-technical"}
LEGACY_TARGET_TYPES = {"site", "web_page", "template", "content_set", "media_set", "sitemap", "locale_cluster"}
LEGACY_CATEGORIES = {"content", "technical", "structured-data", "international", "sitemap", "media", "programmatic", "comparison", "measurement", "accessibility", "policy"}
LEGACY_OWNERS = {"seo-content", "seo-technical", "seo-schema", "seo-hreflang", "seo-sitemap", "seo-images", "seo-programmatic", "seo-competitor-pages", "optimise-seo"}
TARGET_ENVELOPE_FIELDS = {
    "schema_version", "target_id", "target_type", "locale", "source_url", "capture_ref", "capture_sha256",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)


def parse_utc(value: object, field: str, errors: list[str]) -> dt.datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        errors.append(f"{field} must be an ISO 8601 UTC timestamp ending in Z")
        return None
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        errors.append(f"{field} is not a valid timestamp")
        return None
    return parsed if parsed.tzinfo is not None else None


def schemas() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    evidence = load(SCHEMA_ROOT / "evidence-record.schema.json")
    findings = load(SCHEMA_ROOT / "seo-findings.schema.json")
    registry: dict[str, dict[str, Any]] = {evidence["$id"]: evidence, findings["$id"]: findings}
    for name, definition in findings.get("$defs", {}).items():
        if isinstance(definition, dict):
            registry[f"#/$defs/{name}"] = definition
    return findings, registry


def reject_duplicates(items: object, field: str, label: str, errors: list[str]) -> None:
    seen: set[str] = set()
    for index, item in enumerate(items if isinstance(items, list) else []):
        if not isinstance(item, dict):
            continue
        value = item.get(field)
        if isinstance(value, str) and value in seen:
            errors.append(f"{label}[{index}].{field} is a duplicate stable ID")
        elif isinstance(value, str):
            seen.add(value)


def validate_url_less_target_envelope(
    record: dict[str, Any], target: dict[str, Any], raw: Path | None, bundle: Path, label: str, errors: list[str]
) -> bool:
    if raw is None or not raw.is_file():
        return False
    try:
        envelope = load(raw)
    except (OSError, json.JSONDecodeError):
        errors.append(f"{label} URL-less target evidence must be a hash-pinned JSON target envelope")
        return False
    if not isinstance(envelope, dict) or set(envelope) != TARGET_ENVELOPE_FIELDS:
        errors.append(f"{label} URL-less target envelope must contain exactly the target capture fields")
        return False
    expected = {
        "schema_version": "1.0.0",
        "target_id": target.get("target_id"),
        "target_type": target.get("target_type"),
        "locale": target.get("locale"),
        "source_url": None,
    }
    if any(envelope.get(field) != value for field, value in expected.items()):
        errors.append(f"{label} URL-less target envelope does not match its declared scope target")
        return False
    capture_ref, capture_sha = envelope.get("capture_ref"), envelope.get("capture_sha256")
    capture = resolve_relative(bundle, capture_ref, f"{label}.target_envelope.capture_ref", errors)
    if capture is None or not capture.is_file() or digest(capture) != capture_sha:
        errors.append(f"{label} URL-less target envelope capture hash mismatch")
        return False
    return True


def validate_findings(path: Path, bundle: Path) -> None:
    errors: list[str] = []
    artifact = resolve_artifact_in_bundle(path, bundle, errors)
    if artifact is None or errors:
        fail(errors)
    try:
        payload = load(artifact)
    except (OSError, json.JSONDecodeError):
        fail(["seo-findings.json is not valid JSON"])
    schema, registry = schemas()
    validate_schema_instance(payload, schema, registry, "$", errors)
    if not isinstance(payload, dict):
        fail(errors or ["seo-findings.json must contain an object"])
    legacy = payload.get("schema_version") == "1.0.0"
    if legacy and payload.get("producer_skill") not in LEGACY_PRODUCERS:
        errors.append("schema_version 1.1.0 is required for a new specialist producer")

    created_at = parse_utc(payload.get("created_at"), "$.created_at", errors)
    scope = payload.get("scope", {})
    targets = scope.get("targets", []) if isinstance(scope, dict) else []
    reject_duplicates(targets, "target_id", "scope.targets", errors)
    target_by_id = {
        target.get("target_id"): target
        for target in targets if isinstance(target, dict) and isinstance(target.get("target_id"), str)
    }
    if legacy and any(isinstance(target, dict) and target.get("target_type") not in LEGACY_TARGET_TYPES for target in targets):
        errors.append("schema_version 1.1.0 is required for expanded target types")

    evidence = payload.get("evidence", [])
    reject_duplicates(evidence, "claim_id", "evidence", errors)
    evidence_by_id = {
        record.get("claim_id"): record
        for record in evidence if isinstance(record, dict) and isinstance(record.get("claim_id"), str)
    }
    for index, record in enumerate(evidence):
        if not isinstance(record, dict):
            continue
        raw = resolve_relative(bundle, record.get("raw_evidence_ref"), f"evidence[{index}].raw_evidence_ref", errors)
        if raw is not None and not raw.is_file():
            errors.append(f"evidence[{index}] raw evidence does not exist")
        raw_sha = record.get("raw_evidence_sha256")
        if not legacy and raw_sha is None:
            errors.append(f"evidence[{index}].raw_evidence_sha256 is required by SEO Findings 1.1.0")
        elif raw_sha is not None and raw is not None and raw.is_file() and digest(raw) != raw_sha:
            errors.append(f"evidence[{index}] raw evidence hash mismatch")
        if not legacy and record.get("target_id") not in target_by_id:
            errors.append(f"evidence[{index}].target_id must resolve to a scope target in SEO Findings 1.1.0")
        target = target_by_id.get(record.get("target_id"))
        if not legacy and record.get("source_kind") == "direct_observation" and isinstance(target, dict):
            if record.get("locale") != target.get("locale"):
                errors.append(f"evidence[{index}].locale must match its scope target locale")
            if target.get("source_url") is not None:
                if record.get("source_url") != target.get("source_url"):
                    errors.append(f"evidence[{index}].source_url must match its scope target URL")
            else:
                validate_url_less_target_envelope(record, target, raw, bundle, f"evidence[{index}]", errors)
        accessed = parse_utc(record.get("accessed_at"), f"evidence[{index}].accessed_at", errors)
        if created_at is not None and accessed is not None and accessed > created_at:
            errors.append(f"evidence[{index}] chronology: accessed_at is after finding set created_at")

    findings = payload.get("findings", [])
    reject_duplicates(findings, "finding_id", "findings", errors)
    finding_ids: set[str] = set()
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            continue
        finding_id = finding.get("finding_id")
        if isinstance(finding_id, str):
            finding_ids.add(finding_id)
        target = target_by_id.get(finding.get("target_id"))
        if target is None:
            errors.append(f"findings[{index}].target_id does not resolve")
        linked = [evidence_by_id.get(value) for value in finding.get("evidence_ids", [])]
        if not linked or any(record is None for record in linked):
            errors.append(f"findings[{index}].evidence_ids must resolve")
            continue
        records = [record for record in linked if isinstance(record, dict)]
        if target is not None:
            has_target_observation = any(
                record.get("source_kind") == "direct_observation"
                and (
                    record.get("target_id") == finding.get("target_id")
                    and record.get("locale") == target.get("locale")
                    and (
                        record.get("source_url") == target.get("source_url")
                        if target.get("source_url") is not None
                        else True
                    )
                    if not legacy
                    else target.get("source_url") is not None and record.get("source_url") == target.get("source_url")
                )
                for record in records
            )
            if not has_target_observation:
                errors.append(f"findings[{index}] requires capture-tied direct observation evidence for its target")
        classes = [record.get("classification") for record in records if record.get("classification") in CLASSIFICATION_RANK]
        declared = finding.get("classification")
        if classes and declared in CLASSIFICATION_RANK and CLASSIFICATION_RANK[declared] > min(CLASSIFICATION_RANK[value] for value in classes):
            errors.append(f"findings[{index}].classification exceeds its weakest evidence premise")
        if finding.get("category") == "policy" and finding.get("severity") != "critical":
            errors.append(f"findings[{index}] policy findings must be severity=critical")
        if legacy and (finding.get("category") not in LEGACY_CATEGORIES or finding.get("candidate_owner") not in LEGACY_OWNERS):
            errors.append(f"findings[{index}] expanded category or owner requires schema_version 1.1.0")

    if not findings and not payload.get("declined_claims"):
        errors.append("an empty finding set must include at least one declined claim")
    if errors:
        fail(errors)
    print("PASS: seo-findings artifact integrity and evidence traceability")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("validate-findings")
    command.add_argument("artifact", type=Path)
    command.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    validate_findings(args.artifact, args.bundle)


if __name__ == "__main__":
    main()
