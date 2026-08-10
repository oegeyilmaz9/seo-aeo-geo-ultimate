#!/usr/bin/env python3
"""Safely migrate legacy SEO-suite artifacts to current schema versions.

Migrations never modify the source file, never overwrite the destination by
default, and only write an artifact after the owning semantic validator passes.
Where a newer contract requires evidence that cannot be inferred, this tool
refuses automatic migration instead of fabricating it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

from bundle_safety import is_reparse, resolve_artifact_in_bundle, resolve_relative


ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSIONS = {
    "research-pack": "1.1.0",
    "seo-findings": "1.1.0",
    "optimization-brief": "1.1.0",
    "action-plan": "1.2.0",
    "visibility-run": "2.0.0",
}
AUTOMATIC_PATHS = {
    "research-pack": {"1.0.0": "1.1.0"},
    "seo-findings": {"1.0.0": "1.1.0"},
    "optimization-brief": {"1.0.0": "1.1.0"},
}


class MigrationError(ValueError):
    """A user-facing migration error without a traceback."""


def load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationError(f"cannot read JSON from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise MigrationError("artifact must contain a JSON object")
    return payload


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_reference(bundle: Path, value: object, field: str) -> str:
    errors: list[str] = []
    path = resolve_relative(bundle, value, field, errors)
    if errors or path is None:
        raise MigrationError("; ".join(errors) or f"cannot resolve {field}")
    if not path.is_file():
        raise MigrationError(f"{field} does not resolve to a regular file")
    return digest(path)


def object_list(payload: dict[str, Any], field: str) -> list[dict[str, Any]]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise MigrationError(f"{field} must be an array")
    objects: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise MigrationError(f"{field}[{index}] must be an object")
        objects.append(item)
    return objects


def infer_type(payload: dict[str, Any]) -> str:
    if "research_id" in payload and "entities" in payload and "ground_truth" in payload:
        return "research-pack"
    if "finding_set_id" in payload and "findings" in payload:
        return "seo-findings"
    if "brief_id" in payload and "optimization_domain" in payload:
        return "optimization-brief"
    if "plan_id" in payload and "actions" in payload:
        return "action-plan"
    if "run_id" in payload and "research_ref" in payload and "observations" in payload:
        return "visibility-run"
    raise MigrationError("cannot infer artifact type; pass --type explicitly")


def migrate_research_pack(payload: dict[str, Any], bundle: Path) -> dict[str, Any]:
    migrated = deepcopy(payload)
    migrated["schema_version"] = "1.1.0"
    for index, record in enumerate(object_list(migrated, "evidence")):
        record["raw_evidence_sha256"] = hash_reference(
            bundle, record.get("raw_evidence_ref"), f"evidence[{index}].raw_evidence_ref"
        )
    for index, record in enumerate(object_list(migrated, "competitor_observations")):
        record["raw_observation_sha256"] = hash_reference(
            bundle, record.get("raw_observation_ref"), f"competitor_observations[{index}].raw_observation_ref"
        )
    for index, record in enumerate(object_list(migrated, "ground_truth")):
        record["provenance_sha256"] = hash_reference(
            bundle, record.get("provenance_ref"), f"ground_truth[{index}].provenance_ref"
        )
    return migrated


def migrate_findings(payload: dict[str, Any], bundle: Path) -> dict[str, Any]:
    migrated = deepcopy(payload)
    migrated["schema_version"] = "1.1.0"
    findings = object_list(migrated, "findings")
    for index, record in enumerate(object_list(migrated, "evidence")):
        record["raw_evidence_sha256"] = hash_reference(
            bundle, record.get("raw_evidence_ref"), f"evidence[{index}].raw_evidence_ref"
        )
        if not record.get("target_id"):
            claim_id = record.get("claim_id")
            target_ids = {
                finding.get("target_id")
                for finding in findings
                if claim_id in finding.get("evidence_ids", []) and isinstance(finding.get("target_id"), str)
            }
            if len(target_ids) != 1:
                raise MigrationError(
                    f"evidence[{index}].target_id cannot be inferred unambiguously from linked findings"
                )
            record["target_id"] = next(iter(target_ids))
    return migrated


def migrate_brief(payload: dict[str, Any], _bundle: Path) -> dict[str, Any]:
    migrated = deepcopy(payload)
    migrated["schema_version"] = "1.1.0"
    brief_id = migrated.get("brief_id")
    for collection in ("findings", "recommendations"):
        for item in object_list(migrated, collection):
            references = item.get("evidence_refs")
            if not isinstance(references, list):
                raise MigrationError(f"{collection} evidence_refs must be an array")
            for reference in references:
                if (
                    isinstance(reference, dict)
                    and reference.get("artifact_type") == "optimization-brief"
                    and reference.get("artifact_id") == brief_id
                ):
                    reference["schema_version"] = "1.1.0"
    return migrated


MIGRATORS: dict[str, Callable[[dict[str, Any], Path], dict[str, Any]]] = {
    "research-pack": migrate_research_pack,
    "seo-findings": migrate_findings,
    "optimization-brief": migrate_brief,
}


def output_path(source: Path, target_version: str) -> Path:
    suffix = source.suffix if source.suffix else ".json"
    return source.with_name(f"{source.stem}.v{target_version}{suffix}")


def ensure_output_in_bundle(path: Path, bundle: Path) -> None:
    try:
        relative = path.absolute().relative_to(bundle.absolute())
    except ValueError as exc:
        raise MigrationError("output must remain inside --bundle") from exc
    errors: list[str] = []
    resolved = resolve_relative(bundle, relative.as_posix(), "output", errors)
    if resolved is None or errors:
        raise MigrationError("; ".join(errors))


def atomic_write(path: Path, content: str) -> None:
    temporary: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if is_reparse(path) or (path.exists() and not path.is_file()):
            raise MigrationError(f"destination must be a regular non-reparse file: {path}")
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise MigrationError(f"cannot atomically write migration output: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def validator_command(artifact_type: str, artifact: Path, bundle: Path, as_of: str | None, payload: dict[str, Any]) -> list[str]:
    common = [sys.executable]
    if artifact_type == "research-pack":
        if not as_of:
            raise MigrationError("research-pack migration requires --as-of for freshness validation")
        return common + [
            str(ROOT / "scripts" / "validate_ai_search_research.py"),
            "validate-pack",
            str(artifact),
            "--bundle",
            str(bundle),
            "--now",
            as_of,
        ]
    if artifact_type == "seo-findings":
        script, command = "validate_seo_findings.py", "validate-findings"
    elif artifact_type == "optimization-brief":
        producer = payload.get("producer_skill")
        if producer == "seo-aeo":
            script = "validate_seo_aeo.py"
        elif producer == "seo-geo":
            script = "validate_seo_geo.py"
        else:
            raise MigrationError("optimization brief producer_skill must be seo-aeo or seo-geo")
        command = "validate-brief"
    elif artifact_type == "action-plan":
        script, command = "validate_seo_action_plan.py", "validate-plan"
    else:
        raise MigrationError(f"no semantic validator registered for {artifact_type}")
    return common + [str(ROOT / "scripts" / script), command, str(artifact), "--bundle", str(bundle)]


def validate_before_write(
    artifact_type: str,
    payload: dict[str, Any],
    bundle: Path,
    as_of: str | None,
) -> str:
    handle, temporary_name = tempfile.mkstemp(prefix="migration-candidate-", suffix=".json", dir=bundle)
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        completed = subprocess.run(
            validator_command(artifact_type, temporary, bundle, as_of, payload),
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
            raise MigrationError(f"migrated candidate failed semantic validation: {detail}")
        return completed.stdout.strip()
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate validated legacy artifacts without modifying their sources.")
    parser.add_argument("--json", action="store_true", help="Emit one stable JSON result object.")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("paths", help="List automatic migrations and manual-only boundaries.")

    migrate = commands.add_parser("migrate", help="Create a validated current-version copy of a legacy artifact.")
    migrate.add_argument("artifact", type=Path)
    migrate.add_argument("--bundle", type=Path, required=True)
    migrate.add_argument("--type", choices=sorted(CURRENT_VERSIONS), dest="artifact_type")
    migrate.add_argument("--out", type=Path)
    migrate.add_argument("--as-of", help="Pinned UTC time required for Research Pack freshness validation.")
    migrate.add_argument("--overwrite", action="store_true", help="Explicitly replace the exact destination file.")

    args = parser.parse_args()
    try:
        if args.command == "paths":
            payload = {
                "status": "ok",
                "automatic": {
                    artifact_type: [f"{source}->{target}" for source, target in sorted(paths.items())]
                    for artifact_type, paths in sorted(AUTOMATIC_PATHS.items())
                },
                "manual_only": {
                    "action-plan": {
                        "path": "1.0.0/1.1.0->1.2.0",
                        "reason": "current risk_flags and approval semantics cannot be inferred safely from a legacy plan",
                    },
                    "visibility-run": {
                        "path": "1.0.0->2.0.0",
                        "reason": "retrieval traces, repeat context, consulted sources, and citation reviews cannot be inferred safely",
                    }
                },
            }
            if args.json:
                print(json.dumps(payload, sort_keys=True))
            else:
                for name, paths in payload["automatic"].items():
                    print(f"{name}: {', '.join(paths)}")
                print("action-plan: 1.0.0/1.1.0->1.2.0 (manual only; current risk review is required)")
                print("visibility-run: 1.0.0->2.0.0 (manual only; new observation evidence is required)")
            return 0

        bundle = args.bundle.absolute()
        source = args.artifact.absolute()
        errors: list[str] = []
        safe_source = resolve_artifact_in_bundle(source, bundle, errors)
        if safe_source is None or errors:
            raise MigrationError("; ".join(errors))
        payload = load_object(safe_source)
        artifact_type = args.artifact_type or infer_type(payload)
        source_version = payload.get("schema_version")
        if not isinstance(source_version, str):
            raise MigrationError("artifact has no string schema_version")
        target_version = CURRENT_VERSIONS[artifact_type]
        if source_version == target_version:
            raise MigrationError(f"{artifact_type} is already current at {target_version}")
        expected_target = AUTOMATIC_PATHS.get(artifact_type, {}).get(source_version)
        if expected_target is None:
            if artifact_type == "action-plan" and source_version in {"1.0.0", "1.1.0"}:
                raise MigrationError(
                    f"action-plan {source_version}->1.2.0 is manual-only because current risk_flags and approval semantics cannot be inferred"
                )
            if artifact_type == "visibility-run" and source_version == "1.0.0":
                raise MigrationError(
                    "visibility-run 1.0.0->2.0.0 is manual-only because the required retrieval and repeat evidence cannot be inferred"
                )
            raise MigrationError(f"unsupported migration path: {artifact_type} {source_version}->{target_version}")

        destination = (args.out or output_path(safe_source, expected_target)).absolute()
        ensure_output_in_bundle(destination, bundle)
        if destination == safe_source.absolute():
            raise MigrationError("destination must differ from the immutable source artifact")
        if is_reparse(destination):
            raise MigrationError(f"destination must not be a symlink or reparse point: {destination}")
        if destination.exists() and not args.overwrite:
            raise MigrationError(f"refusing to overwrite existing destination: {destination}")
        if destination.exists() and destination.is_dir():
            raise MigrationError(f"destination is a directory: {destination}")

        migrated = MIGRATORS[artifact_type](payload, bundle)
        validation = validate_before_write(artifact_type, migrated, bundle, args.as_of)
        atomic_write(destination, json.dumps(migrated, indent=2, ensure_ascii=False) + "\n")
        result = {
            "status": "validated",
            "artifact_type": artifact_type,
            "source_version": source_version,
            "target_version": expected_target,
            "source": str(safe_source),
            "output": str(destination),
            "source_modified": False,
            "validation": validation,
        }
        if args.json:
            print(json.dumps(result, sort_keys=True))
        else:
            print(
                f"PASS: migrated {artifact_type} {source_version}->{expected_target} to {destination}; "
                "source unchanged; semantic validation passed"
            )
        return 0
    except MigrationError as exc:
        if args.json:
            print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
