from __future__ import annotations

import itertools
import unittest

import numpy as np
import stim

from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
from outputs.qshift_v1_4b_decoder_optimality.mld import ExactLogicalDecoder, dem_mechanisms


def random_dem(seed: int, detectors: int = 7, mechanisms: int = 13) -> stim.DetectorErrorModel:
    rng = np.random.default_rng(seed)
    lines = []
    for _ in range(mechanisms):
        k = int(rng.integers(1, 4))
        lo = int(rng.integers(0, detectors - k + 1))
        dets = sorted(rng.choice(range(lo, min(detectors, lo + 4)), size=min(k, min(detectors, lo + 4) - lo), replace=False))
        targets = " ".join(f"D{d}" for d in dets) + (" L0" if rng.random() < 0.4 else "")
        lines.append(f"error({rng.uniform(0.01, 0.3):.6f}) {targets}")
    lines.append(f"detector D{detectors - 1}")
    lines.append("logical_observable L0")
    return stim.DetectorErrorModel("\n".join(lines))


def brute_force(dem: stim.DetectorErrorModel) -> dict[tuple[tuple[int, ...], int], float]:
    mechs = dem_mechanisms(dem)
    out: dict = {}
    for bits in itertools.product((0, 1), repeat=len(mechs)):
        prob, s, l = 1.0, [0] * dem.num_detectors, 0
        for b, mm in zip(bits, mechs):
            prob *= mm.p if b else 1 - mm.p
            if b:
                for d in mm.detectors:
                    s[d] ^= 1
                l ^= mm.logical
        out[(tuple(s), l)] = out.get((tuple(s), l), 0.0) + prob
    return out


class ExactLogicalDecoderTests(unittest.TestCase):
    def test_matches_brute_force_on_random_dems(self) -> None:
        for seed in range(6):
            dem = random_dem(seed)
            ref = brute_force(dem)
            dec = ExactLogicalDecoder(dem)
            syndromes = np.asarray(list(itertools.product((0, 1), repeat=dem.num_detectors)), dtype=np.uint8)
            log_scale, table = dec.joint(syndromes)
            got = np.exp(log_scale)[:, None] * table
            for row, s in enumerate(syndromes):
                for l in (0, 1):
                    self.assertAlmostEqual(got[row, l], ref.get((tuple(int(x) for x in s), l), 0.0), places=12)
            self.assertAlmostEqual(float(got.sum()), 1.0, places=12)

    def test_merging_duplicate_signatures_is_exact(self) -> None:
        dem = stim.DetectorErrorModel("error(0.1) D0 L0\nerror(0.2) D0 L0\nerror(0.05) D0 D1\n")
        (a, b) = sorted(dem_mechanisms(dem), key=lambda x: x.detectors)
        self.assertAlmostEqual(a.p, 0.1 * 0.8 + 0.2 * 0.9)
        ref = brute_force(stim.DetectorErrorModel("error(0.26) D0 L0\nerror(0.05) D0 D1\n"))
        dec = ExactLogicalDecoder(dem)
        syn = np.asarray([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.uint8)
        log_scale, table = dec.joint(syn)
        got = np.exp(log_scale)[:, None] * table
        for row, s in enumerate(syn):
            for l in (0, 1):
                self.assertAlmostEqual(got[row, l], ref.get((tuple(int(x) for x in s), l), 0.0), places=12)

    def test_v1_1_dem_width_and_normalization(self) -> None:
        spec = m.CodeSpec()
        circuit = m.build_candidate_circuit(spec, 0.01, m.burst_qubits(spec, "scaled_v1"))
        dec = ExactLogicalDecoder(circuit.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True))
        self.assertEqual(dec.max_width, 11)
        # The all-zero syndrome must decode to the trivial class with high confidence.
        pred, post = dec.decode(np.zeros((1, 40), dtype=np.uint8))
        self.assertEqual(int(pred[0, 0]), 0)
        self.assertLess(post[0], 0.01)

    def test_pure_burst_syndrome_is_trivial_class(self) -> None:
        spec = m.CodeSpec()
        qubits = m.burst_qubits(spec, "scaled_v1")
        dem = m.build_candidate_circuit(spec, 0.02, qubits).detector_error_model(
            decompose_errors=False, approximate_disjoint_errors=True)
        dec = ExactLogicalDecoder(dem)
        for event in m.extract_burst_events(spec, qubits):
            row = np.zeros((1, 40), dtype=np.uint8)
            row[0, list(event.detector_ids)] = 1
            self.assertEqual(int(dec.decode(row)[0][0, 0]), event.observable_flip)


if __name__ == "__main__":
    unittest.main()
