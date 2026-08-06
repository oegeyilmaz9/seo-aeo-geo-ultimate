#!/usr/bin/env python3
"""Safely install selected SEO skills into a Codex runtime directory.

The repository remains the source of validators, contracts, source registry, and
tests. This installer deploys only self-contained skill instruction trees. Each
existing target is moved into a timestamped backup before its replacement is
made; no backup is deleted by this tool.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SKILLS = ROOT / "skills"
SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_reparse(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    attributes = getattr(metadata, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def assert_safe_existing_path(path: Path, label: str) -> None:
    absolute = path.absolute()
    anchor = Path(absolute.anchor)
    current = anchor
    for part in absolute.parts[1:]:
        current /= part
        if not current.exists():
            break
        if is_reparse(current):
            raise ValueError(f"{label} must not traverse a symlink or reparse point: {current}")


def paths_overlap(left: Path, right: Path) -> bool:
    left_resolved = left.resolve()
    right_resolved = right.resolve()
    try:
        left_resolved.relative_to(right_resolved)
        return True
    except ValueError:
        try:
            right_resolved.relative_to(left_resolved)
            return True
        except ValueError:
            return False


def iter_tree(root: Path) -> list[Path]:
    entries: list[Path] = []
    for path in root.rglob("*"):
        if is_reparse(path):
            raise ValueError(f"skill tree contains a symlink or reparse point: {path}")
        if path.is_file():
            entries.append(path)
        elif not path.is_dir():
            raise ValueError(f"skill tree contains a non-regular entry: {path}")
    return entries


def tree_hash(root: Path) -> str:
    rows: list[str] = []
    for path in sorted(iter_tree(root), key=lambda item: item.relative_to(root).as_posix()):
        rows.append(f"{path.relative_to(root).as_posix()}\t{sha256(path)}\n")
    return hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()


def validate_source_skill(path: Path) -> None:
    name = path.name
    if not SKILL_NAME_RE.fullmatch(name):
        raise ValueError(f"invalid source skill name: {name}")
    skill_file = path / "SKILL.md"
    interface = path / "agents" / "openai.yaml"
    if not skill_file.is_file() or not interface.is_file():
        raise ValueError(f"{name} is missing SKILL.md or agents/openai.yaml")
    text = skill_file.read_text(encoding="utf-8")
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if match is None or not re.search(rf"^name:\s*{re.escape(name)}\s*$", match.group(1), re.M):
        raise ValueError(f"{name} frontmatter does not bind its directory name")
    if "TODO" in text or "[TODO" in text:
        raise ValueError(f"{name} contains unfinished scaffold text")
    if f"${name}" not in interface.read_text(encoding="utf-8"):
        raise ValueError(f"{name} interface default prompt does not invoke the skill")
    iter_tree(path)


def available_skills() -> dict[str, Path]:
    if not SOURCE_SKILLS.is_dir():
        raise ValueError(f"source skills directory does not exist: {SOURCE_SKILLS}")
    result = {path.name: path for path in SOURCE_SKILLS.iterdir() if path.is_dir()}
    for path in result.values():
        validate_source_skill(path)
    return result


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def copy_stage(source: Path, runtime_root: Path, name: str) -> Path:
    stage = runtime_root / f".{name}.seo-suite-stage-{uuid.uuid4().hex}"
    if stage.exists():
        raise ValueError(f"unexpected staging collision: {stage}")
    shutil.copytree(source, stage, copy_function=shutil.copy2, symlinks=False)
    if tree_hash(stage) != tree_hash(source):
        raise ValueError(f"staging hash mismatch for {name}")
    return stage


def restore(records: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for record in reversed(records):
        target = record["target"]
        backup = record["backup"]
        try:
            if target.exists():
                if is_reparse(target):
                    raise ValueError("target became a reparse point")
                shutil.rmtree(target)
            if backup is not None and backup.exists():
                os.replace(backup, target)
        except BaseException as exc:  # keep recovery details for the caller
            failures.append(f"{record['name']}: {exc}")
    return failures


def install(selected: list[str], runtime_root: Path, state_root: Path, dry_run: bool) -> dict[str, Any]:
    assert_safe_existing_path(runtime_root, "runtime root")
    assert_safe_existing_path(state_root, "state root")
    if paths_overlap(runtime_root, SOURCE_SKILLS):
        raise ValueError("runtime root must not overlap the source skills directory")
    if paths_overlap(state_root, SOURCE_SKILLS):
        raise ValueError("state root must not overlap the source skills directory")
    if paths_overlap(runtime_root, state_root):
        raise ValueError("runtime root and state root must not overlap")
    sources = available_skills()
    unknown = sorted(set(selected) - set(sources))
    if unknown:
        raise ValueError(f"unknown skills: {unknown}")
    timestamp = utc_stamp()
    backup_root = state_root / "backups" / timestamp
    plan = {
        "installer_version": "1.0.0",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_root": str(ROOT),
        "runtime_root": str(runtime_root),
        "backup_root": str(backup_root),
        "dry_run": dry_run,
        "skills": [
            {
                "name": name,
                "source_hash": tree_hash(sources[name]),
                "target": str(runtime_root / name),
                "target_existed": (runtime_root / name).exists(),
            }
            for name in selected
        ],
    }
    if dry_run:
        return plan

    runtime_root.mkdir(parents=True, exist_ok=True)
    if is_reparse(runtime_root):
        raise ValueError("runtime root must not be a symlink or reparse point")
    backup_root.mkdir(parents=True, exist_ok=False)

    stages: dict[str, Path] = {}
    records: list[dict[str, Any]] = []
    try:
        for name in selected:
            stages[name] = copy_stage(sources[name], runtime_root, name)
        for name in selected:
            target = runtime_root / name
            if target.exists() and is_reparse(target):
                raise ValueError(f"runtime target must not be a symlink or reparse point: {target}")
            if target.exists() and not target.is_dir():
                raise ValueError(f"runtime target must be a directory when it already exists: {target}")
            backup = backup_root / name if target.exists() else None
            if backup is not None:
                os.replace(target, backup)
            record = {"name": name, "target": target, "backup": backup}
            records.append(record)
            os.replace(stages[name], target)
            if tree_hash(target) != tree_hash(sources[name]):
                raise ValueError(f"installed hash mismatch for {name}")
    except BaseException:
        rollback_failures = restore(records)
        if rollback_failures:
            raise RuntimeError("installation failed and rollback was incomplete: " + "; ".join(rollback_failures))
        raise
    finally:
        for stage in stages.values():
            if stage.exists() and stage.is_dir() and not is_reparse(stage):
                shutil.rmtree(stage)

    installed = []
    for item in plan["skills"]:
        name = item["name"]
        item["installed_hash"] = tree_hash(runtime_root / name)
        item["backup"] = str(backup_root / name) if item["target_existed"] else None
        installed.append(item)
    plan["skills"] = installed
    manifest = state_root / "installs" / f"{timestamp}.json"
    atomic_json(manifest, plan)
    plan["manifest"] = str(manifest)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Install selected validated SEO skill trees into a Codex runtime with backups.")
    parser.add_argument("--runtime-root", type=Path, default=Path.home() / ".codex" / "skills")
    parser.add_argument("--state-root", type=Path, help="where install manifests and retained backups are stored")
    parser.add_argument("--skills", nargs="+", metavar="SKILL", help="skill names to install; defaults to the entire suite")
    parser.add_argument("--dry-run", action="store_true", help="validate inputs and print the replacement plan without writing")
    args = parser.parse_args()
    runtime_root = args.runtime_root.absolute()
    state_root = (args.state_root or runtime_root.parent / "seo-skill-suite-state").absolute()
    try:
        available = available_skills()
        selected = args.skills or sorted(available)
        result = install(selected, runtime_root, state_root, args.dry_run)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
