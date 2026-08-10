#!/usr/bin/env python3
"""Create deterministic draft scaffolds for the suite's artifact contracts.

This tool intentionally creates ``*.draft.json`` files. A scaffold is a
schema-shaped editing aid, not a validated artifact. Rename it to the canonical
artifact filename only after replacing placeholders and running the owning
validator.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from bundle_safety import is_reparse


ROOT = Path(__file__).resolve().parents[1]
SUITE_MANIFEST = ROOT / "manifests" / "suite.json"
SCHEMA_ROOT = ROOT / "manifests" / "artifact-schemas"
SCAFFOLD_VERSION = "1.0.0"

BUNDLE_PROFILES: dict[str, tuple[str, ...]] = {
    "conventional": ("query-corpus", "seo-findings", "seo-performance-run", "action-plan"),
    "ai-search": ("research-pack", "query-corpus", "optimization-brief", "visibility-run", "action-plan"),
    "architecture": ("query-corpus", "site-graph", "seo-findings", "action-plan"),
    "technical": ("platform-controls", "seo-findings", "action-plan"),
}


class ScaffoldError(ValueError):
    """A user-facing scaffold error without a traceback."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScaffoldError(f"cannot read JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ScaffoldError(f"expected an object in {path}")
    return value


def contract_index() -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    suite = load_json(SUITE_MANIFEST)
    schemas = suite.get("schemas")
    if not isinstance(schemas, dict) or not schemas:
        raise ScaffoldError("suite manifest has no artifact schemas")
    paths: dict[str, str] = {}
    registry: dict[str, dict[str, Any]] = {}
    for artifact_type, filename in sorted(schemas.items()):
        if not isinstance(artifact_type, str) or not isinstance(filename, str):
            raise ScaffoldError("suite manifest schema entries must be strings")
        schema = load_json(SCHEMA_ROOT / filename)
        paths[artifact_type] = filename
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            registry[schema_id] = schema
    return paths, registry


def latest_version(schema: dict[str, Any]) -> str:
    version = schema.get("properties", {}).get("schema_version", {})
    if isinstance(version, dict):
        if isinstance(version.get("const"), str):
            return version["const"]
        enum = version.get("enum")
        if isinstance(enum, list) and enum and all(isinstance(item, str) for item in enum):
            return enum[-1]
    schema_id = schema.get("$id")
    if isinstance(schema_id, str) and re.search(r"/\d+\.\d+\.\d+$", schema_id):
        return schema_id.rsplit("/", 1)[-1]
    return "not-versioned"


def resolve_pointer(schema: dict[str, Any], pointer: str) -> dict[str, Any]:
    current: Any = schema
    for part in pointer.removeprefix("#/").split("/"):
        if not isinstance(current, dict) or part not in current:
            raise ScaffoldError(f"unresolved schema pointer: {pointer}")
        current = current[part.replace("~1", "/").replace("~0", "~")]
    if not isinstance(current, dict):
        raise ScaffoldError(f"schema pointer does not resolve to an object: {pointer}")
    return current


def safe_id(seed: str, field: str) -> str:
    suffix = field.removesuffix("_id").replace("_", "-")
    value = re.sub(r"[^a-z0-9-]+", "-", f"{seed}-{suffix}".lower()).strip("-")
    value = re.sub(r"-+", "-", value)
    if len(value) < 3:
        value = f"{value}-draft"
    return value[:64].rstrip("-")


def permits_null(node: dict[str, Any]) -> bool:
    declared = node.get("type")
    return isinstance(declared, list) and "null" in declared


