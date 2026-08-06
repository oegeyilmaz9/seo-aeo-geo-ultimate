from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from validate_source_registry import parse_day, validate_registry


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
MANIFEST = ROOT / "manifests" / "suite.json"
SOURCE_REGISTRY = ROOT / "docs" / "research" / "2026-08-06-source-registry.json"
LOCAL_LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|#|mailto:)([^)]+)\)")


def load_json(path: Path, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        errors.append(f"missing JSON file: {path.relative_to(ROOT).as_posix()}")
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON: {path.relative_to(ROOT).as_posix()}:{exc.lineno}:{exc.colno}")
    return None


def parse_frontmatter(text: str, skill: str, errors: list[str]) -> None:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if match is None:
        errors.append(f"{skill}: SKILL.md must start with frontmatter")
        return
    frontmatter = match.group(1)
    name = re.search(r"^name:\s*(.+?)\s*$", frontmatter, re.M)
    description = re.search(r"^description:\s*(.+?)\s*$", frontmatter, re.M)
    if name is None or name.group(1).strip(" '\"") != skill:
        errors.append(f"{skill}: frontmatter name must match directory")
    if description is None:
        # A YAML folded description is valid as long as it has content below it.
        folded = re.search(r"^description:\s*>\s*$\r?\n((?:^[ \t].*\r?\n?)+)", frontmatter, re.M)
        if folded is None or not folded.group(1).strip():
            errors.append(f"{skill}: frontmatter description is required")


def validate_interface(path: Path, skill: str, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"{skill}: agents/openai.yaml is missing")
        return
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r'  ([A-Za-z_][A-Za-z0-9_-]*): "(.*)"', line)
        if match is not None:
            values[match.group(1)] = match.group(2)
    required = {"display_name", "short_description", "default_prompt"}
    if set(values) != required:
        errors.append(f"{skill}: openai.yaml must contain exactly {sorted(required)}")
    elif f"${skill}" not in values["default_prompt"]:
        errors.append(f"{skill}: default_prompt must invoke ${skill}")


def validate_skill(path: Path, errors: list[str]) -> None:
    skill = path.name
    skill_md = path / "SKILL.md"
    if not skill_md.is_file():
        errors.append(f"{skill}: SKILL.md is missing")
        return
    text = skill_md.read_text(encoding="utf-8")
    if len(text.splitlines()) >= 500:
        errors.append(f"{skill}: SKILL.md must contain fewer than 500 lines")
    if "TODO" in text or "[TODO" in text:
        errors.append(f"{skill}: scaffold TODO text remains")
    parse_frontmatter(text, skill, errors)
    validate_interface(path / "agents" / "openai.yaml", skill, errors)
    for raw_target in LOCAL_LINK_RE.findall(text):
        target = raw_target.split("#", 1)[0].strip()
        if not target:
            continue
        candidate = (path / target).resolve()
        try:
            candidate.relative_to(path.resolve())
        except ValueError:
            errors.append(f"{skill}: local link escapes skill directory: {raw_target}")
            continue
        if not candidate.exists():
            errors.append(f"{skill}: local link is missing: {raw_target}")


def validate_manifest(skill_names: set[str], errors: list[str]) -> None:
    manifest = load_json(MANIFEST, errors)
    if not isinstance(manifest, dict):
        return
    entries = manifest.get("skills")
    if not isinstance(entries, dict):
        errors.append("suite manifest skills must be an object")
        return
    declared = set(entries)
    if declared != skill_names:
        errors.append(f"suite manifest skill set mismatch: missing={sorted(skill_names - declared)} extra={sorted(declared - skill_names)}")
    schemas = manifest.get("schemas")
    if not isinstance(schemas, dict):
        errors.append("suite manifest schemas must be an object")
        return
    for label, filename in schemas.items():
        if not isinstance(label, str) or not isinstance(filename, str):
            errors.append("suite manifest schema entries must be strings")
            continue
        if not (ROOT / "manifests" / "artifact-schemas" / filename).is_file():
            errors.append(f"suite manifest schema missing: {filename}")
    artifact_names = set(schemas)
    for skill, entry in entries.items():
        if not isinstance(entry, dict):
            errors.append(f"suite manifest {skill} entry must be an object")
            continue
        if not isinstance(entry.get("produces"), list) or not isinstance(entry.get("consumes"), list):
            errors.append(f"suite manifest {skill} must declare produces and consumes arrays")
            continue
        for field in ("produces", "consumes"):
            values = entry[field]
            if not all(isinstance(value, str) for value in values):
                errors.append(f"suite manifest {skill} {field} entries must be strings")
                continue
            unknown = sorted(set(values) - artifact_names)
            if unknown:
                errors.append(f"suite manifest {skill} {field} references unknown artifacts: {unknown}")


def validate_sources(as_of: date, allow_stale: bool, errors: list[str]) -> None:
    payload = load_json(SOURCE_REGISTRY, errors)
    if payload is None:
        return
    result = validate_registry(payload, as_of, allow_stale)
    errors.extend(f"source registry: {error}" for error in result.errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the local SEO skill suite's structural and source-registry invariants.")
    parser.add_argument("--as-of", default=date.today().isoformat(), help="ISO date used to evaluate source freshness")
    parser.add_argument("--allow-stale-sources", action="store_true", help="Report source freshness outside this validator")
    args = parser.parse_args()

    errors: list[str] = []
    parsed_as_of = parse_day(args.as_of, "--as-of", type("Result", (), {"errors": errors})())
    if parsed_as_of is None:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2

    skill_paths = sorted(path for path in SKILLS.iterdir() if path.is_dir())
    for path in skill_paths:
        validate_skill(path, errors)
    validate_manifest({path.name for path in skill_paths}, errors)
    validate_sources(parsed_as_of, args.allow_stale_sources, errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: suite structure, {len(skill_paths)} skills, and source registry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
