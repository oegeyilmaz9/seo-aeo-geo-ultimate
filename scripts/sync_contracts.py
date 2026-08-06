#!/usr/bin/env python3
"""Synchronize every checked-in skill contract from canonical schemas.

The canonical schemas under ``manifests/artifact-schemas`` are authoritative.
Generated skill copies and their hash locks are a release artifact: this tool
either proves they are byte-identical (``--check``) or replaces only those
generated contract directories atomically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "suite.json"
SCHEMA_ROOT = ROOT / "manifests" / "artifact-schemas"


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain an object")
    return value


def relative_to_root(path: Path, label: str) -> Path:
    try:
        relative = path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must remain inside the suite root") from exc
    if ".." in relative.parts:
        raise ValueError(f"{label} must remain inside the suite root")
    return relative


def expected_payloads(skill_name: str, entry: dict[str, Any], manifest: dict[str, Any]) -> tuple[Path, dict[str, bytes]]:
    generated_root = entry.get("generated_contract_root")
    if not isinstance(generated_root, str) or not generated_root:
        raise ValueError(f"{skill_name} has no generated_contract_root")
    skill_root = ROOT / "skills" / skill_name
    target = ROOT / generated_root
    expected_target = skill_root / "references" / "contracts"
    if target.resolve() != expected_target.resolve():
        raise ValueError(f"{skill_name} generated_contract_root must be its references/contracts directory")
    relative_to_root(target, f"{skill_name} generated contract root")

    schema_map = manifest.get("schemas")
    if not isinstance(schema_map, dict):
        raise ValueError("manifests/suite.json has invalid schemas")
    ordered_names = list(schema_map)
    consumes = entry.get("consumes")
    produces = entry.get("produces")
    if not isinstance(consumes, list) or not isinstance(produces, list) or not all(
        isinstance(name, str) for name in [*consumes, *produces]
    ):
        raise ValueError(f"{skill_name} has invalid produces or consumes metadata")
    requested = set(consumes) | set(produces)
    if not requested or any(name not in schema_map for name in requested):
        raise ValueError(f"{skill_name} has invalid produced or consumed contract names")

    payloads: dict[str, bytes] = {}
    rows: list[dict[str, str]] = []
    for schema_name in ordered_names:
        if schema_name not in requested:
            continue
        filename = schema_map[schema_name]
        if not isinstance(filename, str) or not filename.endswith(".json"):
            raise ValueError(f"{schema_name} has invalid canonical schema filename")
        source = SCHEMA_ROOT / filename
        relative_to_root(source, f"{schema_name} canonical schema")
        schema = load_json(source)
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            raise ValueError(f"{filename} has no usable $id")
        content = source.read_bytes()
        payloads[filename] = content
        rows.append(
            {
                "canonical_path": source.relative_to(ROOT).as_posix(),
                "generated_path": (Path("references") / "contracts" / filename).as_posix(),
                "schema_id": schema_id,
                "schema_version": schema_id.rstrip("/").split("/")[-1],
                "canonical_sha256": digest(content),
                "generated_sha256": digest(content),
            }
        )
    version = manifest.get("contract_generation_tool_version")
    if not isinstance(version, str) or not version:
        raise ValueError("manifests/suite.json has no contract_generation_tool_version")
    payloads["contracts-lock.json"] = (
        json.dumps(
            {"lock_version": "1.0.0", "generation_tool_version": version, "contracts": rows},
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    return target, payloads


def is_safe_contract_root(target: Path) -> bool:
    return target.is_dir() and not target.is_symlink() and all(
        child.is_file() and not child.is_symlink() for child in target.iterdir()
    )


def actual_matches(target: Path, payloads: dict[str, bytes]) -> bool:
    return is_safe_contract_root(target) and all(
        (target / name).is_file() and (target / name).read_bytes() == content for name, content in payloads.items()
    ) and {path.name for path in target.iterdir()} == set(payloads)


def replace_atomically(target: Path, payloads: dict[str, bytes]) -> None:
    if target.exists() and not is_safe_contract_root(target):
        raise ValueError(f"refusing to replace non-regular generated contract tree: {target.relative_to(ROOT)}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="contracts-stage-", dir=target.parent))
    backup = target.with_name(f"{target.name}.backup-{uuid.uuid4().hex}")
    moved_existing = False
    try:
        for name, content in payloads.items():
            (staging / name).write_bytes(content)
        if target.exists():
            target.replace(backup)
            moved_existing = True
        try:
            staging.replace(target)
        except BaseException:
            if moved_existing and backup.exists():
                backup.replace(target)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        if backup.exists() and not target.exists():
            backup.replace(target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize generated Codex skill contracts from canonical schemas.")
    parser.add_argument("--check", action="store_true", help="fail on generated-contract drift without writing")
    parser.add_argument("--skills", nargs="+", metavar="SKILL", help="contract-owning skills to check or synchronize")
    args = parser.parse_args()
    try:
        manifest = load_json(MANIFEST)
        skills = manifest.get("skills")
        if not isinstance(skills, dict):
            raise ValueError("manifests/suite.json has invalid skills")
        available = [name for name, entry in skills.items() if isinstance(entry, dict) and "generated_contract_root" in entry]
        selected = args.skills or available
        unknown = sorted(set(selected) - set(available))
        if unknown:
            raise ValueError(f"unknown contract-owning skills: {unknown}")
        drifted: list[str] = []
        for name in selected:
            entry = skills[name]
            target, payloads = expected_payloads(name, entry, manifest)
            if actual_matches(target, payloads):
                continue
            if args.check:
                drifted.append(name)
            else:
                replace_atomically(target, payloads)
        if drifted:
            raise ValueError("generated contract drift: " + ", ".join(drifted))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {'verified' if args.check else 'synchronized'} {len(selected)} generated contract tree(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
