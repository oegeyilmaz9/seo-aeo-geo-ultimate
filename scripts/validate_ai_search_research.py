from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

from bundle_safety import resolve_artifact_in_bundle, resolve_relative

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "ai-search-research"
CANON = ROOT / "manifests" / "artifact-schemas"
CONTRACTS = SKILL / "references" / "contracts"
SCHEMAS = ("evidence-record.schema.json", "research-pack.schema.json")
LOCK_VERSION = "1.0.0"
TOOL_VERSION = "1.0.0"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
LOCALE_RE = re.compile(r"^[a-z]{2}-[A-Z]{2}$")
DATE_TIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
LOCK_KEYS = {"lock_version", "generation_tool_version", "contracts"}
LOCK_ROW_KEYS = {
    "canonical_path",
    "generated_path",
    "schema_id",
    "schema_version",
    "canonical_sha256",
    "generated_sha256",
}
INTERFACE_KEYS = ("display_name", "short_description", "default_prompt")
DISPLAY_NAME = "AI Search Research"
SHORT_DESCRIPTION = "Build locale-declared multilingual AI-search research packs"


def die(messages: list[str]) -> None:
    for message in messages:
        print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def utc(value: object, field: str, errors: list[str]) -> dt.datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        errors.append(f"{field} must be an ISO 8601 UTC timestamp ending in Z")
        return None
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        errors.append(f"{field} is not a valid timestamp")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field} must be an ISO 8601 UTC timestamp ending in Z")
        return None
    return parsed


def parse_now(value: object) -> dt.datetime:
    errors: list[str] = []
    parsed = utc(value, "--now", errors)
    if parsed is None:
        die(["--now must be an ISO 8601 UTC timestamp ending in Z"])
    return parsed


