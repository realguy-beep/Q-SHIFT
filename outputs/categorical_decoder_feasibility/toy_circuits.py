"""Analytically defined distance-1 repetition-memory toy circuits for audit."""
from __future__ import annotations

from itertools import product
from math import prod

import numpy as np
import pymatching
import stim

from categorical_reference import CategoricalLocation, CategoricalModel, FaultOutcome

PAULI_PAIRS = ("IX", "IY", "IZ", "XI", "XX", "XY", "XZ", "YI", "YX", "YY", "YZ", "ZI", "ZX", "ZY", "ZZ")
ONE_Q_PROBS = {"I": 0.94, "X": 0.02, "Y": 0.01, "Z": 0.03}
TWO_Q_NONIDENTITY_TOTAL = 0.12


def repetition_masks(paulis: tuple[str, str, str]) -> tuple[int, int]:
    """Return detector (D0,D1) and logical-Z parity masks for X/Y bit flips."""
    x = [int(p in ("X", "Y")) for p in paulis]
    s0 = x[0] ^ x[1]
    s1 = x[1] ^ x[2]
    detector_mask = s0 | (s1 << 1)
    logical_mask = x[0] ^ x[1] ^ x[2]
    return detector_mask, logical_mask


def one_qubit_model() -> CategoricalModel:
    locations = []
    for q in range(3):
        outcomes = []
        for p in "IXYZ":
            paulis = ["I", "I", "I"]
            paulis[q] = p
            dmask, lmask = repetition_masks(tuple(paulis))
            outcomes.append(FaultOutcome(p, ONE_Q_PROBS[p], dmask, lmask))
        locations.append(CategoricalLocation(f"one_qubit_q{q}", tuple(outcomes), "I"))
    model = CategoricalModel(2, 1, tuple(locations))
    model.validate()
    return model


def two_qubit_probabilities() -> dict[str, float]:
    # Distinct positive probabilities sum to 0.12; II has remaining 0.88.
    return {pair: TWO_Q_NONIDENTITY_TOTAL * rank / 120.0
            for rank, pair in enumerate(PAULI_PAIRS, start=1)}


def two_qubit_model() -> CategoricalModel:
    probs = two_qubit_probabilities()
    identity_prob = 1.0 - sum(probs.values())
    locations = []
    for loc_index, (q0, q1) in enumerate(((0, 1), (1, 2))):
        outcomes = [FaultOutcome("II", identity_prob, 0, 0)]
        for pair in PAULI_PAIRS:
            paulis = ["I", "I", "I"]
            paulis[q0], paulis[q1] = pair
            dmask, lmask = repetition_masks(tuple(paulis))
            outcomes.append(FaultOutcome(pair, probs[pair], dmask, lmask))
        locations.append(CategoricalLocation(f"two_qubit_pair_{loc_index}_{q0}{q1}",
                                              tuple(outcomes), "II"))
    model = CategoricalModel(2, 1, tuple(locations))
    model.validate()
    return model


def noisy_stim_circuit(kind: str) -> stim.Circuit:
    c = stim.Circuit()
    c.append("R", [0, 1, 2])
    if kind == "one_qubit":
        c.append("PAULI_CHANNEL_1", [0, 1, 2], [ONE_Q_PROBS[p] for p in "XYZ"])
    elif kind == "two_qubit":
        probs = [two_qubit_probabilities()[p] for p in PAULI_PAIRS]
        c.append("PAULI_CHANNEL_2", [0, 1, 1, 2], probs)
    else:
        raise ValueError("kind must be one_qubit or two_qubit")
    c.append("MZZ", [0, 1])
    c.append("DETECTOR", [stim.target_rec(-1)])
    c.append("MZZ", [1, 2])
    c.append("DETECTOR", [stim.target_rec(-1)])
    c.append("M", [0, 1, 2])
    c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1), stim.target_rec(-2), stim.target_rec(-3)], 0)
    if c.num_detectors != 2 or c.num_observables != 1:
        raise AssertionError("toy circuit detector/observable dimensions changed")
    return c


