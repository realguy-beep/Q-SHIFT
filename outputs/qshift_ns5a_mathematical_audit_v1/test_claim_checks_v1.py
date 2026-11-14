from decimal import Decimal, localcontext
from fractions import Fraction
import ast
import json
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent / "qshift_method_landscape_research_v1"


def direct_site_distribution(sites):
    states = {0: Fraction(1)}
    for outcomes in sites:
        nxt = {}
        for prior_mask, prior_p in states.items():
            for probability, mask in outcomes:
                merged = prior_mask ^ mask
                nxt[merged] = nxt.get(merged, Fraction(0)) + prior_p * probability
        states = nxt
    return states


def parity_character(sites, subset_mask):
    value = Fraction(1)
    for outcomes in sites:
        local = sum((p * (-1 if (mask & subset_mask).bit_count() % 2 else 1) for p, mask in outcomes), Fraction(0))
        value *= local
    return value


def mixture_freedman(n, alpha, weight, mu, variance, centered_bound):
    with localcontext() as ctx:
        ctx.prec = 90
        a = Decimal(alpha.denominator) / Decimal(alpha.numerator)
        a = (a / weight).ln()
        n_d = Decimal(n)
        x = n_d * mu - a
        if x <= 0:
            return Decimal(1)
        return (-(x * x) / (2 * (n_d * variance + centered_bound * x / 3))).exp()


class CategoricalLawTests(unittest.TestCase):
    def test_character_product_matches_exhaustive_xor_enumeration(self):
        sites = [
            [(Fraction(1, 2), 0), (Fraction(1, 4), 1), (Fraction(1, 4), 2)],
            [(Fraction(1, 3), 0), (Fraction(2, 3), 3)],
        ]
        dist = direct_site_distribution(sites)
        for subset in (0, 1, 2, 3):
            exhaustive = sum((p * (-1 if (mask & subset).bit_count() % 2 else 1) for mask, p in dist.items()), Fraction(0))
            self.assertEqual(parity_character(sites, subset), exhaustive)
        chi0, chi1, chi01 = (parity_character(sites, mask) for mask in (1, 2, 3))
        pair_cofire = (1 - chi0 - chi1 + chi01) / 4
        exhaustive_pair = sum((p for mask, p in dist.items() if (mask & 3) == 3), Fraction(0))
        self.assertEqual(pair_cofire, exhaustive_pair)

    def test_saved_burst_signatures_are_explicit_and_ordered(self):
        data = json.loads((PACKAGE / "CATEGORICAL_CIRCUIT_FEATURE_EXPECTATIONS.json").read_text(encoding="utf-8"))
        self.assertEqual(data["feature_count"], 45)
        self.assertEqual(data["fault_mapping"]["burst_detector_supports"], [[8, 10], [16, 18], [24, 26], [32, 34], [36, 38]])
        self.assertEqual(data["configuration"]["distance"], 3)
        self.assertEqual(data["configuration"]["rounds"], 5)


class EdgeAndEFactorTests(unittest.TestCase):
    def test_shared_edge_inversion_identity_on_boundaries_and_interior(self):
        a, b = Fraction(1, 7), Fraction(2, 11)
        for p in (Fraction(0), Fraction(1, 8), Fraction(1, 3), Fraction(1, 2)):
            pm = {0: 1 - a, 1: a}
            pn = {0: 1 - b, 1: b}
            shared = {0: 1 - p, 1: p}
            means = [Fraction(0), Fraction(0)]
            pair = Fraction(0)
            for x, px in pm.items():
                for y, py in pn.items():
                    for e, pe in shared.items():
                        di, dj = x ^ e, y ^ e
                        mass = px * py * pe
                        means[0] += mass * di
                        means[1] += mass * dj
                        pair += mass * di * dj
            covariance = pair - means[0] * means[1]
            denominator = 1 - 2 * (means[0] + means[1]) + 4 * pair
            radicand = Fraction(1, 4) - covariance / denominator
            self.assertEqual(radicand, (Fraction(1, 2) - p) ** 2)
            self.assertEqual(Fraction(1, 2) - (Fraction(1, 2) - p), p)

    def test_bounded_mean_e_factor_is_nonnegative_and_null_expectation_le_one(self):
        m0 = Fraction(1, 5)
        for lam in (Fraction(0), Fraction(1, 7), Fraction(1)):
            values = [1 + lam * (Fraction(x) / m0 - 1) for x in (0, 1)]
            self.assertGreaterEqual(min(values), 0)
            for mean in (Fraction(0), m0):
                expected = 1 + lam * (mean / m0 - 1)
                self.assertLessEqual(expected, 1)


class SavedCertificateTests(unittest.TestCase):
    def test_exact_rational_envelope_gap_and_dem_separation(self):
        data = json.loads((PACKAGE / "EXACT_THREE_PARAMETER_EFACTOR_ENVELOPE.json").read_text(encoding="utf-8"))
        null_upper = data["tensor_bernstein"]["null_box"]["exact_mean_upper_bound"]
        alt_lower = data["tensor_bernstein"]["high_box"]["exact_mean_lower_bound"]
        null = Fraction(int(null_upper["numerator"]), int(null_upper["denominator"]))
        alt = Fraction(int(alt_lower["numerator"]), int(alt_lower["denominator"]))
        self.assertGreater(alt, null)
        dem = json.loads((PACKAGE / "DEM_THREE_PARAMETER_ENVELOPE_TRANSFER.json").read_text(encoding="utf-8"))
        self.assertEqual(len(dem["finite_grid_violations"]["high_alternative_below_exact_lower"]), 1)

    def test_saved_mixture_delay_row_is_minimal_under_independent_formula(self):
        delays = json.loads((PACKAGE / "EFACTOR_MIXTURE_CHANGEPOINT_DELAY.json").read_text(encoding="utf-8"))
        alpha, delta, start = Fraction(1, 20), Decimal("0.1"), 1
        weight = Decimal(1) / Decimal(start * (start + 1))
        for arm in delays["arms"]:
            mu = Decimal(arm["conditional_log_drift_mu"])
            v = Decimal(arm["variance_upper_v"])
            c = Decimal(arm["centered_increment_bound_c"])
            row = next(r for r in arm["rows"] if r["candidate_change_start_shot"] == start and r["alpha"] == 0.05 and r["delta"] == 0.1)
            n = row["sufficient_postchange_shots"]
            self.assertLessEqual(mixture_freedman(n, alpha, weight, mu, v, c), delta)
            self.assertGreater(mixture_freedman(n - 1, alpha, weight, mu, v, c), delta)

    def test_new_audit_source_has_no_sampling_or_external_runtime_import(self):
        tree = ast.parse((HERE / "efactor_threshold_audit_v1.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        calls = {node.func.attr.lower() for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        self.assertFalse({"stim", "numpy", "pymatching"} & imported)
        self.assertFalse(any("sampl" in name for name in calls))


if __name__ == "__main__":
    unittest.main()
