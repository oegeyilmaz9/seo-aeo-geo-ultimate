#!/usr/bin/env python3
"""Safely install the complete SEO suite into a Codex runtime directory.

The installer deploys selected skill trees plus an immutable support package
containing validators, contracts, protocols, templates, and examples. Installed
skills receive a runtime locator so formal validation still works after the
source checkout is removed. Existing targets are backed up and never deleted.
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
SUITE_MANIFEST = ROOT / "manifests" / "suite.json"
RUNTIME_LOCATOR = ".seo-suite-runtime.json"
SUPPORT_DIRECTORIES = ("scripts", "manifests", "docs", "skills", "examples")
SUPPORT_FILES = ("README.md", "CHANGELOG.md", "LICENSE", "NOTICE", "CITATION.cff", "llms.txt")
SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


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


def installed_skill_source_hash(root: Path) -> str:
    rows: list[str] = []
    for path in sorted(iter_tree(root), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if relative == RUNTIME_LOCATOR:
            continue
        rows.append(f"{relative}\t{sha256(path)}\n")
    return hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()


def suite_version() -> str:
    try:
        payload = json.loads(SUITE_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read suite manifest: {exc}") from exc
    version = payload.get("suite_version") if isinstance(payload, dict) else None
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("suite manifest must declare a semantic suite_version")
    return version


def support_sources() -> list[Path]:
    sources: list[Path] = []
    for name in SUPPORT_DIRECTORIES:
        candidate = ROOT / name
        if candidate.exists():
            if not candidate.is_dir() or is_reparse(candidate):
                raise ValueError(f"support source must be a regular directory: {candidate}")
            sources.append(candidate)
    for name in SUPPORT_FILES:
        candidate = ROOT / name
        if candidate.exists():
            if not candidate.is_file() or is_reparse(candidate):
                raise ValueError(f"support source must be a regular file: {candidate}")
            sources.append(candidate)
    required = {ROOT / "scripts", ROOT / "manifests", ROOT / "docs", ROOT / "skills"}
    if not required.issubset(set(sources)):
        raise ValueError("support package is missing scripts, manifests, docs, or skills")
    return sources


def support_hash() -> str:
    entries: list[tuple[str, Path]] = []
    for source in support_sources():
        if source.is_file():
            entries.append((source.relative_to(ROOT).as_posix(), source))
            continue
        for path in iter_tree(source):
            relative = path.relative_to(ROOT).as_posix()
            if "/__pycache__/" in f"/{relative}/" or relative.endswith((".pyc", ".pyo")):
                continue
            entries.append((relative, path))
    rows = [f"{relative}\t{sha256(path)}\n" for relative, path in sorted(entries)]
    return hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()


def installed_support_hash(root: Path) -> str:
    rows: list[str] = []
    for path in sorted(iter_tree(root), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if "/__pycache__/" in f"/{relative}/" or relative.endswith((".pyc", ".pyo")):
            continue
        rows.append(f"{relative}\t{sha256(path)}\n")
    return hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()


def copy_support_stage(state_root: Path, expected_hash: str) -> Path:
    stage = state_root / f".seo-suite-support-stage-{uuid.uuid4().hex}"
    if stage.exists():
        raise ValueError(f"unexpected support staging collision: {stage}")
    stage.mkdir(parents=True)
    try:
        for source in support_sources():
            destination = stage / source.relative_to(ROOT)
            if source.is_dir():
                shutil.copytree(
                    source,
                    destination,
                    copy_function=shutil.copy2,
                    symlinks=False,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
                )
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
        if installed_support_hash(stage) != expected_hash:
            raise ValueError("support package staging hash mismatch")
    except BaseException:
        if stage.exists() and stage.is_dir() and not is_reparse(stage):
            shutil.rmtree(stage)
        raise
    return stage


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
    assert_safe_existing_path(path.parent, "metadata parent")
    if path.exists() and (is_reparse(path) or not path.is_file()):
        raise ValueError(f"metadata target must be a regular file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists() and temporary.is_file() and not is_reparse(temporary):
            temporary.unlink()


def copy_stage(source: Path, runtime_root: Path, name: str, locator: dict[str, str]) -> Path:
    stage = runtime_root / f".{name}.seo-suite-stage-{uuid.uuid4().hex}"
    if stage.exists():
        raise ValueError(f"unexpected staging collision: {stage}")
    shutil.copytree(source, stage, copy_function=shutil.copy2, symlinks=False)
    if tree_hash(stage) != tree_hash(source):
        raise ValueError(f"staging hash mismatch for {name}")
    atomic_json(stage / RUNTIME_LOCATOR, locator)
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


def verify_install(selected: list[str] | None, runtime_root: Path, state_root: Path) -> dict[str, Any]:
    assert_safe_existing_path(runtime_root, "runtime root")
    assert_safe_existing_path(state_root, "state root")
    current_path = state_root / "current.json"
    try:
        current = json.loads(current_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"installed suite manifest is missing: {current_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"installed suite manifest is invalid JSON: {current_path}") from exc
    if not isinstance(current, dict):
        raise ValueError("installed suite manifest must contain an object")
    package_root_value = current.get("suite_root")
    package_hash = current.get("package_hash")
    version = current.get("suite_version")
    if not all(isinstance(value, str) and value for value in (package_root_value, package_hash, version)):
        raise ValueError("installed suite manifest is missing suite_root, package_hash, or suite_version")
    package_root = Path(package_root_value).absolute()
    try:
        package_root.resolve().relative_to((state_root / "packages").resolve())
    except ValueError as exc:
        raise ValueError("installed support package must stay under the state packages directory") from exc
    assert_safe_existing_path(package_root, "installed support package")
    if not package_root.is_dir() or is_reparse(package_root):
        raise ValueError(f"installed support package is missing or unsafe: {package_root}")
    if installed_support_hash(package_root) != package_hash:
        raise ValueError(f"installed support package hash mismatch: {package_root}")

    package_skills = package_root / "skills"
    if not package_skills.is_dir():
        raise ValueError(f"installed support package has no skills directory: {package_skills}")
    sources = {path.name: path for path in package_skills.iterdir() if path.is_dir()}
    selected = selected or sorted(sources)
    unknown = sorted(set(selected) - set(sources))
    if unknown:
        raise ValueError(f"unknown skills: {unknown}")
    verified: list[dict[str, Any]] = []
    for name in selected:
        target = runtime_root / name
        if not target.is_dir() or is_reparse(target):
            raise ValueError(f"installed skill is missing or unsafe: {target}")
        locator_path = target / RUNTIME_LOCATOR
        try:
            locator = json.loads(locator_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise ValueError(f"installed skill runtime locator is missing or invalid: {locator_path}") from exc
        if locator.get("suite_root") != str(package_root) or locator.get("package_hash") != package_hash:
            raise ValueError(f"installed skill runtime locator drift: {locator_path}")
        expected_hash = tree_hash(sources[name])
        actual_hash = installed_skill_source_hash(target)
        if actual_hash != expected_hash:
            raise ValueError(f"installed skill source hash mismatch: {name}")
        verified.append({"name": name, "source_hash": actual_hash, "target": str(target)})
    return {
        "current_manifest": str(current_path),
        "package_hash": package_hash,
        "runtime_root": str(runtime_root),
        "skills": verified,
        "suite_root": str(package_root),
        "suite_version": version,
        "verified": True,
    }


def install(selected: list[str], runtime_root: Path, state_root: Path, dry_run: bool) -> dict[str, Any]:
    assert_safe_existing_path(runtime_root, "runtime root")
    assert_safe_existing_path(state_root, "state root")
    if paths_overlap(runtime_root, ROOT):
        raise ValueError("runtime root must not overlap the source repository")
    if paths_overlap(state_root, ROOT):
        raise ValueError("state root must not overlap the source repository")
    if paths_overlap(runtime_root, state_root):
        raise ValueError("runtime root and state root must not overlap")
    sources = available_skills()
    unknown = sorted(set(selected) - set(sources))
    if unknown:
        raise ValueError(f"unknown skills: {unknown}")
    version = suite_version()
    package_hash = support_hash()
    package_root = state_root / "packages" / f"{version}-{package_hash[:16]}"
    current_manifest = state_root / "current.json"
    locator = {
        "package_hash": package_hash,
        "suite_root": str(package_root),
        "suite_version": version,
    }
    timestamp = utc_stamp()
    backup_root = state_root / "backups" / timestamp
    plan = {
        "installer_version": "2.0.0",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_root": str(ROOT),
        "runtime_root": str(runtime_root),
        "backup_root": str(backup_root),
        "current_manifest": str(current_manifest),
        "dry_run": dry_run,
        "package_hash": package_hash,
        "suite_root": str(package_root),
        "suite_version": version,
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

    if package_root.exists():
        if not package_root.is_dir() or is_reparse(package_root):
            raise ValueError(f"support package target must be a regular directory: {package_root}")
        if installed_support_hash(package_root) != package_hash:
            raise ValueError(f"existing support package hash mismatch: {package_root}")
    else:
        support_stage = copy_support_stage(state_root, package_hash)
        package_root.parent.mkdir(parents=True, exist_ok=True)
        os.replace(support_stage, package_root)

    stages: dict[str, Path] = {}
    staged_hashes: dict[str, str] = {}
    records: list[dict[str, Any]] = []
    manifest = state_root / "installs" / f"{timestamp}.json"
    plan["manifest"] = str(manifest)
    manifest_written = False
    try:
        for name in selected:
            stages[name] = copy_stage(sources[name], runtime_root, name, locator)
            staged_hashes[name] = tree_hash(stages[name])
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
            if tree_hash(target) != staged_hashes[name]:
                raise ValueError(f"installed hash mismatch for {name}")
        installed = []
        for item in plan["skills"]:
            name = item["name"]
            item["installed_hash"] = tree_hash(runtime_root / name)
            item["backup"] = str(backup_root / name) if item["target_existed"] else None
            installed.append(item)
        plan["skills"] = installed
        atomic_json(manifest, plan)
        manifest_written = True
        atomic_json(
            current_manifest,
            {
                "installed_at": plan["created_at"],
                "package_hash": package_hash,
                "suite_root": str(package_root),
                "suite_version": version,
            },
        )
    except BaseException:
        rollback_failures = restore(records)
        if manifest_written:
            try:
                if manifest.is_file() and not is_reparse(manifest):
                    manifest.unlink()
            except OSError as exc:
                rollback_failures.append(f"install manifest cleanup: {exc}")
        if rollback_failures:
            raise RuntimeError("installation failed and rollback was incomplete: " + "; ".join(rollback_failures))
        raise
    finally:
        for stage in stages.values():
            if stage.exists() and stage.is_dir() and not is_reparse(stage):
                shutil.rmtree(stage)

    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Install selected SEO skills and their self-contained validation runtime.")
    parser.add_argument("--runtime-root", type=Path, default=Path.home() / ".codex" / "skills")
    parser.add_argument("--state-root", type=Path, help="where install manifests and retained backups are stored")
    parser.add_argument("--skills", nargs="+", metavar="SKILL", help="skill names to install; defaults to the entire suite")
    parser.add_argument("--dry-run", action="store_true", help="validate inputs and print the replacement plan without writing")
    parser.add_argument("--verify", action="store_true", help="verify the installed support package, locators, and selected skill hashes")
    args = parser.parse_args()
    runtime_root = args.runtime_root.absolute()
    state_root = (args.state_root or runtime_root.parent / "seo-skill-suite-state").absolute()
    try:
        if args.verify and args.dry_run:
            raise ValueError("--verify and --dry-run are mutually exclusive")
        if args.verify:
            result = verify_install(args.skills, runtime_root, state_root)
        else:
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