def is_date_time(value: str) -> bool:
    if DATE_TIME_RE.fullmatch(value) is None:
        return False
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def json_equal(left: object, right: object) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, list):
        return len(left) == len(right) and all(json_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(json_equal(left[key], right[key]) for key in left)
    return left == right


def type_matches(value: object, expected: str) -> bool:
    checks = {
        "null": lambda: value is None,
        "boolean": lambda: isinstance(value, bool),
        "object": lambda: isinstance(value, dict),
        "array": lambda: isinstance(value, list),
        "string": lambda: isinstance(value, str),
        "integer": lambda: isinstance(value, int) and not isinstance(value, bool),
        "number": lambda: isinstance(value, (int, float)) and not isinstance(value, bool),
    }
    return expected in checks and checks[expected]()


def validate_schema_instance(
    value: object,
    schema: object,
    registry: dict[str, dict[str, Any]],
    where: str,
    errors: list[str],
) -> None:
    if not isinstance(schema, dict):
        errors.append(f"schema: {where} uses an invalid schema node")
        return

    reference = schema.get("$ref")
    if reference is not None:
        target = registry.get(reference) if isinstance(reference, str) else None
        if target is None:
            errors.append(f"schema: {where} has unresolved $ref {reference!r}")
        else:
            validate_schema_instance(value, target, registry, where, errors)

    all_of = schema.get("allOf")
    if all_of is not None:
        if not isinstance(all_of, list):
            errors.append(f"schema: {where} has an invalid allOf declaration")
        else:
            for branch in all_of:
                validate_schema_instance(value, branch, registry, where, errors)

    any_of = schema.get("anyOf")
    if any_of is not None:
        if not isinstance(any_of, list) or not any_of:
            errors.append(f"schema: {where} has an invalid anyOf declaration")
        else:
            branch_errors: list[list[str]] = []
            for branch in any_of:
                trial: list[str] = []
                validate_schema_instance(value, branch, registry, where, trial)
                branch_errors.append(trial)
            if not any(not trial for trial in branch_errors):
                errors.append(f"schema: {where} must match at least one anyOf branch")

    one_of = schema.get("oneOf")
    if one_of is not None:
        if not isinstance(one_of, list) or not one_of:
            errors.append(f"schema: {where} has an invalid oneOf declaration")
        else:
            matches = 0
            for branch in one_of:
                trial: list[str] = []
                validate_schema_instance(value, branch, registry, where, trial)
                if not trial:
                    matches += 1
            if matches != 1:
                errors.append(f"schema: {where} must match exactly one oneOf branch; matched {matches}")

    prohibited = schema.get("not")
    if prohibited is not None:
        trial = []
        validate_schema_instance(value, prohibited, registry, where, trial)
        if not trial:
            errors.append(f"schema: {where} must not match the prohibited schema")

    condition = schema.get("if")
    if condition is not None:
        trial = []
        validate_schema_instance(value, condition, registry, where, trial)
        selected = schema.get("then") if not trial else schema.get("else")
        if selected is not None:
            validate_schema_instance(value, selected, registry, where, errors)

    expected = schema.get("type")
    if expected is not None:
        expected_types = [expected] if isinstance(expected, str) else expected
        if not isinstance(expected_types, list) or not all(isinstance(item, str) for item in expected_types):
            errors.append(f"schema: {where} has an invalid type declaration")
            return
        if not any(type_matches(value, item) for item in expected_types):
            label = " or ".join(expected_types)
            errors.append(f"schema: {where} must have type {label}")
            return

    if "const" in schema and not json_equal(value, schema["const"]):
        errors.append(f"schema: {where} must equal {schema['const']!r}")

    enum = schema.get("enum")
    if isinstance(enum, list) and not any(json_equal(value, candidate) for candidate in enum):
        errors.append(f"schema: {where} must be one of {enum!r}")

    if isinstance(value, str):
        minimum = schema.get("minLength")
        if isinstance(minimum, int) and len(value) < minimum:
            errors.append(f"schema: {where} must contain at least {minimum} character(s)")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, value) is None:
            if where.endswith((".raw_evidence_ref", ".raw_observation_ref", ".provenance_ref")):
                errors.append(f"schema: {where} must be bundle-relative")
            else:
                errors.append(f"schema: {where} does not match required pattern")
        if schema.get("format") == "date-time" and not is_date_time(value):
            errors.append(f"schema: {where} must use date-time format")

    if isinstance(value, list):
        minimum = schema.get("minItems")
        if isinstance(minimum, int) and len(value) < minimum:
            errors.append(f"schema: {where} must contain at least {minimum} item(s)")
        if schema.get("uniqueItems") is True:
            for index, item in enumerate(value):
                if any(json_equal(item, prior) for prior in value[:index]):
                    errors.append(f"schema: {where} must contain unique items")
                    break
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                validate_schema_instance(item, item_schema, registry, f"{where}[{index}]", errors)

    if isinstance(value, dict):
        required_names = schema.get("required", [])
        if isinstance(required_names, list):
            for name in required_names:
                if isinstance(name, str) and name not in value:
                    errors.append(f"schema: {where}.{name} is required")
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            errors.append(f"schema: {where} has invalid properties metadata")
            return
        if schema.get("additionalProperties") is False:
            for name in value.keys() - properties.keys():
                errors.append(f"schema: {where}.{name} is not allowed")
        for name, property_schema in properties.items():
            if name in value:
                validate_schema_instance(value[name], property_schema, registry, f"{where}.{name}", errors)


def load_schema_registry() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_name: dict[str, dict[str, Any]] = {}
    registry: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for name in SCHEMAS:
        path = CANON / name
        if not path.is_file():
            errors.append(f"missing canonical schema: {path}")
            continue
        schema = load(path)
        if not isinstance(schema, dict):
            errors.append(f"canonical schema must be an object: {path}")
            continue
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            errors.append(f"canonical schema has no usable $id: {path}")
            continue
        if schema_id in registry:
            errors.append(f"duplicate canonical schema $id: {schema_id}")
            continue
        by_name[name] = schema
        registry[schema_id] = schema
    if errors:
        die(errors)
    return by_name, registry


def validate_bundle_reference(value: object, field: str, bundle: Path, errors: list[str]) -> None:
    candidate = resolve_relative(bundle, value, field, errors)
    if candidate is None:
        return
    if not candidate.exists():
        errors.append(f"{field} does not resolve")
    elif not candidate.is_file():
        errors.append(f"{field} must resolve to a regular file")


