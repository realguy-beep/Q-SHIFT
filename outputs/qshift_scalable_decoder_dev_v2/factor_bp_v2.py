"""Bounded BP over independent DEM mechanisms, with exact boundary handling."""
from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np


class ImpossibleSyndromeError(ValueError):
    """Raised when a syndrome is outside the model's exact affine support."""


class FactorBPV2:
    """Sum-product detector BP; logical confidence remains a named approximation.

    Each DEM error instruction is one independent Bernoulli mechanism. Separator
    targets are decomposition hints and do not split the mechanism. The graph
    represents each mechanism as one variable connected to every detector it flips.
    """

    def __init__(self, dem, iterations: int = 50, damping: float = 0.5,
                 tolerance: float = 1e-8, clip: float = 1e-12):
        if not isinstance(iterations, int) or isinstance(iterations, bool) or iterations <= 0:
            raise ValueError("iterations must be a positive integer")
        if not math.isfinite(damping) or not 0 <= damping < 1:
            raise ValueError("damping must be finite and in [0, 1)")
        if not math.isfinite(tolerance) or tolerance <= 0:
            raise ValueError("tolerance must be finite and positive")
        if not math.isfinite(clip) or not 0 < clip < 0.5:
            raise ValueError("clip must be finite and in (0, 0.5)")
        if dem.num_observables != 1:
            raise ValueError("exactly one observable required")

        self.n = int(dem.num_detectors)
        self.iterations = iterations
        self.damping = float(damping)
        self.tolerance = float(tolerance)
        self.clip = float(clip)
        self.p: list[float] = []
        self.det: list[tuple[int, ...]] = []
        self.logical: list[bool] = []
        self.fixed_detector_mask = 0
        self.fixed_logical = 0

        for ins in dem.flattened():
            if ins.type != "error":
                if ins.type not in ("detector", "logical_observable"):
                    raise ValueError(f"unsupported DEM instruction: {ins.type}")
                continue
            args = ins.args_copy()
            if len(args) != 1:
                raise ValueError("error instruction must have exactly one probability")
            probability = float(args[0])
            if not math.isfinite(probability) or not 0 <= probability <= 1:
                raise ValueError("mechanism probability must be finite and in [0, 1]")

            detectors: set[int] = set()
            logical = 0
            for target in ins.targets_copy():
                if target.is_separator():
                    continue
                if target.is_relative_detector_id():
                    detector_id = int(target.val)
                    if not 0 <= detector_id < self.n:
                        raise ValueError("detector target is outside declared DEM dimensions")
                    if detector_id in detectors:
                        detectors.remove(detector_id)
                    else:
                        detectors.add(detector_id)
                elif target.is_logical_observable_id():
                    if target.val != 0:
                        raise ValueError("unsupported observable ID")
                    logical ^= 1
                else:
                    raise ValueError("unsupported DEM target")

            if probability == 0:
                continue
            if probability == 1:
                for detector_id in detectors:
                    self.fixed_detector_mask ^= 1 << detector_id
                self.fixed_logical ^= logical
                continue
            # An empty zero-effect mechanism cannot affect any inference quantity.
            if not detectors and not logical:
                continue
            self.p.append(probability)
            self.det.append(tuple(sorted(detectors)))
            self.logical.append(bool(logical))

        if len(self.p) > 50_000:
            raise ValueError("model exceeds 50,000 active-mechanism limit")

        self._basis: dict[int, int] = {}
        self.edges: list[tuple[int, int]] = []
        self.by_v: list[list[int]] = [[] for _ in self.p]
        self.by_c: list[list[int]] = [[] for _ in range(self.n)]
        incidence_count = 0
        for variable, detector_ids in enumerate(self.det):
            support_mask = 0
            for detector_id in detector_ids:
                support_mask ^= 1 << detector_id
                edge = len(self.edges)
                self.edges.append((variable, detector_id))
                self.by_v[variable].append(edge)
                self.by_c[detector_id].append(edge)
                incidence_count += 1
            if detector_ids:
                self._insert_basis_vector(support_mask)
        if incidence_count > 50_000:
            raise ValueError("model exceeds 50,000 incidence-edge limit")

        # log((1-p)/p), evaluated without forming 1-p by subtraction.
        self.prior = np.asarray([math.log1p(-p) - math.log(p) for p in self.p], dtype=float)

    def _insert_basis_vector(self, vector: int) -> None:
        value = vector
        while value:
            pivot = value.bit_length() - 1
            if pivot in self._basis:
                value ^= self._basis[pivot]
            else:
                self._basis[pivot] = value
                return

    def _is_reachable(self, syndrome_mask: int) -> bool:
        value = syndrome_mask
        while value:
            pivot = value.bit_length() - 1
            if pivot not in self._basis:
                return False
            value ^= self._basis[pivot]
        return True

    @staticmethod
    def _probability_one(llr_zero_over_one: float) -> float:
        # Stable sigmoid(-LLR), including large-magnitude finite inputs.
        if llr_zero_over_one >= 0:
            exp_term = math.exp(-llr_zero_over_one)
            return exp_term / (1 + exp_term)
        exp_term = math.exp(llr_zero_over_one)
        return 1 / (1 + exp_term)

    def decode_one(self, syndrome: Iterable[int], include_fault_marginals: bool = False) -> dict:
        x = np.asarray(syndrome)
        if x.shape != (self.n,) or not np.isin(x, (0, 1)).all():
            raise ValueError("invalid detector syndrome")
        observed_mask = sum(int(bit) << index for index, bit in enumerate(x))
        effective_mask = observed_mask ^ self.fixed_detector_mask
        if not self._is_reachable(effective_mask):
            raise ImpossibleSyndromeError("syndrome is outside the model's affine reachable set")

        edge_count = len(self.edges)
        if edge_count == 0 and len(self.p) == 0:
            probabilities = np.zeros(len(self.p), dtype=float)
            logical_p1 = float(self.fixed_logical)
            result = {
                "prediction_approx": self.fixed_logical,
                "logical_p1_approx": logical_p1,
                "logical_probability_exact": True,
                "logical_probability_method": "fixed-logical-offset",
                "converged": True,
                "iterations": 0,
                "message_residual": 0.0,
            }
            if include_fault_marginals:
                result["fault_p1_approx"] = probabilities.tolist()
            return result

        variable_to_check = np.asarray([self.prior[v] for v, _ in self.edges], dtype=float)
        check_to_variable = np.zeros(edge_count, dtype=float)
        converged = False
        residual = math.inf
        performed = 0

        for iteration in range(1, self.iterations + 1):
            updated = np.zeros_like(check_to_variable)
            for check, edge_ids in enumerate(self.by_c):
                if not edge_ids:
                    continue
                tanh_values = [math.tanh(variable_to_check[e] / 2) for e in edge_ids]
                prefix = [1.0]
                for value in tanh_values:
                    prefix.append(prefix[-1] * value)
                suffix = [1.0] * (len(edge_ids) + 1)
                for local_index in range(len(edge_ids) - 1, -1, -1):
                    suffix[local_index] = tanh_values[local_index] * suffix[local_index + 1]
                sign = -1.0 if ((effective_mask >> check) & 1) else 1.0
                for local_index, edge in enumerate(edge_ids):
                    product = sign * prefix[local_index] * suffix[local_index + 1]
                    raw = 2 * math.atanh(max(-1 + self.clip, min(1 - self.clip, product)))
                    updated[edge] = self.damping * check_to_variable[edge] + (1 - self.damping) * raw

            next_variable_to_check = np.empty_like(variable_to_check)
            for variable, edge_ids in enumerate(self.by_v):
                for edge in edge_ids:
                    other_messages = (updated[other] for other in edge_ids if other != edge)
                    next_variable_to_check[edge] = self.prior[variable] + math.fsum(other_messages)

            residual = float(np.max(np.abs(updated - check_to_variable))) if edge_count else 0.0
            check_to_variable = updated
            variable_to_check = next_variable_to_check
            performed = iteration
            if residual < self.tolerance:
                converged = True
                break

        fault_llr = np.empty(len(self.p), dtype=float)
        for variable, edge_ids in enumerate(self.by_v):
            fault_llr[variable] = self.prior[variable] + math.fsum(check_to_variable[e] for e in edge_ids)
        fault_p1 = np.asarray([self._probability_one(float(value)) for value in fault_llr], dtype=float)

        parity_mean = -1.0 if self.fixed_logical else 1.0
        for variable, carries_logical in enumerate(self.logical):
            if carries_logical:
                parity_mean *= math.tanh(float(fault_llr[variable]) / 2)
        logical_p1_approx = min(1.0, max(0.0, (1 - parity_mean) / 2))
        logical_probability_exact = not any(
            flag and self.by_v[index] for index, flag in enumerate(self.logical)
        )
        logical_probability_method = (
            "product of independent logical-only mechanisms; exact"
            if logical_probability_exact
            else "product of fault marginals; approximate under logical-bit dependence"
        )
        result = {
            "prediction_approx": int(logical_p1_approx > 0.5),
            "logical_p1_approx": logical_p1_approx,
            "logical_probability_exact": logical_probability_exact,
            "logical_probability_method": logical_probability_method,
            "converged": converged,
            "iterations": performed,
            "message_residual": residual,
        }
        if include_fault_marginals:
            result["fault_p1_approx"] = fault_p1.tolist()
        return result



