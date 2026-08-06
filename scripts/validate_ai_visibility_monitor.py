from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bundle_safety import resolve_artifact_in_bundle, resolve_relative
from validate_ai_search_research import validate_schema_instance
from validate_seo_aeo import parse_time


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "manifests" / "artifact-schemas"
TRACKING = {"gclid", "fbclid", "msclkid"}
CAUSAL_RE = re.compile(
    r"\b(?<!no )(?<!not )(?:caused|causal uplift|led to|drove|resulted in|attributable to|due to|thanks to|produced uplift|because of (?:the )?optimization|(?:optimization|change|intervention)\s+(?:improved|increased|boosted|raised|enhanced|delivered|yielded|generated|doubled)|was responsible for|as a result of|stemmed from|responsible for|yielded more|generated more)\b",
    re.I,
)
INTERVENTION_RE = re.compile(r"\b(?:optimization|change|intervention|publication|schema change|crawler setting)\b", re.I)
OUTCOME_RE = re.compile(r"\b(?:visibility|mentions?|citations?|referrals?|traffic|uplift)\b", re.I)
CAUSAL_DENIAL_RE = re.compile(r"\b(?:no causal|not causal|cannot be attributed|cannot attribute|no evidence of causation|no causal inference)\b", re.I)
METRIC_CONTRACTS = {
    "mention_rate": ("mention-rate-observed-v1", "Observed answers mentioning the declared entity divided by observed frozen-corpus answers."),
    "citation_rate": ("citation-rate-observed-v1", "Observed answers with at least one citation divided by observed frozen-corpus answers."),
    "cited_source_share": ("cited-source-share-distinct-v1", "Distinct canonical-source matches divided by distinct canonical sources per observed answer."),
    "answer_accuracy": ("answer-accuracy-declared-v1", "Correct declared fact-to-observation checks divided by all declared checks for observed cells."),
    "referral_rate": ("referral-rate-events-v1", "Eligible AI referral events divided by all eligible referral events in the pinned analytics export."),
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)


def resolve(bundle: Path, value: object, field: str, errors: list[str]) -> Path | None:
    return resolve_relative(bundle, value, field, errors)


def canonical_url(value: str) -> str:
    split = urlsplit(value)
    query = [(key, val) for key, val in parse_qsl(split.query, keep_blank_values=True) if not key.lower().startswith("utm_") and key.lower() not in TRACKING]
    path = split.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((split.scheme.lower(), split.netloc.lower(), path, urlencode(sorted(query)), ""))


def duplicate_ids(items: object, field: str, label: str, errors: list[str]) -> None:
    seen: set[str] = set()
    for index, item in enumerate(items if isinstance(items, list) else []):
        value = item.get(field) if isinstance(item, dict) else None
        if isinstance(value, str) and value in seen:
            errors.append(f"{label}[{index}].{field} is duplicated")
        elif isinstance(value, str):
            seen.add(value)


def all_strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from all_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from all_strings(item)


