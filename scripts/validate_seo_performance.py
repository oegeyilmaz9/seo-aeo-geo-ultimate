from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from bundle_safety import resolve_artifact_in_bundle, resolve_relative
from validate_ai_search_research import validate_schema_instance


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "manifests" / "artifact-schemas" / "seo-performance-run.schema.json"
CAUSAL_RE = re.compile(r"\b(?:caused|drove|led to|resulted in|because of|thanks to|produced uplift|responsible for)\b", re.I)
DIMENSION_FIELDS = {"query", "page", "country", "device", "search_appearance", "date"}
METRIC_FIELDS = {"clicks", "impressions", "ctr", "average_position", "organic_sessions", "conversions", "revenue"}


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


def derived_metric(
    run: dict[str, Any], metric: object, record_ids: object, field: str, errors: list[str]
) -> float | int | None:
    if (
        not isinstance(metric, str)
        or not isinstance(record_ids, list)
        or not record_ids
        or any(not isinstance(value, str) or not value for value in record_ids)
    ):
        errors.append(f"{field} must contain non-empty string record IDs")
        return None
    wanted = set(record_ids)
    if metric in {"clicks", "impressions", "ctr", "average_position", "organic_sessions", "conversions", "revenue"}:
        records = {
            row.get("row_id"): row
            for row in run.get("rows", [])
            if isinstance(row, dict) and isinstance(row.get("row_id"), str)
        }
        missing = sorted(wanted - set(records))
        if missing:
            errors.append(f"{field} does not resolve row IDs: {missing}")
            return None
        rows = [records[value] for value in record_ids]
        if metric == "ctr":
            clicks = [row.get("clicks") for row in rows]
            impressions = [row.get("impressions") for row in rows]
            if not all(isinstance(value, int) and not isinstance(value, bool) for value in [*clicks, *impressions]):
                return None
            denominator = sum(impressions)
            return None if denominator == 0 else sum(clicks) / denominator
        if metric == "average_position":
            values = [row.get("average_position") for row in rows]
            weights = [row.get("impressions") for row in rows]
            if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
                return None
            if not all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in weights):
                return None
            denominator = sum(weights)
            return None if denominator == 0 else sum(float(value) * weight for value, weight in zip(values, weights)) / denominator
        values = [row.get(metric) for row in rows]
        return sum(values) if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values) else None
    if metric == "indexed_urls":
        records: dict[str, dict[str, Any]] = {}
        for row in run.get("indexation", []):
            if not isinstance(row, dict) or not isinstance(row.get("target_url"), str):
                continue
            key = row["target_url"]
            if key in records:
                errors.append(f"{field} indexation target is ambiguous: {key}")
            records[key] = row
        missing = sorted(wanted - set(records))
        if missing:
            errors.append(f"{field} does not resolve indexation targets: {missing}")
            return None
        return sum(1 for value in record_ids if records[value].get("status") == "indexed")
    if metric in {"lcp", "inp", "cls"}:
        records: dict[str, dict[str, Any]] = {}
        for row in run.get("web_vitals", []):
            if not isinstance(row, dict) or row.get("metric") != metric:
                continue
            key = f"{row.get('target')}|{row.get('form_factor')}|{metric}"
            if key in records:
                errors.append(f"{field} Web Vital key is ambiguous: {key}")
            records[key] = row
        missing = sorted(wanted - set(records))
        if missing:
            errors.append(f"{field} does not resolve Web Vital keys: {missing}")
            return None
        values = [records[value].get("value") for value in record_ids]
        return sum(values) / len(values) if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values) else None
    return None


def same_number(left: object, right: object) -> bool:
    if left is None or right is None:
        return left is right
    return (
        isinstance(left, (int, float)) and not isinstance(left, bool)
        and isinstance(right, (int, float)) and not isinstance(right, bool)
        and math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
    )


