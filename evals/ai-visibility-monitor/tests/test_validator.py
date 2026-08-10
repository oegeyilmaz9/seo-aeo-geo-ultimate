from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from statistics import NormalDist


ROOT = Path(__file__).resolve().parents[3]
PYTHON = sys.executable
VALIDATOR = ROOT / "scripts" / "validate_ai_visibility_monitor.py"
FIXTURE = ROOT / "evals" / "fixtures" / "aeo-normal"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def mention_score(score_id: str, method: str = "not-estimated", level: float | None = None) -> dict:
    lower: float | None = None
    upper: float | None = None
    if method == "wilson" and level is not None:
        z = NormalDist().inv_cdf(0.5 + level / 2)
        denominator_adjusted = 1 + z * z
        center = (1 + z * z / 2) / denominator_adjusted
        margin = z * ((z * z / 4) ** 0.5) / denominator_adjusted
        lower, upper = center - margin, min(1.0, center + margin)
    return {
        "score_id": score_id,
        "metric": "mention_rate",
        "definition_id": "mention-rate-observed-v1",
        "entity_id": "example-platform",
        "source_url": None,
        "definition": "Observed answers mentioning the declared entity divided by observed frozen-corpus answers.",
        "numerator": 1,
        "denominator": 1,
        "excluded_observation_ids": [],
        "result": 1.0,
        "uncertainty_note": "One observed answer; interpret the interval and point estimate cautiously.",
        "sample_size": 1,
        "repeat_count": 1,
        "confidence_interval": {"method": method, "level": level, "lower": lower, "upper": upper},
    }


def build_valid_run(bundle: Path) -> dict:
    research_path = bundle / "research-pack.json"
    research = json.loads(research_path.read_text(encoding="utf-8"))
    query = research["queries"][0]
    fact = research["ground_truth"][0]
    observed_at = "2026-07-11T10:30:00Z"
    collection_method = "Manual point-in-time answer collection with the recorded locale and surface."
    corpus_path = bundle / "raw" / "query-corpus.json"
    write_json(
        corpus_path,
        {
            "schema_version": "1.0.0",
            "corpus_id": "baseline-corpus",
            "research_id": research["research_id"],
            "frozen_at": "2026-07-11T10:00:00Z",
            "queries": [
                {
                    "query_id": query["query_id"],
                    "text": query["text"],
                    "engine": "google",
                    "surface": "ai-overview",
                    "locale": "tr-TR",
                    "fact_ids": [fact["fact_id"]],
                }
            ],
        },
    )
    raw_answer_path = bundle / "raw" / "answers" / "example-turkiye.json"
    raw_answer = {
        "query_id": query["query_id"],
        "engine": "google",
        "surface": "ai-overview",
        "locale": "tr-TR",
        "observed_at": observed_at,
        "access_status": "observed",
        "disclosed_model": None,
        "collection_method": collection_method,
        "answer": fact["accepted_value"],
        "citations": ["https://example.com/platform-doc"],
    }
    write_json(raw_answer_path, raw_answer)
    return {
        "schema_version": "1.0.0",
        "run_id": "baseline-run",
        "research_id": research["research_id"],
        "research_ref": "research-pack.json",
        "research_sha256": sha256(research_path),
        "created_at": "2026-07-11T12:00:00Z",
        "mode": "baseline",
        "interpretation_type": "observational_association",
        "causal_claim": False,
        "corpus_ref": "raw/query-corpus.json",
        "corpus_sha256": sha256(corpus_path),
        "prior_run_id": None,
        "prior_run_ref": None,
        "prior_run_sha256": None,
        "referral_data_ref": None,
        "referral_data_sha256": None,
        "observations": [
            {
                "observation_id": "baseline-observation",
                "query_id": query["query_id"],
                "engine": "google",
                "surface": "ai-overview",
                "locale": "tr-TR",
                "observed_at": observed_at,
                "access_status": "observed",
                "raw_answer_ref": "raw/answers/example-turkiye.json",
                "raw_answer_sha256": sha256(raw_answer_path),
                "access_attempt_ref": None,
                "access_attempt_sha256": None,
                "mentioned_entities": ["example-platform"],
                "raw_cited_urls": ["https://example.com/platform-doc"],
                "canonical_cited_urls": ["https://example.com/platform-doc"],
                "disclosed_model": None,
                "collection_method": collection_method,
            }
        ],
        "scores": [],
        "accuracy_checks": [
            {
                "check_id": "availability-check",
                "fact_id": fact["fact_id"],
                "observation_id": "baseline-observation",
                "observed_claim": fact["accepted_value"],
                "verdict": "correct",
                "review_method": "Exact raw-answer equality against the declared accepted value.",
                "evidence": [f"research-pack.json#{fact['fact_id']}"],
                "review_ref": None,
                "review_sha256": None,
            }
        ],
        "drift": [],
        "limitations": ["This is a point-in-time observational record, not a causal result."],
    }


