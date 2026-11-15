"""Synthetic three-detector common-cause model and finite-factor decoder.

No sampler is called from this module. The candidate fault is a deliberately
synthetic common-cause X event on data qubits (8, 12, 15) after each MR round
boundary. Each round's event is an independent Bernoulli factor; the event's
detector support is retained as one factor by BurstEnumerationDecoder.
"""
from __future__ import annotations

from dataclasses import dataclass
import itertools
import math
import re
import sys
from pathlib import Path

import numpy as np
import stim
import pymatching


REPO = Path(__file__).resolve().parents[2]
PHASE3A = REPO / "outputs" / "phase3a_correlated_noise_preflight"
if str(PHASE3A) not in sys.path:
    sys.path.insert(0, str(PHASE3A))
from simulator import build_spatial_burst_circuit  # noqa: E402


BURST_QUBITS = (8, 12, 15)
PROBE_PROBABILITY = 0.01
DETECTOR_COUNT = 40
OBSERVABLE_COUNT = 1
MAX_BURST_PROBABILITY = 0.02


@dataclass(frozen=True)
class BurstEvent:
    detector_ids: tuple[int, ...]
    observable_flip: int


def build_base_circuit(*, gate_p: float = 0.003, measurement_p: float = 0.003) -> stim.Circuit:
    return build_spatial_burst_circuit(
        memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=gate_p, measurement_p=measurement_p, bias_ratio=10.0,
        burst_probability=0.0, burst_pair=(8, 10),
    )


def build_candidate_circuit(
    burst_probability: float, *, gate_p: float = 0.003, measurement_p: float = 0.003,
) -> stim.Circuit:
    """Add an independent triple-X common-cause site after each MR boundary."""
    q = float(burst_probability)
    if not math.isfinite(q) or not 0.0 <= q <= MAX_BURST_PROBABILITY:
        raise ValueError(f"burst_probability must be in [0,{MAX_BURST_PROBABILITY}]")
    base = build_base_circuit(gate_p=gate_p, measurement_p=measurement_p).flattened()
    out = stim.Circuit()
    boundaries = 0
    for instruction in base:
        out.append(instruction)
        if instruction.name == "MR":
            boundaries += 1
            if q > 0:
                out.append("CORRELATED_ERROR", [stim.target_x(k) for k in BURST_QUBITS], q)
    if boundaries != 5 or out.num_detectors != DETECTOR_COUNT or out.num_observables != OBSERVABLE_COUNT:
        raise RuntimeError("candidate circuit geometry changed")
    return out


def extract_burst_events() -> tuple[BurstEvent, ...]:
    """Derive the exact five event signatures from a noiseless deterministic DEM."""
    circuit = build_candidate_circuit(PROBE_PROBABILITY, gate_p=0.0, measurement_p=0.0)
    dem = circuit.detector_error_model(decompose_errors=False)
    events: list[BurstEvent] = []
    for line in str(dem).splitlines():
        if not line.startswith(f"error({PROBE_PROBABILITY:g}) "):
            continue
        detector_ids = tuple(int(value) for value in re.findall(r"D(\d+)", line))
        observable_ids = tuple(int(value) for value in re.findall(r"L(\d+)", line))
        if len(detector_ids) != 3 or len(set(detector_ids)) != 3:
            raise RuntimeError(f"expected a three-detector burst event, got: {line}")
        if any(not 0 <= value < DETECTOR_COUNT for value in detector_ids):
            raise RuntimeError("burst DEM detector ID is out of range")
        if any(not 0 <= value < OBSERVABLE_COUNT for value in observable_ids):
            raise RuntimeError("burst DEM observable ID is out of range")
        events.append(BurstEvent(tuple(sorted(detector_ids)), len(set(observable_ids)) % 2))
    if len(events) != 5 or len({event.detector_ids for event in events}) != 5:
        raise RuntimeError(f"expected five distinct burst factors, found {len(events)}")
    return tuple(events)


def build_decomposed_dem(circuit: stim.Circuit) -> stim.DetectorErrorModel:
    return circuit.detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=True
    )


def build_matching(dem: stim.DetectorErrorModel) -> pymatching.Matching:
    if dem.num_detectors != DETECTOR_COUNT or dem.num_observables != OBSERVABLE_COUNT:
        raise ValueError("DEM dimensions do not match the frozen circuit contract")
    return pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)


def _scalar_prediction(value) -> int:
    arr = np.asarray(value).reshape(-1)
    if arr.shape != (1,) or arr[0] not in (0, 1):
        raise RuntimeError("decoder returned an invalid single-observable prediction")
    return int(arr[0])


