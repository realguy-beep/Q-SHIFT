"""Exhaustive likelihood calculator for finite toy categorical Pauli events.

Each independent location is a list of (probability, detector bitmask,
observable bit) outcomes. Detection events and logical effects combine by XOR.
This is only an exact toy reference; it does not make the full surface-code
decoder exact.
"""
from __future__ import annotations

from itertools import product
from collections.abc import Sequence


Outcome = tuple[float, int, int]


def exact_joint_likelihoods(locations: Sequence[Sequence[Outcome]]):
    """Return {(detector_mask, logical_bit): probability} by enumeration."""
    for location in locations:
        if not location or abs(sum(x[0] for x in location) - 1.0) > 1e-12:
            raise ValueError("each categorical location must have outcomes summing to one")
    joint: dict[tuple[int, int], float] = {}
    for choices in product(*locations):
        p = 1.0
        detector = 0
        logical = 0
        for probability, det_mask, obs in choices:
            p *= probability
            detector ^= int(det_mask)
            logical ^= int(obs)
        key = (detector, logical)
        joint[key] = joint.get(key, 0.0) + p
    return joint


def exact_posterior(joint, detector_mask: int) -> float:
    """Return P(L=1 | D=detector_mask), raising if syndrome is impossible."""
    p0 = joint.get((int(detector_mask), 0), 0.0)
    p1 = joint.get((int(detector_mask), 1), 0.0)
    if p0 + p1 == 0:
        raise ValueError("requested detector pattern has zero probability")
    return p1 / (p0 + p1)

