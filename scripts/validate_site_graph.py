from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urljoin, urlsplit

from bundle_safety import resolve_artifact_in_bundle, resolve_relative
from validate_ai_search_research import validate_schema_instance


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "manifests" / "artifact-schemas" / "site-graph.schema.json"
NODE_METADATA_FIELDS = {
    "schema_version", "node_id", "url", "target_type", "locale", "http_status", "index_intent",
    "canonical_url", "title", "captured_at", "capture_ref", "capture_sha256",
}
EDGE_METADATA_FIELDS = {
    "schema_version", "edge_id", "source_node_id", "target_node_id", "raw_href", "location",
    "anchor_text", "accessible_name", "follow_state", "discovery", "edge_type", "captured_at",
    "capture_ref", "capture_sha256",
}
VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, Any]] = []
        self.current: dict[str, Any] | None = None
        self.stack: list[tuple[str, dict[str, str | None]]] = []

    def location(self) -> str:
        context = " ".join(
            " ".join(
                [tag, *(value or "" for name, value in attrs.items() if name in {"class", "id", "role", "aria-label"})]
            )
            for tag, attrs in self.stack
        ).casefold()
        tags = {tag for tag, _attrs in self.stack}
        if "footer" in tags:
            return "footer"
        if "breadcrumb" in context:
            return "breadcrumb"
        if "pagination" in context or "pager" in context:
            return "pagination"
        if "facet" in context or "filter" in context:
            return "facet"
        if "nav" in tags or "navigation" in context:
            if "secondary" in context or "subnav" in context or "sub-nav" in context:
                return "secondary-navigation"
            return "primary-navigation"
        return "body"

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        values = {name.casefold(): value for name, value in attrs}
        if tag == "a":
            rel = {value for value in (values.get("rel") or "").casefold().split() if value}
            location = self.location()
            self.current = {
                "href": values.get("href"),
                "aria_label": values.get("aria-label"),
                "text": [],
                "follow_state": "nofollow" if "nofollow" in rel else "follow",
                "location": location,
                "edge_type": "contextual" if location == "body" else "template",
            }
        if tag not in VOID_ELEMENTS:
            self.stack.append((tag, values))

    def handle_data(self, data: str) -> None:
        if self.current is not None:
            self.current["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag == "a" and self.current is not None:
            self.current["text"] = " ".join("".join(self.current["text"]).split())
            self.links.append(self.current)
            self.current = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)


def captured_links(content: str) -> list[dict[str, Any]]:
    parser = LinkParser()
    parser.feed(content)
    parser.close()
    return parser.links


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