def cohort_signature(
    run: dict[str, Any], metric: object, record_ids: object, field: str, errors: list[str]
) -> tuple[object, ...] | None:
    if not isinstance(metric, str) or not isinstance(record_ids, list) or any(not isinstance(value, str) for value in record_ids):
        return None
    if metric in {"clicks", "impressions", "ctr", "average_position", "organic_sessions", "conversions", "revenue"}:
        records = {
            row.get("row_id"): row
            for row in run.get("rows", [])
            if isinstance(row, dict) and isinstance(row.get("row_id"), str)
        }
        if any(value not in records for value in record_ids):
            return None
        dimensions = [value for value in run.get("dimensions", []) if isinstance(value, str)]
        window = run.get("window", {})
        start = parse_time(window.get("start"), f"{field}.window.start", errors) if isinstance(window, dict) else None
        rows: list[tuple[object, ...]] = []
        for record_id in record_ids:
            row = records[record_id]
            values: list[object] = []
            for dimension in dimensions:
                value: object = row.get(dimension)
                if dimension == "date" and value is not None:
                    observed = parse_time(value, f"{field}.{record_id}.date", errors)
                    value = (observed - start).total_seconds() if observed is not None and start is not None else None
                values.append((dimension, value))
            rows.append(tuple(values))
        return tuple(sorted(rows, key=repr))
    if metric == "indexed_urls":
        return tuple(sorted(record_ids))
    if metric in {"lcp", "inp", "cls"}:
        return tuple(sorted(record_ids))
    return None


