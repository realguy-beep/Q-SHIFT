from fractions import Fraction
import importlib.util
from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("efactor_threshold_audit_v1.py")
SPEC = importlib.util.spec_from_file_location("qshift_efactor_threshold_v1", SOURCE)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class ThresholdBoundaryTests(unittest.TestCase):
    def test_exact_threshold_below_equal_and_above(self):
        self.assertFalse(audit.alarm_exact(Fraction(19)))
        self.assertTrue(audit.alarm_exact(Fraction(20)))
        self.assertTrue(audit.alarm_exact(Fraction(21)))

    def test_fixed_integer_threshold_cross_multiplication(self):
        q = audit.SCALE
        self.assertFalse(audit.alarm_fixed(19 * q + q // 2))
        self.assertTrue(audit.alarm_fixed(20 * q))
        self.assertTrue(audit.alarm_fixed(20 * q + 1))

    def test_alpha_one_fifth_uses_threshold_five(self):
        alpha = Fraction(1, 5)
        self.assertFalse(audit.alarm_exact(Fraction(499, 100), alpha))
        self.assertTrue(audit.alarm_exact(Fraction(5), alpha))
        self.assertFalse(audit.alarm_fixed(4 * audit.SCALE + audit.SCALE // 2, alpha))
        self.assertTrue(audit.alarm_fixed(5 * audit.SCALE, alpha))

    def test_rejects_invalid_alpha_and_integer_inputs(self):
        for bad in (Fraction(0), Fraction(6, 5)):
            with self.assertRaises(ValueError):
                audit.alarm_exact(Fraction(1), bad)
        with self.assertRaises(ValueError):
            audit.alarm_fixed(-1)


class FixedpointExhaustionTests(unittest.TestCase):
    def test_all_length_four_category_sequences_and_prefixes(self):
        certificate = __import__("json").loads(audit.CERTIFICATE.read_text(encoding="utf-8-sig"))
        result = audit.make_audit(certificate, length=4)
        self.assertEqual(len(result["directions"]), 2)
        for row in result["directions"]:
            self.assertEqual(row["distinct_category_prefixes_checked"], 6 + 36 + 216 + 1296)
            self.assertEqual(row["exact_recurrence_direct_sum_checks"], 1554)
            self.assertEqual(row["lower_bound_dominance_checks"], 1554)
            self.assertEqual(row["exact_mixture_crossing_prefixes"], row["fixedpoint_lower_crossing_prefixes"])
            self.assertEqual(row["legacy_loop_prefix_checks"], 5184)
            self.assertEqual(
                row["exact_mixture_crossing_prefixes"],
                239 if row["direction"] == "upward" else 0,
            )
            self.assertEqual(
                row["legacy_loop_corrected_crossing_prefixes_with_suffix_multiplicity"],
                244 if row["direction"] == "upward" else 0,
            )
            self.assertEqual(
                row["full_length_sequences_with_at_least_one_corrected_crossing"],
                238 if row["direction"] == "upward" else 0,
            )

    def test_corrected_and_historical_predicates_differ(self):
        q = audit.SCALE
        e_scaled_for_e20 = 20 * q
        self.assertTrue(audit.alarm_fixed(e_scaled_for_e20))
        # The checkpoint-133 comparison accepted E >= .05, so its predicate
        # would also accept this much smaller value.
        e_scaled_for_point_zero_five = q // 20
        self.assertFalse(audit.alarm_fixed(e_scaled_for_point_zero_five))


if __name__ == "__main__":
    unittest.main()
