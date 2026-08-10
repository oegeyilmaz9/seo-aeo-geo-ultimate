from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "scripts" / "validate_seo_performance.py"


def valid_run(raw_hash: str) -> dict:
    return {
        "schema_version": "1.0.0",
        "run_id": "performance-example",
        "created_at": "2026-08-10T12:00:00Z",
        "mode": "baseline",
        "interpretation_type": "observational_association",
        "causal_claim": False,
        "source_type": "google-search-console",
        "property": "sc-domain:example.com",
        "search_type": "web",
        "filters": [],
        "export_method": "Search Console API export",
        "window": {"start": "2026-08-01T00:00:00Z", "end": "2026-08-08T00:00:00Z", "timezone": "UTC"},
        "raw_source_ref": "raw/gsc-export.json",
        "raw_source_sha256": raw_hash,
        "query_corpus_id": None,
        "query_corpus_ref": None,
        "query_corpus_sha256": None,
        "prior_run_id": None,
        "prior_run_ref": None,
        "prior_run_sha256": None,
        "dimensions": ["date", "query", "page"],
        "rows": [
            {
                "row_id": "performance-row-one",
                "date": "2026-08-02T00:00:00Z",
                "query": "example query",
                "page": "https://example.com/page",
                "country": None,
                "device": None,
                "search_appearance": None,
                "clicks": 10,
                "impressions": 100,
                "ctr": 0.1,
                "average_position": 4.5,
                "organic_sessions": None,
                "conversions": None,
                "revenue": None,
            }
        ],
        "indexation": [],
        "web_vitals": [],
        "data_quality": {
            "sampling_status": "none",
            "anonymized_queries": "excluded",
            "row_limit": 25000,
            "canonical_aggregation": "canonical",
            "notes": ["Search Console omits some anonymized queries."],
        },
        "drift": [],
        "limitations": ["The export is observational and may omit anonymized queries."],
    }


def raw_envelope(payload: dict) -> dict:
    return {
        "schema_version": "1.0.0",
        **{
            field: payload[field]
            for field in ("source_type", "property", "search_type", "filters", "export_method", "window", "dimensions", "rows", "indexation", "web_vitals")
        },
    }


