"""Stepwise single-fault simulator for the isolated exhibition page.

The decoder receives detector bits only. The known injected fault and the
simulator's reference observable are kept in separate fields.
"""
from __future__ import annotations

import threading
from typing import Any, Callable

import numpy as np
import stim

from .geometry import (
    DATA_QUBITS,
    SurfaceCodeGeometry,
    build_ideal_reference,
    insert_single_fault_after_first_check_round,
    inspect_geometry,
)


TABLEAU_MEASUREMENT_SEED = 0x51534849


class InvalidTransition(ValueError):
    """Raised when a demo action is not valid for the current step."""


class InteractiveDemoEngine:
    """Thread-safe deterministic educational state machine.

    `circuit_factory` must be the existing exhibition `make_circuit` function.
    It is called with zero burst probability only to read circuit structure;
    its returned stochastic channels are stripped before deterministic use.
    `decoder_factory` is the existing nominal PyMatching constructor.
    """

    def __init__(
        self,
        circuit_factory: Callable[[float], stim.Circuit],
        decoder_factory: Callable[[float], Any],
    ) -> None:
        self._lock = threading.RLock()
        self._decoder_factory = decoder_factory
        source_circuit = circuit_factory(0.0)
        self._reference_circuit = build_ideal_reference(source_circuit)
        self.geometry: SurfaceCodeGeometry = inspect_geometry(self._reference_circuit)
        if self._reference_circuit.get_detector_coordinates() != source_circuit.get_detector_coordinates():
            raise RuntimeError("Noise stripping changed detector-coordinate mapping")
        self._converter = self._reference_circuit.compile_m2d_converter()
        self._phase = "idle"
        self._transitions: list[str] = ["idle"]
        self._fault_input: dict[str, Any] | None = None
        self._detectors: np.ndarray | None = None
        self._observable: int | None = None
        self._prediction: int | None = None
        self._run_id = 0
        self._display_slice_index = 0

    @property
    def phase(self) -> str:
        with self._lock:
            return self._phase

    def inject_and_prepare_syndrome(self, data_index: int = 4, pauli: str = "X") -> dict[str, Any]:
        """Record a known single fault, then derive its response from Stim."""
        if isinstance(data_index, bool) or not isinstance(data_index, int) or not 0 <= data_index < 9:
            raise ValueError("data_index must be an integer from 0 through 8")
        pauli = str(pauli).upper()
        if pauli not in {"X", "Y", "Z"}:
            raise ValueError("pauli must be X, Y, or Z")

        with self._lock:
            if self._phase != "idle":
                raise InvalidTransition("Reset the current trial before injecting another fault")
            qubit = DATA_QUBITS[data_index]
            self._run_id += 1
            self._phase = "injected"
            self._transitions = ["idle", "injected"]
            self._fault_input = {
                "data_index": data_index,
                "stim_qubit": qubit,
                "pauli": pauli,
                "known_simulated_input": True,
                "injection_after_measurement_round": 1,
            }
            faulted = insert_single_fault_after_first_check_round(
                self._reference_circuit, qubit, pauli, self.geometry
            )

            # This is one fixed-seed, noiseless Clifford/tableau trajectory.
            # No detector sampler, stochastic noise channel, or shot batch runs.
            simulator = stim.TableauSimulator(seed=TABLEAU_MEASUREMENT_SEED)
            simulator.do(faulted)
            measurements = np.asarray(
                simulator.current_measurement_record(), dtype=np.bool_
            )[None, :]
            detectors, observables = self._converter.convert(
                measurements=measurements,
                separate_observables=True,
            )
            detectors = np.asarray(detectors, dtype=np.bool_).reshape(1, -1)
            observables = np.asarray(observables, dtype=np.bool_).reshape(1, -1)
            if detectors.shape != (1, self.geometry.detector_count):
                raise RuntimeError(f"Unexpected deterministic detector shape: {detectors.shape}")
            if observables.shape != (1, 1):
                raise RuntimeError(f"Unexpected deterministic observable shape: {observables.shape}")
            self._detectors = detectors[0].astype(np.uint8, copy=True)
            self._observable = int(observables[0, 0])
            self._prediction = None
            self._phase = "syndrome_ready"
            self._transitions.append("syndrome_ready")
            return self.snapshot()

    def decode(self) -> dict[str, Any]:
        """Decode only the detector vector and reveal simulation truth afterward."""
        with self._lock:
            if self._phase != "syndrome_ready" or self._detectors is None:
                raise InvalidTransition("Inject a simulated fault before decoding")
            detector_input = self._detectors.copy()
            decoder = self._decoder_factory(0.0)
            # The observable label is deliberately not passed to the decoder.
            prediction = np.asarray(decoder.decode(detector_input), dtype=np.uint8).reshape(-1)
            if prediction.size != 1 or int(prediction[0]) not in (0, 1):
                raise RuntimeError("PyMatching did not return one binary observable prediction")
            self._prediction = int(prediction[0])
            self._phase = "decoded"
            self._transitions.append("decoded")
            return self.snapshot()

    def set_display_slice(self, slice_index: int) -> dict[str, Any]:
        """Select one of the six detector-history frames for the exhibit."""
        if isinstance(slice_index, bool) or not isinstance(slice_index, int) or not 0 <= slice_index < 6:
            raise ValueError("slice_index must be an integer from 0 through 5")
        with self._lock:
            self._display_slice_index = slice_index
            return self.snapshot()

    def reset(self) -> dict[str, Any]:
        with self._lock:
            previous = self._phase
            self._phase = "idle"
            self._transitions = [previous, "reset", "idle"]
            self._fault_input = None
            self._detectors = None
            self._observable = None
            self._prediction = None
            self._display_slice_index = 0
            return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            detector_bits = None if self._detectors is None else self._detectors.astype(int).tolist()
            frames = (
                None
                if detector_bits is None
                else self.geometry.render_time_slices(detector_bits)
            )
            simulation_reference = None
            decoder_output = None
            if self._phase == "decoded" and self._observable is not None and self._prediction is not None:
                simulation_reference = {
                    "logical_observable": self._observable,
                    "correct": self._prediction == self._observable,
                    "simulation_only": True,
                }
                decoder_output = {
                    "name": "PyMatching nominal educational decoder",
                    "predicted_logical_observable": self._prediction,
                }
            qubit_states = ["idle"] * len(DATA_QUBITS)
            if self._fault_input is not None:
                qubit_states[self._fault_input["data_index"]] = "known_simulated_fault_input"
            return {
                "version": 1,
                "run_id": self._run_id,
                "mode": "deterministic_simulation_only",
                "phase": self._phase,
                "display_slice_index": self._display_slice_index,
                "transitions": list(self._transitions),
                "code": {
                    "id": "stim_rotated_memory_z_d3_r5_e1",
                    "data_qubits": 9,
                    "check_sites": 8,
                    "detectors": self.geometry.detector_count,
                    "observables": self.geometry.observable_count,
                },
                "layout": {
                    "data_sites": [
                        {
                            "data_index": index,
                            "stim_qubit": qubit,
                            "x": coord[0],
                            "y": coord[1],
                        }
                        for index, (qubit, coord) in enumerate(
                            zip(self.geometry.data_qubits, self.geometry.data_coords)
                        )
                    ],
                    "check_sites": [
                        {
                            "led_index": site.led_index,
                            "stim_qubit": site.stim_qubit,
                            "x": site.x,
                            "y": site.y,
                            "basis": site.basis,
                        }
                        for site in self.geometry.checks
                    ],
                },
                "fault_input": None if self._fault_input is None else dict(self._fault_input),
                "qubit_states": qubit_states,
                "detector_events": detector_bits,
                "detector_frames": frames,
                "decoder": decoder_output,
                "simulation_reference": simulation_reference,
                "physical_processor_data": False,
                "correction_map": None,
            }
