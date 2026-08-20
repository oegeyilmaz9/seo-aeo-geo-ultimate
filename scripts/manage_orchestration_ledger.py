#!/usr/bin/env python3
"""Create and validate the SEO router's complete skill-coverage ledger."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import uuid
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from bundle_safety import is_reparse


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "suite.json"
LEDGER_VERSION = "1.0.0"
LANE_STATES = {
    "required",
    "active",
    "completed",
    "not-applicable",
    "blocked",
    "deferred-by-owner",
}
REQUEST_MODES = {"narrow", "broad", "end-to-end"}
OVERALL_STATES = {"in-progress", "completed", "blocked"}
FINAL_OVERALL_STATES = {"completed", "blocked"}
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")


class LedgerError(ValueError):
    """Raised for a safe, user-facing orchestration-ledger failure."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8-sig"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise LedgerError(f"cannot read JSON {path}: {exc}") from exc


def suite_contract() -> tuple[str, list[str]]:
    payload = load_json(MANIFEST)
    if not isinstance(payload, dict):
        raise LedgerError("suite manifest root must be an object")
    version = payload.get("suite_version")
    skills = payload.get("skills")
    if not isinstance(version, str) or not isinstance(skills, dict) or not skills:
        raise LedgerError("suite manifest must declare suite_version and skills")
    if "seo" not in skills:
        raise LedgerError("suite manifest must include the seo coordinator")
    return version, list(skills)


