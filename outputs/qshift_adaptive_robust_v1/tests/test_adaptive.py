"""Deterministic unit tests for the adaptive-robust prototypes.

All data here are synthetic numpy Bernoulli arrays from literal test seeds (mathematical checks); no Stim
sampling, no study data, no protected evaluation material.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parents[1]
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(REPO))

from adaptive.changepoint import BinomialCUSUM, calibrate_threshold, run_length  # noqa: E402
from adaptive.estimation import estimate_background_scale, log_residual, rescaled_nominal  # noqa: E402
from adaptive.pipeline import AdaptiveController  # noqa: E402
from adaptive.regime import UNKNOWN, RegimeClassifier  # noqa: E402
from benchmark import endpoints as E  # noqa: E402
from benchmark import suite as S  # noqa: E402
from qshift_core_v1.contracts import DecoderMetadata, DecoderPrediction  # noqa: E402
from qshift_core_v1.controller import DecoderRegistry  # noqa: E402

N_DET = 120
NOMINAL = np.linspace(0.01, 0.03, N_DET)
BURST_DETS = (17, 18, 40)


def bernoulli(rates, shots, seed):
    return (np.random.default_rng(seed).random((shots, len(rates))) < rates).astype(np.uint8)


def with_burst(rates, q_eff):
    r = rates.copy()
    r[list(BURST_DETS)] = np.clip(r[list(BURST_DETS)] + q_eff, 0, 0.49)
    return r


class EstimationTests(unittest.TestCase):
    def test_recovers_global_scale_and_ignores_local_burst(self):
        for kappa in (0.83, 1.0, 1.17):
            det = bernoulli(with_burst(NOMINAL * kappa, 0.02), 40_000, seed=11)
            est = estimate_background_scale(det, NOMINAL)
            self.assertAlmostEqual(est.scale[0], kappa, delta=0.02)
            self.assertTrue(set(BURST_DETS) <= set(est.outlier_detectors))
            self.assertLessEqual(len(est.outlier_detectors), len(BURST_DETS) + 1)

    def test_naive_residual_offset_is_removed_by_rescaling(self):
        """The Phase C failure mode: a uniform residual offset under mismatch; rescaling removes it."""
        det = bernoulli(NOMINAL * 1.17, 40_000, seed=12)
        naive = np.median(log_residual(det, NOMINAL))
        fixed = np.median(log_residual(det, rescaled_nominal(NOMINAL, estimate_background_scale(det, NOMINAL))))
        self.assertGreater(naive, 0.1)
        self.assertLess(abs(fixed), 0.02)

    def test_per_class_scales_for_biased_noise(self):
        cls = (np.arange(N_DET) % 2).astype(int)
        true = NOMINAL * np.where(cls == 0, 0.6, 1.3)
        est = estimate_background_scale(bernoulli(true, 40_000, seed=13), NOMINAL, cls)
        self.assertAlmostEqual(est.scale[0], 0.6, delta=0.03)
        self.assertAlmostEqual(est.scale[1], 1.3, delta=0.04)

    def test_burst_free_no_outliers(self):
        est = estimate_background_scale(bernoulli(NOMINAL, 40_000, seed=14), NOMINAL)
        self.assertEqual(est.outlier_detectors, ())

    def test_input_validation(self):
        with self.assertRaises(ValueError):
            estimate_background_scale(np.zeros((10, 3), np.uint8), np.array([0.1, 0.2]))


class ChangePointTests(unittest.TestCase):
    r0, trials = 0.02, 120 * 200

    def test_calibrated_threshold_controls_false_alarms(self):
        h = calibrate_threshold(self.r0, 0.1, self.trials, 200, seed=21, runs=60)
        null = np.random.default_rng(22).binomial(self.trials, self.r0, size=(40, 200))
        alarms = sum(run_length(BinomialCUSUM(self.r0, 0.1, h, self.trials), row) is not None for row in null)
        self.assertLessEqual(alarms, 25)          # median run length >= 200 => well under all runs alarm

    def test_detects_step_change_quickly(self):
        h = calibrate_threshold(self.r0, 0.1, self.trials, 200, seed=21, runs=60)
        rng = np.random.default_rng(23)
        for factor in (1.17, 0.83):
            counts = np.concatenate([rng.binomial(self.trials, self.r0, 50),
                                     rng.binomial(self.trials, self.r0 * factor, 50)])
            c = BinomialCUSUM(self.r0, 0.1, h, self.trials)
            alarms = [t for t, x in enumerate(counts, 1) if c.update(int(x))]
            post = [t for t in alarms if t > 50]
            self.assertTrue(post and post[0] - 50 <= 10, (factor, alarms))


class RegimeTests(unittest.TestCase):
    regimes = {"nominal": NOMINAL, "burst": with_burst(NOMINAL, 0.02), "hot": NOMINAL * 1.3}

    def test_classifies_known_regimes(self):
        clf = RegimeClassifier(self.regimes)
        for i, (k, r) in enumerate(self.regimes.items()):
            res = clf.classify(bernoulli(r, 4_000, seed=30 + i))
            self.assertEqual(res.label, k)
            self.assertGreater(res.confidence, 0.99)

    def test_out_of_family_is_unknown(self):
        clf = RegimeClassifier(self.regimes)
        weird = NOMINAL.copy()
        weird[::3] *= 2.5                         # structured change matching no regime
        self.assertEqual(clf.classify(bernoulli(weird, 4_000, seed=35)).label, UNKNOWN)


class _ConstDecoder:
    def __init__(self, name, bit, experimental=False):
        self.metadata = DecoderMetadata(name=name, implementation="test", version="1", detector_count=N_DET,
                                        observable_count=1, experimental=experimental)
        self.bit = bit

    def decode(self, detectors):
        return DecoderPrediction(np.full((len(detectors), 1), self.bit, np.uint8), self.metadata)


class PipelineTests(unittest.TestCase):
    def make(self):
        reg = DecoderRegistry()
        reg.register("fixed", _ConstDecoder("fixed", 0))
        reg.register("burst_aware", _ConstDecoder("burst_aware", 1))
        clf = RegimeClassifier({"nominal": NOMINAL, "burst": with_burst(NOMINAL, 0.03)})
        return AdaptiveController(reg, "fixed", clf, {"nominal": "fixed", "burst": "burst_aware"}, NOMINAL,
                                  calibration_blocks=2, window_blocks=2)

    def test_causal_switch_with_hysteresis_and_fallback(self):
        ctl = self.make()
        rng_seed = 40
        blocks = ([NOMINAL] * 4) + ([with_burst(NOMINAL, 0.03)] * 6)
        recs = [ctl.step(t, bernoulli(r, 2_000, seed=rng_seed + t)) for t, r in enumerate(blocks)]
        chosen = [r.decision.selected_decoder for r in recs]
        self.assertTrue(all(c == "fixed" for c in chosen[:5]))      # calibration + causal lag
        first = chosen.index("burst_aware")
        self.assertGreaterEqual(first, 6)        # burst starts at block 4; needs evidence + hysteresis
        self.assertTrue(all(c == "burst_aware" for c in chosen[first:]))
        self.assertTrue(all((r.predictions == (1 if r.decision.selected_decoder == "burst_aware" else 0)).all()
                            for r in recs))

    def test_unknown_regime_falls_back(self):
        ctl = self.make()
        weird = NOMINAL.copy()
        weird[::3] *= 2.5
        blocks = ([with_burst(NOMINAL, 0.03)] * 6) + ([weird] * 3)
        recs = [ctl.step(t, bernoulli(r, 2_000, seed=60 + t)) for t, r in enumerate(blocks)]
        self.assertEqual(recs[5].decision.selected_decoder, "burst_aware")
        self.assertEqual(recs[-1].decision.selected_decoder, "fixed")
        self.assertEqual(recs[-2].regime, UNKNOWN)

    def test_api_has_no_label_channel(self):
        import inspect
        self.assertEqual(list(inspect.signature(AdaptiveController.step).parameters), ["self", "block", "detectors"])


def _cond(name, roots, shots, comp_f, cand_f, w=1.0, expected=None):
    return E.ConditionData(name, w, np.full(roots, shots), {"comp": np.array(comp_f), "cand": np.array(cand_f)},
                           expected if expected is not None else float(np.sum(comp_f)))


class EndpointTests(unittest.TestCase):
    def test_pooled_uses_failures_not_mean_of_ratios(self):
        a = _cond("a", 4, 1000, [50] * 4, [1] * 4)     # R = 0.98 at high baseline risk
        b = _cond("b", 4, 1000, [5] * 4, [2] * 4)      # R = 0.60 at low baseline risk
        pooled = E.pooled_reduction([a, b], "cand", "comp")
        self.assertAlmostEqual(pooled, 1 - (4 + 8) / (200 + 20), places=12)
        self.assertNotAlmostEqual(pooled, np.mean([0.98, 0.60]), places=3)

    def test_gates_need_lower_bounds_and_every_condition(self):
        rng = np.random.default_rng(70)
        strong = [_cond(f"c{i}", 24, 10_000, rng.poisson(40, 24), rng.poisson(0.4, 24)) for i in range(3)]
        g = E.gates(strong, "cand", "comp", target=0.95, alpha_agg=0.025, alpha_every=0.025, min_expected=30,
                    reps=2000, seed=71)
        self.assertEqual(g["G_AGG"], "PASS")
        weak = strong + [_cond("weak", 24, 10_000, rng.poisson(40, 24), rng.poisson(8, 24))]
        g2 = E.gates(weak, "cand", "comp", target=0.95, alpha_agg=0.025, alpha_every=0.025, min_expected=30,
                     reps=2000, seed=71)
        self.assertEqual(g2["G_EVERY"], "FAIL")
        self.assertLess(g2["worst_condition_R"], 0.95)

    def test_point_estimate_alone_cannot_pass(self):
        c = _cond("tiny", 6, 1000, [3, 4, 3, 4, 3, 4], [0, 0, 0, 0, 0, 1], expected=40)
        g = E.gates([c], "cand", "comp", target=0.95, alpha_agg=0.025, alpha_every=0.025, min_expected=30,
                    reps=2000, seed=72)
        self.assertGreater(g["R_pool"], 0.95)
        self.assertEqual(g["G_AGG"], "FAIL")

    def test_near_zero_conditions_are_ineligible_by_frozen_projection(self):
        a = _cond("ok", 4, 1000, [50] * 4, [1] * 4)
        z = _cond("zero", 4, 1000, [0] * 4, [0] * 4, expected=2.0)
        g = E.gates([a, z], "cand", "comp", target=0.9, alpha_agg=0.025, alpha_every=0.025, min_expected=30,
                    reps=500, seed=73)
        self.assertEqual(g["ineligible"], ["zero"])

    def test_power_formula(self):
        need = E.required_comparator_failures(0.97, 0.95, 0.025)
        self.assertTrue(400 < need < 900, need)
        self.assertGreater(E.required_comparator_failures(0.96, 0.95, 0.025), need)

    def test_holm(self):
        self.assertEqual(E.holm({"a": 0.001, "b": 0.02, "c": 0.04}, 0.05), {"a": True, "b": True, "c": True})
        self.assertEqual(E.holm({"a": 0.001, "b": 0.03, "c": 0.04}, 0.05), {"a": True, "b": False, "c": False})


class SuiteTests(unittest.TestCase):
    def test_splits_disjoint_and_complete(self):
        ids = [c.cid for c in S.ALL]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({c.split for c in S.ALL}, set(S.SPLITS))
        self.assertEqual(len(set(S.SEED_NAMESPACES.values())), len(S.SPLITS))

    def test_eval_uses_fresh_geometries_only(self):
        dev_val = {c.burst for c in S.by_split("dev") + S.by_split("val")}
        for c in S.by_split("eval"):
            self.assertTrue(c.burst == "none" or c.burst not in dev_val, c)

    def test_primary_and_safety_partition_eval(self):
        ev = S.by_split("eval")
        self.assertEqual(len(S.primary_conditions()) + len(S.safety_conditions()), len(ev))
        self.assertTrue(all(c.q == 0 for c in S.safety_conditions()))


if __name__ == "__main__":
    unittest.main()
