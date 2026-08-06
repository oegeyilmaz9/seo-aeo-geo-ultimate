from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PYTHON = sys.executable
VALIDATOR = ROOT / "scripts" / "validate_ai_visibility_monitor.py"
FIXTURE = ROOT / "evals" / "fixtures" / "aeo-normal"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


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

    def test_valid_baseline_visibility_run_passes(self) -> None:
        completed = self.run_visibility()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS: ai-visibility-monitor run", completed.stdout)

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