def build_valid_v2_run(bundle: Path) -> dict:
    research_path = bundle / "research-pack.json"
    research = json.loads(research_path.read_text(encoding="utf-8"))
    query = research["queries"][0]
    fact = research["ground_truth"][0]
    research_hash = sha256(research_path)
    observed_at = "2026-07-11T10:30:00Z"
    collection_method = "Manual fresh-session answer collection with retrieval tracing where disclosed."
    corpus_path = bundle / "raw" / "query-corpus-v2.json"
    corpus = {
        "schema_version": "1.0.0",
        "corpus_id": "baseline-corpus-v2",
        "research_id": research["research_id"],
        "research_sha256": research_hash,
        "created_at": "2026-07-11T10:00:00Z",
        "frozen_at": "2026-07-11T09:30:00Z",
        "scope": "One engine-bound AI prompt for a repeatable baseline.",
        "queries": [
            {
                "query_id": query["query_id"],
                "need_id": "availability-need",
                "query_type": "ai_prompt",
                "text": query["text"],
                "locale": query["locale"],
                "country": "TR",
                "location": "Istanbul",
                "device": "desktop",
                "engine": "google",
                "surface": "ai-overview",
                "parent_query_id": None,
                "conversation_id": "baseline-conversation",
                "turn_index": 0,
                "intent": query["intent"],
                "audience": query["audience"],
                "journey_stage": query["journey_stage"],
                "target_entities": query["target_entities"],
                "fact_ids": [fact["fact_id"]],
                "applicability": [{"engine": "google", "surface": "ai-overview"}],
                "source": {
                    "source_kind": "research_pack",
                    "source_url": "https://example.com/platform-doc",
                    "source_ref": "raw/evidence.json",
                    "source_sha256": sha256(bundle / "raw" / "evidence.json"),
                    "observed_at": "2026-07-10T10:00:00Z",
                    "methodology": "Copied from the validated Research Pack query.",
                    "limitations": ["No keyword-volume estimate."],
                },
                "demand": {
                    "status": "unavailable",
                    "monthly_volume": None,
                    "trend_index": None,
                    "difficulty": None,
                    "provider": None,
                    "observed_at": None,
                    "source_url": None,
                    "source_ref": None,
                    "source_sha256": None,
                    "limitations": ["Demand source was not supplied."],
                },
                "coverage": {
                    "state": "covered",
                    "current_urls": ["https://example.com/"],
                    "target_url": "https://example.com/",
                    "competing_urls": [],
                    "evidence_ref": "raw/observation.json",
                    "evidence_sha256": sha256(bundle / "raw" / "observation.json"),
                },
                "confidence": "high",
                "limitations": ["One engine/surface cell."],
            }
        ],
        "limitations": ["The corpus is frozen for observational measurement."],
    }
    write_json(corpus_path, corpus)

    citation_claim = {
        "claim_id": "citation-claim-example",
        "citation_url": "https://example.com/platform-doc",
        "claim": fact["accepted_value"],
        "cited_text": "Platform documentation supports the availability statement.",
        "verdict": "supported",
        "review_ref": "raw/reviews/citation-claim-example.json",
        "review_sha256": "pending",
    }
    review_path = bundle / citation_claim["review_ref"]
    write_json(
        review_path,
        {
            "schema_version": "1.0.0",
            "claim_id": citation_claim["claim_id"],
            "citation_url": citation_claim["citation_url"],
            "claim": citation_claim["claim"],
            "cited_text": citation_claim["cited_text"],
            "verdict": citation_claim["verdict"],
            "rationale": "The cited source directly supports the observed answer claim.",
            "reviewer": "fixture-reviewer",
            "reviewed_at": "2026-07-11T11:00:00Z",
        },
    )
    citation_claim["review_sha256"] = sha256(review_path)
    consulted_sources = [{"url": "https://example.com/platform-doc", "title": "Platform documentation", "cited": True}]
    raw_answer_path = bundle / "raw" / "answers" / "example-turkiye-v2.json"
    raw_answer = {
        "query_id": query["query_id"],
        "engine": "google",
        "surface": "ai-overview",
        "locale": "tr-TR",
        "observed_at": observed_at,
        "access_status": "observed",
        "disclosed_model": None,
        "collection_method": collection_method,
        "answer": fact["accepted_value"],
        "citations": ["https://example.com/platform-doc"],
        "repeat_index": 0,
        "conversation_id": "baseline-conversation",
        "turn_index": 0,
        "user_location": {"country": "TR", "region": "Istanbul", "city": "Istanbul"},
        "device": "desktop",
        "authenticated": None,
        "personalization": "unknown",
        "retrieval_mode": "live-web",
        "executed_queries": [query["text"]],
        "consulted_sources": consulted_sources,
        "citation_claims": [citation_claim],
    }
    write_json(raw_answer_path, raw_answer)
    return {
        "schema_version": "2.0.0",
        "run_id": "baseline-run-v2",
        "research_id": research["research_id"],
        "research_ref": "research-pack.json",
        "research_sha256": research_hash,
        "created_at": "2026-07-11T12:00:00Z",
        "mode": "baseline",
        "interpretation_type": "observational_association",
        "causal_claim": False,
        "corpus_ref": "raw/query-corpus-v2.json",
        "corpus_sha256": sha256(corpus_path),
        "collection_profile": {
            "planned_repeats": 1,
            "completed_repeats": 1,
            "confidence_method": "none",
            "confidence_level": None,
            "fresh_session_per_repeat": True,
        },
        "prior_run_id": None,
        "prior_run_ref": None,
        "prior_run_sha256": None,
        "referral_data_ref": None,
        "referral_data_sha256": None,
        "observations": [
            {
                "observation_id": "baseline-observation-v2",
                "query_id": query["query_id"],
                "repeat_index": 0,
                "engine": "google",
                "surface": "ai-overview",
                "locale": "tr-TR",
                "observed_at": observed_at,
                "access_status": "observed",
                "raw_answer_ref": "raw/answers/example-turkiye-v2.json",
                "raw_answer_sha256": sha256(raw_answer_path),
                "access_attempt_ref": None,
                "access_attempt_sha256": None,
                "mentioned_entities": ["example-platform"],
                "raw_cited_urls": ["https://example.com/platform-doc"],
                "canonical_cited_urls": ["https://example.com/platform-doc"],
                "disclosed_model": None,
                "collection_method": collection_method,
                "conversation_id": "baseline-conversation",
                "turn_index": 0,
                "user_location": {"country": "TR", "region": "Istanbul", "city": "Istanbul"},
                "device": "desktop",
                "authenticated": None,
                "personalization": "unknown",
                "retrieval_mode": "live-web",
                "executed_queries": [query["text"]],
                "consulted_sources": consulted_sources,
                "citation_claims": [citation_claim],
            }
        ],
        "scores": [],
        "accuracy_checks": [
            {
                "check_id": "availability-check-v2",
                "fact_id": fact["fact_id"],
                "observation_id": "baseline-observation-v2",
                "observed_claim": fact["accepted_value"],
                "verdict": "correct",
                "review_method": "Exact raw-answer equality against the declared accepted value.",
                "evidence": [f"research-pack.json#{fact['fact_id']}"],
                "review_ref": None,
                "review_sha256": None,
            }
        ],
        "drift": [],
        "limitations": ["This repeated trace is observational and does not establish causation."],
    }


