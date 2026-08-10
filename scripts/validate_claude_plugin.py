#!/usr/bin/env python3
"""Validate the Claude Code plugin and marketplace metadata without Claude Code.

This validator intentionally checks the package shape that Claude Code's
``claude plugin validate`` command will inspect later, while also ensuring the
same 27 skill trees remain valid Codex runtime sources. It does not execute a
model, invoke a network service, or require Claude credentials.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
SUITE_MANIFEST = ROOT / "manifests" / "suite.json"
PLUGIN_MANIFEST = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_MANIFEST = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_NAME = "seo-aeo-geo-ultimate"
MARKETPLACE_NAME = "oegeyilmaz9-skills"
REPOSITORY_URL = "https://github.com/oegeyilmaz9/seo-aeo-geo-ultimate"
REPOSITORY_SLUG = "oegeyilmaz9/seo-aeo-geo-ultimate"
EXPECTED_SKILL_COUNT = 27
REQUIRED_KEYWORDS = {"seo", "aeo", "geo", "ai-search", "agent-skills", "codex", "claude-code", "llms-txt"}
FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.S)
DIRECT_CODEX_SKILL_RE = re.compile(r"\$[a-z][a-z0-9-]*\b")


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        errors.append(f"missing JSON file: {relative(path)}")
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON: {relative(path)}:{exc.lineno}:{exc.colno}")
    return None


def require_string(payload: dict[str, Any], field: str, errors: list[str], *, expected: str | None = None) -> str | None:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be a non-empty string")
        return None
    if expected is not None and value != expected:
        errors.append(f"{field} must be {expected!r}")
    return value


def validate_skills(errors: list[str]) -> set[str]:
    if not SKILLS.is_dir():
        errors.append("skills directory is missing")
        return set()

    skill_paths = sorted(path for path in SKILLS.iterdir() if path.is_dir())
    if len(skill_paths) != EXPECTED_SKILL_COUNT:
        errors.append(f"expected {EXPECTED_SKILL_COUNT} shared skills, found {len(skill_paths)}")

    names: set[str] = set()
    for path in skill_paths:
        skill = path.name
        names.add(skill)
        skill_md = path / "SKILL.md"
        codex_interface = path / "agents" / "openai.yaml"
        if not skill_md.is_file():
            errors.append(f"{skill}: SKILL.md is missing")
            continue
        if not codex_interface.is_file():
            errors.append(f"{skill}: Codex interface metadata is missing")
        text = skill_md.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(text)
        if match is None:
            errors.append(f"{skill}: SKILL.md must begin with frontmatter")
            continue
        frontmatter = match.group(1)
        name = re.search(r"^name:\s*(.+?)\s*$", frontmatter, re.M)
        description = re.search(r"^description:\s*(.+?)\s*$", frontmatter, re.M)
        if name is None or name.group(1).strip(" '\"") != skill:
            errors.append(f"{skill}: frontmatter name must match its directory")
        if description is None or not description.group(1).strip(" '\""):
            errors.append(f"{skill}: frontmatter description is required")
        direct_calls = DIRECT_CODEX_SKILL_RE.findall(text)
        if direct_calls:
            errors.append(f"{skill}: use platform-neutral skill names instead of direct Codex calls: {sorted(set(direct_calls))}")
    return names


def validate_plugin(plugin: Any, suite: Any, skill_names: set[str], errors: list[str]) -> None:
    if not isinstance(plugin, dict):
        return
    allowed = {
        "$schema",
        "name",
        "displayName",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "license",
        "keywords",
        "skills",
    }
    unexpected = sorted(set(plugin) - allowed)
    if unexpected:
        errors.append(f"plugin manifest contains unsupported package fields: {unexpected}")
    require_string(plugin, "$schema", errors, expected="https://json.schemastore.org/claude-code-plugin-manifest.json")
    require_string(plugin, "name", errors, expected=PLUGIN_NAME)
    require_string(plugin, "displayName", errors, expected="SEO-AEO-GEO Ultimate")
    require_string(plugin, "description", errors)
    require_string(plugin, "homepage", errors, expected=REPOSITORY_URL + "#readme")
    require_string(plugin, "repository", errors, expected=REPOSITORY_URL)
    require_string(plugin, "license", errors, expected="Apache-2.0")
    require_string(plugin, "skills", errors, expected="./skills")

    expected_version = suite.get("suite_version") if isinstance(suite, dict) else None
    version = require_string(plugin, "version", errors)
    if not isinstance(expected_version, str) or not expected_version:
        errors.append("suite manifest must declare a non-empty suite_version")
    elif version is not None and version != expected_version:
        errors.append("plugin version must match manifests/suite.json suite_version")

    author = plugin.get("author")
    if not isinstance(author, dict):
        errors.append("plugin author must be an object")
    else:
        require_string(author, "name", errors, expected="Oegeyilmaz9")
        require_string(author, "url", errors, expected="https://github.com/oegeyilmaz9")

    keywords = plugin.get("keywords")
    if not isinstance(keywords, list) or not all(isinstance(value, str) and value for value in keywords):
        errors.append("plugin keywords must be a non-empty array of strings")
    else:
        missing = sorted(REQUIRED_KEYWORDS - set(keywords))
        if missing:
            errors.append(f"plugin keywords are missing discovery terms: {missing}")

    if not skill_names:
        errors.append("plugin must expose at least one skill")


def validate_marketplace(marketplace: Any, plugin: Any, suite: Any, errors: list[str]) -> None:
    if not isinstance(marketplace, dict):
        return
    allowed = {"name", "owner", "description", "plugins"}
    unexpected = sorted(set(marketplace) - allowed)
    if unexpected:
        errors.append(f"marketplace manifest contains unsupported fields: {unexpected}")
    require_string(marketplace, "name", errors, expected=MARKETPLACE_NAME)
    require_string(marketplace, "description", errors)
    owner = marketplace.get("owner")
    if not isinstance(owner, dict):
        errors.append("marketplace owner must be an object")
    else:
        require_string(owner, "name", errors, expected="Oegeyilmaz9")

    entries = marketplace.get("plugins")
    if not isinstance(entries, list) or not entries:
        errors.append("marketplace plugins must be a non-empty array")
        return
    matching = [entry for entry in entries if isinstance(entry, dict) and entry.get("name") == PLUGIN_NAME]
    if len(matching) != 1:
        errors.append(f"marketplace must declare exactly one {PLUGIN_NAME!r} entry")
        return
    entry = matching[0]
    require_string(entry, "description", errors)
    require_string(entry, "version", errors, expected=suite.get("suite_version") if isinstance(suite, dict) else None)
    require_string(entry, "license", errors, expected="Apache-2.0")
    source = entry.get("source")
    if source != {"source": "github", "repo": REPOSITORY_SLUG}:
        errors.append("marketplace source must point to this public GitHub repository")
    if isinstance(plugin, dict) and isinstance(plugin.get("description"), str) and entry.get("description") != plugin["description"]:
        errors.append("marketplace description must match the plugin description")
    if isinstance(plugin, dict) and entry.get("keywords") != plugin.get("keywords"):
        errors.append("marketplace keywords must match the plugin keywords")
    author = entry.get("author")
    if not isinstance(author, dict) or author.get("name") != "Oegeyilmaz9":
        errors.append("marketplace plugin author must identify Oegeyilmaz9")


def main() -> int:
    errors: list[str] = []
    suite = load_json(SUITE_MANIFEST, errors)
    plugin = load_json(PLUGIN_MANIFEST, errors)
    marketplace = load_json(MARKETPLACE_MANIFEST, errors)
    skill_names = validate_skills(errors)
    validate_plugin(plugin, suite, skill_names, errors)
    validate_marketplace(marketplace, plugin, suite, errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: Claude Code plugin, marketplace, and {len(skill_names)} shared skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
