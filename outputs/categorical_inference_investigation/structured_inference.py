"""Exact parity-structured inference using XOR convolution and Walsh transforms.

The algorithm sums categorical factors without enumerating the Cartesian
product of fault outcomes. Arithmetic uses IEEE float64, so "exact" refers to
the inference algorithm; numerical results remain subject to roundoff.
"""
from __future__ import annotations

from collections import defaultdict
import math
import time

import numpy as np


def fwht_inplace(values: np.ndarray) -> None:
    """Unnormalized Walsh-Hadamard transform over a power-of-two 1D vector."""
    n = values.size
    if n == 0 or n & (n-1):
        raise ValueError("FWHT length must be a positive power of two")
    h = 1
    while h < n:
        blocks = values.reshape(-1, 2*h)
        left = blocks[:, :h].copy()
        right = blocks[:, h:].copy()
        blocks[:, :h] = left + right
        blocks[:, h:] = left - right
        h *= 2


def direct_xor_dp(model):
    """Nonnegative reference DP over accumulated parity masks (small models)."""
    state = {0: 1.0}
    for location in model.locations:
        new = defaultdict(float)
        for current, mass in state.items():
            for outcome in location.outcomes:
                mask = outcome.detector_mask | (outcome.observable_mask << model.detector_count)
                new[current ^ mask] += mass * outcome.probability
        state = dict(new)
    return state


def _local_fourier(location, detector_count, total_bits):
    combined = defaultdict(float)
    for outcome in location.outcomes:
        mask = outcome.detector_mask | (outcome.observable_mask << detector_count)
        combined[mask] += outcome.probability
    support = tuple(i for i in range(total_bits) if any((mask >> i) & 1 for mask in combined))
    if not support:
        return (), np.asarray([sum(combined.values())], dtype=np.float64)
    local = np.zeros(1 << len(support), dtype=np.float64)
    for mask, probability in combined.items():
        compact = sum(((mask >> bit) & 1) << j for j, bit in enumerate(support))
        local[compact] += probability
    fwht_inplace(local)
    return support, local


def _projection(freq: np.ndarray, support: tuple[int, ...]) -> np.ndarray:
    compact = np.zeros(freq.size, dtype=np.uint32)
    for j, bit in enumerate(support):
        compact |= (((freq >> bit) & 1).astype(np.uint32) << j)
    return compact


def xor_walsh_posterior(model, *, max_bytes: int = 2 * 1024**3,
                        chunk_size: int = 1 << 20, negative_tolerance: float = 1e-10):
    """Compute the full joint `P(detector_mask, observable_mask)` by transform.

    A location contributes the Fourier transform of its categorical mask
    distribution. XOR convolution across independent locations becomes
    pointwise multiplication. Local transforms depend only on detector/logical
    coordinates touched by that location and are grouped by support.
    """
    model.validate()
    total_bits = model.detector_count + model.observable_count
    state_count = 1 << total_bits
    dense_bytes = state_count * np.dtype(np.float64).itemsize
    # Peak working storage includes transform plus FWHT work arrays, not only
    # the final posterior. Refuse before allocating if a conservative bound
    # would exceed the user-specified cap.
    estimated_peak = 4 * dense_bytes + 64 * 1024**2
    if estimated_peak > max_bytes:
        raise MemoryError(f"estimated peak {estimated_peak} bytes exceeds cap {max_bytes}; output cells={state_count}")
    started = time.perf_counter()
    grouped = {}
    for location in model.locations:
        support, spectrum = _local_fourier(location, model.detector_count, total_bits)
        if not support:
            continue
        if support in grouped:
            grouped[support] *= spectrum
        else:
            grouped[support] = spectrum

    transformed = np.ones(state_count, dtype=np.float64)
    for support, local_spectrum in grouped.items():
        for start in range(0, state_count, chunk_size):
            end = min(state_count, start + chunk_size)
            freq = np.arange(start, end, dtype=np.uint64)
            index = _projection(freq, support)
            np.multiply(transformed[start:end], local_spectrum[index],
                        out=transformed[start:end])
    fwht_inplace(transformed)
    transformed /= state_count
    raw_mass = float(transformed.sum())
    minimum = float(transformed.min())
    negative_mass = float(-transformed[transformed < 0].sum())
    if minimum < -negative_tolerance:
        raise ArithmeticError(f"inverse transform produced material negative probability {minimum}")
    # Tiny negative residues from floating-point cancellation are clipped and
    # their total mass is separately recorded; this is only a numerical repair.
    transformed[transformed < 0] = 0.0
    clipped_mass = negative_mass
    mass_after_clip = float(transformed.sum())
    if not math.isfinite(mass_after_clip) or mass_after_clip <= 0:
        raise ArithmeticError("invalid posterior normalization")
    transformed /= mass_after_clip
    return transformed, {
        "algorithm": "categorical XOR convolution via grouped Walsh-Hadamard factors",
        "categorical_locations": len(model.locations),
        "output_bits": total_bits,
        "joint_state_count": state_count,
        "unique_local_supports": len(grouped),
        "local_support_sizes": sorted({len(s) for s in grouped}),
        "dense_output_bytes": dense_bytes,
        "conservative_estimated_peak_bytes": estimated_peak,
        "raw_mass_before_clipping": raw_mass,
        "minimum_raw_probability": minimum,
        "negative_mass_clipped": clipped_mass,
        "mass_after_clipping_before_renormalization": mass_after_clip,
        "normalization_factor": mass_after_clip,
        "runtime_seconds": time.perf_counter() - started,
    }


def map_metrics(posterior, detector_count, observable_count, *, tie_atol=1e-15):
    """Extract deterministic MAP decisions and exact-channel Bayes risk."""
    n_det = 1 << detector_count
    n_obs = 1 << observable_count
    table = posterior.reshape(n_obs, n_det)
    if n_obs == 2:
        p0, p1 = table[0], table[1]
        ties = np.abs(p0-p1) <= tie_atol
        choose_one = (p1 > p0) & ~ties
        risk = float(np.sum(p0+p1-np.where(choose_one,p1,p0)))
        decisions = ({s: int(choose_one[s]) for s in range(n_det)} if n_det <= 4096 else None)
        return {"decisions": decisions, "tie_count": int(np.count_nonzero(ties)),
                "tie_syndromes": np.flatnonzero(ties).tolist() if n_det <= 4096 else None,
                "logical_error_probability": risk,
                "posterior_total_mass": float(posterior.sum()),
                "syndrome_count_scored": n_det}
    decisions = {}
    ties = []
    risk = 0.0
    for syndrome in range(n_det):
        probs = table[:, syndrome]
        maximum = float(np.max(probs))
        winners = [logical for logical, p in enumerate(probs) if abs(float(p)-maximum) <= tie_atol]
        decision = min(winners)
        decisions[syndrome] = decision
        if len(winners) > 1:
            ties.append(syndrome)
        risk += float(np.sum(probs)) - float(probs[decision])
    return {"decisions": decisions, "tie_syndromes": ties, "logical_error_probability": risk,
            "posterior_total_mass": float(posterior.sum())}


def mask_distribution_to_joint(state_probabilities, detector_count, observable_count):
    """Return joint dictionary using the same low-order detector bit convention."""
    result = {}
    for mask, probability in state_probabilities.items():
        syndrome = mask & ((1 << detector_count)-1)
        observable = mask >> detector_count
        bucket = result.setdefault(syndrome, [0.0] * (1 << observable_count))
        bucket[observable] += probability
    return {s: tuple(v) for s,v in result.items()}