def parse_timestamp(value: object, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        errors.append(f"{label} must be an ISO 8601 UTC timestamp ending in Z")
        return
    try:
        dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        errors.append(f"{label} must be a valid ISO 8601 UTC timestamp")


def nonempty_text(value: object, label: str, errors: list[str]) -> bool:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return False
    if any(ord(character) < 32 and character not in "\t" for character in value):
        errors.append(f"{label} must not contain control characters")
        return False
    return True


def validate_reference(value: object, label: str, errors: list[str]) -> None:
    if not nonempty_text(value, label, errors):
        return
    assert isinstance(value, str)
    if "\n" in value or "\r" in value:
        errors.append(f"{label} must be a single-line reference")
        return
    if "://" in value:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None or parsed.password is not None:
            errors.append(f"{label} must be a credential-free HTTPS URL or a portable relative reference")
        return
    if "\\" in value or value.startswith("/") or WINDOWS_DRIVE_RE.match(value):
        errors.append(f"{label} must be a portable relative reference")
        return
    path_part = value.split("#", 1)[0]
    if not path_part or ".." in PurePosixPath(path_part).parts:
        errors.append(f"{label} must not be empty or traverse parent directories")


def validate_reference_list(value: object, label: str, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return
    if len(value) != len(set(item for item in value if isinstance(item, str))):
        errors.append(f"{label} must not contain duplicate references")
    for index, item in enumerate(value):
        validate_reference(item, f"{label}[{index}]", errors)


def validate_row(row: object, index: int, expected_skills: set[str], errors: list[str]) -> str | None:
    label = f"skills[{index}]"
    expected_fields = {
        "skill",
        "state",
        "reason",
        "evidence_refs",
        "output_refs",
        "blocker",
        "owner_decision_ref",
    }
    if not isinstance(row, dict):
        errors.append(f"{label} must be an object")
        return None
    if set(row) != expected_fields:
        errors.append(f"{label} must contain exactly {sorted(expected_fields)}")
        return None

    skill = row["skill"]
    if not isinstance(skill, str) or skill not in expected_skills:
        errors.append(f"{label}.skill must name a current suite skill")
        skill_name = None
    else:
        skill_name = skill

    state = row["state"]
    if state not in LANE_STATES:
        errors.append(f"{label}.state must be one of {sorted(LANE_STATES)}")
    nonempty_text(row["reason"], f"{label}.reason", errors)
    validate_reference_list(row["evidence_refs"], f"{label}.evidence_refs", errors)
    validate_reference_list(row["output_refs"], f"{label}.output_refs", errors)

    blocker = row["blocker"]
    owner_decision_ref = row["owner_decision_ref"]
    if state == "completed" and not row["evidence_refs"] and not row["output_refs"]:
        errors.append(f"{label} completed state requires evidence_refs or output_refs")
    if state == "blocked":
        nonempty_text(blocker, f"{label}.blocker", errors)
    elif blocker is not None:
        errors.append(f"{label}.blocker must be null unless state is blocked")
    if state == "deferred-by-owner":
        validate_reference(owner_decision_ref, f"{label}.owner_decision_ref", errors)
    elif owner_decision_ref is not None:
        errors.append(f"{label}.owner_decision_ref must be null unless state is deferred-by-owner")
    return skill_name


def validate_ledger(payload: Any) -> list[str]:
    errors: list[str] = []
    suite_version, skill_order = suite_contract()
    expected_skills = set(skill_order)
    expected_fields = {
        "ledger_version",
        "suite_version",
        "created_at",
        "request",
        "overall_state",
        "skills",
        "coverage_summary",
        "limitations",
    }
    if not isinstance(payload, dict):
        return ["ledger root must be an object"]
    if set(payload) != expected_fields:
        return [f"ledger root must contain exactly {sorted(expected_fields)}"]
    if payload["ledger_version"] != LEDGER_VERSION:
        errors.append(f"ledger_version must be {LEDGER_VERSION}")
    if payload["suite_version"] != suite_version:
        errors.append(f"suite_version must match the installed suite ({suite_version})")
    parse_timestamp(payload["created_at"], "created_at", errors)

    request = payload["request"]
    if not isinstance(request, dict) or set(request) != {"summary", "mode", "authorized_boundary"}:
        errors.append("request must contain exactly summary, mode, and authorized_boundary")
        mode = None
    else:
        nonempty_text(request["summary"], "request.summary", errors)
        nonempty_text(request["authorized_boundary"], "request.authorized_boundary", errors)
        mode = request["mode"]
        if mode not in REQUEST_MODES:
            errors.append(f"request.mode must be one of {sorted(REQUEST_MODES)}")

    overall_state = payload["overall_state"]
    if overall_state not in OVERALL_STATES:
        errors.append(f"overall_state must be one of {sorted(OVERALL_STATES)}")
    skills = payload["skills"]
    names: list[str] = []
    states: dict[str, object] = {}
    if not isinstance(skills, list):
        errors.append("skills must be an array")
    else:
        for index, row in enumerate(skills):
            name = validate_row(row, index, expected_skills, errors)
            if name is not None:
                names.append(name)
                states[name] = row["state"]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        missing = sorted(expected_skills - set(names))
        if duplicates:
            errors.append(f"skills contains duplicate suite rows: {duplicates}")
        if missing:
            errors.append(f"skills is missing current suite rows: {missing}")
        if len(skills) != len(skill_order):
            errors.append(f"skills must contain exactly {len(skill_order)} rows")

    coverage_summary = payload["coverage_summary"]
    if not isinstance(coverage_summary, str):
        errors.append("coverage_summary must be a string")
    limitations = payload["limitations"]
    if not isinstance(limitations, list):
        errors.append("limitations must be an array")
    else:
        for index, limitation in enumerate(limitations):
            nonempty_text(limitation, f"limitations[{index}]", errors)

    if states.get("seo") in {"not-applicable", "deferred-by-owner", "blocked"}:
        errors.append("the seo coordinator cannot be not-applicable, deferred, or blocked")
    if overall_state in FINAL_OVERALL_STATES:
        unfinished = sorted(name for name, state in states.items() if state in {"required", "active"})
        if unfinished:
            errors.append(f"final ledger cannot contain required or active lanes: {unfinished}")
        if states.get("seo") != "completed":
            errors.append("final ledger requires the seo coordinator to be completed")
        if mode in {"broad", "end-to-end"} and (not isinstance(coverage_summary, str) or len(coverage_summary.strip()) < 20):
            errors.append("a final broad or end-to-end ledger requires a compact coverage_summary")
    if overall_state == "completed" and any(state == "blocked" for state in states.values()):
        errors.append("completed ledger cannot contain blocked lanes")
    if overall_state == "blocked" and not any(state == "blocked" for state in states.values()):
        errors.append("blocked ledger requires at least one blocked lane")
    return errors


def assert_safe_output(path: Path, overwrite: bool) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:-1]:
        current /= part
        if not current.exists():
            break
        if is_reparse(current):
            raise LedgerError(f"output path must not traverse a symlink or reparse point: {current}")
    if path.exists():
        if is_reparse(path) or not path.is_file():
            raise LedgerError(f"output must be a regular file: {path}")
        if not overwrite:
            raise LedgerError(f"output already exists; pass --overwrite to replace it: {path}")
    if path.parent.exists() and is_reparse(path.parent):
        raise LedgerError(f"output parent must not be a symlink or reparse point: {path.parent}")


def atomic_write(path: Path, payload: dict[str, Any], overwrite: bool) -> None:
    assert_safe_output(path, overwrite)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists() and temporary.is_file() and not is_reparse(temporary):
            temporary.unlink()


def new_ledger(summary: str, mode: str, authorized_boundary: str, created_at: str) -> dict[str, Any]:
    suite_version, skills = suite_contract()
    return {
        "ledger_version": LEDGER_VERSION,
        "suite_version": suite_version,
        "created_at": created_at,
        "request": {
            "summary": summary,
            "mode": mode,
            "authorized_boundary": authorized_boundary,
        },
        "overall_state": "in-progress",
        "skills": [
            {
                "skill": skill,
                "state": "unassessed",
                "reason": "",
                "evidence_refs": [],
                "output_refs": [],
                "blocker": None,
                "owner_decision_ref": None,
            }
            for skill in skills
        ],
        "coverage_summary": "",
        "limitations": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or validate the SEO router's complete 27-skill coverage ledger.")
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init", help="Create an explicitly unassessed ledger draft from the current suite manifest.")
    initialize.add_argument("--output", type=Path, required=True)
    initialize.add_argument("--request", required=True, dest="request_summary")
    initialize.add_argument("--mode", choices=sorted(REQUEST_MODES), required=True)
    initialize.add_argument("--authorized-boundary", required=True)
    initialize.add_argument("--created-at", default=None)
    initialize.add_argument("--overwrite", action="store_true")
    validate = commands.add_parser("validate", help="Validate complete coverage and terminal-state invariants.")
    validate.add_argument("ledger", type=Path)
    args = parser.parse_args()

    try:
        if args.command == "init":
            created_at = args.created_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            timestamp_errors: list[str] = []
            parse_timestamp(created_at, "--created-at", timestamp_errors)
            if timestamp_errors:
                raise LedgerError(timestamp_errors[0])
            payload = new_ledger(args.request_summary, args.mode, args.authorized_boundary, created_at)
            atomic_write(args.output, payload, args.overwrite)
            print(f"DRAFT: {args.output} contains {len(payload['skills'])} unassessed suite rows; fill and validate it before closeout")
            return 0

        payload = load_json(args.ledger)
        errors = validate_ledger(payload)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 2
        print(f"PASS: {args.ledger} covers all {len(payload['skills'])} current suite skills")
        return 0
    except LedgerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