class BurstEnumerationDecoder:
    """Enumerate five burst factors; decode each residual with background MWPM.

    This is an explicit finite-factor hybrid, not exact maximum likelihood for
    the entire circuit. It chooses the minimum of background PyMatching edge
    weight plus independent burst-factor log-odds, preserving each triple
    syndrome as one candidate event instead of treating component edges as
    independent. Ties favor fewer burst events, then the lowest mask.
    """

    def __init__(self, background_matching: pymatching.Matching,
                 events: tuple[BurstEvent, ...], burst_probability: float):
        q = float(burst_probability)
        if not math.isfinite(q) or not 0.0 <= q <= MAX_BURST_PROBABILITY:
            raise ValueError("invalid burst probability")
        if len(events) != 5:
            raise ValueError("the frozen circuit requires exactly five burst factors")
        self.matching = background_matching
        self.events = events
        self.q = q
        self.edge_weights: dict[tuple[int, int], float] = {}
        self.edge_logical_parity: dict[tuple[int, int], int] = {}
        for u, v, data in background_matching.edges():
            key = (int(u), -1) if v is None else tuple(sorted((int(u), int(v))))
            if key in self.edge_weights:
                raise RuntimeError(f"parallel matching edge cannot be scored safely: {key}")
            self.edge_weights[key] = float(data["weight"])
            self.edge_logical_parity[key] = len(data["fault_ids"]) % 2

    def decode_one(self, detectors: np.ndarray) -> int:
        syndrome = np.asarray(detectors)
        if syndrome.shape != (DETECTOR_COUNT,) or not np.isin(syndrome, [0, 1]).all():
            raise ValueError("detectors must be a binary vector of length 40")
        if self.q == 0:
            return _scalar_prediction(self.matching.decode(syndrome, enable_correlations=True))

        log_odds = math.log((1.0 - self.q) / self.q)
        best: tuple[float, int, int, int] | None = None
        for mask in range(1 << len(self.events)):
            residual = np.asarray(syndrome, dtype=np.uint8).copy()
            logical = 0
            burst_count = 0
            for index, event in enumerate(self.events):
                if (mask >> index) & 1:
                    residual[list(event.detector_ids)] ^= 1
                    logical ^= event.observable_flip
                    burst_count += 1
            edges = self.matching.decode_to_edges_array(residual, enable_correlations=True)
            try:
                background_cost = 0.0
                background_logical = 0
                for edge in edges:
                    key = ((int(edge[0]), -1) if int(edge[1]) == -1
                           else tuple(sorted((int(edge[0]), int(edge[1])))))
                    background_cost += self.edge_weights[key]
                    background_logical ^= self.edge_logical_parity[key]
            except KeyError as exc:
                raise RuntimeError(f"PyMatching returned an unrecognized edge {exc}") from exc
            cost = float(background_cost + burst_count * log_odds)
            prediction = background_logical ^ logical
            candidate = (cost, burst_count, mask, prediction)
            if best is None or candidate < best:
                best = candidate
        assert best is not None
        return best[3]
    def decode_batch(self, detectors: np.ndarray) -> np.ndarray:
        x = np.asarray(detectors)
        if x.ndim != 2 or x.shape[1] != DETECTOR_COUNT or not np.isin(x, [0, 1]).all():
            raise ValueError("detectors must be a binary [shots,40] array")
        return np.asarray([self.decode_one(row) for row in x], dtype=np.uint8).reshape(-1, 1)


class BurstRateEstimator:
    """Training-only affine calibration of triple-cofire rate to burst p."""

    def __init__(self, events: tuple[BurstEvent, ...], max_probability: float = MAX_BURST_PROBABILITY):
        self.events = events
        self.max_probability = float(max_probability)

    def _rate(self, detectors: np.ndarray) -> float:
        x = np.asarray(detectors)
        if x.ndim != 2 or x.shape[1] != DETECTOR_COUNT or not np.isin(x, [0, 1]).all():
            raise ValueError("detectors must be a binary [shots,40] array")
        event_bits = np.column_stack([
            np.all(x[:, event.detector_ids] == 1, axis=1) for event in self.events
        ])
        return float(event_bits.mean())

    def fit(self, train_detectors: np.ndarray, probability_targets: np.ndarray) -> "BurstRateEstimator":
        x = np.asarray(train_detectors)
        y = np.asarray(probability_targets, dtype=np.float64).reshape(-1)
        if x.ndim != 2 or x.shape != (len(y), DETECTOR_COUNT) or len(y) == 0:
            raise ValueError("training arrays must be [shots,40] and aligned p targets")
        if not np.isin(x, [0, 1]).all() or not np.isfinite(y).all():
            raise ValueError("training arrays contain invalid values")
        probabilities = np.unique(y)
        if len(probabilities) < 2 or probabilities[0] < 0 or probabilities[-1] > self.max_probability:
            raise ValueError("training targets must cover at least two configured p values")
        rates = np.asarray([self._rate(x[y == q]) for q in probabilities], dtype=np.float64)
        if any(np.count_nonzero(y == q) < 100 for q in probabilities):
            raise ValueError("each training condition requires at least 100 rows")
        self.intercept, self.slope = map(float, np.polyfit(probabilities, rates, deg=1))
        if not math.isfinite(self.slope) or self.slope <= 0:
            raise RuntimeError("training data do not identify an increasing detector-only burst profile")
        self.training_condition_rates = {str(float(q)): float(rate) for q, rate in zip(probabilities, rates)}
        return self

    def estimate(self, calibration_detectors: np.ndarray) -> float:
        if not hasattr(self, "slope"):
            raise RuntimeError("estimator is not fitted")
        return float(np.clip((self._rate(calibration_detectors) - self.intercept) / self.slope,
                             0.0, self.max_probability))
