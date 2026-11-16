"""V1.4 distance-general common-cause burst model and five-factor decoder.

Generalizes outputs/qshift_correlated_decoder_feasibility_v1_1/model.py (left
unmodified) to any odd distance, round count and base noise. At the V1.1
parameters (d=3, 5 rounds, p=0.003, burst family "scaled_v1") every builder here
is pinned by tests to reproduce V1.1 exactly. No sampler is called in this module.

Burst support is fixed by a geometric rule declared before any d>=5 sampling and
never chosen by decoder performance. With data-qubit grid indices (col,row),
col,row in 0..d-1 and m=(d-1)//2:
  * "scaled_v1": (0,m), (d-1,m), (0,m+1)  -> at d=3 exactly V1.1's X8 X12 X15
  * "centre_row": (m-1,m), (m,m), (m+1,m) -> robustness family
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np
import pymatching
import stim

from outputs.phase2b_pauli_bias.noise_model import one_qubit_probabilities, two_qubit_probabilities

BURST_FAMILIES = ("scaled_v1", "centre_row")
PROBE_PROBABILITY = 0.01
MAX_BURST_PROBABILITY = 0.02


@dataclass(frozen=True)
class CodeSpec:
    distance: int = 3
    rounds: int = 5
    gate_p: float = 0.003
    measurement_p: float = 0.003
    bias_ratio: float = 10.0
    regime: str = "balanced"

    def __post_init__(self):
        if self.distance < 3 or self.distance % 2 == 0 or self.rounds < 1:
            raise ValueError("distance must be odd and >=3; rounds >=1")

    @property
    def detectors(self) -> int:
        return self.rounds * (self.distance ** 2 - 1)


@dataclass(frozen=True)
class BurstEvent:
    detector_ids: tuple[int, ...]
    observable_flip: int


def build_base_circuit(spec: CodeSpec) -> stim.Circuit:
    """Phase 2B noise model (explicit Pauli channels) at any distance; flattened.

    Text-identical to phase2b build_circuit(...).flattened() at d=3 (pinned by test);
    the d=3-only 40-detector assertion is replaced by rounds*(d^2-1).
    """
    p1 = one_qubit_probabilities(spec.regime, spec.gate_p, spec.bias_ratio)
    p2 = two_qubit_probabilities(spec.regime, spec.gate_p, spec.bias_ratio)
    generated = stim.Circuit.generated(
        "surface_code:rotated_memory_z", distance=spec.distance, rounds=spec.rounds,
        after_clifford_depolarization=0.003,  # placeholder; replaced below (as in Phase 2B)
        before_measure_flip_probability=spec.measurement_p,
    )
    body = str(generated)
    p1_text = "PAULI_CHANNEL_1(" + ",".join(format(v, ".17g") for v in p1) + ")"
    p2_text = "PAULI_CHANNEL_2(" + ",".join(format(v, ".17g") for v in p2) + ")"
    body, n1 = re.subn(r"DEPOLARIZE1\([^)]*\)", p1_text, body)
    body, n2 = re.subn(r"DEPOLARIZE2\([^)]*\)", p2_text, body)
    if n1 == 0 or n2 == 0:
        raise RuntimeError("expected generated 1Q and 2Q depolarizing locations")
    circuit = stim.Circuit(body).flattened()
    if circuit.num_detectors != spec.detectors or circuit.num_observables != 1:
        raise RuntimeError(f"unexpected circuit shape: {circuit.num_detectors} detectors")
    return circuit


def data_qubit_grid(spec: CodeSpec) -> dict[tuple[int, int], int]:
    """(col,row) -> qubit index for data qubits at coordinates (2col+1, 2row+1)."""
    circuit = build_base_circuit(spec)
    coords = circuit.get_final_qubit_coordinates()
    data = {int(t.value) for ins in circuit if ins.name == "M" for t in ins.targets_copy() if t.is_qubit_target}
    grid = {}
    for q in data:
        x, y = coords[q][:2]
        col, row = (int(x) - 1) // 2, (int(y) - 1) // 2
        if (int(x) - 1) % 2 or (int(y) - 1) % 2:
            raise RuntimeError("unexpected data-qubit coordinate")
        grid[(col, row)] = q
    if len(grid) != spec.distance ** 2:
        raise RuntimeError("data-qubit grid is incomplete")
    return grid


def burst_qubits(spec: CodeSpec, family: str) -> tuple[int, ...]:
    d, m = spec.distance, (spec.distance - 1) // 2
    cells = {"scaled_v1": [(0, m), (d - 1, m), (0, m + 1)],
             "centre_row": [(m - 1, m), (m, m), (m + 1, m)]}
    if family not in cells:
        raise ValueError(f"unknown burst family {family}")
    grid = data_qubit_grid(spec)
    return tuple(grid[c] for c in cells[family])


def build_candidate_circuit(spec: CodeSpec, q: float, qubits: tuple[int, ...]) -> stim.Circuit:
    """Base circuit plus an independent CORRELATED_ERROR(q) X-burst after each MR."""
    q = float(q)
    if not math.isfinite(q) or not 0.0 <= q <= MAX_BURST_PROBABILITY:
        raise ValueError(f"burst probability must be in [0,{MAX_BURST_PROBABILITY}]")
    out = stim.Circuit()
    boundaries = 0
    for instruction in build_base_circuit(spec):
        out.append(instruction)
        if instruction.name == "MR":
            boundaries += 1
            if q > 0:
                out.append("CORRELATED_ERROR", [stim.target_x(k) for k in qubits], q)
    if boundaries != spec.rounds or out.num_detectors != spec.detectors:
        raise RuntimeError("candidate circuit geometry changed")
    return out


def extract_burst_events(spec: CodeSpec, qubits: tuple[int, ...]) -> tuple[BurstEvent, ...]:
    """Exact per-round event signatures from a noiseless probe DEM."""
    noiseless = CodeSpec(spec.distance, spec.rounds, 0.0, 0.0, spec.bias_ratio, spec.regime)
    dem = build_candidate_circuit(noiseless, PROBE_PROBABILITY, qubits).detector_error_model(decompose_errors=False)
    events = []
    for line in str(dem).splitlines():
        if not line.startswith(f"error({PROBE_PROBABILITY:g}) "):
            continue
        dets = tuple(sorted(int(v) for v in re.findall(r"D(\d+)", line)))
        obs = re.findall(r"L(\d+)", line)
        if not dets or len(set(dets)) != len(dets) or any(not 0 <= v < spec.detectors for v in dets):
            raise RuntimeError(f"invalid burst event signature: {line}")
        events.append(BurstEvent(dets, len(obs) % 2))
    if len(events) != spec.rounds or len({e.detector_ids for e in events}) != spec.rounds:
        raise RuntimeError(f"expected {spec.rounds} distinct burst events, found {len(events)}")
    return tuple(events)


def build_decomposed_dem(circuit: stim.Circuit) -> stim.DetectorErrorModel:
    return circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)


def build_matching(dem: stim.DetectorErrorModel) -> pymatching.Matching:
    if dem.num_observables != 1:
        raise ValueError("expected one logical observable")
    return pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)


class FiveFactorDecoder:
    """Burst-subset enumeration (2^rounds masks) + background PyMatching, multi-prior.

    correlations=True reproduces the frozen V1.1 decoder (with its cost mismatch);
    correlations=False is V1.3's cost-consistent decoder. Same scoring, ties and
    q=0 fast path as V1.1/V1.3.
    """

    def __init__(self, background_matching: pymatching.Matching, events: tuple[BurstEvent, ...],
                 detectors: int, *, correlations: bool):
        self.matching = background_matching
        self.events = events
        self.detectors = int(detectors)
        self.correlations = bool(correlations)
        self.edge_weights: dict[tuple[int, int], float] = {}
        self.edge_logical_parity: dict[tuple[int, int], int] = {}
        for u, v, data in background_matching.edges():
            key = (int(u), -1) if v is None else tuple(sorted((int(u), int(v))))
            if key in self.edge_weights:
                raise RuntimeError(f"parallel matching edge cannot be scored safely: {key}")
            self.edge_weights[key] = float(data["weight"])
            self.edge_logical_parity[key] = len(data["fault_ids"]) % 2

    def options(self, syndrome: np.ndarray) -> list[tuple[int, int, float, int]]:
        out = []
        for mask in range(1 << len(self.events)):
            residual = np.asarray(syndrome, dtype=np.uint8).copy()
            logical = count = 0
            for index, event in enumerate(self.events):
                if (mask >> index) & 1:
                    residual[list(event.detector_ids)] ^= 1
                    logical ^= event.observable_flip
                    count += 1
            edges = self.matching.decode_to_edges_array(residual, enable_correlations=self.correlations)
            cost = 0.0
            parity = 0
            for edge in edges:
                key = ((int(edge[0]), -1) if int(edge[1]) == -1
                       else tuple(sorted((int(edge[0]), int(edge[1])))))
                try:
                    cost += self.edge_weights[key]
                    parity ^= self.edge_logical_parity[key]
                except KeyError as exc:
                    raise RuntimeError(f"PyMatching returned an unrecognized edge {exc}") from exc
            out.append((count, mask, float(cost), parity ^ logical))
        return out

    @staticmethod
    def choose(options, q: float) -> int:
        log_odds = math.log((1.0 - q) / q)
        return min((cost + count * log_odds, count, mask, prediction)
                   for count, mask, cost, prediction in options)[3]

    def decode_rows(self, detectors: np.ndarray, priors: dict[str, float]) -> dict[str, np.ndarray]:
        x = np.asarray(detectors)
        if x.ndim != 2 or x.shape[1] != self.detectors or not np.isin(x, [0, 1]).all():
            raise ValueError(f"detectors must be a binary [shots,{self.detectors}] array")
        for name, q in priors.items():
            if not math.isfinite(q) or not 0.0 <= q <= MAX_BURST_PROBABILITY:
                raise ValueError(f"invalid prior for {name}: {q}")
        out = {name: np.empty((len(x), 1), dtype=np.uint8) for name in priors}
        zero = [n for n, q in priors.items() if q == 0.0]
        positive = {n: q for n, q in priors.items() if q != 0.0}
        if zero:
            z = np.asarray([int(np.asarray(self.matching.decode(row, enable_correlations=self.correlations)).reshape(-1)[0])
                            for row in x], dtype=np.uint8)
            for n in zero:
                out[n][:, 0] = z
        if positive:
            for i, row in enumerate(x):
                opts = self.options(row)
                for n, q in positive.items():
                    out[n][i, 0] = self.choose(opts, q)
        return out


class BurstRateEstimator:
    """Training-only affine calibration of burst-signature cofire rate to q (as V1.1)."""

    def __init__(self, events: tuple[BurstEvent, ...], detectors: int,
                 max_probability: float = MAX_BURST_PROBABILITY):
        self.events = events
        self.detectors = int(detectors)
        self.max_probability = float(max_probability)

    def _rate(self, x: np.ndarray) -> float:
        x = np.asarray(x)
        if x.ndim != 2 or x.shape[1] != self.detectors or not np.isin(x, [0, 1]).all():
            raise ValueError(f"detectors must be a binary [shots,{self.detectors}] array")
        bits = np.column_stack([np.all(x[:, e.detector_ids] == 1, axis=1) for e in self.events])
        return float(bits.mean())

    def fit(self, x: np.ndarray, targets: np.ndarray) -> "BurstRateEstimator":
        y = np.asarray(targets, dtype=np.float64).reshape(-1)
        x = np.asarray(x)
        if x.shape != (len(y), self.detectors) or len(y) == 0:
            raise ValueError("training arrays must be aligned [shots,detectors]")
        qs = np.unique(y)
        if len(qs) < 2 or any(np.count_nonzero(y == q) < 100 for q in qs):
            raise ValueError("training needs >=2 conditions with >=100 rows each")
        rates = np.asarray([self._rate(x[y == q]) for q in qs])
        self.slope, self.intercept = map(float, np.polyfit(qs, rates, deg=1))
        if not math.isfinite(self.slope) or self.slope <= 0:
            raise RuntimeError("training data do not identify an increasing burst profile")
        self.training_condition_rates = {str(float(q)): float(r) for q, r in zip(qs, rates)}
        return self

    def estimate(self, x: np.ndarray) -> float:
        return float(np.clip((self._rate(x) - self.intercept) / self.slope, 0.0, self.max_probability))