def contract_payloads() -> dict[str, bytes]:
    schemas, _ = load_schema_registry()
    payloads: dict[str, bytes] = {}
    rows: list[dict[str, str]] = []
    for name in SCHEMAS:
        source = CANON / name
        content = source.read_bytes()
        payloads[name] = content
        schema_id = schemas[name]["$id"]
        rows.append(
            {
                "canonical_path": source.relative_to(ROOT).as_posix(),
                "generated_path": (Path("references") / "contracts" / name).as_posix(),
                "schema_id": schema_id,
                "schema_version": schema_id.rstrip("/").split("/")[-1],
                "canonical_sha256": digest_bytes(content),
                "generated_sha256": digest_bytes(content),
            }
        )
    lock = {
        "lock_version": LOCK_VERSION,
        "generation_tool_version": TOOL_VERSION,
        "contracts": rows,
    }
    payloads["contracts-lock.json"] = (json.dumps(lock, indent=2) + "\n").encode("utf-8")
    return payloads


def sync_contracts() -> None:
    payloads = contract_payloads()
    CONTRACTS.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="contracts-stage-", dir=CONTRACTS.parent))
    backup = CONTRACTS.with_name(f"{CONTRACTS.name}.backup-{uuid.uuid4().hex}")
    moved_existing = False
    try:
        for name, content in payloads.items():
            (staging / name).write_bytes(content)
        if CONTRACTS.exists():
            CONTRACTS.replace(backup)
            moved_existing = True
        try:
            staging.replace(CONTRACTS)
        except BaseException:
            if moved_existing and backup.exists():
                backup.replace(CONTRACTS)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        if backup.exists() and not CONTRACTS.exists():
            backup.replace(CONTRACTS)
    print(f"PASS: synchronized {len(SCHEMAS)} contracts")


def validate_contract_lock(lock: object, errors: list[str]) -> None:
    if not isinstance(lock, dict):
        errors.append("contracts-lock.json must contain an object")
        return
    if set(lock) != LOCK_KEYS:
        errors.append(
            "contracts-lock.json keys mismatch: "
            f"missing={sorted(LOCK_KEYS - set(lock))} extra={sorted(set(lock) - LOCK_KEYS)}"
        )
    if lock.get("lock_version") != LOCK_VERSION:
        errors.append(f"lock_version must equal {LOCK_VERSION}")
    if lock.get("generation_tool_version") != TOOL_VERSION:
        errors.append(f"generation_tool_version must equal {TOOL_VERSION}")

    rows = lock.get("contracts")
    if not isinstance(rows, list):
        errors.append("contracts must be an array")
        return
    if len(rows) != len(SCHEMAS):
        errors.append(f"lock must contain exactly {len(SCHEMAS)} contract rows")

    comparable_rows = [row for row in rows if isinstance(row, dict)]
    if len(comparable_rows) != len(rows):
        errors.append("every lock contract row must be an object")
    for key in ("canonical_path", "generated_path", "schema_id"):
        values = [row.get(key) for row in comparable_rows]
        if len(values) != len(set(values)):
            errors.append(f"lock contract rows must have unique {key} values")

    for index, name in enumerate(SCHEMAS):
        if index >= len(rows) or not isinstance(rows[index], dict):
            continue
        row = rows[index]
        if set(row) != LOCK_ROW_KEYS:
            errors.append(
                f"lock row {index} keys mismatch: "
                f"missing={sorted(LOCK_ROW_KEYS - set(row))} extra={sorted(set(row) - LOCK_ROW_KEYS)}"
            )
        canonical = CANON / name
        generated = CONTRACTS / name
        if not canonical.is_file():
            errors.append(f"missing canonical schema: {name}")
            continue
        schema = load(canonical)
        if not isinstance(schema, dict) or not isinstance(schema.get("$id"), str):
            errors.append(f"canonical schema metadata invalid: {name}")
            continue
        schema_id = schema["$id"]
        expected = {
            "canonical_path": canonical.relative_to(ROOT).as_posix(),
            "generated_path": (Path("references") / "contracts" / name).as_posix(),
            "schema_id": schema_id,
            "schema_version": schema_id.rstrip("/").split("/")[-1],
        }
        for key, expected_value in expected.items():
            if row.get(key) != expected_value:
                errors.append(f"{key} mismatch: {name}")
        canonical_hash = digest(canonical)
        if row.get("canonical_sha256") != canonical_hash:
            errors.append(f"canonical hash drift: {name}")
        if not generated.is_file():
            errors.append(f"missing generated schema: {name}")
            continue
        generated_hash = digest(generated)
        if row.get("generated_sha256") != generated_hash:
            errors.append(f"generated hash drift: {name}")
        if canonical_hash != generated_hash:
            errors.append(f"generated copy edited: {name}")


