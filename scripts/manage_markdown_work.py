#!/usr/bin/env python3
"""Maintain a private, direct-link Markdown index for every material work step."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, unquote

from manage_markdown_site import sha, text, local, read_json, SLUG, markdown_links
from install_runtime import assert_safe_existing_path

STATES = {"draft", "provisional", "completed", "blocked", "not-applicable"}


def index(payload: dict) -> str:
    lines = [f"# {payload['title']}", "", "Private work documents. Public delivery and engine outcomes are recorded separately.", ""]
    for s in payload["steps"]:
        lines.append(f"- [{s['title']}]({s['path']}): {s['status']} — {s['outcome']}. Owner: {s['owner']}.")
    return "\n".join(lines) + "\n"


def save(root: Path, payload: dict) -> None:
    for name in ("work-ledger.json", "index.md"):
        assert_safe_existing_path(root / name, "work index")
    (root / "work-ledger.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "index.md").write_text(index(payload), encoding="utf-8")


def register(root: Path, step_id: str, path: str, title: str, status: str, owner: str, outcome: str) -> None:
    payload = read_json(root / "work-ledger.json")
    if payload.get("ledger_version") != "1.0.0":
        raise ValueError("unsupported work ledger")
    if not SLUG.fullmatch(step_id) or status not in STATES:
        raise ValueError("invalid step id/status")
    doc = local(root, path)
    if doc.suffix != ".md" or path == "index.md" or not doc.read_text(encoding="utf-8").strip():
        raise ValueError("step must be a substantive Markdown document")
    if any(s["path"] == path and s["id"] != step_id for s in payload["steps"]):
        raise ValueError("one canonical step per document; use explicit sections inside it for subactions")
    record = {"id": step_id, "path": path, "title": text(title, "title"), "status": status,
              "owner": text(owner, "owner"), "outcome": text(outcome, "outcome"), "sha256": sha(doc.read_bytes())}
    payload["steps"] = [s for s in payload["steps"] if s["id"] != step_id] + [record]
    save(root, payload)


def check(root: Path, final: bool) -> None:
    payload = read_json(root / "work-ledger.json")
    if payload.get("ledger_version") != "1.0.0" or not payload.get("steps"):
        raise ValueError("unsupported or empty work ledger")
    ids, paths = set(), set()
    for s in payload["steps"]:
        if s["id"] in ids or s["path"] in paths or s["status"] not in STATES:
            raise ValueError("duplicate step/path or invalid status")
        ids.add(s["id"]); paths.add(s["path"])
        document = local(root, s["path"])
        if sha(document.read_bytes()) != s["sha256"]:
            raise ValueError(f"stale registered document: {s['path']}; register its current state")
        for target in markdown_links(document.read_text(encoding="utf-8")):
            parsed = urlsplit(target)
            if parsed.scheme in ("https", "http", "mailto", "tel"):
                continue
            target_path = unquote(parsed.path)
            dest = document if not target_path else local(document.parent, target_path)
            if not dest.is_file():
                raise ValueError(f"broken work-document destination: {s['path']} -> {target}")
            if parsed.fragment and dest.suffix == ".md":
                headings = re.findall(r"^#{1,6}\s+(.+)$", dest.read_text(encoding="utf-8"), re.M)
                anchors = {re.sub(r"[^\w -]", "", h.lower()).replace(" ", "-") for h in headings}
                if unquote(parsed.fragment) not in anchors:
                    raise ValueError(f"broken work-document section: {target}")
        if final and s["status"] in ("draft", "provisional", "blocked"):
            raise ValueError(f"unresolved step: {s['id']} ({s['status']})")
    # Any step document omitted from the index is a closeout gap.
    actual = set()
    for p in root.rglob("*"):
        assert_safe_existing_path(p, "work document")
        if p.is_file() and p.suffix == ".md" and p != root / "index.md" and "raw" not in p.relative_to(root).parts:
            actual.add(p.relative_to(root).as_posix())
    if actual != paths:
        raise ValueError(f"unregistered or missing Markdown step documents: {sorted(actual ^ paths)}")
    if (root / "index.md").read_text(encoding="utf-8") != index(payload):
        raise ValueError("work index differs from ledger")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("init"); p.add_argument("--title", required=True)
    p = subs.add_parser("add")
    for name in ("id", "path", "title", "owner", "outcome"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--status", choices=sorted(STATES), required=True)
    p = subs.add_parser("check"); p.add_argument("--final", action="store_true")
    a = parser.parse_args()
    try:
        assert_safe_existing_path(a.root, "private work root")
        if a.command == "init":
            if any((a.root / n).exists() for n in ("index.md", "work-ledger.json")):
                raise ValueError("existing work index must be preserved")
            a.root.mkdir(parents=True, exist_ok=True)
            save(a.root, {"ledger_version": "1.0.0", "title": text(a.title, "title"), "steps": []})
        elif a.command == "add":
            register(a.root, a.id, a.path, a.title, a.status, a.owner, a.outcome)
        else:
            check(a.root, a.final)
        print(f"PASS: Markdown work {a.command}")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
