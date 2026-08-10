from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "scripts" / "validate_query_corpus.py"
EMPTY_JSON_SHA256 = hashlib.sha256(b"{}").hexdigest()


def valid_corpus() -> dict:
    return {
        "schema_version": "1.0.0",
        "corpus_id": "query-corpus-example",
        "research_id": None,
        "research_sha256": None,
        "created_at": "2026-08-10T12:00:00Z",
        "frozen_at": "2026-08-10T11:00:00Z",
        "scope": "Turkish product-discovery prompt baseline",
        "queries": [
            {
                "query_id": "prompt-example",
                "need_id": "need-example",
                "query_type": "ai_prompt",
                "text": "Which product fits this need?",
                "locale": "tr-TR",
                "country": "TR",
                "location": "Istanbul",
                "device": "desktop",
                "engine": "openai",
                "surface": "chatgpt-search",
                "parent_query_id": None,
                "conversation_id": "conversation-example",
                "turn_index": 0,
                "intent": "commercial investigation",
                "audience": "buyer",
                "journey_stage": "consideration",
                "target_entities": ["product-example"],
                "fact_ids": ["fact-example"],
                "applicability": [{"engine": "openai", "surface": "chatgpt-search"}],
                "source": {
                    "source_kind": "first_party",
                    "source_url": "https://example.com/research",
                    "source_ref": "raw/source.json",
                    "source_sha256": EMPTY_JSON_SHA256,
                    "observed_at": "2026-08-10T10:00:00Z",
                    "methodology": "Mapped from a validated Research Pack.",
                    "limitations": ["No authenticated consumer-surface run."],
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
                    "limitations": ["No first-party or licensed demand source."],
                },
                "coverage": {
                    "state": "gap",
                    "current_urls": [],
                    "target_url": None,
                    "competing_urls": [],
                    "evidence_ref": "raw/coverage.json",
                    "evidence_sha256": EMPTY_JSON_SHA256,
                },
                "confidence": "medium",
                "limitations": ["Demand is unknown."],
            }
        ],
        "limitations": ["This corpus preserves questions; it does not predict ranking."],
    }


class QueryCorpusValidatorTests(unittest.TestCase):
    def run_case(self, mutate=None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            (bundle / "raw").mkdir()
            (bundle / "raw" / "source.json").write_text("{}", encoding="utf-8")
            (bundle / "raw" / "coverage.json").write_text("{}", encoding="utf-8")
            payload = valid_corpus()
            if mutate is not None:
                mutate(payload)
            artifact = bundle / "query-corpus.json"
            artifact.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), "validate-corpus", str(artifact), "--bundle", str(bundle)],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_valid_corpus_passes(self) -> None:
        completed = self.run_case()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS", completed.stdout)

    def test_executed_subquery_requires_observed_parent(self) -> None:
        def mutate(payload: dict) -> None:
            query = payload["queries"][0]
            query["query_type"] = "executed_subquery"
            query["source"]["source_kind"] = "editorial_hypothesis"

        completed = self.run_case(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("parent_query_id", completed.stderr)
        self.assertIn("direct_observation", completed.stderr)

    def test_unavailable_demand_cannot_invent_volume(self) -> None:
        completed = self.run_case(lambda payload: payload["queries"][0]["demand"].update({"monthly_volume": 500}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unavailable demand", completed.stderr)

    def test_source_hash_drift_fails(self) -> None:
        completed = self.run_case(
            lambda payload: payload["queries"][0]["source"].update({"source_sha256": "0" * 64})
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("source evidence hash mismatch", completed.stderr)

    def test_observed_search_query_cannot_be_an_editorial_hypothesis(self) -> None:
        def mutate(payload: dict) -> None:
            query = payload["queries"][0]
            query["query_type"] = "observed_search_query"
            query["source"].update(
                {
                    "source_kind": "editorial_hypothesis",
                    "source_url": None,
                    "source_ref": None,
                    "source_sha256": None,
                }
            )

        completed = self.run_case(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("observed_search_query requires", completed.stderr)

    def test_covered_state_requires_a_current_target_and_evidence(self) -> None:
        def mutate(payload: dict) -> None:
            payload["queries"][0]["coverage"].update(
                {
                    "state": "covered",
                    "current_urls": [],
                    "target_url": None,
                    "evidence_ref": None,
                    "evidence_sha256": None,
                }
            )

        completed = self.run_case(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("covered coverage requires at least one current URL", completed.stderr)
        self.assertIn("asserted coverage state requires hash-pinned evidence", completed.stderr)

    def test_observed_demand_requires_dated_source_provenance(self) -> None:
        def mutate(payload: dict) -> None:
            payload["queries"][0]["demand"].update(
                {
                    "status": "observed",
                    "monthly_volume": 100,
                    "provider": "Example provider",
                    "observed_at": "2026-08-10T09:00:00Z",
                }
            )

        completed = self.run_case(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("requires a source URL or hash-pinned source file", completed.stderr)

    def test_parent_cycle_fails(self) -> None:
        def mutate(payload: dict) -> None:
            first = payload["queries"][0]
            first["query_type"] = "executed_subquery"
            first["parent_query_id"] = "subquery-two"
            first["source"]["source_kind"] = "direct_observation"
            second = json.loads(json.dumps(first))
            second["query_id"] = "subquery-two"
            second["parent_query_id"] = "prompt-example"
            second["conversation_id"] = "conversation-two"
            payload["queries"].append(second)

        completed = self.run_case(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("cycle", completed.stderr)


if __name__ == "__main__":
    unittest.main()