def parse_frontmatter_scalar(value: str, field: str, errors: list[str]) -> str | None:
    value = value.strip()
    if not value:
        return value
    if value[0] == '"' or value[-1] == '"':
        if value[0] != '"' or value[-1] != '"':
            errors.append(f"frontmatter scalar must be valid quoted syntax: {field}")
            return None
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            errors.append(f"frontmatter scalar must be valid quoted syntax: {field}")
            return None
        if not isinstance(decoded, str):
            errors.append(f"frontmatter scalar must be valid quoted syntax: {field}")
            return None
        return decoded
    if value[0] == "'" or value[-1] == "'":
        if value[0] != "'" or value[-1] != "'":
            errors.append(f"frontmatter scalar must be valid quoted syntax: {field}")
            return None
        inner = value[1:-1]
        decoded: list[str] = []
        index = 0
        while index < len(inner):
            if inner[index] != "'":
                decoded.append(inner[index])
                index += 1
            elif index + 1 < len(inner) and inner[index + 1] == "'":
                decoded.append("'")
                index += 2
            else:
                errors.append(f"frontmatter scalar must be valid quoted syntax: {field}")
                return None
        return "".join(decoded)
    return value


def validate_openai_interface(path: Path, errors: list[str]) -> None:
    top_level: list[str] = []
    interface: list[str] = []
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):\s*", line)
            top_level.append(match.group(1) if match else line)
            continue
        match = re.fullmatch(r"  ([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*", line)
        if match is None:
            errors.append("openai.yaml interface entries must use two-space indentation")
            continue
        key, raw_value = match.groups()
        interface.append(key)
        if len(raw_value) < 2 or raw_value[0] != '"' or raw_value[-1] != '"':
            errors.append(f"interface values must be quoted strings: {key}")
            continue
        try:
            decoded = json.loads(raw_value)
        except json.JSONDecodeError:
            errors.append(f"interface value must be a valid double-quoted string: {key}")
            continue
        if not isinstance(decoded, str):
            errors.append(f"interface value must be a valid double-quoted string: {key}")
            continue
        values[key] = decoded
    if top_level != ["interface"]:
        errors.append("openai.yaml may contain only the interface top-level key")
    if len(interface) != len(INTERFACE_KEYS) or set(interface) != set(INTERFACE_KEYS):
        errors.append("interface keys must be exactly display_name, short_description, default_prompt")
    for key in INTERFACE_KEYS:
        if key in values and not values[key].strip():
            errors.append(f"interface values must be nonempty strings: {key}")
    if values.get("display_name") != DISPLAY_NAME:
        errors.append(f"display_name must equal {DISPLAY_NAME}")
    short_description = values.get("short_description", "")
    if short_description and not 25 <= len(short_description) <= 64:
        errors.append("short_description must contain 25-64 characters")
    if short_description != SHORT_DESCRIPTION:
        errors.append(f"short_description must equal {SHORT_DESCRIPTION}")
    if "$ai-search-research" not in values.get("default_prompt", ""):
        errors.append("default_prompt must contain $ai-search-research")


