from __future__ import annotations

import unittest

import numpy as np

from outputs.qshift_correlated_decoder_feasibility_v1_1 import model as v11
from outputs.qshift_correlated_decoder_v1_3.multi_prior import ModeAwareFiveFactor
from outputs.qshift_correlated_decoder_v1_3.tests.test_mode_aware_decoder import fixture_syndromes
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m

V11 = m.CodeSpec()  # d=3, 5 rounds, p=0.003, balanced, bias 10
PRIORS = {"zero": 0.0, "small": 0.0025, "mid": 0.01, "max": 0.02}


def sparse_syndromes(detectors: int, events, seed: int, n: int = 60) -> np.ndarray:
    rng = np.random.default_rng(seed)
    rows = [np.zeros(detectors, dtype=np.uint8)]
    for event in events:
        row = np.zeros(detectors, dtype=np.uint8)
        row[list(event.detector_ids)] = 1
        rows.append(row)
    for _ in range(n):
        row = np.zeros(detectors, dtype=np.uint8)
        row[rng.choice(detectors, size=int(rng.integers(1, 7)), replace=False)] = 1
        rows.append(row)
    for event in events:
        row = np.zeros(detectors, dtype=np.uint8)
        row[list(event.detector_ids)] = 1
        row[rng.choice(detectors, size=2, replace=False)] ^= 1
        rows.append(row)
    return np.vstack(rows)


class D3EquivalenceTests(unittest.TestCase):
    """At V1.1 parameters, the generalized model must reproduce V1.1 exactly."""

    def test_base_circuit_text_identical(self) -> None:
        self.assertEqual(str(m.build_base_circuit(V11)), str(v11.build_base_circuit().flattened()))

    def test_scaled_v1_family_is_exactly_v1_1_burst(self) -> None:
        self.assertEqual(m.burst_qubits(V11, "scaled_v1"), v11.BURST_QUBITS)

    def test_candidate_circuit_text_identical(self) -> None:
        qubits = m.burst_qubits(V11, "scaled_v1")
        for q in (0.0, 0.0025, 0.01, 0.02):
            self.assertEqual(str(m.build_candidate_circuit(V11, q, qubits)), str(v11.build_candidate_circuit(q)), q)

    def test_events_identical(self) -> None:
        got = m.extract_burst_events(V11, m.burst_qubits(V11, "scaled_v1"))
        self.assertEqual([(e.detector_ids, e.observable_flip) for e in got],
                         [(e.detector_ids, e.observable_flip) for e in v11.extract_burst_events()])

    def test_decoder_predictions_identical_both_modes(self) -> None:
        events = m.extract_burst_events(V11, m.burst_qubits(V11, "scaled_v1"))
        base14 = m.build_matching(m.build_decomposed_dem(m.build_base_circuit(V11)))
        base11 = v11.build_matching(v11.build_decomposed_dem(v11.build_base_circuit()))
        x = fixture_syndromes()
        for correlations in (True, False):
            got = m.FiveFactorDecoder(base14, events, V11.detectors, correlations=correlations).decode_rows(x, PRIORS)
            ref = ModeAwareFiveFactor(base11, v11.extract_burst_events(), correlations=correlations).decode_rows(x, PRIORS)
            for name in PRIORS:
                np.testing.assert_array_equal(got[name], ref[name], err_msg=f"{correlations} {name}")

    def test_estimator_identical(self) -> None:
        rng = np.random.default_rng(7)
        x = (rng.random((900, 40)) < 0.05).astype(np.uint8)
        y = np.repeat([0.0, 0.01, 0.02], 300)
        for row, q in zip(x, y):  # make the cofire rate rise with q
            if rng.random() < 40 * q:
                row[[5, 7, 10]] = 1
        a = m.BurstRateEstimator(m.extract_burst_events(V11, v11.BURST_QUBITS), 40).fit(x, y)
        b = v11.BurstRateEstimator(v11.extract_burst_events()).fit(x, y)
        self.assertEqual((a.slope, a.intercept), (b.slope, b.intercept))
        self.assertEqual(a.estimate(x[:200]), b.estimate(x[:200]))


class LargerDistanceTests(unittest.TestCase):
    def test_shapes_events_and_families(self) -> None:
        for d in (5, 7):
            spec = m.CodeSpec(distance=d, gate_p=0.001, measurement_p=0.001)
            self.assertEqual(m.build_base_circuit(spec).num_detectors, 5 * (d * d - 1))
            grid = m.data_qubit_grid(spec)
            for family in m.BURST_FAMILIES:
                qubits = m.burst_qubits(spec, family)
                self.assertEqual(len(set(qubits)), 3)
                self.assertTrue(set(qubits) <= set(grid.values()))
                events = m.extract_burst_events(spec, qubits)
                self.assertEqual(len(events), 5)

    def test_d5_off_mode_cost_equals_pymatching_solution_weight(self) -> None:
        spec = m.CodeSpec(distance=5, gate_p=0.001, measurement_p=0.001)
        events = m.extract_burst_events(spec, m.burst_qubits(spec, "scaled_v1"))
        base = m.build_matching(m.build_decomposed_dem(m.build_base_circuit(spec)))
        dec = m.FiveFactorDecoder(base, events, spec.detectors, correlations=False)
        for row in sparse_syndromes(spec.detectors, events, 5)[:40]:
            for _, mask, cost, _ in dec.options(row):
                residual = row.copy()
                for i, event in enumerate(events):
                    if (mask >> i) & 1:
                        residual[list(event.detector_ids)] ^= 1
                _, weight = base.decode(residual, return_weight=True, enable_correlations=False)
                self.assertLess(abs(cost - float(weight)), 1e-5)

    def test_d5_burst_only_syndromes_are_removed_exactly(self) -> None:
        # A pure burst syndrome must be explained by the burst factor, giving its logical flip.
        spec = m.CodeSpec(distance=5, gate_p=0.001, measurement_p=0.001)
        events = m.extract_burst_events(spec, m.burst_qubits(spec, "scaled_v1"))
        base = m.build_matching(m.build_decomposed_dem(m.build_base_circuit(spec)))
        dec = m.FiveFactorDecoder(base, events, spec.detectors, correlations=False)
        for event in events:
            row = np.zeros((1, spec.detectors), dtype=np.uint8)
            row[0, list(event.detector_ids)] = 1
            self.assertEqual(int(dec.decode_rows(row, {"q": 0.02})["q"][0, 0]), event.observable_flip)


if __name__ == "__main__":
    unittest.main()