def validate_run(path: Path, bundle: Path) -> None:
    errors: list[str] = []
    artifact = resolve_artifact_in_bundle(path, bundle, errors)
    if artifact is None or errors:
        fail(errors)
    try:
        payload = load(artifact)
    except (OSError, json.JSONDecodeError):
        fail(["seo-performance-run.json is not valid JSON"])

    schema = load(SCHEMA_PATH)
    registry: dict[str, dict[str, Any]] = {schema["$id"]: schema}
    for name, definition in schema.get("$defs", {}).items():
        if isinstance(definition, dict):
            registry[f"#/$defs/{name}"] = definition
    validate_schema_instance(payload, schema, registry, "$", errors)
    if not isinstance(payload, dict):
        fail(errors or ["seo-performance-run.json must contain an object"])

    created_at = parse_time(payload.get("created_at"), "$.created_at", errors)
    window = payload.get("window", {})
    start = parse_time(window.get("start"), "$.window.start", errors) if isinstance(window, dict) else None
    end = parse_time(window.get("end"), "$.window.end", errors) if isinstance(window, dict) else None
    if start is not None and end is not None and start >= end:
        errors.append("measurement window start must be before end")
    if created_at is not None and end is not None and end > created_at:
        errors.append("measurement window cannot end after run creation")

    raw_path = resolve_relative(bundle, payload.get("raw_source_ref"), "raw_source_ref", errors)
    if raw_path is None or not raw_path.is_file():
        errors.append("raw source export does not exist")
    elif digest(raw_path) != payload.get("raw_source_sha256"):
        errors.append("raw source export hash mismatch")
    else:
        try:
            raw_source = load(raw_path)
        except (OSError, json.JSONDecodeError):
            raw_source = None
        raw_keys = {"schema_version", "source_type", "property", "search_type", "filters", "export_method", "window", "dimensions", "rows", "indexation", "web_vitals"}
        if not isinstance(raw_source, dict) or set(raw_source) != raw_keys or raw_source.get("schema_version") != "1.0.0":
            errors.append("raw source must be a versioned normalized export envelope")
        elif any(raw_source.get(field) != payload.get(field) for field in ("source_type", "property", "search_type", "filters", "export_method", "window", "dimensions", "rows", "indexation", "web_vitals")):
            errors.append("normalized metrics do not match the hash-pinned raw source envelope")

    corpus_fields = (payload.get("query_corpus_id"), payload.get("query_corpus_ref"), payload.get("query_corpus_sha256"))
    bound_corpus: dict[str, Any] | None = None
    if any(value is None for value in corpus_fields) and any(value is not None for value in corpus_fields):
        errors.append("query corpus ID, reference, and hash must all be null or present")
    elif all(value is not None for value in corpus_fields):
        corpus_path = resolve_relative(bundle, payload.get("query_corpus_ref"), "query_corpus_ref", errors)
        if corpus_path is None or not corpus_path.is_file() or digest(corpus_path) != payload.get("query_corpus_sha256"):
            errors.append("query corpus hash mismatch")
        else:
            corpus = load(corpus_path)
            if not isinstance(corpus, dict) or corpus.get("corpus_id") != payload.get("query_corpus_id"):
                errors.append("query corpus identity mismatch")
            else:
                bound_corpus = corpus
                corpus_created = parse_time(corpus.get("created_at"), "query_corpus.created_at", errors)
                if corpus_created is not None and created_at is not None and corpus_created > created_at:
                    errors.append("query corpus cannot be newer than the performance run")
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "validate_query_corpus.py"),
                        "validate-corpus",
                        str(corpus_path),
                        "--bundle",
                        str(bundle),
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                if completed.returncode != 0:
                    errors.append(f"query corpus semantic validation failed: {(completed.stderr or completed.stdout).strip()}")

    dimensions = set(payload.get("dimensions", [])) if isinstance(payload.get("dimensions"), list) else set()
    if not any(payload.get(collection) for collection in ("rows", "indexation", "web_vitals")):
        errors.append("a performance run requires at least one measured row, indexation observation, or Web Vital")
    row_ids: set[str] = set()
    for index, row in enumerate(payload.get("rows", []) if isinstance(payload.get("rows"), list) else []):
        if not isinstance(row, dict):
            continue
        row_id = row.get("row_id")
        if isinstance(row_id, str) and row_id in row_ids:
            errors.append(f"rows[{index}].row_id is duplicated")
        elif isinstance(row_id, str):
            row_ids.add(row_id)
        if not any(row.get(field) is not None for field in METRIC_FIELDS):
            errors.append(f"rows[{index}] must contain at least one measured metric")
        for field in DIMENSION_FIELDS:
            if field not in dimensions and row.get(field) is not None:
                errors.append(f"rows[{index}].{field} is populated but not declared as a dimension")
        row_date = parse_time(row.get("date"), f"rows[{index}].date", errors) if row.get("date") is not None else None
        if row_date is not None and start is not None and end is not None and not (start <= row_date < end):
            errors.append(f"rows[{index}].date falls outside the measurement window")
        for field in ("clicks", "impressions", "organic_sessions", "conversions", "revenue", "average_position"):
            value = row.get(field)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value < 0:
                errors.append(f"rows[{index}].{field} cannot be negative")
        clicks, impressions, ctr = row.get("clicks"), row.get("impressions"), row.get("ctr")
        if isinstance(clicks, int) and isinstance(impressions, int):
            expected = None if impressions == 0 else clicks / impressions
            if expected is None and ctr is not None:
                errors.append(f"rows[{index}].ctr must be null when impressions are zero")
            elif expected is not None and (not isinstance(ctr, (int, float)) or not math.isclose(float(ctr), expected, rel_tol=1e-9, abs_tol=1e-12)):
                errors.append(f"rows[{index}].ctr does not equal clicks/impressions")
        if isinstance(ctr, (int, float)) and not 0 <= ctr <= 1:
            errors.append(f"rows[{index}].ctr must be between zero and one")

    if bound_corpus is not None and "query" in dimensions:
        declared_queries = {
            query.get("text")
            for query in bound_corpus.get("queries", [])
            if isinstance(query, dict) and query.get("query_type") == "observed_search_query"
        }
        for index, row in enumerate(payload.get("rows", []) if isinstance(payload.get("rows"), list) else []):
            if isinstance(row, dict) and row.get("query") is not None and row.get("query") not in declared_queries:
                errors.append(f"rows[{index}].query is outside the bound observed-search Query Corpus")

    for index, item in enumerate(payload.get("indexation", []) if isinstance(payload.get("indexation"), list) else []):
        observed = parse_time(item.get("observed_at"), f"indexation[{index}].observed_at", errors) if isinstance(item, dict) else None
        if created_at is not None and observed is not None and observed > created_at:
            errors.append(f"indexation[{index}] was observed after run creation")
    for index, item in enumerate(payload.get("web_vitals", []) if isinstance(payload.get("web_vitals"), list) else []):
        observed = parse_time(item.get("observed_at"), f"web_vitals[{index}].observed_at", errors) if isinstance(item, dict) else None
        if created_at is not None and observed is not None and observed > created_at:
            errors.append(f"web_vitals[{index}] was observed after run creation")
        if isinstance(item, dict) and isinstance(item.get("value"), (int, float)) and item.get("value") < 0:
            errors.append(f"web_vitals[{index}].value cannot be negative")

    quality = payload.get("data_quality", {})
    if isinstance(quality, dict):
        uncertain = quality.get("sampling_status") != "none" or quality.get("anonymized_queries") in {"excluded", "unknown"} or quality.get("canonical_aggregation") == "unknown"
        if uncertain and not quality.get("notes") and not payload.get("limitations"):
            errors.append("sampling, anonymized-query, or aggregation uncertainty requires a note or limitation")

    mode = payload.get("mode")
    prior_fields = (payload.get("prior_run_id"), payload.get("prior_run_ref"), payload.get("prior_run_sha256"))
    non_comparable_inputs = False
    prior: dict[str, Any] | None = None
    if mode == "baseline":
        if any(value is not None for value in prior_fields):
            errors.append("baseline prior-run fields must be null")
        if payload.get("drift"):
            errors.append("baseline run must not contain drift")
    elif mode == "comparison":
        if not payload.get("drift"):
            errors.append("comparison mode requires at least one record-bound drift row")
        if any(value is None for value in prior_fields):
            errors.append("comparison requires a hash-pinned prior run")
        else:
            prior_path = resolve_relative(bundle, payload.get("prior_run_ref"), "prior_run_ref", errors)
            if prior_path is None or not prior_path.is_file() or digest(prior_path) != payload.get("prior_run_sha256"):
                errors.append("prior run hash mismatch")
            elif prior_path.resolve() == artifact.resolve():
                errors.append("prior run cannot reference itself")
            else:
                prior = load(prior_path)
                if not isinstance(prior, dict) or prior.get("run_id") != payload.get("prior_run_id"):
                    errors.append("prior run identity mismatch")
                else:
                    prior_created = parse_time(prior.get("created_at"), "prior.created_at", errors)
                    if prior_created is not None and created_at is not None and prior_created >= created_at:
                        errors.append("prior run must be older than comparison run")
                    prior_window = prior.get("window", {})
                    prior_start = parse_time(prior_window.get("start"), "prior.window.start", errors) if isinstance(prior_window, dict) else None
                    prior_end = parse_time(prior_window.get("end"), "prior.window.end", errors) if isinstance(prior_window, dict) else None
                    current_duration = end - start if start is not None and end is not None else None
                    prior_duration = prior_end - prior_start if prior_start is not None and prior_end is not None else None
                    non_comparable_inputs = any([
                        prior.get("property") != payload.get("property"),
                        prior.get("source_type") != payload.get("source_type"),
                        prior.get("search_type") != payload.get("search_type"),
                        prior.get("filters") != payload.get("filters"),
                        prior.get("export_method") != payload.get("export_method"),
                        prior.get("query_corpus_sha256") != payload.get("query_corpus_sha256"),
                        prior.get("dimensions") != payload.get("dimensions"),
                        prior.get("data_quality") != payload.get("data_quality"),
                        prior_duration != current_duration,
                    ])
                    visited = {value for value in os.environ.get("SEO_PERFORMANCE_VISITED", "").split(",") if value}
                    prior_hash = digest(prior_path)
                    if prior_hash in visited:
                        errors.append("prior run lineage contains a cycle")
                    else:
                        env = os.environ.copy()
                        env["SEO_PERFORMANCE_VISITED"] = ",".join(sorted(visited | {digest(artifact), prior_hash}))
                        completed = subprocess.run(
                            [sys.executable, str(Path(__file__).resolve()), "validate-run", str(prior_path), "--bundle", str(bundle)],
                            text=True,
                            capture_output=True,
                            check=False,
                            env=env,
                        )
                        if completed.returncode != 0:
                            errors.append(f"prior run semantic validation failed: {(completed.stderr or completed.stdout).strip()}")

    drift_ids: set[str] = set()
    for index, drift in enumerate(payload.get("drift", []) if isinstance(payload.get("drift"), list) else []):
        if not isinstance(drift, dict):
            continue
        drift_id = drift.get("drift_id")
        if isinstance(drift_id, str) and drift_id in drift_ids:
            errors.append(f"drift[{index}].drift_id is duplicated")
        elif isinstance(drift_id, str):
            drift_ids.add(drift_id)
        prior_value, current_value, delta = drift.get("prior_value"), drift.get("current_value"), drift.get("delta")
        if prior is not None:
            expected_prior = derived_metric(prior, drift.get("metric"), drift.get("prior_record_ids"), f"drift[{index}].prior_record_ids", errors)
            expected_current = derived_metric(payload, drift.get("metric"), drift.get("current_record_ids"), f"drift[{index}].current_record_ids", errors)
            if not same_number(prior_value, expected_prior) or not same_number(current_value, expected_current):
                errors.append(f"drift[{index}] values do not derive from the declared prior/current records")
            prior_cohort = cohort_signature(prior, drift.get("metric"), drift.get("prior_record_ids"), f"drift[{index}].prior_cohort", errors)
            current_cohort = cohort_signature(payload, drift.get("metric"), drift.get("current_record_ids"), f"drift[{index}].current_cohort", errors)
            cohort_changed = prior_cohort != current_cohort
        else:
            expected_prior = expected_current = None
            cohort_changed = True
        numeric = all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in (prior_value, current_value, delta))
        if numeric and not math.isclose(delta, current_value - prior_value, rel_tol=1e-12, abs_tol=1e-12):
            errors.append(f"drift[{index}].delta arithmetic mismatch")
        if not numeric and any(value is not None for value in (prior_value, current_value, delta)):
            errors.append(f"drift[{index}] values must be all numeric or all null")
        drift_non_comparable = non_comparable_inputs or cohort_changed or expected_prior is None or expected_current is None or prior_value is None or current_value is None
        if (drift_non_comparable or drift.get("comparable") is False) and not drift.get("warning"):
            errors.append(f"drift[{index}] non-comparable drift requires a warning")
        if drift_non_comparable and drift.get("comparable") is True:
            errors.append(f"drift[{index}] changed source context, selected cohort, or null value cannot be comparable")

    text_values = list(payload.get("limitations", []))
    if isinstance(quality, dict):
        text_values.extend(quality.get("notes", []))
    text_values.extend(item.get("warning") or "" for item in payload.get("drift", []) if isinstance(item, dict))
    if any(isinstance(value, str) and CAUSAL_RE.search(value) for value in text_values):
        errors.append("causal language is not allowed in observational SEO performance runs")

    if errors:
        fail(errors)
    print("PASS: SEO performance provenance, arithmetic, quality, and comparability")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("validate-run")
    command.add_argument("artifact", type=Path)
    command.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    validate_run(args.artifact, args.bundle)


if __name__ == "__main__":
    main()