def normalized_claim(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(re.sub(r"[^\w\s]", " ", value.casefold(), flags=re.UNICODE).split())


def phrase_present(answer: str, phrase: object) -> bool:
    if not isinstance(phrase, str) or not phrase.strip():
        return False
    return re.search(rf"(?<!\w){re.escape(phrase.casefold())}(?!\w)", answer.casefold(), re.UNICODE) is not None


def score_signature(score: dict[str, Any]) -> tuple[object, object, object]:
    return (score.get("metric"), score.get("entity_id"), score.get("source_url"))


def causal_assertion(value: str) -> bool:
    if CAUSAL_RE.search(value):
        return True
    if INTERVENTION_RE.search(value) and OUTCOME_RE.search(value):
        return CAUSAL_DENIAL_RE.search(value) is None
    return False


def validate_run(path: Path, bundle: Path) -> None:
    errors: list[str] = []
    artifact = resolve_artifact_in_bundle(path, bundle, errors)
    if artifact is None or errors:
        fail(errors)
    schema = load(SCHEMAS / "visibility-run.schema.json")
    registry = {schema["$id"]: schema}
    for name, definition in schema.get("$defs", {}).items():
        registry[f"#/$defs/{name}"] = definition
    try:
        data = load(artifact)
    except (OSError, json.JSONDecodeError):
        fail(["visibility-run.json is not valid JSON"])
    validate_schema_instance(data, schema, registry, "$", errors)
    if not isinstance(data, dict):
        fail(errors or ["visibility run must be an object"])
    if errors:
        fail(errors)

    research_path = resolve(bundle, data.get("research_ref"), "research_ref", errors)
    if research_path is None or not research_path.is_file():
        errors.append("hash-pinned Research Pack is required")
        research: dict[str, Any] = {}
    elif digest(research_path) != data.get("research_sha256"):
        errors.append("Research Pack hash mismatch")
        research = {}
    else:
        research = load(research_path)
        if research.get("research_id") != data.get("research_id"):
            errors.append("research_id does not match Research Pack")
        semantic = subprocess.run([
            sys.executable, str(ROOT / "scripts" / "validate_ai_search_research.py"), "validate-pack", str(research_path),
            "--bundle", str(bundle), "--now", str(data.get("created_at")),
        ], text=True, capture_output=True, check=False)
        if semantic.returncode != 0:
            errors.append(f"research-pack semantic validation failed: {(semantic.stderr or semantic.stdout).strip()}")

    corpus_path = resolve(bundle, data.get("corpus_ref"), "corpus_ref", errors)
    corpus: dict[str, Any] = {}
    if corpus_path is None or not corpus_path.is_file():
        errors.append("query corpus does not exist")
    elif digest(corpus_path) != data.get("corpus_sha256"):
        errors.append("query corpus hash mismatch")
    else:
        corpus = load(corpus_path)
        if set(corpus) != {"schema_version", "corpus_id", "research_id", "frozen_at", "queries"} or corpus.get("schema_version") != "1.0.0" or corpus.get("research_id") != data.get("research_id"):
            errors.append("query corpus metadata is invalid")

    research_queries = {item.get("query_id"): item for item in research.get("queries", []) if isinstance(item, dict)}
    corpus_queries: dict[str, dict[str, Any]] = {}
    for index, query in enumerate(corpus.get("queries", []) if isinstance(corpus, dict) else []):
        if not isinstance(query, dict) or set(query) != {"query_id", "text", "engine", "surface", "locale", "fact_ids"}:
            errors.append(f"corpus.queries[{index}] has invalid fields")
            continue
        query_id = query.get("query_id")
        if query_id in corpus_queries:
            errors.append(f"corpus.queries[{index}].query_id is duplicated")
        corpus_queries[query_id] = query
        source = research_queries.get(query_id)
        applicability = {(row.get("engine"), row.get("surface")) for row in source.get("applicability", [])} if isinstance(source, dict) else set()
        if not isinstance(source, dict) or source.get("text") != query.get("text") or source.get("locale") != query.get("locale") or (query.get("engine"), query.get("surface")) not in applicability:
            errors.append(f"corpus.queries[{index}] does not match Research Pack query")
        fact_ids = query.get("fact_ids")
        research_fact_ids = {row.get("fact_id") for row in research.get("ground_truth", []) if isinstance(row, dict)}
        if not isinstance(fact_ids, list) or not fact_ids or len(fact_ids) != len(set(fact_ids)) or any(value not in research_fact_ids for value in fact_ids):
            errors.append(f"corpus.queries[{index}].fact_ids must be a non-empty unique Research Pack fact set")
    corpus_frozen_at = parse_time(corpus.get("frozen_at")) if isinstance(corpus, dict) else None
    if not isinstance(corpus, dict) or set(corpus) != {"schema_version", "corpus_id", "research_id", "frozen_at", "queries"} or corpus_frozen_at is None:
        errors.append("query corpus frozen metadata is invalid")
    if not corpus_queries:
        errors.append("query corpus must contain at least one frozen cell")

    for collection, field in (("observations", "observation_id"), ("scores", "score_id"), ("accuracy_checks", "check_id"), ("drift", "drift_id")):
        duplicate_ids(data.get(collection), field, collection, errors)

    created_at = parse_time(data.get("created_at"))
    entities = {item.get("entity_id"): item for item in research.get("entities", []) if isinstance(item, dict)}
    observations: dict[str, dict[str, Any]] = {}
    raw_answers: dict[str, str] = {}
    observation_counts = {query_id: 0 for query_id in corpus_queries}
    for index, observation in enumerate(data.get("observations", [])):
        if not isinstance(observation, dict):
            continue
        observation_id = observation.get("observation_id")
        if isinstance(observation_id, str):
            observations[observation_id] = observation
        query = corpus_queries.get(observation.get("query_id"))
        if not isinstance(query, dict) or any(observation.get(key) != query.get(key) for key in ("engine", "surface", "locale")):
            errors.append(f"observations[{index}] does not match frozen corpus cell")
        elif observation.get("query_id") in observation_counts:
            observation_counts[observation["query_id"]] += 1
        observed_at = parse_time(observation.get("observed_at"))
        if observed_at is None or (created_at is not None and observed_at > created_at):
            errors.append(f"observations[{index}] chronology is invalid")
        if observation.get("access_status") != "observed":
            if observation.get("raw_answer_ref") is not None or observation.get("raw_answer_sha256") is not None or observation.get("mentioned_entities") or observation.get("raw_cited_urls") or observation.get("canonical_cited_urls"):
                errors.append(f"observations[{index}] unobserved access must preserve null answer state")
            attempt_path = resolve(bundle, observation.get("access_attempt_ref"), f"observations[{index}].access_attempt_ref", errors)
            attempt: dict[str, Any] | None = None
            if attempt_path is None or not attempt_path.is_file() or digest(attempt_path) != observation.get("access_attempt_sha256"):
                errors.append(f"observations[{index}] access-attempt hash mismatch")
            else:
                candidate = load(attempt_path)
                keys = {"query_id", "engine", "surface", "locale", "observed_at", "access_status", "collection_method", "reason"}
                attempt = candidate if isinstance(candidate, dict) and set(candidate) == keys else None
            if attempt is None or not isinstance(attempt.get("reason"), str) or not attempt.get("reason", "").strip() or any(
                attempt.get(key) != observation.get(key)
                for key in ("query_id", "engine", "surface", "locale", "observed_at", "access_status", "collection_method")
            ):
                errors.append(f"observations[{index}] access-attempt envelope does not match observation")
            continue
        if observation.get("access_attempt_ref") is not None or observation.get("access_attempt_sha256") is not None:
            errors.append(f"observations[{index}] observed access must not carry an access-attempt receipt")
        raw_path = resolve(bundle, observation.get("raw_answer_ref"), f"observations[{index}].raw_answer_ref", errors)
        raw: dict[str, Any] | None = None
        if raw_path is None or not raw_path.is_file() or digest(raw_path) != observation.get("raw_answer_sha256"):
            errors.append(f"observations[{index}] raw answer hash mismatch")
        else:
            try:
                candidate = load(raw_path)
                expected_keys = {
                    "query_id", "engine", "surface", "locale", "observed_at", "access_status",
                    "disclosed_model", "collection_method", "answer", "citations",
                }
                raw = candidate if isinstance(candidate, dict) and set(candidate) == expected_keys else None
            except (OSError, json.JSONDecodeError):
                raw = None
            if raw is None or not isinstance(raw.get("answer"), str) or not isinstance(raw.get("citations"), list) or raw.get("citations") != observation.get("raw_cited_urls"):
                errors.append(f"observations[{index}] raw answer content does not match observation")
            elif any(raw.get(key) != observation.get(key) for key in (
                "query_id", "engine", "surface", "locale", "observed_at", "access_status",
                "disclosed_model", "collection_method",
            )):
                errors.append(f"observations[{index}] raw answer envelope does not match observation")
        expected_canonical = list(dict.fromkeys(canonical_url(url) for url in observation.get("raw_cited_urls", [])))
        if observation.get("canonical_cited_urls") != expected_canonical:
            errors.append(f"observations[{index}] canonical cited URL does not derive from raw URL")
        if raw is not None:
            matched_entities: set[str] = set()
            for entity_id, entity in entities.items():
                names = [entity.get("name"), *entity.get("aliases", [])] if isinstance(entity, dict) else []
                if any(phrase_present(raw.get("answer", ""), name) for name in names):
                    matched_entities.add(entity_id)
            if set(observation.get("mentioned_entities", [])) != matched_entities:
                errors.append(f"observations[{index}] mentioned entities do not equal raw-answer matches")
            if isinstance(observation_id, str):
                raw_answers[observation_id] = raw.get("answer", "")

    if any(count != 1 for count in observation_counts.values()) or len(data.get("observations", [])) != len(corpus_queries):
        errors.append("run must contain exactly one observation per frozen corpus cell")
    observation_times = [parse_time(row.get("observed_at")) for row in data.get("observations", []) if isinstance(row, dict)]
    if corpus_frozen_at is not None and any(value is not None and corpus_frozen_at > value for value in observation_times):
        errors.append("query corpus must be frozen no later than the first observation")

    observed_ids = {key for key, value in observations.items() if value.get("access_status") == "observed"}
    score_rows = {row.get("score_id"): row for row in data.get("scores", []) if isinstance(row, dict)}
    score_signatures: set[tuple[object, object, object]] = set()
    for index, score in enumerate(data.get("scores", [])):
        if not isinstance(score, dict):
            continue
        numerator, denominator, result = score.get("numerator"), score.get("denominator"), score.get("result")
        if isinstance(numerator, int) and isinstance(denominator, int):
            if numerator < 0 or denominator < 0 or numerator > denominator:
                errors.append(f"scores[{index}] score numerator cannot exceed denominator")
            if denominator == 0 and result is not None:
                errors.append(f"scores[{index}] zero denominator requires null result")
            if denominator > 0 and (not isinstance(result, (int, float)) or not math.isclose(result, numerator / denominator, rel_tol=1e-12, abs_tol=1e-12)):
                errors.append(f"scores[{index}] result does not equal numerator/denominator")
        excluded = score.get("excluded_observation_ids", [])
        if any(value not in observations for value in excluded):
            errors.append(f"scores[{index}] excluded observation does not resolve")
        if excluded:
            errors.append(f"scores[{index}] post-collection exclusions are not allowed; freeze the cohort in the corpus")
        eligible = observed_ids
        metric, entity_id, source_url = score.get("metric"), score.get("entity_id"), score.get("source_url")
        expected_contract = METRIC_CONTRACTS.get(metric)
        if expected_contract is None or (score.get("definition_id"), score.get("definition")) != expected_contract:
            errors.append(f"scores[{index}] metric definition does not match the canonical metric contract")
        signature = (metric, entity_id, source_url)
        if signature in score_signatures:
            errors.append(f"scores[{index}] metric/entity/source combination is duplicated")
        score_signatures.add(signature)
        if metric == "mention_rate":
            if entity_id not in entities or source_url is not None:
                errors.append(f"scores[{index}] mention_rate requires one resolved entity and no source URL")
        elif metric == "cited_source_share":
            if entity_id is not None or not isinstance(source_url, str) or canonical_url(source_url) != source_url:
                errors.append(f"scores[{index}] cited_source_share requires one canonical source URL and no entity")
        elif entity_id is not None or source_url is not None:
            errors.append(f"scores[{index}] {metric} does not accept entity_id or source_url")
        if score.get("metric") in {"mention_rate", "citation_rate"} and denominator != len(eligible):
            errors.append(f"scores[{index}] denominator does not equal eligible observed cohort")
        if score.get("metric") == "mention_rate":
            entity_id = score.get("entity_id")
            expected = sum(entity_id in observations[value].get("mentioned_entities", []) for value in eligible)
            if numerator != expected:
                errors.append(f"scores[{index}] mention numerator does not match observations")
        if score.get("metric") == "citation_rate":
            expected = sum(bool(observations[value].get("canonical_cited_urls")) for value in eligible)
            if numerator != expected:
                errors.append(f"scores[{index}] citation numerator does not match observations")
        if metric == "cited_source_share":
            citations = [url for value in eligible for url in observations[value].get("canonical_cited_urls", [])]
            expected = sum(url == source_url for url in citations)
            if denominator != len(citations):
                errors.append(f"scores[{index}] cited-source denominator does not match observations")
            if numerator != expected:
                errors.append(f"scores[{index}] cited-source numerator does not match observations")

    facts = {item.get("fact_id"): item for item in research.get("ground_truth", []) if isinstance(item, dict)}
    accuracy_pairs: set[tuple[object, object]] = set()
    accuracy_rows: list[dict[str, Any]] = []
    for index, check in enumerate(data.get("accuracy_checks", [])):
        if not isinstance(check, dict):
            continue
        if check.get("fact_id") not in facts or check.get("observation_id") not in observed_ids:
            errors.append(f"accuracy_checks[{index}] fact or observation does not resolve")
            continue
        pair = (check.get("fact_id"), check.get("observation_id"))
        if pair in accuracy_pairs:
            errors.append(f"accuracy_checks[{index}] fact/observation pair is duplicated")
        accuracy_pairs.add(pair)
        answer = raw_answers.get(check.get("observation_id"), "")
        if check.get("observed_claim", "").strip().lower() not in answer.lower():
            errors.append(f"accuracy_checks[{index}] observed claim is not present in raw answer")
        expected_pointer = f"{data.get('research_ref')}#{check.get('fact_id')}"
        if expected_pointer not in check.get("evidence", []):
            errors.append(f"accuracy_checks[{index}] evidence does not resolve to the ground-truth fact")
        fact = facts.get(check.get("fact_id"), {})
        accepted = fact.get("accepted_value") if isinstance(fact, dict) else None
        exact_claim = normalized_claim(check.get("observed_claim")) == normalized_claim(accepted)
        exact_answer = normalized_claim(answer) == normalized_claim(accepted)
        automatic_correct = check.get("verdict") == "correct" and exact_claim and exact_answer
        if automatic_correct:
            if check.get("review_ref") is not None or check.get("review_sha256") is not None:
                errors.append(f"accuracy_checks[{index}] automatic exact correct verdict must not carry a discretionary review")
        else:
            review_path = resolve(bundle, check.get("review_ref"), f"accuracy_checks[{index}].review_ref", errors)
            review: dict[str, Any] | None = None
            if review_path is None or not review_path.is_file() or digest(review_path) != check.get("review_sha256"):
                errors.append(f"accuracy_checks[{index}] non-exact verdict requires a hash-pinned review")
            else:
                candidate = load(review_path)
                keys = {"schema_version", "check_id", "fact_id", "observation_id", "observed_claim", "accepted_value", "verdict", "rationale", "reviewed_at", "reviewer"}
                review = candidate if isinstance(candidate, dict) and set(candidate) == keys and candidate.get("schema_version") == "1.0.0" else None
            if review is None or any(review.get(key) != check.get(key) for key in ("check_id", "fact_id", "observation_id", "observed_claim", "verdict")) or review.get("accepted_value") != accepted or not isinstance(review.get("rationale"), str) or not review.get("rationale", "").strip() or not isinstance(review.get("reviewer"), str) or not review.get("reviewer", "").strip():
                errors.append(f"accuracy_checks[{index}] review envelope does not match the check")
            else:
                reviewed_at = parse_time(review.get("reviewed_at"))
                observed_at = parse_time(observations[check.get("observation_id")].get("observed_at"))
                if reviewed_at is None or observed_at is None or created_at is None or not (observed_at <= reviewed_at <= created_at):
                    errors.append(f"accuracy_checks[{index}] review chronology is invalid")
        if check.get("verdict") == "correct" and not automatic_correct and check.get("review_ref") is None:
            errors.append(f"accuracy_checks[{index}] correct verdict requires full-answer equality or a hash-pinned review")
        accuracy_rows.append(check)

    required_accuracy_pairs = {
        (fact_id, observation_id)
        for observation_id in observed_ids
        for fact_id in corpus_queries.get(observations[observation_id].get("query_id"), {}).get("fact_ids", [])
    }
    if accuracy_pairs != required_accuracy_pairs:
        errors.append("accuracy checks must cover every declared fact for every observed corpus cell")

    correct_accuracy = [row for row in accuracy_rows if row.get("verdict") == "correct"]
    referral_ref, referral_sha = data.get("referral_data_ref"), data.get("referral_data_sha256")
    referral_data: dict[str, Any] | None = None
    if (referral_ref is None) != (referral_sha is None):
        errors.append("referral data reference and hash must both be null or both be present")
    elif referral_ref is not None:
        referral_path = resolve(bundle, referral_ref, "referral_data_ref", errors)
        if referral_path is None or not referral_path.is_file() or digest(referral_path) != referral_sha:
            errors.append("referral data hash mismatch")
        else:
            candidate = load(referral_path)
            keys = {"schema_version", "dataset_id", "created_at", "window_start", "window_end", "source", "measurement_method", "numerator", "denominator", "definition", "raw_source_ref", "raw_source_sha256"}
            if not isinstance(candidate, dict) or set(candidate) != keys or candidate.get("schema_version") != "1.0.0":
                errors.append("referral data envelope is invalid")
            else:
                referral_data = candidate
                start, end, referral_created = (parse_time(candidate.get(key)) for key in ("window_start", "window_end", "created_at"))
                if start is None or end is None or referral_created is None or created_at is None or not (start < end <= referral_created <= created_at):
                    errors.append("referral data chronology is invalid")
                if not isinstance(candidate.get("dataset_id"), str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", candidate.get("dataset_id", "")) or not isinstance(candidate.get("source"), str) or not candidate.get("source", "").strip() or not isinstance(candidate.get("measurement_method"), str) or not candidate.get("measurement_method", "").strip() or not isinstance(candidate.get("definition"), str) or not candidate.get("definition", "").strip():
                    errors.append("referral data metadata is invalid")
                numerator, denominator = candidate.get("numerator"), candidate.get("denominator")
                if not isinstance(numerator, int) or isinstance(numerator, bool) or not isinstance(denominator, int) or isinstance(denominator, bool) or numerator < 0 or denominator <= 0 or numerator > denominator:
                    errors.append("referral data numerator/denominator is invalid")
                raw_source = resolve(bundle, candidate.get("raw_source_ref"), "referral_data.raw_source_ref", errors)
                if raw_source is None or not raw_source.is_file() or digest(raw_source) != candidate.get("raw_source_sha256"):
                    errors.append("referral raw source hash mismatch")
                else:
                    try:
                        raw_export = load(raw_source)
                    except (OSError, json.JSONDecodeError):
                        raw_export = None
                    raw_keys = {"schema_version", "source", "measurement_method", "window_start", "window_end", "events"}
                    if not isinstance(raw_export, dict) or set(raw_export) != raw_keys or raw_export.get("schema_version") != "1.0.0" or raw_export.get("source") != candidate.get("source") or raw_export.get("measurement_method") != candidate.get("measurement_method") or raw_export.get("window_start") != candidate.get("window_start") or raw_export.get("window_end") != candidate.get("window_end") or not isinstance(raw_export.get("events"), list):
                        errors.append("referral raw export envelope is invalid")
                    else:
                        event_ids: set[str] = set()
                        derived_numerator = 0
                        derived_denominator = 0
                        for event_index, event in enumerate(raw_export["events"]):
                            event_keys = {"event_id", "occurred_at", "source_category", "eligible"}
                            if not isinstance(event, dict) or set(event) != event_keys or not isinstance(event.get("event_id"), str) or not event.get("event_id") or event.get("event_id") in event_ids or event.get("source_category") not in {"ai", "non_ai"} or not isinstance(event.get("eligible"), bool):
                                errors.append(f"referral raw export event[{event_index}] is invalid")
                                continue
                            event_ids.add(event["event_id"])
                            occurred_at = parse_time(event.get("occurred_at"))
                            if occurred_at is None or start is None or end is None or not (start <= occurred_at < end):
                                errors.append(f"referral raw export event[{event_index}] is outside the declared window")
                                continue
                            if event["eligible"]:
                                derived_denominator += 1
                                derived_numerator += event["source_category"] == "ai"
                        if candidate.get("numerator") != derived_numerator or candidate.get("denominator") != derived_denominator:
                            errors.append("referral data numerator/denominator does not derive from raw export events")

    for index, score in enumerate(data.get("scores", [])):
        if not isinstance(score, dict):
            continue
        if score.get("metric") == "answer_accuracy":
            if score.get("denominator") != len(accuracy_rows):
                errors.append(f"scores[{index}] answer-accuracy denominator does not match checks")
            if score.get("numerator") != len(correct_accuracy):
                errors.append(f"scores[{index}] answer-accuracy numerator does not match checks")
        if score.get("metric") == "referral_rate":
            if referral_data is None:
                errors.append(f"scores[{index}] referral_rate requires hash-pinned referral data")
            elif score.get("numerator") != referral_data.get("numerator") or score.get("denominator") != referral_data.get("denominator"):
                errors.append(f"scores[{index}] referral score does not match referral data")
            elif score.get("definition") != referral_data.get("definition"):
                errors.append(f"scores[{index}] referral score definition does not match referral data")

    mode = data.get("mode")
    prior_fields = (data.get("prior_run_id"), data.get("prior_run_ref"), data.get("prior_run_sha256"))
    if mode == "baseline":
        if any(value is not None for value in prior_fields):
            errors.append("baseline prior-run fields must be null")
        if data.get("drift"):
            errors.append("baseline drift must be empty")
    elif mode == "comparison":
        if any(value is None for value in prior_fields):
            errors.append("comparison requires hash-pinned prior run")
        else:
            prior_path = resolve(bundle, data.get("prior_run_ref"), "prior_run_ref", errors)
            if prior_path is None or not prior_path.is_file() or digest(prior_path) != data.get("prior_run_sha256"):
                errors.append("prior run hash mismatch")
            else:
                prior = load(prior_path)
                if prior.get("run_id") != data.get("prior_run_id") or prior.get("schema_version") != "1.0.0":
                    errors.append("prior run identity/version mismatch")
                if prior.get("run_id") == data.get("run_id") or prior.get("research_id") != data.get("research_id"):
                    errors.append("prior run must have a different identity and the same Research Pack")
                prior_created = parse_time(prior.get("created_at"))
                if prior_created is None or created_at is None or prior_created >= created_at:
                    errors.append("prior run chronology is invalid")
                visited = {value for value in os.environ.get("AIVM_VISITED_RUN_HASHES", "").split(",") if value}
                current_hash = digest(path)
                prior_hash = digest(prior_path)
                if prior_hash in visited or prior_hash == current_hash:
                    errors.append("prior run lineage contains a cycle")
                else:
                    env = os.environ.copy()
                    env["AIVM_VISITED_RUN_HASHES"] = ",".join(sorted(visited | {current_hash, prior_hash}))
                    semantic = subprocess.run(
                        [sys.executable, str(Path(__file__).resolve()), "validate-run", str(prior_path), "--bundle", str(bundle)],
                        text=True, capture_output=True, check=False, env=env,
                    )
                    if semantic.returncode != 0:
                        errors.append(f"prior run semantic validation failed: {(semantic.stderr or semantic.stdout).strip()}")
                corpus_changed = prior.get("corpus_sha256") != data.get("corpus_sha256")
                research_changed = prior.get("research_sha256") != data.get("research_sha256")
                current_access = {row.get("query_id"): row.get("access_status") for row in data.get("observations", []) if isinstance(row, dict)}
                prior_access = {row.get("query_id"): row.get("access_status") for row in prior.get("observations", []) if isinstance(row, dict)}
                access_changed = current_access != prior_access
                prior_scores = {row.get("score_id"): row for row in prior.get("scores", []) if isinstance(row, dict)}
                prior_referral_data: dict[str, Any] | None = None
                if prior.get("referral_data_ref") is not None:
                    prior_referral_path = resolve(bundle, prior.get("referral_data_ref"), "prior.referral_data_ref", errors)
                    if prior_referral_path is not None and prior_referral_path.is_file() and digest(prior_referral_path) == prior.get("referral_data_sha256"):
                        candidate_prior_referral = load(prior_referral_path)
                        if isinstance(candidate_prior_referral, dict):
                            prior_referral_data = candidate_prior_referral
                current_by_signature = {score_signature(row): row for row in score_rows.values()}
                prior_by_signature = {score_signature(row): row for row in prior_scores.values()}
                drift_signatures: set[tuple[object, object, object]] = set()
                for index, drift in enumerate(data.get("drift", [])):
                    if not isinstance(drift, dict):
                        continue
                    current_score = score_rows.get(drift.get("current_score_id"))
                    prior_score = prior_scores.get(drift.get("prior_score_id"))
                    if not isinstance(current_score, dict) or not isinstance(prior_score, dict) or drift.get("metric") != current_score.get("metric") or drift.get("metric") != prior_score.get("metric"):
                        errors.append(f"drift[{index}] referenced scores do not resolve to the same metric")
                        continue
                    current_signature, prior_signature = score_signature(current_score), score_signature(prior_score)
                    if current_signature != prior_signature:
                        errors.append(f"drift[{index}] prior and current score targets do not match")
                        continue
                    if current_signature in drift_signatures:
                        errors.append(f"drift[{index}] score signature is duplicated")
                    drift_signatures.add(current_signature)
                    values_match = drift.get("prior_value") == prior_score.get("result") and drift.get("current_value") == current_score.get("result")
                    if not values_match:
                        errors.append(f"drift[{index}] drift values do not match referenced scores")
                    definitions_changed = prior_score.get("definition") != current_score.get("definition")
                    null_value = prior_score.get("result") is None or current_score.get("result") is None
                    referral_changed = False
                    if drift.get("metric") == "referral_rate":
                        if referral_data is None or prior_referral_data is None:
                            referral_changed = True
                        else:
                            current_start, current_end = parse_time(referral_data.get("window_start")), parse_time(referral_data.get("window_end"))
                            prior_start, prior_end = parse_time(prior_referral_data.get("window_start")), parse_time(prior_referral_data.get("window_end"))
                            current_duration = current_end - current_start if current_start is not None and current_end is not None else None
                            prior_duration = prior_end - prior_start if prior_start is not None and prior_end is not None else None
                            referral_changed = any(referral_data.get(key) != prior_referral_data.get(key) for key in ("schema_version", "source", "measurement_method")) or current_duration != prior_duration
                    non_comparable = corpus_changed or research_changed or definitions_changed or access_changed or null_value or referral_changed
                    if (non_comparable or drift.get("comparable") is False) and not drift.get("comparability_warning"):
                        errors.append(f"drift[{index}] non-comparable drift requires warning")
                    if non_comparable and drift.get("comparable") is True:
                        errors.append(f"drift[{index}] changed research, cohort, access profile, referral method, definition, or null value cannot be comparable")
                    prior_value, current_value, delta = drift.get("prior_value"), drift.get("current_value"), drift.get("delta")
                    if all(isinstance(value, (int, float)) for value in (prior_value, current_value, delta)) and not math.isclose(delta, current_value - prior_value, rel_tol=1e-12, abs_tol=1e-12):
                        errors.append(f"drift[{index}] delta arithmetic mismatch")
                common_signatures = set(current_by_signature) & set(prior_by_signature)
                if drift_signatures != common_signatures:
                    errors.append("comparison drift must cover every semantically shared score")

    if any(item.get("access_status") != "observed" for item in data.get("observations", []) if isinstance(item, dict)) and not data.get("limitations"):
        errors.append("access gaps require a limitation")
    interpretive_text = list(data.get("limitations", []))
    interpretive_text.extend(row.get("uncertainty_note", "") for row in data.get("scores", []) if isinstance(row, dict))
    for row in data.get("drift", []):
        if isinstance(row, dict):
            interpretive_text.extend([row.get("comparable_cohort", ""), row.get("comparability_warning", "") or ""])
    if any(isinstance(value, str) and causal_assertion(value) for value in interpretive_text):
        errors.append("causal language is not allowed in observational visibility runs")
    if errors:
        fail(errors)
    print("PASS: ai-visibility-monitor run")


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
