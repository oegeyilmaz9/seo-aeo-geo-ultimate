from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from bundle_safety import resolve_artifact_in_bundle, resolve_relative
from validate_ai_search_research import validate_schema_instance


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "manifests" / "artifact-schemas"
ALLOWED_OWNERS = {"seo-technical", "seo-content", "seo-schema", "seo-hreflang", "optimise-seo"}
CLASSIFICATION_RANK = {"speculative": 0, "experimental": 1, "vendor-recommended": 2, "confirmed": 3}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)


def schema_registry() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    evidence = load(SCHEMA_ROOT / "evidence-record.schema.json")
    research = load(SCHEMA_ROOT / "research-pack.schema.json")
    brief = load(SCHEMA_ROOT / "optimization-brief.schema.json")
    registry = {evidence["$id"]: evidence, research["$id"]: research, brief["$id"]: brief}
    # The compact in-repo validator resolves local definitions by their full fragment IDs.
    for name, definition in brief.get("$defs", {}).items():
        registry[f"#/$defs/{name}"] = definition
    return brief, registry


def validate_reference(ref: object, brief: dict[str, Any], research: dict[str, Any], research_path: Path, where: str, errors: list[str]) -> dict[str, Any] | None:
    if not isinstance(ref, dict):
        return None
    artifact_type = ref.get("artifact_type")
    if artifact_type == "research-pack":
        if ref.get("artifact_id") != research.get("research_id") or ref.get("schema_version") != research.get("schema_version"):
            errors.append(f"{where} research artifact identity/version mismatch")
        if ref.get("artifact_sha256") != digest(research_path):
            errors.append(f"{where} artifact_sha256 does not match research-pack.json")
        if ref.get("collection") != "evidence":
            errors.append(f"{where} research-pack reference must use collection=evidence")
        records = research.get("evidence", [])
    elif artifact_type == "optimization-brief":
        if ref.get("artifact_id") != brief.get("brief_id") or ref.get("schema_version") != brief.get("schema_version"):
            errors.append(f"{where} optimization brief identity/version mismatch")
        if ref.get("artifact_sha256") != "SELF":
            errors.append(f"{where} intra-brief artifact_sha256 must be SELF")
        if ref.get("collection") != "audit_evidence":
            errors.append(f"{where} optimization-brief reference must use collection=audit_evidence")
        records = brief.get("audit_evidence", [])
    else:
        return None
    record_id = ref.get("record_id")
    record = next((item for item in records if isinstance(item, dict) and item.get("claim_id") == record_id), None)
    if record is None:
        errors.append(f"{where} record_id does not resolve")
        return None
    return record


def evidence_fingerprint(record: dict[str, Any]) -> str:
    material = {key: value for key, value in record.items() if key not in {"claim_id", "raw_evidence_ref"}}
    return json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def reject_duplicate_ids(items: object, field: str, collection: str, errors: list[str]) -> None:
    seen: set[str] = set()
    for index, item in enumerate(items if isinstance(items, list) else []):
        if not isinstance(item, dict):
            continue
        value = item.get(field)
        if isinstance(value, str) and value in seen:
            errors.append(f"{collection}[{index}].{field} is a duplicate stable ID")
        elif isinstance(value, str):
            seen.add(value)


def parse_time(value: object) -> dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None


def ref_key(ref: object) -> tuple[object, ...] | None:
    if not isinstance(ref, dict):
        return None
    return tuple(ref.get(key) for key in ("artifact_type", "artifact_id", "schema_version", "collection", "record_id"))