def validate_skill() -> None:
    errors: list[str] = []
    allowed_roots = {"SKILL.md", "agents", "references"}
    extras = sorted(path.name for path in SKILL.iterdir() if path.name not in allowed_roots)
    if extras:
        errors.append(f"deployable allow-list violation: {extras}")
    allowed_files = {
        "SKILL.md",
        "agents/openai.yaml",
        "references/evidence-policy.md",
        "references/capture-protocol.md",
        "references/contracts/evidence-record.schema.json",
        "references/contracts/research-pack.schema.json",
        "references/contracts/contracts-lock.json",
    }
    actual = {path.relative_to(SKILL).as_posix() for path in SKILL.rglob("*") if path.is_file()}
    if actual != allowed_files:
        errors.append(
            "deployable file set mismatch: "
            f"missing={sorted(allowed_files - actual)} extra={sorted(actual - allowed_files)}"
        )
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    if len(text.splitlines()) >= 500:
        errors.append("SKILL.md must be fewer than 500 lines")
    lines = text.splitlines()
    body = text
    if not lines or lines[0] != "---":
        errors.append("SKILL.md line 1 must be exactly ---")
    else:
        try:
            closing = lines.index("---", 1)
        except ValueError:
            errors.append("SKILL.md frontmatter must end with a later line exactly ---")
        else:
            field_lines = lines[1:closing]
            body = "\n".join(lines[closing + 1 :])
            if len("\n".join(field_lines)) > 1024:
                errors.append("frontmatter must be at most 1024 characters")
            if len(field_lines) != 2:
                errors.append("frontmatter must contain exactly two single-line fields")
            if any("---" in line for line in field_lines):
                errors.append("frontmatter fields must not contain delimiter text")
            parsed: list[tuple[str, str]] = []
            for line in field_lines:
                match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)", line)
                if match is not None:
                    value = parse_frontmatter_scalar(match.group(2), match.group(1), errors)
                    if value is not None:
                        parsed.append((match.group(1), value))
            keys = [key for key, _ in parsed]
            if keys != ["name", "description"]:
                errors.append(f"frontmatter keys must be exactly name, description; got {keys}")
            metadata = dict(parsed)
            if metadata.get("name") != SKILL.name:
                errors.append(f"frontmatter name must match skill folder: {SKILL.name}")
            description = metadata.get("description", "")
            if not description.startswith("Use when"):
                errors.append("frontmatter description must start with 'Use when'")
            if len(description) > 500:
                errors.append("frontmatter description must be at most 500 characters")
    if re.search(r"^#{1,6}\s+When to use(?:\s|$)", body, re.I | re.M):
        errors.append("trigger section is forbidden in body")

    validate_openai_interface(SKILL / "agents" / "openai.yaml", errors)

    lock_path = CONTRACTS / "contracts-lock.json"
    if not lock_path.is_file():
        errors.append("contracts-lock.json missing")
    else:
        validate_contract_lock(load(lock_path), errors)
    if errors:
        die(errors)
    print("PASS: skill structure, allow-list, and contract lock")


