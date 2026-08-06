from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "manifests" / "artifact-schemas"

# The in-repository validator intentionally implements a compact, explicit
# JSON Schema subset. This guard prevents a future contract change from adding
# a keyword that the validator would silently ignore.
SUPPORTED = {
    "$defs",
    "$id",
    "$ref",
    "$schema",
    "additionalProperties",
    "allOf",
    "anyOf",
    "const",
    "else",
    "enum",
    "format",
    "if",
    "items",
    "minItems",
    "minLength",
    "not",
    "oneOf",
    "pattern",
    "properties",
    "required",
    "then",
    "title",
    "type",
    "uniqueItems",
}


def schema_keyword_set(schema: object) -> set[str]:
    if not isinstance(schema, dict):
        return set()
    keys = set(schema)
    for child in schema.get("properties", {}).values():
        keys.update(schema_keyword_set(child))
    for child in schema.get("$defs", {}).values():
        keys.update(schema_keyword_set(child))
    items = schema.get("items")
    if isinstance(items, dict):
        keys.update(schema_keyword_set(items))
    elif isinstance(items, list):
        for child in items:
            keys.update(schema_keyword_set(child))
    for keyword in ("allOf", "anyOf", "oneOf"):
        for child in schema.get(keyword, []):
            keys.update(schema_keyword_set(child))
    for keyword in ("not", "if", "then", "else"):
        keys.update(schema_keyword_set(schema.get(keyword)))
    return keys


class SchemaKeywordCoverageTests(unittest.TestCase):
    def test_every_contract_keyword_is_explicitly_supported(self) -> None:
        observed: set[str] = set()
        for path in SCHEMAS.glob("*.json"):
            observed.update(schema_keyword_set(json.loads(path.read_text(encoding="utf-8"))))
        self.assertEqual(observed - SUPPORTED, set())


if __name__ == "__main__":
    unittest.main()