def placeholder(
    node: dict[str, Any],
    *,
    root_schema: dict[str, Any],
    registry: dict[str, dict[str, Any]],
    field: str,
    seed: str,
    created_at: str,
) -> Any:
    reference = node.get("$ref")
    if isinstance(reference, str):
        if reference.startswith("#/"):
            return placeholder(
                resolve_pointer(root_schema, reference),
                root_schema=root_schema,
                registry=registry,
                field=field,
                seed=seed,
                created_at=created_at,
            )
        target = registry.get(reference)
        if target is None:
            raise ScaffoldError(f"unresolved external schema reference: {reference}")
        return placeholder(
            target,
            root_schema=target,
            registry=registry,
            field=field,
            seed=seed,
            created_at=created_at,
        )

    if "const" in node:
        return node["const"]
    enum = node.get("enum")
    if isinstance(enum, list) and enum:
        return enum[-1] if field == "schema_version" else enum[0]

    if field == "schema_version":
        return latest_version(root_schema)
    if field.endswith("_sha256"):
        return "0" * 64
    if field.endswith("_id") or field in {"record_id", "artifact_id"}:
        return safe_id(seed, field)
    if field in {"created_at", "captured_at", "accessed_at", "observed_at", "frozen_at", "valid_from", "reviewed_at"}:
        return created_at
    if field in {"valid_until", "source_published_or_updated_at", "prior_run_ref", "prior_run_sha256", "prior_run_id"} and permits_null(node):
        return None
    if field in {"source_url", "citation_url", "url"}:
        return f"https://example.test/{seed}/{field.replace('_', '-')}"
    if field == "locale":
        return "en-US"
    if field == "locales":
        return ["en-US"]
    if field.endswith("_ref"):
        return f"raw/{field.removesuffix('_ref').replace('_', '-')}.json"

    declared = node.get("type")
    if isinstance(declared, list):
        non_null = [item for item in declared if item != "null"]
        declared = non_null[0] if non_null else "null"
    if declared is None and isinstance(node.get("properties"), dict):
        declared = "object"

    if declared == "object":
        properties = node.get("properties", {})
        required = node.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list):
            return {}
        return {
            name: placeholder(
                properties[name],
                root_schema=root_schema,
                registry=registry,
                field=name,
                seed=seed,
                created_at=created_at,
            )
            for name in required
            if name in properties and isinstance(properties[name], dict)
        }
    if declared == "array":
        if field == "limitations":
            return ["TODO: replace this draft limitation with a bounded, evidence-based limitation."]
        count = max(0, int(node.get("minItems", 0)))
        item = node.get("items")
        if count and isinstance(item, dict):
            return [
                placeholder(
                    item,
                    root_schema=root_schema,
                    registry=registry,
                    field=field.removesuffix("s") or "item",
                    seed=seed,
                    created_at=created_at,
                )
                for _ in range(count)
            ]
        return []
    if declared == "boolean":
        return False
    if declared in {"integer", "number"}:
        return 0
    if declared == "null":
        return None
    if field in {"scope", "objective", "claim", "title", "description"}:
        return f"TODO: define {field.replace('_', ' ')} for {seed}."
    return f"TODO: {field.replace('_', ' ')}"


def build_draft(artifact_type: str, seed: str, created_at: str) -> tuple[dict[str, Any], str]:
    paths, registry = contract_index()
    filename = paths.get(artifact_type)
    if filename is None:
        raise ScaffoldError(f"unknown artifact type: {artifact_type}")
    schema = load_json(SCHEMA_ROOT / filename)
    draft = placeholder(
        schema,
        root_schema=schema,
        registry=registry,
        field=artifact_type,
        seed=seed,
        created_at=created_at,
    )
    if not isinstance(draft, dict):
        raise ScaffoldError(f"{artifact_type} schema did not produce an object scaffold")
    return draft, latest_version(schema)


def encoded_json(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def preflight(paths: list[Path], overwrite: bool) -> None:
    for path in paths:
        if is_reparse(path):
            raise ScaffoldError(f"refusing symlink or reparse-point output: {path}")
        current = path.parent
        while current != current.parent:
            if current.exists() and is_reparse(current):
                raise ScaffoldError(f"output must not traverse a symlink or reparse point: {current}")
            current = current.parent
    existing = [path for path in paths if path.exists()]
    if existing and not overwrite:
        rendered = ", ".join(str(path) for path in existing)
        raise ScaffoldError(f"refusing to overwrite existing path(s): {rendered}")
    for path in paths:
        if path.exists() and path.is_dir():
            raise ScaffoldError(f"output path is a directory: {path}")


def write_files(files: dict[Path, str], overwrite: bool) -> None:
    preflight(list(files), overwrite)
    staged: list[tuple[Path, Path]] = []
    backups: dict[Path, Path | None] = {}
    promoted: set[Path] = set()
    try:
        for path, content in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            if is_reparse(path.parent) or (path.exists() and (is_reparse(path) or not path.is_file())):
                raise ScaffoldError(f"output must be a regular non-reparse file: {path}")
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
            )
            temporary = Path(temporary_name)
            staged.append((temporary, path))
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        for temporary, path in staged:
            if path.exists() and not overwrite:
                raise ScaffoldError(f"refusing to overwrite existing path: {path}")
            backup: Path | None = None
            if path.exists():
                descriptor, backup_name = tempfile.mkstemp(
                    prefix=f".{path.name}.", suffix=".backup", dir=path.parent
                )
                os.close(descriptor)
                backup = Path(backup_name)
                backup.unlink()
                os.replace(path, backup)
            backups[path] = backup
            os.replace(temporary, path)
            promoted.add(path)
    except OSError as exc:
        rollback_errors: list[str] = []
        for _temporary, path in reversed(staged):
            if path not in backups:
                continue
            backup = backups[path]
            try:
                if backup is None:
                    if path in promoted:
                        path.unlink(missing_ok=True)
                elif backup.exists():
                    os.replace(backup, path)
            except OSError as rollback_exc:
                rollback_errors.append(f"{path}: {rollback_exc}")
        detail = f"cannot stage or atomically replace scaffold output: {exc}"
        if rollback_errors:
            detail += "; rollback incomplete; retained backup files: " + "; ".join(rollback_errors)
        raise ScaffoldError(detail) from exc
    else:
        for backup in backups.values():
            if backup is not None:
                backup.unlink(missing_ok=True)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def draft_readme(profile: str, artifact_types: tuple[str, ...]) -> str:
    listed = "\n".join(f"- `{name}.draft.json`" for name in artifact_types)
    return f"""# DRAFT artifact bundle

Status: **draft / not validated**

Profile: `{profile}`

{listed}

These files are deterministic schema-shaped scaffolds. Placeholder values,
zero hashes, empty collections, and TODO text are expected. Add immutable raw
evidence below `raw/`, replace every placeholder, rename each completed file to
its canonical `*.json` filename, and run its owning validator. Do not hand this
bundle to another skill or describe it as validated until those commands pass.
"""