class AiVisibilityMonitorValidatorTests(unittest.TestCase):
    def run_visibility(self, mutator=None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(FIXTURE, bundle)
            artifact = bundle / "visibility-run.json"
            payload = build_valid_run(bundle)
            if mutator:
                mutator(payload)
            write_json(artifact, payload)
            return subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-run", str(artifact), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )

    def run_v2(self, mutator=None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(FIXTURE, bundle)
            artifact = bundle / "visibility-run.json"
            payload = build_valid_v2_run(bundle)
            if mutator:
                mutator(bundle, payload)
            write_json(artifact, payload)
            return subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-run", str(artifact), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_valid_baseline_visibility_run_passes(self) -> None:
        completed = self.run_visibility()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS: ai-visibility-monitor run", completed.stdout)

    def test_valid_v2_trace_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(FIXTURE, bundle)
            artifact = bundle / "visibility-run.json"
            payload = build_valid_v2_run(bundle)
            write_json(artifact, payload)
            completed = subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-run", str(artifact), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_v2_visible_citation_must_resolve_to_consulted_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(FIXTURE, bundle)
            artifact = bundle / "visibility-run.json"
            payload = build_valid_v2_run(bundle)
            payload["observations"][0]["consulted_sources"] = []
            write_json(artifact, payload)
            completed = subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-run", str(artifact), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("visible citation", completed.stderr)

    def test_v2_repeat_index_must_match_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(FIXTURE, bundle)
            artifact = bundle / "visibility-run.json"
            payload = build_valid_v2_run(bundle)
            payload["observations"][0]["repeat_index"] = 3
            write_json(artifact, payload)
            completed = subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-run", str(artifact), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("repeat_index", completed.stderr)

    def test_v2_observation_context_must_match_frozen_corpus(self) -> None:
        def mutate(bundle: Path, payload: dict) -> None:
            observation = payload["observations"][0]
            observation["device"] = "mobile"
            raw_path = bundle / observation["raw_answer_ref"]
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            raw["device"] = "mobile"
            write_json(raw_path, raw)
            observation["raw_answer_sha256"] = sha256(raw_path)

        completed = self.run_v2(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("device does not match the frozen corpus", completed.stderr)

    def test_v2_formal_executed_subquery_lineage_passes(self) -> None:
        def mutate(bundle: Path, payload: dict) -> None:
            corpus_path = bundle / payload["corpus_ref"]
            corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
            root = corpus["queries"][0]
            subquery = json.loads(json.dumps(root))
            subquery.update(
                {
                    "query_id": "executed-availability-subquery",
                    "query_type": "executed_subquery",
                    "text": "example availability in turkey",
                    "parent_query_id": root["query_id"],
                    "conversation_id": "pilot-conversation",
                    "turn_index": 1,
                }
            )
            subquery["source"].update(
                {
                    "source_kind": "direct_observation",
                    "source_url": None,
                    "source_ref": "raw/evidence.json",
                    "source_sha256": sha256(bundle / "raw" / "evidence.json"),
                    "observed_at": "2026-07-10T09:00:00Z",
                    "methodology": "Captured from a prior disclosed retrieval trace.",
                }
            )
            corpus["queries"].append(subquery)
            write_json(corpus_path, corpus)
            payload["corpus_sha256"] = sha256(corpus_path)
            observation = payload["observations"][0]
            observation["executed_queries"] = [subquery["text"]]
            raw_path = bundle / observation["raw_answer_ref"]
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            raw["executed_queries"] = observation["executed_queries"]
            write_json(raw_path, raw)
            observation["raw_answer_sha256"] = sha256(raw_path)

        completed = self.run_v2(mutate)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_v2_disclosed_query_must_match_declared_subquery_lineage(self) -> None:
        def mutate(bundle: Path, payload: dict) -> None:
            corpus_path = bundle / payload["corpus_ref"]
            corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
            root = corpus["queries"][0]
            subquery = json.loads(json.dumps(root))
            subquery.update(
                {
                    "query_id": "executed-availability-subquery",
                    "query_type": "executed_subquery",
                    "text": "declared retrieval query",
                    "parent_query_id": root["query_id"],
                    "conversation_id": "pilot-conversation",
                    "turn_index": 1,
                }
            )
            subquery["source"].update(
                {
                    "source_kind": "direct_observation",
                    "source_url": None,
                    "source_ref": "raw/evidence.json",
                    "source_sha256": sha256(bundle / "raw" / "evidence.json"),
                    "observed_at": "2026-07-10T09:00:00Z",
                }
            )
            corpus["queries"].append(subquery)
            write_json(corpus_path, corpus)
            payload["corpus_sha256"] = sha256(corpus_path)
            payload["observations"][0]["executed_queries"] = ["different disclosed query"]
            raw_path = bundle / payload["observations"][0]["raw_answer_ref"]
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            raw["executed_queries"] = ["different disclosed query"]
            write_json(raw_path, raw)
            payload["observations"][0]["raw_answer_sha256"] = sha256(raw_path)

        completed = self.run_v2(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("does not match declared Query Corpus subquery lineage", completed.stderr)

    def test_v2_wilson_interval_is_recomputed(self) -> None:
        def valid_wilson(_bundle: Path, payload: dict) -> None:
            payload["collection_profile"].update({"confidence_method": "wilson", "confidence_level": 0.95})
            payload["scores"] = [mention_score("mention-score-wilson", "wilson", 0.95)]

        completed = self.run_v2(valid_wilson)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

        def forged_wilson(_bundle: Path, payload: dict) -> None:
            payload["collection_profile"].update({"confidence_method": "wilson", "confidence_level": 0.95})
            score = mention_score("mention-score-wilson", "wilson", 0.95)
            score["confidence_interval"].update({"lower": 1.0, "upper": 1.0})
            payload["scores"] = [score]

        completed = self.run_v2(forged_wilson)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Wilson bounds do not derive", completed.stderr)

    def test_v2_comparison_rejects_changed_collection_context(self) -> None:
        def mutate(bundle: Path, current: dict) -> None:
            prior = build_valid_v2_run(bundle)
            prior["run_id"] = "prior-run-v2"
            prior["scores"] = [mention_score("prior-mention-score")]
            prior_answer = bundle / "raw" / "answers" / "prior-v2.json"
            source_answer = bundle / prior["observations"][0]["raw_answer_ref"]
            prior_answer.write_bytes(source_answer.read_bytes())
            prior["observations"][0]["raw_answer_ref"] = "raw/answers/prior-v2.json"
            prior["observations"][0]["raw_answer_sha256"] = sha256(prior_answer)
            prior_path = bundle / "prior-run-v2.json"
            write_json(prior_path, prior)

            current.update(
                {
                    "run_id": "current-run-v2",
                    "created_at": "2026-07-12T12:00:00Z",
                    "mode": "comparison",
                    "prior_run_id": prior["run_id"],
                    "prior_run_ref": "prior-run-v2.json",
                    "prior_run_sha256": sha256(prior_path),
                    "scores": [mention_score("current-mention-score")],
                    "drift": [
                        {
                            "drift_id": "mention-drift",
                            "metric": "mention_rate",
                            "prior_score_id": "prior-mention-score",
                            "current_score_id": "current-mention-score",
                            "comparable_cohort": "Same query and repeat cohort.",
                            "prior_value": 1.0,
                            "current_value": 1.0,
                            "delta": 0.0,
                            "comparable": True,
                            "comparability_warning": None,
                        }
                    ],
                }
            )
            observation = current["observations"][0]
            observation.update({"authenticated": True, "personalization": "active", "retrieval_mode": "cache"})
            raw_path = bundle / observation["raw_answer_ref"]
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            raw.update({"authenticated": True, "personalization": "active", "retrieval_mode": "cache"})
            write_json(raw_path, raw)
            observation["raw_answer_sha256"] = sha256(raw_path)

        completed = self.run_v2(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("collection context", completed.stderr)

    def test_causal_language_is_rejected(self) -> None:
        completed = self.run_visibility(
            lambda payload: payload.update({"limitations": ["The optimization increased visibility."]})
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("causal language is not allowed", completed.stderr)

    def test_artifact_cannot_live_outside_declared_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            shutil.copytree(FIXTURE, bundle)
            payload = build_valid_run(bundle)
            outside = root / "visibility-run.json"
            write_json(outside, payload)
            completed = subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-run", str(outside), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("artifact must be inside --bundle", completed.stderr)

    def test_invalid_json_is_reported_without_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "bundle"
            shutil.copytree(FIXTURE, bundle)
            artifact = bundle / "visibility-run.json"
            artifact.write_text("{not-json", encoding="utf-8")
            completed = subprocess.run(
                [PYTHON, str(VALIDATOR), "validate-run", str(artifact), "--bundle", str(bundle)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("visibility-run.json is not valid JSON", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
