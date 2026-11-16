"""Independent exhaustive reference for tiny, source-authored DEMs only."""
from __future__ import annotations

import itertools
import math

import numpy as np


def exact_posterior(dem, syndrome, max_mechanisms: int = 12):
    """Return exact conditional logical and fault marginals; never samples.

    This intentionally does not import or call FactorBPV2. It enumerates all
    mechanism assignments and is limited to tiny deterministic test models.
    Returns None for a zero-probability syndrome.
    """
    n_detectors = int(dem.num_detectors)
    observed = np.asarray(syndrome)
    if observed.shape != (n_detectors,) or not np.isin(observed, (0, 1)).all():
        raise ValueError("invalid syndrome")
    mechanisms = []
    for instruction in dem.flattened():
        if instruction.type != "error":
            continue
        args = instruction.args_copy()
        if len(args) != 1:
            raise ValueError("unsupported error instruction")
        probability = float(args[0])
        support = 0
        logical = 0
        for target in instruction.targets_copy():
            if target.is_separator():
                continue
            if target.is_relative_detector_id():
                support ^= 1 << int(target.val)
            elif target.is_logical_observable_id() and target.val == 0:
                logical ^= 1
            else:
                raise ValueError("unsupported target in exact reference")
        if probability != 0 and (support != 0 or logical):
            mechanisms.append((probability, support, logical))
    if len(mechanisms) > max_mechanisms:
        raise ValueError("exact oracle mechanism limit exceeded")

    totals = [0.0, 0.0]
    fault_ones = [0.0] * len(mechanisms)
    target_mask = sum(int(bit) << index for index, bit in enumerate(observed))
    for assignment in itertools.product((0, 1), repeat=len(mechanisms)):
        probability = 1.0
        detector_mask = 0
        logical = 0
        for index, (bit, (p, support, logical_bit)) in enumerate(zip(assignment, mechanisms)):
            probability *= p if bit else 1 - p
            if bit:
                detector_mask ^= support
                logical ^= logical_bit
        if detector_mask == target_mask:
            totals[logical] += probability
            for index, bit in enumerate(assignment):
                if bit:
                    fault_ones[index] += probability
    normalization = math.fsum(totals)
    if normalization == 0:
        return None
    return {
        "logical_p1": totals[1] / normalization,
        "fault_p1": [value / normalization for value in fault_ones],
        "normalization": normalization,
    }


