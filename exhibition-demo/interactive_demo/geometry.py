"""Stim-derived geometry and detector-to-check mapping for the E1 demo.

This module only inspects circuit annotations. It never constructs a sampler.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import stim


DATA_QUBITS: tuple[int, ...] = (1, 3, 5, 8, 10, 12, 15, 17, 19)
DATA_COORDS: tuple[tuple[int, int], ...] = (
    (1, 1), (3, 1), (5, 1),
    (1, 3), (3, 3), (5, 3),
    (1, 5), (3, 5), (5, 5),
)


@dataclass(frozen=True)
class CheckSite:
    led_index: int
    stim_qubit: int
    x: int
    y: int
    basis: str


# Stable physical LED order. The basis labels are confirmed by the generated
# circuit's first Hadamard layer: q2/q11/q16/q25 enter the X-check path.
CHECK_SITES: tuple[CheckSite, ...] = (
    CheckSite(0, 2, 2, 0, "X"),
    CheckSite(1, 9, 2, 2, "Z"),
    CheckSite(2, 11, 4, 2, "X"),
    CheckSite(3, 13, 6, 2, "Z"),
    CheckSite(4, 14, 0, 4, "Z"),
    CheckSite(5, 16, 2, 4, "X"),
    CheckSite(6, 18, 4, 4, "Z"),
    CheckSite(7, 25, 4, 6, "X"),
)

TIME_SLICES = tuple(range(6))

# Noise operations present in the existing exhibition circuit. They are
# removed only from the deterministic signature reference; its Clifford,
# measurement, detector, observable, and coordinate instructions remain.
_NOISE_INSTRUCTIONS = frozenset(
    {
        "DEPOLARIZE1",
        "DEPOLARIZE2",
        "X_ERROR",
        "Y_ERROR",
        "Z_ERROR",
        "PAULI_CHANNEL_1",
        "PAULI_CHANNEL_2",
        "CORRELATED_ERROR",
        "ELSE_CORRELATED_ERROR",
        "HERALDED_ERASE",
        "HERALDED_PAULI_CHANNEL_1",
        "M_ERROR",
        "MXX_ERROR",
        "MYY_ERROR",
        "MZZ_ERROR",
    }
)


@dataclass(frozen=True)
class DetectorLocation:
    detector_id: int
    check_index: int
    time_index: int


@dataclass(frozen=True)
class SurfaceCodeGeometry:
    data_qubits: tuple[int, ...]
    data_coords: tuple[tuple[int, int], ...]
    checks: tuple[CheckSite, ...]
    detector_locations: tuple[DetectorLocation, ...]
    detector_count: int
    observable_count: int
    measurement_count: int

    def render_time_slices(self, detector_bits: Sequence[int | bool]) -> list[dict[str, object]]:
        """Project 40 detector events to six 8-check frames without losing time.

        `valid` is false where that check has no detector at a code boundary;
        `events` is false there and must be interpreted together with `valid`.
        """
        if len(detector_bits) != self.detector_count:
            raise ValueError(
                f"Expected {self.detector_count} detector bits, received {len(detector_bits)}"
            )
        valid = [[False] * len(self.checks) for _ in TIME_SLICES]
        events = [[False] * len(self.checks) for _ in TIME_SLICES]
        for location in self.detector_locations:
            valid[location.time_index][location.check_index] = True
            events[location.time_index][location.check_index] = bool(
                detector_bits[location.detector_id]
            )
        return [
            {
                "time_index": time_index,
                "valid": valid[time_index],
                "events": events[time_index],
            }
            for time_index in TIME_SLICES
        ]


def build_ideal_reference(noisy_circuit: stim.Circuit) -> stim.Circuit:
    """Remove stochastic channels from the existing generated circuit.

    No gate, reset, measurement, detector, observable, coordinate, or timing
    instruction is synthesized. Unsupported noise operations fail closed.
    """
    ideal = stim.Circuit()
    for instruction in noisy_circuit.flattened():
        name = instruction.name
        if name in _NOISE_INSTRUCTIONS:
            continue
        if "ERROR" in name or name.startswith("DEPOLARIZE") or name.startswith("HERALDED"):
            raise ValueError(f"Unreviewed stochastic instruction in reference circuit: {name}")
        ideal.append(instruction)

    if (ideal.num_detectors, ideal.num_observables, ideal.num_measurements) != (
        noisy_circuit.num_detectors,
        noisy_circuit.num_observables,
        noisy_circuit.num_measurements,
    ):
        raise RuntimeError("Removing noise changed the detector/readout structure")
    return ideal


def inspect_geometry(circuit: stim.Circuit) -> SurfaceCodeGeometry:
    """Verify and extract the pinned distance-3, five-round Stim geometry."""
    if circuit.num_detectors != 40 or circuit.num_observables != 1:
        raise ValueError(
            f"E1 expects 40 detectors and one observable; got "
            f"{circuit.num_detectors} and {circuit.num_observables}"
        )
    qubit_coords = circuit.get_final_qubit_coordinates()
    expected_data_coords = {
        1: (1, 1), 3: (3, 1), 5: (5, 1),
        8: (1, 3), 10: (3, 3), 12: (5, 3),
        15: (1, 5), 17: (3, 5), 19: (5, 5),
    }
    for qubit, expected in expected_data_coords.items():
        actual = qubit_coords.get(qubit)
        if actual is None or tuple(int(round(v)) for v in actual[:2]) != expected:
            raise ValueError(f"Unexpected data-qubit coordinate for Stim qubit {qubit}: {actual}")
    if len(qubit_coords) != 17:
        raise ValueError(f"Expected 17 coordinate-assigned code sites, got {len(qubit_coords)}")

    for site in CHECK_SITES:
        actual = qubit_coords.get(site.stim_qubit)
        if actual is None or tuple(int(round(v)) for v in actual[:2]) != (site.x, site.y):
            raise ValueError(f"Unexpected check coordinate for Stim qubit {site.stim_qubit}: {actual}")

    check_index_by_xy = {(site.x, site.y): site.led_index for site in CHECK_SITES}
    detector_coords = circuit.get_detector_coordinates()
    if len(detector_coords) != circuit.num_detectors:
        raise ValueError("Stim detector-coordinate metadata is incomplete")
    locations: list[DetectorLocation] = []
    seen: set[tuple[int, int]] = set()
    for detector_id in range(circuit.num_detectors):
        coords = detector_coords.get(detector_id)
        if coords is None or len(coords) != 3:
            raise ValueError(f"Detector {detector_id} has unexpected coordinates: {coords}")
        x, y, time_index = (int(round(v)) for v in coords)
        check_index = check_index_by_xy.get((x, y))
        if check_index is None or time_index not in TIME_SLICES:
            raise ValueError(f"Detector {detector_id} does not map to a known check/time: {coords}")
        key = (check_index, time_index)
        if key in seen:
            raise ValueError(f"Duplicate detector coordinate for check/time {key}")
        seen.add(key)
        locations.append(DetectorLocation(detector_id, check_index, time_index))

    expected_per_check = (4, 6, 4, 6, 6, 4, 6, 4)
    counts = [0] * len(CHECK_SITES)
    for item in locations:
        counts[item.check_index] += 1
    if tuple(counts) != expected_per_check:
        raise ValueError(f"Unexpected detector-event history per check: {counts}")
    return SurfaceCodeGeometry(
        data_qubits=DATA_QUBITS,
        data_coords=DATA_COORDS,
        checks=CHECK_SITES,
        detector_locations=tuple(locations),
        detector_count=circuit.num_detectors,
        observable_count=circuit.num_observables,
        measurement_count=circuit.num_measurements,
    )


def insert_single_fault_after_first_check_round(
    ideal_reference: stim.Circuit,
    stim_qubit: int,
    pauli: str,
    geometry: SurfaceCodeGeometry,
) -> stim.Circuit:
    """Add one controlled Pauli after the first measured stabilizer round."""
    pauli = pauli.upper()
    if pauli not in {"X", "Y", "Z"}:
        raise ValueError("Pauli must be X, Y, or Z")
    if stim_qubit not in geometry.data_qubits:
        raise ValueError("A controlled fault must target one of the nine data qubits")

    faulted = stim.Circuit()
    inserted = False
    for instruction in ideal_reference.flattened():
        faulted.append(instruction)
        if instruction.name == "MR" and not inserted:
            faulted.append(pauli, [stim_qubit])
            inserted = True
    if not inserted:
        raise RuntimeError("Reference circuit has no first stabilizer measurement boundary")
    if (faulted.num_detectors, faulted.num_observables, faulted.num_measurements) != (
        ideal_reference.num_detectors,
        ideal_reference.num_observables,
        ideal_reference.num_measurements,
    ):
        raise RuntimeError("Controlled fault changed circuit annotation dimensions")
    return faulted