def validate_graph(path: Path, bundle: Path) -> None:
    errors: list[str] = []
    artifact = resolve_artifact_in_bundle(path, bundle, errors)
    if artifact is None or errors:
        fail(errors)
    try:
        payload = load(artifact)
    except (OSError, json.JSONDecodeError):
        fail(["site-graph.json is not valid JSON"])
    schema = load(SCHEMA_PATH)
    registry: dict[str, dict[str, Any]] = {schema["$id"]: schema}
    for name, definition in schema.get("$defs", {}).items():
        if isinstance(definition, dict):
            registry[f"#/$defs/{name}"] = definition
    validate_schema_instance(payload, schema, registry, "$", errors)
    if not isinstance(payload, dict):
        fail(errors or ["site-graph.json must contain an object"])

    created_at = parse_time(payload.get("created_at"), "$.created_at", errors)
    scope = payload.get("scope", {})
    domains = set(scope.get("domains", [])) if isinstance(scope, dict) else set()
    node_ids: set[str] = set()
    nodes: dict[str, dict[str, Any]] = {}
    urls: set[str] = set()
    node_capture_refs: set[str] = set()
    node_metadata_refs: set[str] = set()
    for index, node in enumerate(payload.get("nodes", []) if isinstance(payload.get("nodes"), list) else []):
        if not isinstance(node, dict):
            continue
        node_id = node.get("node_id")
        if isinstance(node_id, str) and node_id in node_ids:
            errors.append(f"nodes[{index}].node_id is duplicated")
        elif isinstance(node_id, str):
            node_ids.add(node_id)
            nodes[node_id] = node
        url = node.get("url")
        if isinstance(url, str):
            if url in urls:
                errors.append(f"nodes[{index}].url is duplicated")
            urls.add(url)
            if urlsplit(url).hostname not in domains:
                errors.append(f"nodes[{index}].url is outside declared domains")
        status = node.get("http_status")
        if not isinstance(status, int) or isinstance(status, bool) or not 100 <= status <= 599:
            errors.append(f"nodes[{index}].http_status must be between 100 and 599")
        captured_at = parse_time(node.get("captured_at"), f"nodes[{index}].captured_at", errors)
        if created_at is not None and captured_at is not None and captured_at > created_at:
            errors.append(f"nodes[{index}] was captured after graph creation")
        capture = resolve_relative(bundle, node.get("capture_ref"), f"nodes[{index}].capture_ref", errors)
        capture_ref = node.get("capture_ref")
        if isinstance(capture_ref, str) and capture_ref in node_capture_refs:
            errors.append(f"nodes[{index}].capture_ref is reused for a different node")
        elif isinstance(capture_ref, str):
            node_capture_refs.add(capture_ref)
        if capture is None or not capture.is_file() or digest(capture) != node.get("capture_sha256"):
            errors.append(f"nodes[{index}] capture hash mismatch")
        metadata_ref = node.get("metadata_ref")
        metadata = resolve_relative(bundle, metadata_ref, f"nodes[{index}].metadata_ref", errors)
        if isinstance(metadata_ref, str) and metadata_ref in node_metadata_refs:
            errors.append(f"nodes[{index}].metadata_ref is reused for a different node")
        elif isinstance(metadata_ref, str):
            node_metadata_refs.add(metadata_ref)
        if metadata is None or not metadata.is_file() or digest(metadata) != node.get("metadata_sha256"):
            errors.append(f"nodes[{index}] metadata hash mismatch")
        else:
            try:
                envelope = load(metadata)
            except (OSError, json.JSONDecodeError):
                errors.append(f"nodes[{index}] metadata envelope is not valid JSON")
            else:
                if not isinstance(envelope, dict) or set(envelope) != NODE_METADATA_FIELDS:
                    errors.append(f"nodes[{index}] metadata envelope must contain exactly the node capture fields")
                else:
                    if envelope.get("schema_version") != "1.0.0":
                        errors.append(f"nodes[{index}] metadata envelope schema_version must equal 1.0.0")
                    for field in NODE_METADATA_FIELDS - {"schema_version"}:
                        if envelope.get(field) != node.get(field):
                            errors.append(f"nodes[{index}].{field} does not match its hash-pinned metadata envelope")

    if isinstance(scope, dict):
        for seed in scope.get("seed_node_ids", []):
            if seed not in nodes:
                errors.append("scope.seed_node_ids must resolve to graph nodes")
        max_urls = scope.get("max_urls")
        if max_urls is not None and (not isinstance(max_urls, int) or isinstance(max_urls, bool) or max_urls <= 0):
            errors.append("scope.max_urls must be a positive integer or null")
        if scope.get("completeness") == "complete" and max_urls is not None and len(nodes) >= max_urls:
            errors.append("a graph that reached its URL limit cannot claim complete coverage")

    edge_ids: set[str] = set()
    edge_signatures: set[tuple[object, ...]] = set()
    edge_metadata_refs: set[str] = set()
    for index, edge in enumerate(payload.get("edges", []) if isinstance(payload.get("edges"), list) else []):
        if not isinstance(edge, dict):
            continue
        edge_id = edge.get("edge_id")
        if isinstance(edge_id, str) and edge_id in edge_ids:
            errors.append(f"edges[{index}].edge_id is duplicated")
        elif isinstance(edge_id, str):
            edge_ids.add(edge_id)
        source_node = nodes.get(edge.get("source_node_id"))
        target_node = nodes.get(edge.get("target_node_id"))
        if source_node is None or target_node is None:
            errors.append(f"edges[{index}] source/target node does not resolve")
        elif isinstance(edge.get("raw_href"), str):
            resolved_href = urldefrag(urljoin(source_node.get("url", ""), edge["raw_href"]))[0]
            target_url = urldefrag(target_node.get("url", ""))[0]
            if resolved_href != target_url:
                errors.append(f"edges[{index}].raw_href does not resolve to the target node URL")
            if edge.get("capture_ref") != source_node.get("capture_ref") or edge.get("capture_sha256") != source_node.get("capture_sha256"):
                errors.append(f"edges[{index}] capture must be the source node capture")
        if not any(isinstance(edge.get(field), str) and edge.get(field, "").strip() for field in ("anchor_text", "accessible_name")):
            errors.append(f"edges[{index}] requires anchor_text or accessible_name")
        signature = tuple(edge.get(field) for field in ("source_node_id", "target_node_id", "location", "anchor_text", "accessible_name", "discovery"))
        if signature in edge_signatures:
            errors.append(f"edges[{index}] duplicates a captured link edge")
        edge_signatures.add(signature)
        captured_at = parse_time(edge.get("captured_at"), f"edges[{index}].captured_at", errors)
        if created_at is not None and captured_at is not None and captured_at > created_at:
            errors.append(f"edges[{index}] was captured after graph creation")
        capture_mode = scope.get("capture_mode") if isinstance(scope, dict) else None
        if capture_mode in {"raw", "rendered"} and edge.get("discovery") != capture_mode:
            errors.append(f"edges[{index}].discovery must match scope.capture_mode={capture_mode}")
        capture = resolve_relative(bundle, edge.get("capture_ref"), f"edges[{index}].capture_ref", errors)
        if capture is None or not capture.is_file() or digest(capture) != edge.get("capture_sha256"):
            errors.append(f"edges[{index}] capture hash mismatch")
        elif isinstance(edge.get("raw_href"), str):
            capture_text = capture.read_bytes().decode("utf-8", errors="ignore")
            matching_links = [link for link in captured_links(capture_text) if link.get("href") == edge["raw_href"]]
            if not matching_links:
                errors.append(f"edges[{index}].raw_href is not a captured anchor href in its source capture")
            else:
                anchor_text = edge.get("anchor_text")
                accessible_name = edge.get("accessible_name")
                label_match = any(
                    (not isinstance(anchor_text, str) or not anchor_text.strip() or anchor_text == link.get("text"))
                    and (
                        not isinstance(accessible_name, str)
                        or not accessible_name.strip()
                        or accessible_name == (link.get("aria_label") or link.get("text"))
                    )
                    for link in matching_links
                )
                if not label_match:
                    errors.append(f"edges[{index}] labels do not match the captured anchor")
                semantic_match = any(
                    edge.get("follow_state") == link.get("follow_state")
                    and edge.get("location") == link.get("location")
                    and edge.get("edge_type") == link.get("edge_type")
                    for link in matching_links
                )
                if not semantic_match:
                    errors.append(f"edges[{index}] follow_state, location, or edge_type does not match the captured anchor context")
        metadata_ref = edge.get("metadata_ref")
        metadata = resolve_relative(bundle, metadata_ref, f"edges[{index}].metadata_ref", errors)
        if isinstance(metadata_ref, str) and metadata_ref in edge_metadata_refs:
            errors.append(f"edges[{index}].metadata_ref is reused for a different edge")
        elif isinstance(metadata_ref, str):
            edge_metadata_refs.add(metadata_ref)
        if metadata is None or not metadata.is_file() or digest(metadata) != edge.get("metadata_sha256"):
            errors.append(f"edges[{index}] metadata hash mismatch")
        else:
            try:
                envelope = load(metadata)
            except (OSError, json.JSONDecodeError):
                errors.append(f"edges[{index}] metadata envelope is not valid JSON")
            else:
                if not isinstance(envelope, dict) or set(envelope) != EDGE_METADATA_FIELDS:
                    errors.append(f"edges[{index}] metadata envelope must contain exactly the edge capture fields")
                else:
                    if envelope.get("schema_version") != "1.0.0":
                        errors.append(f"edges[{index}] metadata envelope schema_version must equal 1.0.0")
                    for field in EDGE_METADATA_FIELDS - {"schema_version"}:
                        if envelope.get(field) != edge.get(field):
                            errors.append(f"edges[{index}].{field} does not match its hash-pinned metadata envelope")

    if errors:
        fail(errors)
    print("PASS: site graph scope, nodes, edges, and capture integrity")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("validate-graph")
    command.add_argument("artifact", type=Path)
    command.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    validate_graph(args.artifact, args.bundle)


if __name__ == "__main__":
    main()
