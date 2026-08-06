from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

from bundle_safety import resolve_artifact_in_bundle, resolve_relative
from validate_ai_search_research import validate_schema_instance


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "manifests" / "artifact-schemas"
SKILL = ROOT / "skills" / "seo-action-plan"
CONTRACTS = SKILL / "references" / "contracts"
SCHEMA_NAMES = (
    "evidence-record.schema.json",
    "research-pack.schema.json",
    "optimization-brief.schema.json",
    "seo-findings.schema.json",
    "action-plan.schema.json",
)
LOCK_VERSION = "1.0.0"
TOOL_VERSION = "1.0.0"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def die(errors: list[str]) -> None:
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


def schema_registry() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    schemas: dict[str, dict[str, Any]] = {}
    registry: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for name in SCHEMA_NAMES:
        path = SCHEMA_ROOT / name
        if not path.is_file():
            errors.append(f"missing canonical schema: {name}")
            continue
        schema = load(path)
        if not isinstance(schema, dict) or not isinstance(schema.get("$id"), str):
            errors.append(f"invalid canonical schema: {name}")
            continue
        schemas[name] = schema
        registry[schema["$id"]] = schema
    action = schemas.get("action-plan.schema.json")
    if isinstance(action, dict):
        for name, definition in action.get("$defs", {}).items():
            if isinstance(definition, dict):
                registry[f"#/$defs/{name}"] = definition
    if errors:
        die(errors)
    return schemas, registry


def reject_duplicate_ids(items: object, field: str, label: str, errors: list[str]) -> None:
    seen: set[str] = set()
    for index, item in enumerate(items if isinstance(items, list) else []):
        if not isinstance(item, dict):
            continue
        value = item.get(field)
        if isinstance(value, str) and value in seen:
            errors.append(f"{label}[{index}].{field} is a duplicate stable ID")
        elif isinstance(value, str):
            seen.add(value)


def run_upstream_validator(
    descriptor: dict[str, Any], artifact: Path, input_bundle: Path, errors: list[str], index: int
) -> None:
    producer = descriptor.get("producer_skill")
    validators = {
        "seo-aeo": ROOT / "scripts" / "validate_seo_aeo.py",
        "seo-geo": ROOT / "scripts" / "validate_seo_geo.py",
    }
    validator = validators.get(producer)
    if validator is None:
        errors.append(f"input_briefs[{index}].producer_skill has no upstream validator")
        return
    completed = subprocess.run(
        [sys.executable, str(validator), "validate-brief", str(artifact), "--bundle", str(input_bundle)],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}")
        errors.append(f"input_briefs[{index}] upstream validation failed: {detail}")