def deterministic_fault_circuit(kind: str, selected: tuple[FaultOutcome, ...]) -> stim.Circuit:
    """Create a deterministic Stim channel circuit with one-hot categorical outcomes."""
    c = stim.Circuit()
    c.append("R", [0, 1, 2])
    if kind == "one_qubit":
        for q, outcome in enumerate(selected):
            if outcome.label != "I":
                args = [int(outcome.label == p) for p in "XYZ"]
                c.append("PAULI_CHANNEL_1", [q], args)
    elif kind == "two_qubit":
        for (q0, q1), outcome in zip(((0, 1), (1, 2)), selected):
            pair = outcome.label
            if pair != "II":
                args = [int(pair == p) for p in PAULI_PAIRS]
                c.append("PAULI_CHANNEL_2", [q0, q1], args)
    else:
        raise ValueError("kind must be one_qubit or two_qubit")
    c.append("MZZ", [0, 1])
    c.append("DETECTOR", [stim.target_rec(-1)])
    c.append("MZZ", [1, 2])
    c.append("DETECTOR", [stim.target_rec(-1)])
    c.append("M", [0, 1, 2])
    c.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1), stim.target_rec(-2), stim.target_rec(-3)], 0)
    return c


def stim_exhaustive_joint(model: CategoricalModel, kind: str) -> tuple[dict[int, tuple[float, float]], int]:
    """Independent exhaustive route: enumerate locations directly and observe forced Stim outputs."""
    joint = {}
    count = 0
    # Deliberately do not call CategoricalModel.enumerate_configurations here.
    # The reference implementation has its own direct Cartesian-product loop;
    # Stim supplies the detector/observable mapping for each forced outcome.
    for selected in product(*(location.outcomes for location in model.locations)):
        probability = prod(outcome.probability for outcome in selected)
        c = deterministic_fault_circuit(kind, selected)
        # The circuit has only Pauli gates and Z-basis parity measurements, so
        # each chosen fault configuration yields deterministic detector/observable bits.
        dem = c.without_noise().detector_error_model(decompose_errors=True)
        if dem.num_detectors != 2 or dem.num_observables != 1:
            raise AssertionError("forced-fault circuit changed detector/observable count")
        detectors, observables = c.compile_detector_sampler(seed=1).sample(
            1, separate_observables=True)
        actual_s = int(detectors[0, 0]) | (int(detectors[0, 1]) << 1)
        actual_l = int(observables[0, 0])
        # Cross-check the model's separately declared masks against circuit outputs.
        detector_mask = 0
        observable_mask = 0
        for outcome in selected:
            detector_mask ^= outcome.detector_mask
            observable_mask ^= outcome.observable_mask
        if actual_s != detector_mask or actual_l != observable_mask:
            raise AssertionError(f"Stim vs analytic mapping mismatch: {(kind, selected, detector_mask, observable_mask, actual_s, actual_l)}")
        bucket = joint.setdefault(actual_s, [0.0, 0.0])
        bucket[actual_l] += probability
        count += 1
    return {s: tuple(v) for s, v in joint.items()}, count


def pymatching_decisions(kind: str, syndromes: list[int]) -> dict[str, dict[int, int]]:
    c = noisy_stim_circuit(kind)
    dem = c.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    if dem.num_detectors != 2 or dem.num_observables != 1:
        raise AssertionError("toy DEM dimensions do not match circuit")
    results = {"dem_text": str(dem), "dem_error_count": int(dem.num_errors),
               "dem_separator_count": str(dem).count("^"), "detectors": int(dem.num_detectors),
               "observables": int(dem.num_observables), "decoders": {}}
    for correlated in (False, True):
        name = "correlation_enabled" if correlated else "correlation_disabled"
        matcher = pymatching.Matching.from_detector_error_model(dem, enable_correlations=correlated)
        decisions = {}
        for syndrome in syndromes:
            bits = np.asarray([(syndrome >> j) & 1 for j in range(2)], dtype=np.uint8)
            prediction = np.asarray(matcher.decode(bits, enable_correlations=correlated), dtype=np.uint8).reshape(-1)
            if prediction.size != 1:
                raise AssertionError("PyMatching did not return one logical observable bit")
            decisions[syndrome] = int(prediction[0])
        results["decoders"][name] = {str(k): v for k, v in decisions.items()}
    return results