def emit(payload: dict[str, Any], json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"DRAFT: {payload['message']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create deterministic draft artifacts and workflow bundles.")
    parser.add_argument("--json", action="store_true", help="Emit one stable JSON result object.")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="List artifact types and bundle profiles.")

    artifact = commands.add_parser("artifact", help="Create one explicitly named *.draft.json file.")
    artifact.add_argument("artifact_type")
    artifact.add_argument("--out", type=Path, required=True)
    artifact.add_argument("--seed", required=True, help="Stable lowercase seed used for placeholder IDs.")
    artifact.add_argument("--created-at", required=True, help="Pinned ISO 8601 timestamp used in the scaffold.")
    artifact.add_argument("--overwrite", action="store_true", help="Explicitly replace the exact output file.")

    bundle = commands.add_parser("bundle", help="Create a multi-artifact draft workflow bundle.")
    bundle.add_argument("profile", choices=sorted((*BUNDLE_PROFILES, "all")))
    bundle.add_argument("--out", type=Path, required=True)
    bundle.add_argument("--seed", required=True, help="Stable lowercase seed used for placeholder IDs.")
    bundle.add_argument("--created-at", required=True, help="Pinned ISO 8601 timestamp used in the scaffold.")
    bundle.add_argument("--overwrite", action="store_true", help="Explicitly replace generated scaffold files.")

    args = parser.parse_args()
    try:
        paths, _ = contract_index()
        if args.command == "list":
            payload = {
                "status": "ok",
                "artifact_types": sorted(paths),
                "bundle_profiles": {**{key: list(value) for key, value in BUNDLE_PROFILES.items()}, "all": sorted(paths)},
            }
            if args.json:
                print(json.dumps(payload, sort_keys=True))
            else:
                print("Artifact types: " + ", ".join(payload["artifact_types"]))
                for profile, members in payload["bundle_profiles"].items():
                    print(f"{profile}: {', '.join(members)}")
            return 0

        seed = re.sub(r"[^a-z0-9-]+", "-", args.seed.lower()).strip("-")
        if len(seed) < 3:
            raise ScaffoldError("--seed must contain at least three lowercase letters, digits, or hyphens")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", args.created_at):
            raise ScaffoldError("--created-at must use the deterministic YYYY-MM-DDTHH:MM:SSZ form")
        try:
            dt.datetime.fromisoformat(args.created_at.removesuffix("Z") + "+00:00")
        except ValueError as exc:
            raise ScaffoldError("--created-at must be a real UTC calendar timestamp") from exc

        if args.command == "artifact":
            if not args.out.name.endswith(".draft.json"):
                raise ScaffoldError("artifact output must end with .draft.json so draft status stays explicit")
            draft, version = build_draft(args.artifact_type, seed, args.created_at)
            write_files({args.out: encoded_json(draft)}, args.overwrite)
            emit(
                {
                    "status": "draft",
                    "artifact_type": args.artifact_type,
                    "schema_version": version,
                    "path": str(args.out),
                    "message": f"created unvalidated {args.artifact_type} scaffold at {args.out}",
                },
                args.json,
            )
            return 0

        artifact_types = tuple(sorted(paths)) if args.profile == "all" else BUNDLE_PROFILES[args.profile]
        versions: dict[str, str] = {}
        files: dict[Path, str] = {}
        for artifact_type in artifact_types:
            draft, version = build_draft(artifact_type, seed, args.created_at)
            versions[artifact_type] = version
            files[args.out / f"{artifact_type}.draft.json"] = encoded_json(draft)
        manifest = {
            "scaffold_version": SCAFFOLD_VERSION,
            "suite_version": load_json(SUITE_MANIFEST).get("suite_version"),
            "status": "draft",
            "validation_status": "not_run",
            "profile": args.profile,
            "seed": seed,
            "created_at": args.created_at,
            "artifacts": [
                {"artifact_type": name, "schema_version": versions[name], "path": f"{name}.draft.json"}
                for name in artifact_types
            ],
        }
        files[args.out / "draft-manifest.json"] = encoded_json(manifest)
        files[args.out / "DRAFT.md"] = draft_readme(args.profile, artifact_types)
        files[args.out / "raw" / ".gitkeep"] = ""
        write_files(files, args.overwrite)
        emit(
            {
                "status": "draft",
                "profile": args.profile,
                "path": str(args.out),
                "artifact_count": len(artifact_types),
                "message": f"created unvalidated {args.profile} draft bundle at {args.out}",
            },
            args.json,
        )
        return 0
    except ScaffoldError as exc:
        if args.json:
            print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