def run_findings_validator(artifact: Path, input_bundle: Path, errors: list[str], index: int) -> None:
    validator = ROOT / "scripts" / "validate_seo_findings.py"
    completed = subprocess.run(
        [sys.executable, str(validator), "validate-findings", str(artifact), "--bundle", str(input_bundle)],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
        errors.append(f"input_findings[{index}] upstream validation failed: {detail}")


def evidence_key(brief_id: str, item: object) -> tuple[str, str, str, str] | None:
    if not isinstance(item, dict):
        return None
    artifact_type = item.get("artifact_type")
    collection = item.get("collection")
    record_id = item.get("record_id")
    if all(isinstance(value, str) for value in (artifact_type, collection, record_id)):
        return (brief_id, artifact_type, collection, record_id)
    return None


def resolve_input(
    descriptor: dict[str, Any], bundle: Path, errors: list[str], index: int
) -> dict[str, Any] | None:
    input_bundle = resolve_relative(bundle, descriptor.get("bundle_ref"), f"input_briefs[{index}].bundle_ref", errors)
    artifact = resolve_relative(bundle, descriptor.get("artifact_ref"), f"input_briefs[{index}].artifact_ref", errors)
    if input_bundle is None or artifact is None:
        return None
    if not input_bundle.is_dir():
        errors.append(f"input_briefs[{index}].bundle_ref must resolve to a directory")
        return None
    if not artifact.is_file():
        errors.append(f"input_briefs[{index}].artifact_ref must resolve to a regular file")
        return None
    try:
        artifact.resolve().relative_to(input_bundle.resolve())
    except ValueError:
        errors.append(f"input_briefs[{index}].artifact_ref must be inside bundle_ref")
        return None
    if descriptor.get("artifact_sha256") != digest(artifact):
        errors.append(f"input_briefs[{index}].artifact_sha256 does not match artifact_ref")
    try:
        brief = load(artifact)
    except (OSError, json.JSONDecodeError):
        errors.append(f"input_briefs[{index}].artifact_ref is not valid JSON")
        return None
    if not isinstance(brief, dict):
        errors.append(f"input_briefs[{index}].artifact_ref must contain an object")
        return None
    for field in ("brief_id", "schema_version", "producer_skill", "optimization_domain"):
        if descriptor.get(field) != brief.get(field):
            errors.append(f"input_briefs[{index}].{field} does not match artifact")

    research_path = resolve_relative(input_bundle, "research-pack.json", f"input_briefs[{index}].research-pack.json", errors)
    if research_path is None or not research_path.is_file():
        errors.append(f"input_briefs[{index}] input bundle is missing research-pack.json")
        research: dict[str, Any] = {}
    else:
        try:
            research = load(research_path)
        except (OSError, json.JSONDecodeError):
            errors.append(f"input_briefs[{index}] research-pack.json is invalid JSON")
            research = {}
    run_upstream_validator(descriptor, artifact, input_bundle, errors, index)
    return {"descriptor": descriptor, "bundle": input_bundle, "brief": brief, "research": research}


def resolve_findings_input(
    descriptor: dict[str, Any], bundle: Path, errors: list[str], index: int
) -> dict[str, Any] | None:
    label = f"input_findings[{index}]"
    input_bundle = resolve_relative(bundle, descriptor.get("bundle_ref"), f"{label}.bundle_ref", errors)
    artifact = resolve_relative(bundle, descriptor.get("artifact_ref"), f"{label}.artifact_ref", errors)
    if input_bundle is None or artifact is None:
        return None
    if not input_bundle.is_dir():
        errors.append(f"{label}.bundle_ref must resolve to a directory")
        return None
    if not artifact.is_file():
        errors.append(f"{label}.artifact_ref must resolve to a regular file")
        return None
    try:
        artifact.resolve().relative_to(input_bundle.resolve())
    except ValueError:
        errors.append(f"{label}.artifact_ref must be inside bundle_ref")
        return None
    if descriptor.get("artifact_sha256") != digest(artifact):
        errors.append(f"{label}.artifact_sha256 does not match artifact_ref")
    try:
        finding_set = load(artifact)
    except (OSError, json.JSONDecodeError):
        errors.append(f"{label}.artifact_ref is not valid JSON")
        return None
    if not isinstance(finding_set, dict):
        errors.append(f"{label}.artifact_ref must contain an object")
        return None
    for field in ("finding_set_id", "schema_version", "producer_skill"):
        if descriptor.get(field) != finding_set.get(field):
            errors.append(f"{label}.{field} does not match artifact")
    run_findings_validator(artifact, input_bundle, errors, index)
    return {"descriptor": descriptor, "bundle": input_bundle, "findings": finding_set}


def finding_map(brief: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["finding_id"]: item
        for item in brief.get("findings", [])
        if isinstance(item, dict) and isinstance(item.get("finding_id"), str)
    }


def evidence_record_map(item: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    brief = item["brief"]
    research = item["research"]
    records: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in brief.get("audit_evidence", []):
        if isinstance(record, dict) and isinstance(record.get("claim_id"), str):
            records[("optimization-brief", "audit_evidence", record["claim_id"])] = record
    for record in research.get("evidence", []):
        if isinstance(record, dict) and isinstance(record.get("claim_id"), str):
            records[("research-pack", "evidence", record["claim_id"])] = record
    return records


def seo_finding_map(item: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        finding["finding_id"]: finding
        for finding in item["findings"].get("findings", [])
        if isinstance(finding, dict) and isinstance(finding.get("finding_id"), str)
    }


def seo_evidence_record_map(item: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {
        ("seo-findings", "evidence", record["claim_id"]): record
        for record in item["findings"].get("evidence", [])
        if isinstance(record, dict) and isinstance(record.get("claim_id"), str)
    }


def graph_has_cycle(edges: dict[str, list[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for child in edges.get(node, []):
            if visit(child):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in edges)


def validate_plan(path: Path, bundle: Path) -> None:
    errors: list[str] = []
    artifact = resolve_artifact_in_bundle(path, bundle, errors)
    if artifact is None or errors:
        die(errors)
    try:
        plan = load(artifact)
    except (OSError, json.JSONDecodeError):
        die(["action-plan.json is not valid JSON"])
    schemas, registry = schema_registry()
    validate_schema_instance(plan, schemas["action-plan.schema.json"], registry, "$", errors)
    if not isinstance(plan, dict):
        die(errors or ["action-plan.json must contain an object"])

    plan_created_at = parse_utc(plan.get("created_at"), "$.created_at", errors)
    brief_descriptors = plan.get("input_briefs", [])
    findings_descriptors = plan.get("input_findings", [])
    if not isinstance(brief_descriptors, list):
        brief_descriptors = []
    if not isinstance(findings_descriptors, list):
        findings_descriptors = []
    if not brief_descriptors and not findings_descriptors:
        errors.append("an action plan requires at least one input brief or finding set")
    if findings_descriptors and plan.get("schema_version") != "1.1.0":
        errors.append("schema_version must equal '1.1.0' when input_findings are present")
    reject_duplicate_ids(brief_descriptors, "brief_id", "input_briefs", errors)
    reject_duplicate_ids(findings_descriptors, "finding_set_id", "input_findings", errors)

    brief_inputs: dict[str, dict[str, Any]] = {}
    for index, descriptor in enumerate(brief_descriptors):
        if not isinstance(descriptor, dict):
            continue
        resolved = resolve_input(descriptor, bundle, errors, index)
        brief_id = descriptor.get("brief_id")
        if resolved is not None and isinstance(brief_id, str):
            brief_inputs[brief_id] = resolved
            brief_created_at = parse_utc(resolved["brief"].get("created_at"), f"input_briefs[{index}].artifact.created_at", errors)
            if plan_created_at is not None and brief_created_at is not None and brief_created_at > plan_created_at:
                errors.append(f"input_briefs[{index}] chronology: input brief is newer than action plan")

    findings_inputs: dict[str, dict[str, Any]] = {}
    for index, descriptor in enumerate(findings_descriptors):
        if not isinstance(descriptor, dict):
            continue
        resolved = resolve_findings_input(descriptor, bundle, errors, index)
        finding_set_id = descriptor.get("finding_set_id")
        if resolved is not None and isinstance(finding_set_id, str):
            findings_inputs[finding_set_id] = resolved
            findings_created_at = parse_utc(
                resolved["findings"].get("created_at"), f"input_findings[{index}].artifact.created_at", errors
            )
            if plan_created_at is not None and findings_created_at is not None and findings_created_at > plan_created_at:
                errors.append(f"input_findings[{index}] chronology: input finding set is newer than action plan")

    all_target_ids: set[str] = set()
    all_locales: set[str] = set()
    target_origins: dict[str, str] = {}

    def add_targets(targets: object, origin: str) -> None:
        for target in targets if isinstance(targets, list) else []:
            if isinstance(target, dict):
                target_id = target.get("target_id")
                locale = target.get("locale")
                if isinstance(target_id, str):
                    prior = target_origins.get(target_id)
                    if prior is not None and prior != origin:
                        errors.append(f"target_id {target_id!r} is ambiguous across {prior} and {origin}")
                    target_origins[target_id] = origin
                    all_target_ids.add(target_id)
                if isinstance(locale, str):
                    all_locales.add(locale)

    for item_id, item in brief_inputs.items():
        add_targets(item["brief"].get("targets", []), f"brief {item_id}")
    for item_id, item in findings_inputs.items():
        scope = item["findings"].get("scope", {})
        targets = scope.get("targets", []) if isinstance(scope, dict) else []
        add_targets(targets, f"finding set {item_id}")

    scope = plan.get("scope")
    if isinstance(scope, dict):
        for index, target_id in enumerate(scope.get("target_ids", [])):
            if target_id not in all_target_ids:
                errors.append(f"scope.target_ids[{index}] does not resolve in an input artifact")
        for index, locale in enumerate(scope.get("locales", [])):
            if locale not in all_locales:
                errors.append(f"scope.locales[{index}] does not resolve in an input artifact")

    actions = plan.get("actions", [])
    declined = plan.get("declined_actions", [])
    if isinstance(actions, list) and not actions and not declined:
        errors.append("an empty action plan must contain at least one declined action")
    reject_duplicate_ids(actions, "action_id", "actions", errors)
    reject_duplicate_ids(declined, "declined_id", "declined_actions", errors)

    action_ids = {
        action.get("action_id")
        for action in actions if isinstance(action, dict) and isinstance(action.get("action_id"), str)
    }
    dependencies: dict[str, list[str]] = {}
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            continue
        action_id = action.get("action_id")
        linked_findings: list[dict[str, Any]] = []
        linked_evidence_keys: set[tuple[str, str, str, str]] = set()
        classifications: list[str] = []
        for ref_index, ref in enumerate(action.get("finding_refs", [])):
            if not isinstance(ref, dict):
                continue
            brief_id = ref.get("brief_id")
            finding_set_id = ref.get("finding_set_id")
            finding_id = ref.get("finding_id")
            if isinstance(brief_id, str) == isinstance(finding_set_id, str):
                errors.append(f"actions[{index}].finding_refs[{ref_index}] must name exactly one input artifact")
                continue
            finding: dict[str, Any] | None = None
            if isinstance(brief_id, str):
                input_item = brief_inputs.get(brief_id)
                finding = finding_map(input_item["brief"]).get(finding_id) if input_item and isinstance(finding_id, str) else None
                if finding is not None:
                    for source_ref in finding.get("evidence_refs", []):
                        key = evidence_key(brief_id, source_ref)
                        if key is not None:
                            linked_evidence_keys.add(key)
            elif isinstance(finding_set_id, str):
                input_item = findings_inputs.get(finding_set_id)
                finding = seo_finding_map(input_item).get(finding_id) if input_item and isinstance(finding_id, str) else None
                if finding is not None:
                    for evidence_id in finding.get("evidence_ids", []):
                        if isinstance(evidence_id, str):
                            linked_evidence_keys.add((finding_set_id, "seo-findings", "evidence", evidence_id))
            if finding is None:
                errors.append(f"actions[{index}].finding_refs[{ref_index}] does not resolve")
                continue
            linked_findings.append(finding)
            classification = finding.get("classification")
            if isinstance(classification, str):
                classifications.append(classification)

        resolved_evidence: list[dict[str, Any]] = []
        action_evidence_keys: set[tuple[str, str, str, str]] = set()
        for ref_index, ref in enumerate(action.get("evidence_refs", [])):
            if not isinstance(ref, dict):
                continue
            brief_id = ref.get("brief_id")
            finding_set_id = ref.get("finding_set_id")
            if isinstance(brief_id, str) == isinstance(finding_set_id, str):
                errors.append(f"actions[{index}].evidence_refs[{ref_index}] must name exactly one input artifact")
                continue
            source_id = brief_id if isinstance(brief_id, str) else finding_set_id if isinstance(finding_set_id, str) else None
            key = evidence_key(source_id, ref) if isinstance(source_id, str) else None
            if key is None:
                errors.append(f"actions[{index}].evidence_refs[{ref_index}] does not resolve")
                continue
            if isinstance(brief_id, str):
                input_item = brief_inputs.get(brief_id)
                record = evidence_record_map(input_item).get(key[1:]) if input_item else None
            elif isinstance(finding_set_id, str):
                input_item = findings_inputs.get(finding_set_id)
                record = seo_evidence_record_map(input_item).get(key[1:]) if input_item else None
            else:
                record = None
            if record is None:
                errors.append(f"actions[{index}].evidence_refs[{ref_index}] record does not resolve")
                continue
            action_evidence_keys.add(key)
            resolved_evidence.append(record)
            classification = record.get("classification")
            if isinstance(classification, str):
                classifications.append(classification)

        if linked_evidence_keys and action_evidence_keys.isdisjoint(linked_evidence_keys):
            errors.append(f"actions[{index}] evidence_refs do not overlap linked finding evidence")
        if not linked_findings:
            errors.append(f"actions[{index}] must resolve at least one finding")
        if not resolved_evidence:
            errors.append(f"actions[{index}] must resolve at least one evidence record")

        confidence = action.get("confidence")
        if "speculative" in classifications:
            errors.append(f"actions[{index}] cannot be based on speculative evidence or findings")
        if confidence == "high" and any(value != "confirmed" for value in classifications):
            errors.append(f"actions[{index}].confidence high requires only confirmed evidence and findings")
        if confidence == "medium" and any(value not in {"confirmed", "vendor-recommended"} for value in classifications):
            errors.append(f"actions[{index}].confidence medium exceeds its evidence premise")
        if "experimental" in classifications and (confidence != "low" or action.get("priority") != "later"):
            errors.append(f"actions[{index}] experimental support requires a low-confidence later action")

        owner = action.get("owner")
        if isinstance(owner, dict):
            owner_text = " ".join(str(owner.get(key, "")) for key in ("team", "role")).casefold()
            if "seo-action-plan" in owner_text or "seo action plan" in owner_text:
                errors.append(f"actions[{index}].owner cannot assign implementation to seo-action-plan")

        rollback = action.get("rollback")
        if isinstance(rollback, dict) and action.get("risk") == "high" and rollback.get("required") is not True:
            errors.append(f"actions[{index}] high-risk changes require rollback.required=true")
        if action.get("change_type") == "policy" and action.get("risk") != "high":
            errors.append(f"actions[{index}] policy changes must be high risk")

        action_dependencies = action.get("dependencies", [])
        if isinstance(action_id, str):
            dependencies[action_id] = []
            for dependency_index, dependency in enumerate(action_dependencies):
                if dependency not in action_ids:
                    errors.append(f"actions[{index}].dependencies[{dependency_index}] does not resolve")
                elif dependency == action_id:
                    errors.append(f"actions[{index}] cannot depend on itself")
                elif isinstance(dependency, str):
                    dependencies[action_id].append(dependency)
    if graph_has_cycle(dependencies):
        errors.append("action dependencies must not contain a cycle")

    if errors:
        die(errors)
    print("PASS: seo-action-plan artifact integrity and evidence traceability")


def contract_payloads() -> dict[str, bytes]:
    schemas, _ = schema_registry()
    rows: list[dict[str, str]] = []
    payloads: dict[str, bytes] = {}
    for name in SCHEMA_NAMES:
        path = SCHEMA_ROOT / name
        content = path.read_bytes()
        payloads[name] = content
        schema = schemas[name]
        schema_id = schema["$id"]
        rows.append(
            {
                "canonical_path": path.relative_to(ROOT).as_posix(),
                "generated_path": (Path("references") / "contracts" / name).as_posix(),
                "schema_id": schema_id,
                "schema_version": schema_id.rstrip("/").split("/")[-1],
                "canonical_sha256": hashlib.sha256(content).hexdigest(),
                "generated_sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    payloads["contracts-lock.json"] = (
        json.dumps(
            {"lock_version": LOCK_VERSION, "generation_tool_version": TOOL_VERSION, "contracts": rows},
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    return payloads


def sync_contracts() -> None:
    payloads = contract_payloads()
    CONTRACTS.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="action-plan-contracts-", dir=CONTRACTS.parent))
    backup = CONTRACTS.with_name(f"{CONTRACTS.name}.backup-{uuid.uuid4().hex}")
    moved_existing = False
    try:
        for name, content in payloads.items():
            (staging / name).write_bytes(content)
        if CONTRACTS.exists():
            CONTRACTS.replace(backup)
            moved_existing = True
        staging.replace(CONTRACTS)
        if backup.exists():
            shutil.rmtree(backup)
    except BaseException:
        if moved_existing and backup.exists() and not CONTRACTS.exists():
            backup.replace(CONTRACTS)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    print(f"PASS: synchronized {len(SCHEMA_NAMES)} contracts")


def validate_contract_lock(errors: list[str]) -> None:
    if not (CONTRACTS / "contracts-lock.json").is_file():
        errors.append("contracts-lock.json missing")
        return
    try:
        actual = load(CONTRACTS / "contracts-lock.json")
    except (OSError, json.JSONDecodeError):
        errors.append("contracts-lock.json is invalid JSON")
        return
    expected = json.loads(contract_payloads()["contracts-lock.json"])
    if actual != expected:
        errors.append("contracts-lock.json does not match canonical contracts")
    for name in SCHEMA_NAMES:
        canonical = SCHEMA_ROOT / name
        generated = CONTRACTS / name
        if not generated.is_file():
            errors.append(f"generated contract missing: {name}")
        elif digest(canonical) != digest(generated):
            errors.append(f"generated contract drift: {name}")


def validate_openai_yaml(path: Path, errors: list[str]) -> None:
    if not path.is_file():
        errors.append("agents/openai.yaml missing")
        return
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines or lines[0] != "interface:":
        errors.append("openai.yaml must start with interface:")
        return
    expected = {
        "display_name": "SEO Action Plan",
        "short_description": "Turn findings into safe action plans",
    }
    values: dict[str, str] = {}
    for line in lines[1:]:
        match = re.fullmatch(r'  ([A-Za-z_][A-Za-z0-9_-]*): "(.*)"', line)
        if match is None:
            errors.append("openai.yaml interface entries must be quoted two-space keys")
            continue
        values[match.group(1)] = match.group(2)
    if set(values) != {"display_name", "short_description", "default_prompt"}:
        errors.append("openai.yaml must contain exactly display_name, short_description, default_prompt")
    for key, value in expected.items():
        if values.get(key) != value:
            errors.append(f"openai.yaml {key} mismatch")
    if "$seo-action-plan" not in values.get("default_prompt", ""):
        errors.append("openai.yaml default_prompt must contain $seo-action-plan")
    description = values.get("short_description", "")
    if description and not 25 <= len(description) <= 64:
        errors.append("openai.yaml short_description must contain 25-64 characters")


def validate_skill() -> None:
    errors: list[str] = []
    allowed_roots = {"SKILL.md", "agents", "references", "scripts"}
    actual_roots = {path.name for path in SKILL.iterdir()}
    if actual_roots - allowed_roots:
        errors.append(f"deployable root allow-list violation: {sorted(actual_roots - allowed_roots)}")
    scaffold_scripts = SKILL / "scripts"
    if scaffold_scripts.exists() and any(scaffold_scripts.iterdir()):
        errors.append("scripts/ must stay empty; validators are suite-level tooling")
    expected_files = {
        "SKILL.md",
        "agents/openai.yaml",
        "references/action-plan-protocol.md",
        "references/contracts/evidence-record.schema.json",
        "references/contracts/research-pack.schema.json",
        "references/contracts/optimization-brief.schema.json",
        "references/contracts/seo-findings.schema.json",
        "references/contracts/action-plan.schema.json",
        "references/contracts/contracts-lock.json",
    }
    actual_files = {path.relative_to(SKILL).as_posix() for path in SKILL.rglob("*") if path.is_file()}
    if actual_files != expected_files:
        errors.append(f"deployable file set mismatch: missing={sorted(expected_files - actual_files)} extra={sorted(actual_files - expected_files)}")
    skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8") if (SKILL / "SKILL.md").is_file() else ""
    lines = skill_text.splitlines()
    if len(lines) >= 500:
        errors.append("SKILL.md must be fewer than 500 lines")
    if "TODO" in skill_text or "[TODO" in skill_text:
        errors.append("SKILL.md must not contain scaffold TODO text")
    if len(lines) < 4 or lines[0] != "---" or lines[3] != "---":
        errors.append("SKILL.md frontmatter must be exactly two fields between delimiters")
    else:
        if lines[1] != "name: seo-action-plan":
            errors.append("SKILL.md frontmatter name mismatch")
        if not lines[2].startswith("description: Use when"):
            errors.append("SKILL.md description must start with 'Use when'")
    validate_openai_yaml(SKILL / "agents" / "openai.yaml", errors)
    validate_contract_lock(errors)
    if errors:
        die(errors)
    print("PASS: seo-action-plan skill structure and contracts")


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate-plan")
    validate.add_argument("artifact", type=Path)
    validate.add_argument("--bundle", type=Path, required=True)
    commands.add_parser("sync-contracts")
    commands.add_parser("validate-skill")
    args = parser.parse_args()
    if args.command == "validate-plan":
        validate_plan(args.artifact, args.bundle)
    elif args.command == "sync-contracts":
        sync_contracts()
    else:
        validate_skill()


if __name__ == "__main__":
    main()
