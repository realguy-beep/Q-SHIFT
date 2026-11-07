"""Small Phase 3A spatial common-cause error prototype.

Adds an independent per-round correlated X burst on a neighboring pair of
data qubits to the frozen Phase 2B Stim circuit. This is a synthetic stochastic
proxy for a common control/crosstalk event, not a hardware-calibrated model.
"""
from __future__ import annotations

import sys
from pathlib import Path

import stim

REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE2B = REPO_ROOT / "outputs" / "phase2b_pauli_bias"
if str(PHASE2B) not in sys.path:
    sys.path.insert(0, str(PHASE2B))
from noise_model import build_circuit as build_phase2b_circuit  # noqa: E402


DEFAULT_BURST_PAIR = (8, 10)


def build_spatial_burst_circuit(*, memory_basis: str = "z", regime: str = "balanced",
                                distance: int = 3, rounds: int = 5,
                                gate_p: float = 0.003, measurement_p: float = 0.003,
                                bias_ratio: float = 10.0, burst_probability: float = 0.0,
                                burst_pair: tuple[int, int] = DEFAULT_BURST_PAIR) -> stim.Circuit:
    """Build frozen Phase 2B circuit plus one cross-location burst site/round.

    `burst_probability` is the probability of a simultaneous X error on both
    data qubits at each ancilla-measurement/reset boundary. The five events are
    independent across rounds; the correlation is spatial within each event.
    """
    if not 0 <= burst_probability <= 1:
        raise ValueError("burst_probability must lie in [0, 1]")
    if len(burst_pair) != 2 or burst_pair[0] == burst_pair[1]:
        raise ValueError("burst_pair must contain two distinct data qubits")

    base = build_phase2b_circuit(memory_basis, regime, distance=distance, rounds=rounds,
                                 gate_p=gate_p, measurement_p=measurement_p,
                                 bias_ratio=bias_ratio).flattened()
    data_qubits = {
        int(target.value)
        for instruction in base
        if instruction.name == "M"
        for target in instruction.targets_copy()
        if target.is_qubit_target
    }
    if not set(map(int, burst_pair)).issubset(data_qubits):
        raise ValueError(f"burst pair {burst_pair} must be data qubits; data set={sorted(data_qubits)}")

    out = stim.Circuit()
    round_boundaries = 0
    for instruction in base:
        out.append(instruction)
        if instruction.name == "MR":
            round_boundaries += 1
            if burst_probability > 0:
                out.append("CORRELATED_ERROR",
                           [stim.target_x(int(burst_pair[0])), stim.target_x(int(burst_pair[1]))],
                           float(burst_probability))
    if round_boundaries != rounds:
        raise RuntimeError(f"Expected {rounds} MR round boundaries; found {round_boundaries}")
    if out.num_detectors != base.num_detectors or out.num_observables != base.num_observables:
        raise RuntimeError("Correlation injection changed detector or observable definitions")
    return out


def build_isolated_burst_circuit(probability: float) -> stim.Circuit:
    """Minimal measurement fixture exposing both locations of one burst."""
    if not 0 <= probability <= 1:
        raise ValueError("probability must lie in [0, 1]")
    return stim.Circuit(
        f"R 0 1\nCORRELATED_ERROR({probability:.17g}) X0 X1\nM 0 1\n"
    )


def build_matching(circuit: stim.Circuit, *, enable_correlations: bool):
    """Construct PyMatching from the stated DEM conversion used in Phase 2B.

    Categorical PAULI_CHANNEL_2 sites require approximate_disjoint_errors=True
    in Stim's DEM converter. This approximation is shared by both arms.
    """
    import pymatching

    dem = circuit.detector_error_model(
        decompose_errors=True,
        approximate_disjoint_errors=True,
    )
    matching = pymatching.Matching.from_detector_error_model(
        dem, enable_correlations=enable_correlations
    )
    return dem, matching