def validate_pack(path: Path, bundle: Path, now: dt.datetime) -> None:
    errors: list[str] = []
    artifact = resolve_artifact_in_bundle(path, bundle, errors)
    if artifact is None or errors:
        die(errors)
    try:
        data = load(artifact)
    except (OSError, json.JSONDecodeError):
        die(["research-pack.json is not valid JSON"])
    schemas, registry = load_schema_registry()
    schema_errors: list[str] = []
    validate_schema_instance(data, schemas["research-pack.schema.json"], registry, "$", schema_errors)
    if schema_errors:
        die(schema_errors)

    utc(data["created_at"], "$.created_at", errors)
    locales = data["locales"]
    if any(not LOCALE_RE.fullmatch(locale) for locale in locales):
        errors.append("$.locales must contain explicit locale codes")
    declared_locales = set(locales)

    for engine_index, item in enumerate(data["engines"]):
        for locale_index, locale in enumerate(item["locales"]):
            if locale not in declared_locales:
                errors.append(
                    f"$.engines[{engine_index}].locales[{locale_index}] "
                    f"is not declared in $.locales: {locale}"
                )

    engine_cells = {
        (item["engine"], surface, locale)
        for item in data["engines"]
        for surface in item["surfaces"]
        for locale in item["locales"]
    }
    entity_ids = {item["entity_id"] for item in data["entities"]}
    query_locales: set[str] = set()
    for index, item in enumerate(data["queries"]):
        query_locales.add(item["locale"])
        if item["locale"] not in declared_locales:
            errors.append(f"$.queries[{index}].locale is not declared in $.locales: {item['locale']}")
        if any(entity not in entity_ids for entity in item["target_entities"]):
            errors.append(f"$.queries[{index}] has unknown target entity")
        for applicability_index, applicability in enumerate(item["applicability"]):
            cell = (applicability["engine"], applicability["surface"], item["locale"])
            if cell not in engine_cells:
                errors.append(
                    f"$.queries[{index}].applicability[{applicability_index}] "
                    f"is not declared for query locale {item['locale']}: "
                    f"{applicability['engine']}/{applicability['surface']}"
                )
    missing_query_locales = sorted(declared_locales - query_locales)
    if missing_query_locales:
        errors.append(f"queries must cover every declared locale; missing={missing_query_locales}")

    evidence_ids = {item["claim_id"] for item in data["evidence"]}
    observation_ids = {item["observation_id"] for item in data["competitor_observations"]}
    source_kind_thresholds = {
        "direct_observation": dt.timedelta(days=14),
        "vendor_documentation": dt.timedelta(days=30),
        "standard": dt.timedelta(days=90),
        "original_research": dt.timedelta(days=365),
        "secondary_context": dt.timedelta(days=30),
    }
    for index, item in enumerate(data["evidence"]):
        where = f"$.evidence[{index}]"
        validate_bundle_reference(item["raw_evidence_ref"], f"{where}.raw_evidence_ref", bundle, errors)
        accessed = utc(item["accessed_at"], f"{where}.accessed_at", errors)
        if item["source_published_or_updated_at"] is not None:
            utc(
                item["source_published_or_updated_at"],
                f"{where}.source_published_or_updated_at",
                errors,
            )
        if accessed is None:
            continue
        if accessed > now:
            errors.append(f"{where}.accessed_at must not be in the future")
            continue
        if now - accessed > source_kind_thresholds[item["source_kind"]]:
            claim_id = item["claim_id"]
            linked = any(
                gap["gap_type"] == "stale_input" and claim_id in gap["related_claim_ids"]
                for gap in data["gaps"]
            )
            if not linked:
                errors.append(f"{where} is stale and lacks a stale_input gap linked to {claim_id}")

    for index, item in enumerate(data["competitor_observations"]):
        where = f"$.competitor_observations[{index}]"
        validate_bundle_reference(item["raw_observation_ref"], f"{where}.raw_observation_ref", bundle, errors)
        observed = utc(item["observed_at"], f"{where}.observed_at", errors)
        if observed is None:
            continue
        if observed > now:
            errors.append(f"{where}.observed_at must not be in the future")
            continue
        if now - observed > dt.timedelta(days=14):
            observation_id = item["observation_id"]
            linked = any(
                gap["gap_type"] == "stale_input"
                and observation_id in gap.get("related_observation_ids", [])
                for gap in data["gaps"]
            )
            if not linked:
                errors.append(
                    f"{where} is stale and lacks a stale_input gap linked to observation {observation_id}"
                )

    for index, item in enumerate(data["ground_truth"]):
        where = f"$.ground_truth[{index}]"
        validate_bundle_reference(item["provenance_ref"], f"{where}.provenance_ref", bundle, errors)
        utc(item["valid_from"], f"{where}.valid_from", errors)
        if item["valid_until"] is not None:
            utc(item["valid_until"], f"{where}.valid_until", errors)

    for index, gap in enumerate(data["gaps"]):
        dimensions = (gap["engine"], gap["surface"], gap["locale"])
        if gap["locale"] != "not_applicable" and gap["locale"] not in declared_locales:
            errors.append(f"$.gaps[{index}].locale is not declared in $.locales: {gap['locale']}")
        explicit_dimensions = [
            (dimension_index, value)
            for dimension_index, value in enumerate(dimensions)
            if value != "not_applicable"
        ]
        matches_declared_cell = not explicit_dimensions or any(
            all(cell[dimension_index] == value for dimension_index, value in explicit_dimensions)
            for cell in engine_cells
        )
        if not matches_declared_cell:
            errors.append(
                f"$.gaps[{index}] explicit dimensions match no declared engine cell: "
                f"{gap['engine']}/{gap['surface']}/{gap['locale']}"
            )
        unknown = [claim_id for claim_id in gap["related_claim_ids"] if claim_id not in evidence_ids]
        if unknown:
            errors.append(f"$.gaps[{index}].related_claim_ids contains unknown claim ids: {unknown}")
        unknown_observations = [
            observation_id
            for observation_id in gap.get("related_observation_ids", [])
            if observation_id not in observation_ids
        ]
        if unknown_observations:
            errors.append(
                f"$.gaps[{index}].related_observation_ids contains unknown observation ids: "
                f"{unknown_observations}"
            )

    if errors:
        die(errors)
    print("PASS: research-pack contract, provenance, locale coverage, and freshness")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("sync-contracts")
    subparsers.add_parser("validate-skill")
    pack_parser = subparsers.add_parser("validate-pack")
    pack_parser.add_argument("artifact", type=Path)
    pack_parser.add_argument("--bundle", type=Path, required=True)
    pack_parser.add_argument("--now", required=True)
    args = parser.parse_args()

    try:
        if args.command == "sync-contracts":
            sync_contracts()
        elif args.command == "validate-skill":
            validate_skill()
        else:
            validate_pack(args.artifact, args.bundle, parse_now(args.now))
    except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
        die([str(exc)])


if __name__ == "__main__":
    main()
