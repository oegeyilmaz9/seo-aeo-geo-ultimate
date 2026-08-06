from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_ai_search_research import validate_schema_instance  # noqa: E402


class SchemaCombinatorTests(unittest.TestCase):
    def validate(self, value: object, schema: dict) -> list[str]:
        errors: list[str] = []
        validate_schema_instance(value, schema, {}, "$", errors)
        return errors

    def test_all_of_applies_every_branch(self) -> None:
        schema = {"allOf": [{"type": "string"}, {"minLength": 3}]}
        self.assertEqual(self.validate("valid", schema), [])
        self.assertTrue(self.validate("no", schema))

    def test_any_of_requires_at_least_one_matching_branch(self) -> None:
        schema = {"anyOf": [{"type": "string"}, {"type": "integer"}]}
        self.assertEqual(self.validate("answer", schema), [])
        self.assertEqual(self.validate(42, schema), [])
        self.assertIn("must match at least one anyOf branch", self.validate(False, schema)[0])

    def test_one_of_rejects_ambiguous_or_unmatched_values(self) -> None:
        schema = {"oneOf": [{"type": "integer"}, {"const": 2}]}
        self.assertEqual(self.validate(3, schema), [])
        self.assertIn("must match exactly one oneOf branch", self.validate(2, schema)[0])
        self.assertIn("must match exactly one oneOf branch", self.validate("two", schema)[0])

    def test_not_rejects_a_prohibited_match(self) -> None:
        schema = {"not": {"const": "forbidden"}}
        self.assertEqual(self.validate("allowed", schema), [])
        self.assertIn("must not match the prohibited schema", self.validate("forbidden", schema)[0])

    def test_conditional_selects_then_or_else_branch(self) -> None:
        schema = {
            "type": "object",
            "properties": {"kind": {"type": "string"}, "value": {}},
            "if": {"properties": {"kind": {"const": "number"}}, "required": ["kind"]},
            "then": {"properties": {"value": {"type": "number"}}, "required": ["value"]},
            "else": {"properties": {"value": {"type": "string"}}, "required": ["value"]},
        }
        self.assertEqual(self.validate({"kind": "number", "value": 3}, schema), [])
        self.assertEqual(self.validate({"kind": "text", "value": "three"}, schema), [])
        self.assertTrue(self.validate({"kind": "number", "value": "three"}, schema))
        self.assertTrue(self.validate({"kind": "text", "value": 3}, schema))


if __name__ == "__main__":
    unittest.main()