class SeoPerformanceValidatorTests(unittest.TestCase):
    def run_case(self, mutate=None, bind_corpus: bool = False, corpus_mutate=None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            (bundle / "raw").mkdir()
            raw = bundle / "raw" / "gsc-export.json"
            payload = valid_run("0" * 64)
            raw.write_text(json.dumps(raw_envelope(payload)), encoding="utf-8")
            payload["raw_source_sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
            if bind_corpus:
                corpus = {
                    "schema_version": "1.0.0",
                    "corpus_id": "performance-corpus",
                    "research_id": None,
                    "research_sha256": None,
                    "created_at": "2026-08-10T10:00:00Z",
                    "frozen_at": "2026-08-10T09:00:00Z",
                    "scope": "Observed Search Console query used by this run.",
                    "queries": [
                        {
                            "query_id": "performance-query",
                            "need_id": "performance-need",
                            "query_type": "observed_search_query",
                            "text": "example query",
                            "locale": "en-US",
                            "country": None,
                            "location": None,
                            "device": "unspecified",
                            "engine": "google",
                            "surface": "web-search",
                            "parent_query_id": None,
                            "conversation_id": None,
                            "turn_index": None,
                            "intent": "informational",
                            "audience": "searcher",
                            "journey_stage": "awareness",
                            "target_entities": [],
                            "fact_ids": [],
                            "applicability": [{"engine": "google", "surface": "web-search"}],
                            "source": {
                                "source_kind": "first_party",
                                "source_url": "https://search.google.com/search-console",
                                "source_ref": None,
                                "source_sha256": None,
                                "observed_at": "2026-08-10T08:00:00Z",
                                "methodology": "Observed in the authorized export.",
                                "limitations": ["Some anonymized queries are unavailable."],
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
                                "limitations": ["The export is not a keyword-volume source."],
                            },
                            "coverage": {
                                "state": "covered",
                                "current_urls": ["https://example.com/page"],
                                "target_url": "https://example.com/page",
                                "competing_urls": [],
                                "evidence_ref": "raw/gsc-export.json",
                                "evidence_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
                            },
                            "confidence": "high",
                            "limitations": ["One first-party export row."],
                        }
                    ],
                    "limitations": ["The corpus does not reconstruct anonymized queries."],
                }
                if corpus_mutate is not None:
                    corpus_mutate(corpus)
                corpus_path = bundle / "query-corpus.json"
                corpus_path.write_text(json.dumps(corpus), encoding="utf-8")
                payload.update(
                    {
                        "query_corpus_id": corpus["corpus_id"],
                        "query_corpus_ref": "query-corpus.json",
                        "query_corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
                    }
                )
            if mutate is not None:
                mutate(payload)
            artifact = bundle / "seo-performance-run.json"
            artifact.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), "validate-run", str(artifact), "--bundle", str(bundle)],
                text=True,
                capture_output=True,
                check=False,
            )

    def run_comparison(self, mutate=None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            (bundle / "raw").mkdir()

            prior = valid_run("0" * 64)
            prior["run_id"] = "performance-prior"
            prior_raw = bundle / "raw" / "prior.json"
            prior["raw_source_ref"] = "raw/prior.json"
            prior_raw.write_text(json.dumps(raw_envelope(prior)), encoding="utf-8")
            prior["raw_source_sha256"] = hashlib.sha256(prior_raw.read_bytes()).hexdigest()
            prior_artifact = bundle / "prior-run.json"
            prior_artifact.write_text(json.dumps(prior), encoding="utf-8")

            current = valid_run("0" * 64)
            current.update(
                {
                    "run_id": "performance-current",
                    "created_at": "2026-08-16T12:00:00Z",
                    "mode": "comparison",
                    "window": {"start": "2026-08-08T00:00:00Z", "end": "2026-08-15T00:00:00Z", "timezone": "UTC"},
                    "prior_run_id": prior["run_id"],
                    "prior_run_ref": "prior-run.json",
                    "prior_run_sha256": hashlib.sha256(prior_artifact.read_bytes()).hexdigest(),
                }
            )
            current["rows"][0].update(
                {
                    "row_id": "performance-row-current",
                    "date": "2026-08-09T00:00:00Z",
                    "clicks": 15,
                    "ctr": 0.15,
                }
            )
            current["drift"] = [
                {
                    "drift_id": "clicks-window-drift",
                    "metric": "clicks",
                    "cohort": "All declared query/page rows",
                    "prior_record_ids": ["performance-row-one"],
                    "current_record_ids": ["performance-row-current"],
                    "prior_value": 10,
                    "current_value": 15,
                    "delta": 5,
                    "comparable": True,
                    "warning": None,
                }
            ]
            if mutate is not None:
                mutate(current)
            current_raw = bundle / "raw" / "current.json"
            current["raw_source_ref"] = "raw/current.json"
            current_raw.write_text(json.dumps(raw_envelope(current)), encoding="utf-8")
            current["raw_source_sha256"] = hashlib.sha256(current_raw.read_bytes()).hexdigest()
            artifact = bundle / "seo-performance-run.json"
            artifact.write_text(json.dumps(current), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), "validate-run", str(artifact), "--bundle", str(bundle)],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_valid_baseline_passes(self) -> None:
        completed = self.run_case()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS", completed.stdout)

    def test_valid_hash_bound_query_corpus_passes(self) -> None:
        completed = self.run_case(bind_corpus=True)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_bound_query_rows_must_belong_to_observed_search_corpus(self) -> None:
        completed = self.run_case(
            bind_corpus=True,
            corpus_mutate=lambda corpus: corpus["queries"][0].update({"text": "unrelated query"}),
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("outside the bound observed-search Query Corpus", completed.stderr)

    def test_partial_query_corpus_binding_fails(self) -> None:
        completed = self.run_case(lambda payload: payload.update({"query_corpus_id": "performance-corpus"}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("ID, reference, and hash", completed.stderr)

    def test_ctr_must_derive_from_clicks_and_impressions(self) -> None:
        completed = self.run_case(lambda payload: payload["rows"][0].update({"ctr": 0.9}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("clicks/impressions", completed.stderr)

    def test_non_finite_metric_is_rejected_even_when_raw_envelope_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            (bundle / "raw").mkdir()
            payload = valid_run("0" * 64)
            payload["rows"][0]["revenue"] = float("inf")
            raw = bundle / "raw" / "gsc-export.json"
            raw.write_text(json.dumps(raw_envelope(payload)), encoding="utf-8")
            payload["raw_source_sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
            artifact = bundle / "seo-performance-run.json"
            artifact.write_text(json.dumps(payload), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(VALIDATOR), "validate-run", str(artifact), "--bundle", str(bundle)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("must have type number or null", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)

    def test_normalized_rows_must_match_raw_envelope(self) -> None:
        completed = self.run_case(lambda payload: payload["rows"][0].update({"clicks": 99}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("do not match", completed.stderr)

    def test_empty_measurement_run_fails(self) -> None:
        def mutate(payload: dict) -> None:
            payload["rows"] = []
            payload["indexation"] = []
            payload["web_vitals"] = []

        completed = self.run_case(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("requires at least one measured", completed.stderr)

    def test_baseline_cannot_have_prior_run(self) -> None:
        completed = self.run_case(lambda payload: payload.update({"prior_run_id": "prior-example"}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("baseline prior-run", completed.stderr)

    def test_causal_language_fails(self) -> None:
        completed = self.run_case(lambda payload: payload.update({"limitations": ["The optimization caused traffic growth."]}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("causal language", completed.stderr)

    def test_valid_comparison_derives_drift_from_bound_records(self) -> None:
        completed = self.run_comparison()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_forged_comparison_values_fail(self) -> None:
        def mutate(payload: dict) -> None:
            payload["drift"][0].update({"prior_value": 999, "current_value": 1000, "delta": 1})

        completed = self.run_comparison(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("do not derive", completed.stderr)

    def test_changed_search_type_cannot_be_marked_comparable(self) -> None:
        completed = self.run_comparison(lambda payload: payload.update({"search_type": "image"}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("cannot be comparable", completed.stderr)

    def test_different_query_page_cohorts_cannot_be_marked_comparable(self) -> None:
        def mutate(payload: dict) -> None:
            payload["rows"][0].update({"query": "a completely different cohort", "page": "https://example.com/other"})

        completed = self.run_comparison(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("selected cohort", completed.stderr)

    def test_null_derived_drift_cannot_be_marked_comparable(self) -> None:
        def mutate(payload: dict) -> None:
            payload["drift"][0].update(
                {
                    "metric": "conversions",
                    "prior_value": None,
                    "current_value": None,
                    "delta": None,
                    "warning": "Conversions are unavailable in both windows.",
                }
            )

        completed = self.run_comparison(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("null value cannot be comparable", completed.stderr)


if __name__ == "__main__":
    unittest.main()