def validate_brief(
    path: Path,
    bundle: Path,
    expected_domain: str = "aeo",
    expected_producer: str = "seo-aeo",
    allowed_dimensions: set[str] | None = None,
    pass_label: str = "seo-aeo",
) -> None:
    errors: list[str] = []
    artifact = resolve_artifact_in_bundle(path, bundle, errors)
    if artifact is None or errors:
        fail(errors)
    try:
        brief = load(artifact)
    except (OSError, json.JSONDecodeError):
        fail(["optimization-brief.json is not valid JSON"])
    schema, registry = schema_registry()
    validate_schema_instance(brief, schema, registry, "$", errors)

    if not isinstance(brief, dict) or errors:
        fail(errors or ["optimization brief must be an object"])
    if brief.get("optimization_domain") != expected_domain:
        errors.append(f"optimization_domain must be '{expected_domain}'")
    if brief.get("producer_skill") != expected_producer:
        errors.append(f"producer_skill must be '{expected_producer}'")

    research_path = resolve_relative(bundle, "research-pack.json", "research-pack.json", errors)
    if research_path is None or not research_path.is_file():
        errors.append("research-pack.json is required in the bundle")
        research: dict[str, Any] = {}
    else:
        try:
            loaded_research = load(research_path)
        except (OSError, json.JSONDecodeError):
            errors.append("research-pack.json is not valid JSON")
            loaded_research = {}
        research = loaded_research if isinstance(loaded_research, dict) else {}
        if not isinstance(loaded_research, dict):
            errors.append("research-pack.json must contain an object")
        research_schema = load(SCHEMA_ROOT / "research-pack.schema.json")
        research_schema_errors: list[str] = []
        validate_schema_instance(research, research_schema, registry, "research-pack", research_schema_errors)
        errors.extend(f"research-pack schema: {error}" for error in research_schema_errors)
        if research.get("research_id") != brief.get("research_id"):
            errors.append("research_id does not match research-pack.json")
        semantic_now = brief.get("created_at")
        if isinstance(semantic_now, str):
            semantic = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate_ai_search_research.py"),
                    "validate-pack",
                    str(research_path),
                    "--bundle",
                    str(bundle),
                    "--now",
                    semantic_now,
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            if semantic.returncode != 0:
                detail = semantic.stderr.strip() or semantic.stdout.strip() or f"exit {semantic.returncode}"
                errors.append(f"research-pack semantic validation failed: {detail}")

    for collection, field in (
        ("entities", "entity_id"), ("queries", "query_id"), ("evidence", "claim_id"),
        ("competitor_observations", "observation_id"), ("ground_truth", "fact_id"), ("gaps", "gap_id")
    ):
        before = len(errors)
        reject_duplicate_ids(research.get(collection), field, f"research-pack {collection}", errors)
        if len(errors) > before:
            errors.append(f"research-pack duplicate stable ID detected in {collection}")

    reject_duplicate_ids(brief.get("targets"), "target_id", "targets", errors)
    reject_duplicate_ids(brief.get("audit_evidence"), "claim_id", "audit_evidence", errors)
    reject_duplicate_ids(brief.get("findings"), "finding_id", "findings", errors)
    reject_duplicate_ids(brief.get("recommendations"), "recommendation_id", "recommendations", errors)
    reject_duplicate_ids(brief.get("experiments"), "experiment_id", "experiments", errors)

    research_evidence = [item for item in research.get("evidence", []) if isinstance(item, dict)]
    audit_evidence = [item for item in brief.get("audit_evidence", []) if isinstance(item, dict)]
    research_claim_ids = {item.get("claim_id") for item in research_evidence}
    research_fingerprints = {evidence_fingerprint(item) for item in research_evidence}
    targets_by_capture = {item.get("capture_ref"): item for item in brief.get("targets", []) if isinstance(item, dict)}
    capture_refs = set(targets_by_capture)
    for index, record in enumerate(audit_evidence):
        if record.get("claim_id") in research_claim_ids or evidence_fingerprint(record) in research_fingerprints:
            errors.append(f"audit_evidence[{index}] audit_evidence copies Research Pack evidence")
        raw = resolve_relative(bundle, record.get("raw_evidence_ref"), f"audit_evidence[{index}].raw_evidence_ref", errors)
        if raw is not None and not raw.is_file():
            errors.append(f"audit_evidence[{index}] raw evidence does not exist")
        if record.get("source_kind") != "direct_observation" or record.get("raw_evidence_ref") not in capture_refs:
            errors.append(f"audit_evidence[{index}] audit evidence must be a capture-tied direct observation")
        else:
            target = targets_by_capture[record.get("raw_evidence_ref")]
            if record.get("source_url") != target.get("source_url"):
                errors.append(f"audit_evidence[{index}] audit evidence source_url does not match target metadata")

    target_ids: set[str] = set()
    targets_by_id: dict[str, dict[str, Any]] = {}
    for index, target in enumerate(brief.get("targets", [])):
        if not isinstance(target, dict):
            continue
        target_id = target.get("target_id")
        if isinstance(target_id, str):
            target_ids.add(target_id)
            targets_by_id[target_id] = target
        capture = resolve_relative(bundle, target.get("capture_ref"), f"targets[{index}].capture_ref", errors)
        metadata_path = resolve_relative(bundle, target.get("metadata_ref"), f"targets[{index}].metadata_ref", errors)
        if metadata_path is None or not metadata_path.is_file():
            errors.append(f"targets[{index}] supplied target metadata does not exist")
        elif target.get("metadata_sha256") != digest(metadata_path):
            errors.append(f"targets[{index}] target metadata hash mismatch")
        else:
            try:
                metadata = load(metadata_path)
            except (OSError, json.JSONDecodeError):
                metadata = None
                errors.append(f"targets[{index}] supplied target metadata is invalid JSON")
            expected_keys = {"target_id", "target_type", "locale", "source_url", "capture_ref", "capture_sha256", "captured_at"}
            if not isinstance(metadata, dict) or set(metadata) != expected_keys:
                errors.append(f"targets[{index}] supplied target metadata has invalid fields")
            elif any(target.get(key) != metadata.get(key) for key in expected_keys):
                errors.append(f"targets[{index}] target fields do not match supplied metadata")
        if target.get("target_type") == "web_page" and (not isinstance(target.get("source_url"), str) or not target.get("source_url", "").startswith("https://")):
            errors.append(f"targets[{index}].source_url must be an https URL for web_page")
        if capture is not None and not capture.is_file():
            errors.append(f"targets[{index}] target capture does not exist")
        elif capture is not None and target.get("capture_sha256") != digest(capture):
            errors.append(f"targets[{index}] target capture hash mismatch")

    created_at = parse_time(brief.get("created_at"))
    if created_at is not None:
        for index, target in enumerate(brief.get("targets", [])):
            if isinstance(target, dict) and (captured := parse_time(target.get("captured_at"))) is not None and captured > created_at:
                errors.append(f"targets[{index}] chronology: captured_at is after brief created_at")
        for index, record in enumerate(audit_evidence):
            if (accessed := parse_time(record.get("accessed_at"))) is not None and accessed > created_at:
                errors.append(f"audit_evidence[{index}] chronology: accessed_at is after brief created_at")

    queries_by_id = {item.get("query_id"): item for item in research.get("queries", []) if isinstance(item, dict)}

    finding_ids: set[str] = set()
    findings_by_id: dict[str, dict[str, Any]] = {}
    for index, finding in enumerate(brief.get("findings", [])):
        if not isinstance(finding, dict):
            continue
        finding_id = finding.get("finding_id")
        if isinstance(finding_id, str):
            finding_ids.add(finding_id)
            findings_by_id[finding_id] = finding
        if finding.get("target_id") not in target_ids:
            errors.append(f"findings[{index}].target_id does not resolve")
        if allowed_dimensions is not None and finding.get("dimension") not in allowed_dimensions:
            errors.append(f"findings[{index}].dimension is not owned by {expected_producer}")
        resolved_records: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for ref_index, ref in enumerate(finding.get("evidence_refs", [])):
            record = validate_reference(ref, brief, research, research_path, f"findings[{index}].evidence_refs[{ref_index}]", errors)
            if record is not None and isinstance(ref, dict):
                resolved_records.append((ref, record))
                locale_ok = record.get("locale") == "not_applicable" or record.get("locale") in finding.get("locales", [])
                engine_ok = record.get("engine") == "not_applicable" or record.get("engine") in finding.get("engines", [])
                surface_ok = record.get("surface") == "not_applicable" or record.get("surface") in finding.get("surfaces", [])
                if not (locale_ok and engine_ok and surface_ok):
                    errors.append(f"findings[{index}].evidence_refs[{ref_index}] evidence scope does not match finding scope")
        target = targets_by_id.get(finding.get("target_id"))
        capture_ref = target.get("capture_ref") if isinstance(target, dict) else None
        has_capture_observation = any(
            ref.get("artifact_type") == "optimization-brief"
            and record.get("source_kind") == "direct_observation"
            and record.get("raw_evidence_ref") == capture_ref
            for ref, record in resolved_records
        )
        if not has_capture_observation:
            errors.append(f"findings[{index}] target observation requires intra-brief audit evidence pinned to its capture")
        if finding.get("dimension") == "cited_source_alignment" and (
            not isinstance(target, dict)
            or target.get("target_type") != "content_set"
            or not str(target.get("capture_ref", "")).startswith("raw/observations/")
        ):
            errors.append(f"findings[{index}] cited-source alignment requires a raw engine observation target")
        elif finding.get("dimension") == "cited_source_alignment" and isinstance(target, dict):
            observation_path = resolve_relative(bundle, target.get("capture_ref"), f"findings[{index}].observation_ref", errors)
            observation = None
            if observation_path is not None and observation_path.is_file():
                try:
                    observation = load(observation_path)
                except (OSError, json.JSONDecodeError):
                    observation = None
            required_observation_keys = {
                "observed_at", "engine", "surface", "locale", "access_status", "answer",
                "mentioned_entities", "cited_urls", "collection_method",
            }
            valid_observation = isinstance(observation, dict) and set(observation) == required_observation_keys
            if valid_observation:
                cited_urls = observation.get("cited_urls")
                mentioned_entities = observation.get("mentioned_entities")
                observed_at = parse_time(observation.get("observed_at"))
                captured_at = parse_time(target.get("captured_at"))
                valid_observation = (
                    observation.get("access_status") == "observed"
                    and isinstance(observation.get("answer"), str) and bool(observation.get("answer").strip())
                    and isinstance(observation.get("collection_method"), str) and bool(observation.get("collection_method").strip())
                    and isinstance(mentioned_entities, list) and all(isinstance(value, str) for value in mentioned_entities)
                    and isinstance(cited_urls, list) and bool(cited_urls)
                    and all(isinstance(value, str) and value.startswith("https://") for value in cited_urls)
                    and observation.get("engine") in finding.get("engines", [])
                    and observation.get("surface") in finding.get("surfaces", [])
                    and observation.get("locale") in finding.get("locales", [])
                    and observed_at is not None
                    and captured_at is not None
                    and observed_at <= captured_at
                    and (created_at is None or observed_at <= created_at)
                )
                if observed_at is not None and captured_at is not None and observed_at > captured_at:
                    errors.append(f"findings[{index}] observed_at cannot follow target captured_at")
            if not valid_observation:
                errors.append(f"findings[{index}] raw engine observation is invalid")
            else:
                research_source_urls = {
                    record.get("source_url")
                    for ref, record in resolved_records
                    if ref.get("artifact_type") == "research-pack" and isinstance(record.get("source_url"), str)
                }
                if research_source_urls.isdisjoint(set(observation.get("cited_urls", []))):
                    errors.append(f"findings[{index}] observed cited URLs do not align with referenced Research Pack sources")
        query_ids = finding.get("query_ids", [])
        queries = [queries_by_id.get(query_id) for query_id in query_ids]
        if not queries or any(query is None for query in queries):
            errors.append(f"findings[{index}] query_ids do not resolve")
        elif isinstance(target, dict):
            target_locale = target.get("locale")
            allowed_pairs = {
                (row.get("engine"), row.get("surface"))
                for query in queries if isinstance(query, dict) and query.get("locale") == target_locale
                for row in query.get("applicability", []) if isinstance(row, dict)
            }
            declared_pairs = {(engine, surface) for engine in finding.get("engines", []) for surface in finding.get("surfaces", [])}
            if finding.get("locales") != [target_locale] or not declared_pairs or not declared_pairs.issubset(allowed_pairs):
                errors.append(f"findings[{index}] finding scope does not match target/query applicability")
        classifications = [record.get("classification") for _, record in resolved_records if record.get("classification") in CLASSIFICATION_RANK]
        declared = finding.get("classification")
        if classifications and declared in CLASSIFICATION_RANK and CLASSIFICATION_RANK[declared] > min(CLASSIFICATION_RANK[value] for value in classifications):
            errors.append(f"findings[{index}].classification exceeds its weakest evidence premise")
        if finding.get("dimension") == "documented_engine_control" and not any(
            record.get("source_kind") in {"vendor_documentation", "standard"}
            and record.get("classification") in {"confirmed", "vendor-recommended"}
            for _, record in resolved_records
        ):
            errors.append(f"findings[{index}] documented engine control requires vendor documentation or standard evidence")

    for index, recommendation in enumerate(brief.get("recommendations", [])):
        if not isinstance(recommendation, dict):
            continue
        refs = recommendation.get("evidence_refs", [])
        if not refs:
            errors.append(f"recommendations[{index}] recommendation evidence_refs must not be empty")
        records = [
            validate_reference(ref, brief, research, research_path, f"recommendations[{index}].evidence_refs[{ref_index}]", errors)
            for ref_index, ref in enumerate(refs)
        ]
        classifications = [record.get("classification") for record in records if isinstance(record, dict)]
        if "speculative" in classifications:
            errors.append(f"recommendations[{index}] speculative evidence cannot support an implementation recommendation")
            if recommendation.get("confidence") == "high":
                errors.append(f"recommendations[{index}] speculative evidence cannot support a high-confidence recommendation")
        if recommendation.get("confidence") == "high" and any(value != "confirmed" for value in classifications):
            errors.append(f"recommendations[{index}] high confidence requires only confirmed evidence")
        if recommendation.get("confidence") == "medium" and any(value in {"experimental", "speculative"} for value in classifications):
            errors.append(f"recommendations[{index}] medium confidence exceeds its evidence premise")
        if classifications and all(value == "experimental" for value in classifications):
            errors.append(f"recommendations[{index}] experimental-only evidence belongs in experiments")
        if recommendation.get("owner_skill") not in ALLOWED_OWNERS:
            errors.append(f"recommendations[{index}] owner_skill is not an approved implementation owner")
        for finding_id in recommendation.get("finding_ids", []):
            if finding_id not in finding_ids:
                errors.append(f"recommendations[{index}].finding_ids contains an unresolved finding")
        recommendation_keys = {key for ref in refs if (key := ref_key(ref)) is not None}
        for finding_id in recommendation.get("finding_ids", []):
            linked = findings_by_id.get(finding_id)
            linked_keys = {key for ref in linked.get("evidence_refs", []) if (key := ref_key(ref)) is not None} if isinstance(linked, dict) else set()
            if linked_keys and recommendation_keys.isdisjoint(linked_keys):
                errors.append(f"recommendations[{index}] recommendation evidence does not overlap linked finding evidence")
        linked_findings = [findings_by_id.get(value) for value in recommendation.get("finding_ids", [])]
        linked_classifications = [
            finding.get("classification") for finding in linked_findings if isinstance(finding, dict)
        ]
        if any(value in {"speculative", "experimental"} for value in linked_classifications):
            errors.append(f"recommendations[{index}] linked speculative or experimental finding cannot support implementation")
        if recommendation.get("confidence") == "high" and any(value != "confirmed" for value in linked_classifications):
            errors.append(f"recommendations[{index}] high confidence exceeds linked finding classification")
        if recommendation.get("confidence") == "medium" and any(value not in {"confirmed", "vendor-recommended"} for value in linked_classifications):
            errors.append(f"recommendations[{index}] medium confidence exceeds linked finding classification")
        allowed_locales = {locale for finding in linked_findings if isinstance(finding, dict) for locale in finding.get("locales", [])}
        allowed_engines = {engine for finding in linked_findings if isinstance(finding, dict) for engine in finding.get("engines", [])}
        allowed_surfaces = {surface for finding in linked_findings if isinstance(finding, dict) for surface in finding.get("surfaces", [])}
        for record in records:
            if not isinstance(record, dict):
                continue
            if ((record.get("locale") != "not_applicable" and record.get("locale") not in allowed_locales)
                    or (record.get("engine") != "not_applicable" and record.get("engine") not in allowed_engines)
                    or (record.get("surface") != "not_applicable" and record.get("surface") not in allowed_surfaces)):
                errors.append(f"recommendations[{index}] recommendation evidence scope is incompatible with linked findings")

    if errors:
        fail(errors)
    print(f"PASS: {pass_label} optimization brief")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("validate-brief")
    command.add_argument("artifact", type=Path)
    command.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    validate_brief(args.artifact, args.bundle)


if __name__ == "__main__":
    main()
