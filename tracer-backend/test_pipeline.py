import os
import unittest

os.environ.setdefault("GOOGLE_API_KEY", "test-key")

from pipeline import _resolve_verdict


class ValidationResolutionTest(unittest.TestCase):
    def test_compares_compatible_units_deterministically(self):
        verdict = _resolve_verdict(
            {"operator": "==", "value": "3.3", "unit": "V"},
            "3300 mV",
            "needs_review",
        )

        self.assertEqual(verdict, ("pass", "deterministic"))

    def test_fails_numeric_requirement_deterministically(self):
        verdict = _resolve_verdict(
            {"operator": ">=", "value": "1", "unit": "year"},
            "30 day",
            "pass",
        )

        self.assertEqual(verdict, ("fail", "deterministic"))

    def test_requires_review_for_unit_mismatch(self):
        verdict = _resolve_verdict(
            {"operator": ">=", "value": "1", "unit": "year"},
            "6 bananas",
            "pass",
        )

        self.assertEqual(verdict, ("needs_review", "unit_mismatch"))

    def test_requires_review_when_design_value_is_missing(self):
        verdict = _resolve_verdict(
            {"operator": "<=", "value": "250", "unit": "mA"},
            None,
            "pass",
        )

        self.assertEqual(verdict, ("needs_review", "incomplete_value"))


if __name__ == "__main__":
    unittest.main()
