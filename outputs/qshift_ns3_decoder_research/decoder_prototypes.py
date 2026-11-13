"""Deterministic detector-error-model decoder prototypes for NS-3A.

The factor-graph method assumes independent Bernoulli DEM mechanisms. Stim's
approximate DEM for categorical circuit channels is not the exact circuit law.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import Sequence

import numpy as np


EXACT_ORACLE_MAX_STATES = 1 << 20


@dataclass(frozen=True)
class FaultMechanism:
    detectors: tuple[int, ...]
    logical: int
    probability: float

    def __post_init__(self) -> None:
        if any(type(d) is not int or d < 0 for d in self.detectors):
            raise ValueError("detector IDs must be nonnegative integers")
        # A DEM event toggles each target modulo two. Repeated targets cancel.
        parity: dict[int, int] = {}
        for d in self.detectors:
            parity[d] = parity.get(d, 0) ^ 1
        object.__setattr__(self, "detectors", tuple(sorted(d for d, bit in parity.items() if bit)))
        if type(self.logical) is not int or self.logical not in (0, 1):
            raise ValueError("logical parity must be integer 0 or 1")
        if isinstance(self.probability, bool) or not isinstance(self.probability, Real):
            raise ValueError("mechanism probability must be a real number")
        if not math.isfinite(float(self.probability)) or not 0 <= self.probability <= 1:
            raise ValueError("mechanism probability must be finite and in [0,1]")
        object.__setattr__(self, "probability", float(self.probability))


@dataclass(frozen=True)
class DetectorModel:
    n_detectors: int
    mechanisms: tuple[FaultMechanism, ...]
    detector_ids: tuple[int, ...] | None = None
    observable_ids: tuple[int, ...] = (0,)

    def __post_init__(self) -> None:
        if type(self.n_detectors) is not int or self.n_detectors < 1:
            raise ValueError("n_detectors must be a positive integer")
        ids = tuple(range(self.n_detectors)) if self.detector_ids is None else tuple(self.detector_ids)
        if ids != tuple(range(self.n_detectors)):
            raise ValueError("detector IDs must be contiguous Stim order 0..N-1")
        object.__setattr__(self, "detector_ids", ids)
        if tuple(self.observable_ids) != (0,):
            raise ValueError("prototype currently supports exactly observable L0")
        object.__setattr__(self, "observable_ids", (0,))
        if not isinstance(self.mechanisms, tuple) or any(not isinstance(f, FaultMechanism) for f in self.mechanisms):
            raise ValueError("mechanisms must be a tuple of FaultMechanism values")
        for f in self.mechanisms:
            if any(d >= self.n_detectors for d in f.detectors):
                raise ValueError("fault references detector outside declared model")

    @classmethod
    def from_stim_dem(cls, dem, *, n_detectors: int | None = None) -> "DetectorModel":
        """Parse flattened independent-mechanism DEMs; preserve duplicate events."""
        if n_detectors is None:
            n_detectors = int(dem.num_detectors)
        if int(dem.num_observables) != 1 or int(dem.num_detectors) != n_detectors:
            raise ValueError("expected exact detector dimension and one observable")
        faults = []
        for inst in dem.flattened():
            if inst.type == "detector":
                continue
            if inst.type != "error":
                raise ValueError(f"unsupported DEM instruction {inst.type!r}")
            detector_parity: dict[int, int] = {}
            logical = 0
            for target in inst.targets_copy():
                if target.is_separator():
                    raise ValueError("separator target unsupported; use an undecomposed DEM")
                if target.is_relative_detector_id():
                    d = int(target.val)
                    detector_parity[d] = detector_parity.get(d, 0) ^ 1
                elif target.is_logical_observable_id():
                    if int(target.val) != 0:
                        raise ValueError("only L0 is supported")
                    logical ^= 1
                else:
                    raise ValueError(f"unsupported DEM target {target!r}")
            args = inst.args_copy()
            if len(args) != 1:
                raise ValueError("expected one independent error probability")
            detectors = tuple(sorted(d for d, bit in detector_parity.items() if bit))
            faults.append(FaultMechanism(detectors, logical, float(args[0])))
        return cls(n_detectors, tuple(faults))

    @property
    def n_mechanisms(self) -> int:
        return len(self.mechanisms)

    @property
    def parity_matrix(self) -> np.ndarray:
        h = np.zeros((self.n_detectors, self.n_mechanisms), dtype=np.uint8)
        for j, fault in enumerate(self.mechanisms):
            for d in fault.detectors:
                h[d, j] = 1
        return h


@dataclass(frozen=True)
class BPRowDiagnostics:
    iterations: int
    converged: bool
    max_message_delta: float
    logical_llr: float
    tie: bool
    probability_clipped: bool


class BPConvergenceError(RuntimeError):
    def __init__(self, rows: tuple[int, ...], diagnostics: tuple[BPRowDiagnostics, ...]):
        self.rows = rows
        self.diagnostics = diagnostics
        super().__init__(f"belief propagation did not converge for batch rows {rows}")


class LogicalDecoder:
    def __init__(self, model: DetectorModel):
        self.model = model

    def _validate_inputs(
        self, syndromes: np.ndarray, detector_ids: Sequence[int] | None,
        observable_ids: Sequence[int] | None,
    ) -> np.ndarray:
        a = np.asarray(syndromes)
        if a.ndim != 2 or a.shape[1] != self.model.n_detectors:
            raise ValueError(f"syndromes must have shape [shots,{self.model.n_detectors}]")
        if a.dtype.kind not in "biuf" or not np.isfinite(a).all() or np.any((a != 0) & (a != 1)):
            raise ValueError("syndromes must contain only finite binary values")
        if detector_ids is not None and tuple(detector_ids) != self.model.detector_ids:
            raise ValueError("detector column IDs/order mismatch")
        if observable_ids is not None and tuple(observable_ids) != self.model.observable_ids:
            raise ValueError("observable output IDs/order mismatch")
        return np.array(a, dtype=np.uint8, copy=True)

    def decode_batch(
        self, syndromes: np.ndarray, *, detector_ids: Sequence[int] | None = None,
        observable_ids: Sequence[int] | None = None,
    ) -> np.ndarray:
        source = self._validate_inputs(syndromes, detector_ids, observable_ids)
        out = np.asarray([self._decode(row) for row in source], dtype=np.uint8)
        return out.reshape((-1, 1))

    def _decode(self, syndrome: np.ndarray) -> int:
        raise NotImplementedError


class ExactMAPOracle(LogicalDecoder):
    """Bounded exhaustive MAP logical-class oracle (never a full Q-SHIFT decoder)."""

    def __init__(self, model: DetectorModel, *, max_states: int = EXACT_ORACLE_MAX_STATES):
        super().__init__(model)
        if type(max_states) is not int or max_states < 1 or max_states > EXACT_ORACLE_MAX_STATES:
            raise ValueError(f"max_states must be an integer in [1,{EXACT_ORACLE_MAX_STATES}]")
        self.max_states = max_states
        states = 1 << model.n_mechanisms
        if states > self.max_states:
            raise ValueError(f"oracle cap exceeded: {states} assignments > {self.max_states}")

    @staticmethod
    def _logadd(a: float, b: float) -> float:
        if a == -math.inf:
            return b
        if b == -math.inf:
            return a
        m = max(a, b)
        return m + math.log1p(math.exp(min(a, b) - m))

    def _decode(self, syndrome: np.ndarray) -> int:
        target = sum(int(bit) << i for i, bit in enumerate(syndrome))
        det_masks, logicals, log0, log1 = [], [], [], []
        for fault in self.model.mechanisms:
            det_masks.append(sum(1 << d for d in fault.detectors))
            logicals.append(fault.logical)
            p = fault.probability
            log0.append(math.log1p(-p) if p < 1 else -math.inf)
            log1.append(math.log(p) if p > 0 else -math.inf)
        class_logs = [-math.inf, -math.inf]
        for bits in range(1 << len(det_masks)):
            detector_mask = 0
            logical = 0
            log_probability = 0.0
            impossible = False
            for j, mask in enumerate(det_masks):
                is_fault = (bits >> j) & 1
                if is_fault:
                    detector_mask ^= mask
                    logical ^= logicals[j]
                term = log1[j] if is_fault else log0[j]
                if term == -math.inf:
                    impossible = True
                    break
                log_probability += term
            if not impossible and detector_mask == target:
                class_logs[logical] = self._logadd(class_logs[logical], log_probability)
        if class_logs[0] == class_logs[1] == -math.inf:
            raise ValueError("syndrome has zero probability under the declared model")
        return int(class_logs[1] > class_logs[0])  # exact ties choose L0=0


class FactorGraphBP(LogicalDecoder):
    """Loopy sum-product BP over independent DEM fault variables.

    An auxiliary L0 variable is connected by an XOR factor to every L0-bearing
    mechanism. `decode_batch` fails closed on nonconvergence; diagnostics are
    available via `decode_batch_with_diagnostics`.
    """

    def __init__(
        self, model: DetectorModel, *, iterations: int = 50, damping: float = 0.25,
        convergence_tol: float = 1e-7, tie_tol: float = 1e-10, llr_cap: float = 60.0,
    ):
        super().__init__(model)
        if type(iterations) is not int or iterations < 1:
            raise ValueError("iterations must be a positive integer")
        if not 0 <= damping < 1 or not math.isfinite(damping):
            raise ValueError("damping must lie in [0,1)")
        if convergence_tol <= 0 or not math.isfinite(convergence_tol):
            raise ValueError("convergence_tol must be finite and positive")
        if tie_tol < 0 or not math.isfinite(tie_tol):
            raise ValueError("tie_tol must be finite and nonnegative")
        if llr_cap <= 0 or not math.isfinite(llr_cap):
            raise ValueError("llr_cap must be finite and positive")
        self.iterations = iterations
        self.damping = float(damping)
        self.convergence_tol = float(convergence_tol)
        self.tie_tol = float(tie_tol)
        self.llr_cap = float(llr_cap)
        self._fault_count = model.n_mechanisms
        self._logical_var = model.n_mechanisms
        self._priors = [self._prior_llr(f.probability) for f in model.mechanisms] + [0.0]
        self.probability_clipped = any(
            p == 0 or p == 1 or min(p, 1 - p) < math.exp(-self.llr_cap)
            for p in (f.probability for f in model.mechanisms)
        )
        self._checks: list[tuple[tuple[int, ...], int]] = []
        for d in range(model.n_detectors):
            neighbors = tuple(j for j, f in enumerate(model.mechanisms) if d in f.detectors)
            self._checks.append((neighbors, 0))
        logical_neighbors = tuple(j for j, f in enumerate(model.mechanisms) if f.logical) + (self._logical_var,)
        self._checks.append((logical_neighbors, 0))
        self._var_checks: list[list[int]] = [[] for _ in self._priors]
        for c, (neighbors, _) in enumerate(self._checks):
            for v in neighbors:
                self._var_checks[v].append(c)

    def _prior_llr(self, p: float) -> float:
        eps = math.exp(-self.llr_cap)
        p = min(1 - eps, max(eps, p))
        return max(-self.llr_cap, min(self.llr_cap, math.log1p(-p) - math.log(p)))

    @staticmethod
    def _phi(x: float) -> float:
        """Stable phi(x)=-log(tanh(x/2)) for nonnegative x."""
        if x <= 0:
            return math.inf
        if x > 40:
            e = math.exp(-x)
            return math.log1p(2 * e / (1 - e))
        return math.log1p(2 / math.expm1(x))

    def _check_messages(self, incoming: tuple[float, ...], parity: int) -> tuple[float, ...]:
        """Compute all parity-check outputs in O(degree), using stable phi LLRs."""
        degree = len(incoming)
        if degree == 0:
            return ()
        finite_phi = [0.0 if value == 0 else self._phi(abs(value)) for value in incoming]
        prefix = [0.0] * (degree + 1)
        negative_prefix = [0] * (degree + 1)
        zero_prefix = [0] * (degree + 1)
        for i, value in enumerate(incoming):
            prefix[i + 1] = prefix[i] + finite_phi[i]
            negative_prefix[i + 1] = negative_prefix[i] + int(value < 0)
            zero_prefix[i + 1] = zero_prefix[i] + int(value == 0)
        total_phi = prefix[-1]
        total_negative = negative_prefix[-1]
        total_zero = zero_prefix[-1]
        output = []
        for i, value in enumerate(incoming):
            other_zeros = total_zero - int(value == 0)
            if other_zeros:
                output.append(0.0)
                continue
            phi_sum = total_phi - finite_phi[i]
            if phi_sum <= 1e-15:
                magnitude = self.llr_cap
            else:
                x = math.exp(-phi_sum)
                x = min(1 - 1e-15, max(0.0, x))
                magnitude = min(self.llr_cap, 2 * math.atanh(x))
            other_negative = total_negative - int(value < 0)
            sign = -1.0 if (parity + other_negative) % 2 else 1.0
            output.append(sign * magnitude)
        return tuple(output)

    def _decode_with_diagnostics(self, syndrome: np.ndarray) -> tuple[int, BPRowDiagnostics]:
        checks = [(neighbors, int(syndrome[i]) if i < self.model.n_detectors else 0)
                  for i, (neighbors, _) in enumerate(self._checks)]
        v2c: dict[tuple[int, int], float] = {}
        c2v: dict[tuple[int, int], float] = {}
        for c, (neighbors, _) in enumerate(checks):
            for v in neighbors:
                v2c[(v, c)] = self._priors[v]
                c2v[(c, v)] = 0.0
        logical_check = len(checks) - 1
        converged = False
        max_delta = math.inf
        completed = 0
        for iteration in range(1, self.iterations + 1):
            raw_c2v: dict[tuple[int, int], float] = {}
            for c, (neighbors, parity) in enumerate(checks):
                incoming = tuple(v2c[(v, c)] for v in neighbors)
                for v, message in zip(neighbors, self._check_messages(incoming, parity)):
                    raw_c2v[(c, v)] = message
            next_c2v = {
                key: self.damping * c2v[key] + (1 - self.damping) * value
                for key, value in raw_c2v.items()
            } if self.damping else raw_c2v
            raw_v2c: dict[tuple[int, int], float] = {}
            for v, check_ids in enumerate(self._var_checks):
                for c in check_ids:
                    total = self._priors[v] + math.fsum(next_c2v[(other, v)] for other in check_ids if other != c)
                    raw_v2c[(v, c)] = max(-self.llr_cap, min(self.llr_cap, total))
            next_v2c = {
                key: self.damping * v2c[key] + (1 - self.damping) * value
                for key, value in raw_v2c.items()
            } if self.damping else raw_v2c
            max_delta = max(
                (abs(next_c2v[k] - c2v[k]) for k in c2v),
                default=0.0,
            )
            max_delta = max(max_delta, max(
                (abs(next_v2c[k] - v2c[k]) for k in v2c), default=0.0
            ))
            c2v, v2c = next_c2v, next_v2c
            completed = iteration
            if max_delta <= self.convergence_tol:
                converged = True
                break
        logical_llr = c2v[(logical_check, self._logical_var)]
        tie = abs(logical_llr) <= self.tie_tol
        prediction = int(logical_llr < -self.tie_tol)
        return prediction, BPRowDiagnostics(
            iterations=completed, converged=converged, max_message_delta=max_delta,
            logical_llr=logical_llr, tie=tie, probability_clipped=self.probability_clipped,
        )

    def decode_batch_with_diagnostics(
        self, syndromes: np.ndarray, *, detector_ids: Sequence[int] | None = None,
        observable_ids: Sequence[int] | None = None,
    ) -> tuple[np.ndarray, tuple[BPRowDiagnostics, ...]]:
        source = self._validate_inputs(syndromes, detector_ids, observable_ids)
        decoded = [self._decode_with_diagnostics(row) for row in source]
        predictions = np.asarray([x[0] for x in decoded], dtype=np.uint8).reshape((-1, 1))
        diagnostics = tuple(x[1] for x in decoded)
        return predictions, diagnostics

    def decode_batch(
        self, syndromes: np.ndarray, *, detector_ids: Sequence[int] | None = None,
        observable_ids: Sequence[int] | None = None, allow_nonconverged: bool = False,
    ) -> np.ndarray:
        predictions, diagnostics = self.decode_batch_with_diagnostics(
            syndromes, detector_ids=detector_ids, observable_ids=observable_ids
        )
        failed = tuple(i for i, item in enumerate(diagnostics) if not item.converged)
        if failed and not allow_nonconverged:
            raise BPConvergenceError(failed, diagnostics)
        return predictions

    def _decode(self, syndrome: np.ndarray) -> int:
        prediction, diagnostics = self._decode_with_diagnostics(syndrome)
        if not diagnostics.converged:
            raise BPConvergenceError((0,), (diagnostics,))
        return prediction
