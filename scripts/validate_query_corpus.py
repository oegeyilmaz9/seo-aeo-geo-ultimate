from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from bundle_safety import resolve_artifact_in_bundle, resolve_relative
from validate_ai_search_research import validate_schema_instance


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "manifests" / "artifact-schemas" / "query-corpus.schema.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_time(value: object, field: str, errors: list[str]) -> dt.datetime | None:
    if not isinstance(value, str):
        errors.append(f"{field} must be a timestamp")
        return None
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        errors.append(f"{field} is not a valid timestamp")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field} must include a timezone")
        return None
    return parsed


def fail(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)


def has_parent_cycle(parents: dict[str, str]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        parent = parents.get(node)
        if parent is not None and visit(parent):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in parents)


def validate_corpus(path: Path, bundle: Path) -> None:
    errors: list[str] = []
    artifact = resolve_artifact_in_bundle(path, bundle, errors)
    if artifact is None or errors:
        fail(errors)
    try:
        payload = load(artifact)
    except (OSError, json.JSONDecodeError):
        fail(["query-corpus.json is not valid JSON"])

    schema = load(SCHEMA_PATH)
    registry: dict[str, dict[str, Any]] = {schema["$id"]: schema}
    for name, definition in schema.get("$defs", {}).items():
        if isinstance(definition, dict):
            registry[f"#/$defs/{name}"] = definition
    validate_schema_instance(payload, schema, registry, "$", errors)
    if not isinstance(payload, dict):
        fail(errors or ["query-corpus.json must contain an object"])

    created_at = parse_time(payload.get("created_at"), "$.created_at", errors)
    frozen_at = parse_time(payload.get("frozen_at"), "$.frozen_at", errors)
    if created_at is not None and frozen_at is not None and frozen_at > created_at:
        errors.append("frozen_at must not be later than created_at")

    research: dict[str, Any] = {}
    research_id, research_sha = payload.get("research_id"), payload.get("research_sha256")
    if (research_id is None) != (research_sha is None):
        errors.append("research_id and research_sha256 must both be null or both be present")
    elif research_id is not None:
        research_path = bundle / "research-pack.json"
        if not research_path.is_file() or digest(research_path) != research_sha:
            errors.append("hash-pinned research-pack.json is required when research_id is present")
        else:
            candidate = load(research_path)
            if not isinstance(candidate, dict) or candidate.get("research_id") != research_id:
                errors.append("research_id does not match research-pack.json")
            else:
                research = candidate
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "validate_ai_search_research.py"),
                        "validate-pack",
                        str(research_path),
                        "--bundle",
                        str(bundle),
                        "--now",
                        str(payload.get("created_at")),
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                if completed.returncode != 0:
                    errors.append(f"research-pack semantic validation failed: {(completed.stderr or completed.stdout).strip()}")

    queries = payload.get("queries", [])
    query_by_id: dict[str, dict[str, Any]] = {}
    parents: dict[str, str] = {}
    conversation_turns: set[tuple[str, int]] = set()
    for index, query in enumerate(queries if isinstance(queries, list) else []):
        if not isinstance(query, dict):
            continue
        query_id = query.get("query_id")
        if isinstance(query_id, str):
            if query_id in query_by_id:
                errors.append(f"queries[{index}].query_id is duplicated")
            query_by_id[query_id] = query
        source = query.get("source", {})
        if isinstance(source, dict):
            source_time = parse_time(source.get("observed_at"), f"queries[{index}].source.observed_at", errors)
            if frozen_at is not None and source_time is not None and source_time > frozen_at:
                errors.append(f"queries[{index}] source was observed after the corpus was frozen")
            source_ref = source.get("source_ref")
            source_sha = source.get("source_sha256")
            source_url = source.get("source_url")
            if source.get("source_kind") != "editorial_hypothesis" and source_ref is None and source_url is None:
                errors.append(f"queries[{index}] non-hypothesis source requires source_url or source_ref")
            if (source_ref is None) != (source_sha is None):
                errors.append(f"queries[{index}] source_ref and source_sha256 must both be null or present")
            elif source_ref is not None:
                resolved = resolve_relative(bundle, source_ref, f"queries[{index}].source.source_ref", errors)
                if resolved is None or not resolved.is_file() or digest(resolved) != source_sha:
                    errors.append(f"queries[{index}] source evidence hash mismatch")

        coverage = query.get("coverage", {})
        if isinstance(coverage, dict):
            evidence_ref = coverage.get("evidence_ref")
            evidence_sha = coverage.get("evidence_sha256")
            if (evidence_ref is None) != (evidence_sha is None):
                errors.append(f"queries[{index}] coverage evidence_ref and evidence_sha256 must both be null or present")
            elif evidence_ref is not None:
                resolved = resolve_relative(bundle, evidence_ref, f"queries[{index}].coverage.evidence_ref", errors)
                if resolved is None or not resolved.is_file() or digest(resolved) != evidence_sha:
                    errors.append(f"queries[{index}] coverage evidence hash mismatch")
            state = coverage.get("state")
            current = coverage.get("current_urls", [])
            target = coverage.get("target_url")
            competing = coverage.get("competing_urls", [])
            if state != "unknown" and evidence_ref is None:
                errors.append(f"queries[{index}] asserted coverage state requires hash-pinned evidence")
            if state == "covered":
                if not isinstance(current, list) or not current:
                    errors.append(f"queries[{index}] covered coverage requires at least one current URL")
                if not isinstance(target, str) or target not in current:
                    errors.append(f"queries[{index}] covered coverage target_url must identify a current URL")
                if isinstance(competing, list) and competing:
                    errors.append(f"queries[{index}] covered coverage must not declare competing URLs")
            elif state == "gap":
                if isinstance(current, list) and current:
                    errors.append(f"queries[{index}] gap coverage must not declare current URLs")
                if isinstance(competing, list) and competing:
                    errors.append(f"queries[{index}] gap coverage must not declare competing URLs")
            elif state == "cannibalized":
                if not isinstance(current, list) or len(current) < 2:
                    errors.append(f"queries[{index}] cannibalized coverage requires at least two current URLs")
                if not isinstance(competing, list) or len(competing) < 2:
                    errors.append(f"queries[{index}] cannibalized coverage requires at least two competing URLs")
                elif isinstance(current, list) and any(url not in current for url in competing):
                    errors.append(f"queries[{index}] cannibalized competing URLs must be current URLs")
                if target is not None and isinstance(current, list) and target not in current:
                    errors.append(f"queries[{index}] cannibalized target_url must be null or identify a current URL")
            elif state == "unknown":
                if any(isinstance(value, list) and value for value in (current, competing)) or target is not None:
                    errors.append(f"queries[{index}] unknown coverage must not assert URLs")

        demand = query.get("demand", {})
        if isinstance(demand, dict):
            metrics = (demand.get("monthly_volume"), demand.get("trend_index"), demand.get("difficulty"))
            if demand.get("status") == "unavailable":
                if any(value is not None for value in metrics) or any(demand.get(field) is not None for field in ("provider", "observed_at", "source_url", "source_ref", "source_sha256")):
                    errors.append(f"queries[{index}] unavailable demand must not invent provider, date, source, or metrics")
            else:
                if not isinstance(demand.get("provider"), str) or not demand.get("provider", "").strip():
                    errors.append(f"queries[{index}] available demand requires provider")
                demand_time = parse_time(demand.get("observed_at"), f"queries[{index}].demand.observed_at", errors)
                if frozen_at is not None and demand_time is not None and demand_time > frozen_at:
                    errors.append(f"queries[{index}] demand was observed after the corpus was frozen")
                demand_ref, demand_sha = demand.get("source_ref"), demand.get("source_sha256")
                if (demand_ref is None) != (demand_sha is None):
                    errors.append(f"queries[{index}] demand source_ref and source_sha256 must both be null or present")
                elif demand_ref is not None:
                    resolved = resolve_relative(bundle, demand_ref, f"queries[{index}].demand.source_ref", errors)
                    if resolved is None or not resolved.is_file() or digest(resolved) != demand_sha:
                        errors.append(f"queries[{index}] demand source evidence hash mismatch")
                if demand.get("source_url") is None and demand_ref is None:
                    errors.append(f"queries[{index}] available demand requires a source URL or hash-pinned source file")
            for value in metrics:
                if isinstance(value, (int, float)) and not isinstance(value, bool) and value < 0:
                    errors.append(f"queries[{index}] demand metrics cannot be negative")

        query_type = query.get("query_type")
        parent = query.get("parent_query_id")
        if isinstance(query_id, str) and isinstance(parent, str):
            parents[query_id] = parent
        if query_type == "executed_subquery":
            if not isinstance(parent, str):
                errors.append(f"queries[{index}] executed_subquery requires parent_query_id")
            if query.get("engine") is None or query.get("surface") is None:
                errors.append(f"queries[{index}] executed_subquery requires engine and surface")
            if not isinstance(source, dict) or source.get("source_kind") != "direct_observation":
                errors.append(f"queries[{index}] executed_subquery requires direct_observation provenance")
        elif query_type == "observed_search_query":
            if not isinstance(source, dict) or source.get("source_kind") not in {"first_party", "third_party_estimate", "direct_observation"}:
                errors.append(f"queries[{index}] observed_search_query requires first-party, third-party, or direct-observation provenance")
        conversation_id, turn_index = query.get("conversation_id"), query.get("turn_index")
        if (conversation_id is None) != (turn_index is None):
            errors.append(f"queries[{index}] conversation_id and turn_index must both be present or both be null")
        if isinstance(conversation_id, str) and isinstance(turn_index, int) and not isinstance(turn_index, bool):
            if turn_index < 0:
                errors.append(f"queries[{index}].turn_index cannot be negative")
            key = (conversation_id, turn_index)
            if key in conversation_turns:
                errors.append(f"queries[{index}] duplicates a conversation turn")
            conversation_turns.add(key)

    for query_id, parent in parents.items():
        if parent not in query_by_id:
            errors.append(f"query {query_id} parent_query_id does not resolve")
        elif parent == query_id:
            errors.append(f"query {query_id} cannot parent itself")
        elif query_by_id.get(query_id, {}).get("query_type") == "executed_subquery" and query_by_id[parent].get("query_type") not in {"ai_prompt", "executed_subquery"}:
            errors.append(f"query {query_id} executed_subquery parent must be an ai_prompt or executed_subquery")
    if has_parent_cycle(parents):
        errors.append("query parent graph contains a cycle")

    if research:
        entity_ids = {item.get("entity_id") for item in research.get("entities", []) if isinstance(item, dict)}
        fact_ids = {item.get("fact_id") for item in research.get("ground_truth", []) if isinstance(item, dict)}
        research_queries = {item.get("query_id"): item for item in research.get("queries", []) if isinstance(item, dict)}
        for index, query in enumerate(queries if isinstance(queries, list) else []):
            if not isinstance(query, dict):
                continue
            source_query = research_queries.get(query.get("query_id"))
            if query.get("query_type") != "executed_subquery":
                if not isinstance(source_query, dict):
                    errors.append(f"queries[{index}] base query_id must resolve to the Research Pack")
                elif query.get("text") != source_query.get("text") or query.get("locale") != source_query.get("locale"):
                    errors.append(f"queries[{index}] text/locale does not match Research Pack")
            if any(value not in entity_ids for value in query.get("target_entities", [])):
                errors.append(f"queries[{index}].target_entities must resolve to Research Pack entities")
            if any(value not in fact_ids for value in query.get("fact_ids", [])):
                errors.append(f"queries[{index}].fact_ids must resolve to Research Pack ground truth")

    if errors:
        fail(errors)
    print("PASS: query corpus provenance, hierarchy, demand, and coverage")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("validate-corpus")
    command.add_argument("artifact", type=Path)
    command.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    validate_corpus(args.artifact, args.bundle)


if __name__ == "__main__":
    main()
