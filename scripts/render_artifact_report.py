#!/usr/bin/env python3
"""Render a semantically validated SEO-suite artifact as readable Markdown."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from bundle_safety import is_reparse, resolve_artifact_in_bundle


ROOT = Path(__file__).resolve().parents[1]
IDENTITY_FIELDS = (
    "research_id",
    "corpus_id",
    "brief_id",
    "run_id",
    "graph_id",
    "registry_id",
    "finding_set_id",
    "plan_id",
    "receipt_id",
)
COLLECTIONS = (
    "entities",
    "queries",
    "evidence",
    "competitor_observations",
    "ground_truth",
    "gaps",
    "targets",
    "audit_evidence",
    "findings",
    "recommendations",
    "experiments",
    "features",
    "crawlers",
    "change_notifications",
    "protocol_capabilities",
    "nodes",
    "edges",
    "observations",
    "scores",
    "accuracy_checks",
    "rows",
    "indexation",
    "web_vitals",
    "drift",
    "actions",
    "declined_claims",
    "declined_actions",
    "outcomes",
)


class RenderError(ValueError):
    """A user-facing rendering error without a traceback."""


def load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RenderError(f"cannot read JSON from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RenderError("artifact must contain a JSON object")
    return payload


def infer_type(payload: dict[str, Any]) -> str:
    if "research_id" in payload and "entities" in payload and "ground_truth" in payload:
        return "research-pack"
    if "corpus_id" in payload and "queries" in payload:
        return "query-corpus"
    if "brief_id" in payload and "optimization_domain" in payload:
        return "optimization-brief"
    if "finding_set_id" in payload:
        return "seo-findings"
    if "plan_id" in payload:
        return "action-plan"
    if "graph_id" in payload:
        return "site-graph"
    if "registry_id" in payload and "features" in payload:
        return "platform-controls"
    if "run_id" in payload and "source_type" in payload:
        return "seo-performance-run"
    if "run_id" in payload and "research_ref" in payload:
        return "visibility-run"
    if "receipt_id" in payload and "provider" in payload and "operation" in payload:
        return "provider-operation-receipt"
    raise RenderError("cannot infer artifact type; pass --type explicitly")


def validator_command(
    artifact_type: str,
    artifact: Path,
    bundle: Path,
    payload: dict[str, Any],
    as_of: str | None,
) -> list[str]:
    command = [sys.executable]
    if artifact_type == "research-pack":
        if not as_of:
            raise RenderError("research-pack rendering requires --as-of for freshness validation")
        return command + [
            str(ROOT / "scripts" / "validate_ai_search_research.py"),
            "validate-pack",
            str(artifact),
            "--bundle",
            str(bundle),
            "--now",
            as_of,
        ]
    if artifact_type == "optimization-brief":
        producer = payload.get("producer_skill")
        if producer == "seo-aeo":
            script = "validate_seo_aeo.py"
        elif producer == "seo-geo":
            script = "validate_seo_geo.py"
        else:
            raise RenderError("optimization brief producer_skill must be seo-aeo or seo-geo")
        verb = "validate-brief"
    elif artifact_type == "query-corpus":
        script, verb = "validate_query_corpus.py", "validate-corpus"
    elif artifact_type == "visibility-run":
        script, verb = "validate_ai_visibility_monitor.py", "validate-run"
    elif artifact_type == "seo-performance-run":
        script, verb = "validate_seo_performance.py", "validate-run"
    elif artifact_type == "site-graph":
        script, verb = "validate_site_graph.py", "validate-graph"
    elif artifact_type == "platform-controls":
        if not as_of:
            raise RenderError("platform-controls rendering requires --as-of for lifecycle validation")
        return command + [
            str(ROOT / "scripts" / "validate_platform_controls.py"),
            "validate-registry",
            str(artifact),
            "--bundle",
            str(bundle),
            "--as-of",
            as_of,
        ]
    elif artifact_type == "seo-findings":
        script, verb = "validate_seo_findings.py", "validate-findings"
    elif artifact_type == "action-plan":
        script, verb = "validate_seo_action_plan.py", "validate-plan"
    elif artifact_type == "provider-operation-receipt":
        script, verb = "validate_provider_operation.py", "validate-receipt"
    else:
        raise RenderError(f"{artifact_type} has no standalone semantic validator and cannot be labelled validated")
    return command + [str(ROOT / "scripts" / script), verb, str(artifact), "--bundle", str(bundle)]


def validate(
    artifact_type: str,
    artifact: Path,
    bundle: Path,
    payload: dict[str, Any],
    as_of: str | None,
) -> str:
    completed = subprocess.run(
        validator_command(artifact_type, artifact, bundle, payload, as_of),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
        raise RenderError(f"artifact is not validated; renderer stopped: {detail}")
    return completed.stdout.strip()


def scalar(value: object) -> str:
    if value is None:
        return "Not supplied"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (str, int, float)):
        return str(value)
    if isinstance(value, list):
        if not value:
            return "None"
        if all(isinstance(item, (str, int, float, bool)) or item is None for item in value):
            return ", ".join(scalar(item) for item in value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def markdown(value: object) -> str:
    return scalar(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def heading(value: object) -> str:
    return markdown(value).replace("\\", "\\\\").replace("#", "\\#").replace("`", "\\`")


def artifact_id(payload: dict[str, Any]) -> str:
    for field in IDENTITY_FIELDS:
        value = payload.get(field)
        if isinstance(value, str):
            return value
    return "unidentified-artifact"


def item_title(item: dict[str, Any], index: int) -> str:
    for field in (
        "title",
        "action_id",
        "finding_id",
        "query_id",
        "claim_id",
        "observation_id",
        "recommendation_id",
        "entity_id",
        "fact_id",
        "gap_id",
        "score_id",
        "check_id",
        "row_id",
        "node_id",
        "edge_id",
        "feature_id",
        "crawler_id",
        "change_id",
        "capability_id",
        "declined_id",
        "kind",
    ):
        value = item.get(field)
        if isinstance(value, str) and value:
            return heading(value)
    return f"Item {index + 1}"


def important_fields(item: dict[str, Any]) -> list[str]:
    priority = (
        "finding_id",
        "action_id",
        "target_id",
        "query_id",
        "claim_id",
        "observation_id",
        "title",
        "text",
        "claim",
        "observation",
        "description",
        "classification",
        "severity",
        "category",
        "candidate_owner",
        "owner_skill",
        "priority",
        "risk",
        "risk_flags",
        "confidence",
        "desired_outcome",
        "verification_method",
        "source_url",
        "raw_evidence_ref",
        "raw_answer_ref",
        "engine",
        "surface",
        "locale",
        "access_status",
        "metric",
        "result",
        "current_value",
        "delta",
        "limitations",
    )
    selected = [field for field in priority if field in item]
    if selected:
        return selected
    return [field for field in item if field not in {"schema_version"}][:12]


def render_scope(payload: dict[str, Any]) -> list[str]:
    scope = payload.get("scope")
    if scope is None:
        return []
    lines = ["## Scope", ""]
    if isinstance(scope, str):
        lines.extend([scope, ""])
        return lines
    if isinstance(scope, dict):
        objective = scope.get("objective")
        if objective:
            lines.extend([str(objective), ""])
        for key, value in scope.items():
            if key != "objective":
                lines.append(f"- **{key.replace('_', ' ').title()}:** {markdown(value)}")
        lines.append("")
        return lines
    lines.extend([f"`{markdown(scope)}`", ""])
    return lines


def render_collection(name: str, items: list[Any], max_items: int) -> list[str]:
    if not items:
        return []
    label = name.replace("_", " ").title()
    lines = [f"## {label} ({len(items)})", ""]
    visible = items[:max_items]
    for index, item in enumerate(visible):
        if isinstance(item, dict):
            lines.extend([f"### {item_title(item, index)}", ""])
            for field in important_fields(item):
                lines.append(f"- **{field.replace('_', ' ').title()}:** {markdown(item[field])}")
            lines.append("")
        else:
            lines.append(f"- {markdown(item)}")
    if len(items) > len(visible):
        lines.extend(["", f"_{len(items) - len(visible)} additional item(s) omitted by `--max-items`._", ""])
    return lines


def render_report(
    artifact_type: str,
    artifact: Path,
    payload: dict[str, Any],
    validation: str,
    as_of: str | None,
    max_items: int,
) -> str:
    identifier = artifact_id(payload)
    checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
    lines = [
        f"# {artifact_type.replace('-', ' ').title()}: {heading(identifier)}",
        "",
        "> Status: **Validated** - the owning suite validator passed before this report was rendered.",
        "",
        "## Artifact metadata",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Artifact type | `{artifact_type}` |",
        f"| Artifact ID | `{markdown(identifier)}` |",
        f"| Schema version | `{markdown(payload.get('schema_version', 'not-versioned'))}` |",
        f"| Created at | {markdown(payload.get('created_at', payload.get('recorded_at')))} |",
        f"| Producer | {markdown(payload.get('producer_skill'))} |",
        f"| Mode | {markdown(payload.get('mode'))} |",
        f"| SHA-256 | `{checksum}` |",
    ]
    if as_of:
        lines.append(f"| Validation as-of | {markdown(as_of)} |")
    lines.extend(["", f"Validator result: `{markdown(validation)}`", ""])
    lines.extend(render_scope(payload))

    counts = [(name, len(payload[name])) for name in COLLECTIONS if isinstance(payload.get(name), list)]
    if counts:
        lines.extend(["## Collection summary", "", "| Collection | Count |", "| --- | ---: |"])
        lines.extend(f"| {name.replace('_', ' ').title()} | {count} |" for name, count in counts)
        lines.append("")

    for name in COLLECTIONS:
        items = payload.get(name)
        if isinstance(items, list):
            lines.extend(render_collection(name, items, max_items))

    limitations = payload.get("limitations")
    if isinstance(limitations, list) and limitations:
        lines.extend(["## Artifact limitations", ""])
        lines.extend(f"- {markdown(item)}" for item in limitations)
        lines.append("")
    elif "limitations" in payload:
        lines.extend(["## Artifact limitations", "", "- None declared.", ""])

    lines.extend(
        [
            "## Interpretation boundary",
            "",
            "Validation establishes contract and semantic consistency for the supplied bundle. It does not prove ranking, indexing, retrieval, citation, traffic, revenue, or conversion outcomes.",
            "",
        ]
    )
    return "\n".join(lines)


def atomic_write(path: Path, content: str) -> None:
    temporary: Path | None = None
    try:
        current = path.parent
        while current != current.parent:
            if current.exists() and is_reparse(current):
                raise RenderError(f"report output must not traverse a symlink or reparse point: {current}")
            current = current.parent
        path.parent.mkdir(parents=True, exist_ok=True)
        if is_reparse(path) or (path.exists() and not path.is_file()):
            raise RenderError(f"report output must be a regular non-reparse file: {path}")
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise RenderError(f"cannot atomically write report output: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an SEO-suite artifact and render a bounded Markdown report.")
    parser.add_argument("--json", action="store_true", help="Emit one stable JSON result object.")
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument(
        "--type",
        choices=(
            "research-pack",
            "query-corpus",
            "optimization-brief",
            "visibility-run",
            "seo-performance-run",
            "site-graph",
            "platform-controls",
            "seo-findings",
            "action-plan",
            "provider-operation-receipt",
        ),
        dest="artifact_type",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--as-of", help="Pinned UTC timestamp/date for freshness or lifecycle validation.")
    parser.add_argument("--max-items", type=int, default=50, help="Maximum rendered items per collection (1-200).")
    parser.add_argument("--overwrite", action="store_true", help="Explicitly replace the exact Markdown output file.")
    args = parser.parse_args()

    try:
        if not 1 <= args.max_items <= 200:
            raise RenderError("--max-items must be between 1 and 200")
        bundle = args.bundle.absolute()
        artifact = args.artifact.absolute()
        errors: list[str] = []
        safe_artifact = resolve_artifact_in_bundle(artifact, bundle, errors)
        if safe_artifact is None or errors:
            raise RenderError("; ".join(errors))
        payload = load_object(safe_artifact)
        artifact_type = args.artifact_type or infer_type(payload)
        if args.out.absolute() == safe_artifact.absolute():
            raise RenderError("report output must differ from the immutable source artifact")
        if is_reparse(args.out):
            raise RenderError(f"report output must not be a symlink or reparse point: {args.out}")
        if args.out.exists() and not args.overwrite:
            raise RenderError(f"refusing to overwrite existing report: {args.out}")
        if args.out.exists() and args.out.is_dir():
            raise RenderError(f"report output is a directory: {args.out}")
        validation = validate(artifact_type, safe_artifact, bundle, payload, args.as_of)
        report = render_report(artifact_type, safe_artifact, payload, validation, args.as_of, args.max_items)
        atomic_write(args.out, report)
        result = {
            "status": "validated",
            "artifact_type": artifact_type,
            "artifact": str(safe_artifact),
            "report": str(args.out),
            "sha256": hashlib.sha256(safe_artifact.read_bytes()).hexdigest(),
        }
        if args.json:
            print(json.dumps(result, sort_keys=True))
        else:
            print(f"PASS: validated {artifact_type} and wrote Markdown report to {args.out}")
        return 0
    except RenderError as exc:
        if args.json:
            print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
