from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "scripts" / "validate_site_graph.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SiteGraphValidatorTests(unittest.TestCase):
    def run_case(self, mutate=None, homepage_html: str = '<body><a href="/product">Product</a></body>') -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            raw = bundle / "raw" / "homepage.html"
            raw.parent.mkdir()
            raw.write_text(homepage_html, encoding="utf-8")
            raw_hash = digest(raw)
            product_raw = bundle / "raw" / "product.html"
            product_raw.write_text('<h1>Product</h1>', encoding="utf-8")
            product_hash = digest(product_raw)
            payload = {
                "schema_version": "1.0.0",
                "graph_id": "site-graph-example",
                "created_at": "2026-08-10T12:00:00Z",
                "scope": {
                    "domains": ["example.com"],
                    "seed_node_ids": ["home-node"],
                    "excluded_patterns": ["/account"],
                    "collection_method": "Authorized bounded raw HTML capture.",
                    "capture_mode": "raw",
                    "max_urls": 100,
                    "completeness": "bounded",
                },
                "nodes": [
                    {
                        "node_id": "home-node",
                        "url": "https://example.com/",
                        "target_type": "web_page",
                        "locale": "en-US",
                        "http_status": 200,
                        "index_intent": "index",
                        "canonical_url": "https://example.com/",
                        "title": "Home",
                        "business_role": "Primary discovery hub",
                        "captured_at": "2026-08-10T11:00:00Z",
                        "capture_ref": "raw/homepage.html",
                        "capture_sha256": raw_hash,
                        "metadata_ref": "raw/homepage.metadata.json",
                        "metadata_sha256": "pending",
                    },
                    {
                        "node_id": "product-node",
                        "url": "https://example.com/product",
                        "target_type": "web_page",
                        "locale": "en-US",
                        "http_status": 200,
                        "index_intent": "index",
                        "canonical_url": "https://example.com/product",
                        "title": "Product",
                        "business_role": "Product detail",
                        "captured_at": "2026-08-10T11:00:00Z",
                        "capture_ref": "raw/product.html",
                        "capture_sha256": product_hash,
                        "metadata_ref": "raw/product.metadata.json",
                        "metadata_sha256": "pending",
                    },
                ],
                "edges": [
                    {
                        "edge_id": "home-product-edge",
                        "source_node_id": "home-node",
                        "target_node_id": "product-node",
                        "raw_href": "/product",
                        "location": "body",
                        "anchor_text": "Product",
                        "accessible_name": "Product",
                        "follow_state": "follow",
                        "discovery": "raw",
                        "edge_type": "contextual",
                        "captured_at": "2026-08-10T11:00:00Z",
                        "capture_ref": "raw/homepage.html",
                        "capture_sha256": raw_hash,
                        "metadata_ref": "raw/home-product-edge.metadata.json",
                        "metadata_sha256": "pending",
                    }
                ],
                "limitations": ["The graph is bounded to supplied pages."],
            }
            for node in payload["nodes"]:
                envelope = {
                    "schema_version": "1.0.0",
                    **{
                        field: node[field]
                        for field in (
                            "node_id", "url", "target_type", "locale", "http_status", "index_intent",
                            "canonical_url", "title", "captured_at", "capture_ref", "capture_sha256",
                        )
                    },
                }
                metadata_path = bundle / node["metadata_ref"]
                metadata_path.write_text(json.dumps(envelope), encoding="utf-8")
                node["metadata_sha256"] = digest(metadata_path)
            for edge in payload["edges"]:
                envelope = {
                    "schema_version": "1.0.0",
                    **{
                        field: edge[field]
                        for field in (
                            "edge_id", "source_node_id", "target_node_id", "raw_href", "location",
                            "anchor_text", "accessible_name", "follow_state", "discovery", "edge_type",
                            "captured_at", "capture_ref", "capture_sha256",
                        )
                    },
                }
                metadata_path = bundle / edge["metadata_ref"]
                metadata_path.write_text(json.dumps(envelope), encoding="utf-8")
                edge["metadata_sha256"] = digest(metadata_path)
            if mutate is not None:
                mutate(payload)
            artifact = bundle / "site-graph.json"
            artifact.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), "validate-graph", str(artifact), "--bundle", str(bundle)],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_valid_graph_passes(self) -> None:
        completed = self.run_case()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_edge_nodes_must_resolve(self) -> None:
        completed = self.run_case(lambda payload: payload["edges"][0].update({"target_node_id": "missing-node"}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("does not resolve", completed.stderr)

    def test_capture_hash_is_required(self) -> None:
        completed = self.run_case(lambda payload: payload["nodes"][0].update({"capture_sha256": "0" * 64}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("capture hash mismatch", completed.stderr)

    def test_graph_at_url_limit_cannot_claim_complete(self) -> None:
        def mutate(payload: dict) -> None:
            payload["scope"].update({"max_urls": 2, "completeness": "complete"})

        completed = self.run_case(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("cannot claim complete", completed.stderr)

    def test_edge_href_must_resolve_to_target_node(self) -> None:
        completed = self.run_case(lambda payload: payload["edges"][0].update({"raw_href": "/unrelated"}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("does not resolve to the target node URL", completed.stderr)

    def test_distinct_nodes_cannot_reuse_one_capture(self) -> None:
        def mutate(payload: dict) -> None:
            payload["nodes"][1]["capture_ref"] = payload["nodes"][0]["capture_ref"]
            payload["nodes"][1]["capture_sha256"] = payload["nodes"][0]["capture_sha256"]

        completed = self.run_case(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("capture_ref is reused", completed.stderr)

    def test_href_and_label_substrings_without_an_anchor_do_not_bind_an_edge(self) -> None:
        completed = self.run_case(homepage_html='<script>const route="/product"</script><p>Product</p>')
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("captured anchor href", completed.stderr)

    def test_node_fields_must_match_hash_pinned_metadata(self) -> None:
        def mutate(payload: dict) -> None:
            payload["nodes"][1].update(
                {
                    "title": "Fabricated title",
                    "canonical_url": "https://evil.example/hijack",
                    "http_status": 599,
                    "index_intent": "exclude",
                }
            )

        completed = self.run_case(mutate)
        self.assertNotEqual(completed.returncode, 0)
        for field in ("title", "canonical_url", "http_status", "index_intent"):
            self.assertIn(f".{field} does not match", completed.stderr)

    def test_edge_semantics_must_match_anchor_context_and_rel(self) -> None:
        completed = self.run_case(homepage_html='<body><a href="/product" rel="nofollow">Product</a></body>')
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("follow_state, location, or edge_type", completed.stderr)

        completed = self.run_case(homepage_html='<footer><a href="/product">Product</a></footer>')
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("follow_state, location, or edge_type", completed.stderr)

    def test_edge_discovery_must_match_declared_capture_mode(self) -> None:
        completed = self.run_case(lambda payload: payload["edges"][0].update({"discovery": "rendered"}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("scope.capture_mode=raw", completed.stderr)

    def test_one_graph_cannot_claim_both_raw_and_rendered_capture_modes(self) -> None:
        def mutate(payload: dict) -> None:
            payload["scope"]["capture_mode"] = "both"
            payload["edges"][0]["discovery"] = "both"

        completed = self.run_case(mutate)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("$.scope.capture_mode", completed.stderr)
        self.assertIn("$.edges[0].discovery", completed.stderr)

    def test_edge_fields_must_match_hash_pinned_metadata(self) -> None:
        completed = self.run_case(lambda payload: payload["edges"][0].update({"follow_state": "nofollow"}))
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("follow_state does not match its hash-pinned metadata envelope", completed.stderr)


if __name__ == "__main__":
    unittest.main()
