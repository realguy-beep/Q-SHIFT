"""Small exhaustive reference for independent categorical Pauli fault locations.

This is deliberately an exact enumerator, not a scalable decoder. Each location
has one mutually exclusive outcome (including identity); configurations are the
Cartesian product over locations.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import math
from typing import Iterable


@dataclass(frozen=True)
class FaultOutcome:
    label: str
    probability: float
    detector_mask: int
    observable_mask: int


@dataclass(frozen=True)
class CategoricalLocation:
    name: str
    outcomes: tuple[FaultOutcome, ...]
    identity_label: str

    def validate(self, detector_count: int, observable_count: int, *, tol: float = 1e-12) -> None:
        if not self.outcomes:
            raise ValueError(f"location {self.name} has no outcomes")
        labels = [o.label for o in self.outcomes]
        if len(set(labels)) != len(labels):
            raise ValueError(f"location {self.name} has duplicate outcome labels")
        identity = [o for o in self.outcomes if o.label == self.identity_label]
        if len(identity) != 1:
            raise ValueError(f"location {self.name} must have exactly one identity outcome")
        if identity[0].detector_mask != 0 or identity[0].observable_mask != 0:
            raise ValueError(f"location {self.name} identity outcome must have zero masks")
        total = 0.0
        for outcome in self.outcomes:
            if not math.isfinite(outcome.probability) or not (0.0 <= outcome.probability <= 1.0):
                raise ValueError(f"invalid probability at {self.name}/{outcome.label}")
            if outcome.detector_mask < 0 or outcome.detector_mask >= (1 << detector_count):
                raise ValueError(f"detector mask outside range at {self.name}/{outcome.label}")
            if outcome.observable_mask < 0 or outcome.observable_mask >= (1 << observable_count):
                raise ValueError(f"observable mask outside range at {self.name}/{outcome.label}")
            total += outcome.probability
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=tol):
            raise ValueError(f"probabilities at {self.name} sum to {total}, not 1")


@dataclass(frozen=True)
class CategoricalModel:
    detector_count: int
    observable_count: int
    locations: tuple[CategoricalLocation, ...]

    def validate(self) -> None:
        if self.detector_count < 0 or self.observable_count < 1:
            raise ValueError("detector_count must be nonnegative and observable_count positive")
        if not self.locations:
            raise ValueError("model needs at least one noisy location")
        for location in self.locations:
            location.validate(self.detector_count, self.observable_count)

    @property
    def configuration_count(self) -> int:
        return math.prod(len(location.outcomes) for location in self.locations)

    def enumerate_configurations(self) -> Iterable[tuple[tuple[FaultOutcome, ...], float, int, int]]:
        """Yield one selected outcome per location, with product probability and XOR masks."""
        self.validate()
        for selected in product(*(loc.outcomes for loc in self.locations)):
            probability = math.prod(outcome.probability for outcome in selected)
            detector_mask = 0
            observable_mask = 0
            for outcome in selected:
                detector_mask ^= outcome.detector_mask
                observable_mask ^= outcome.observable_mask
            yield selected, probability, detector_mask, observable_mask


@dataclass(frozen=True)
class ExactPosterior:
    joint: dict[int, tuple[float, ...]]
    decisions: dict[int, int]
    conditional: dict[int, tuple[float, ...]]
    tie_syndromes: tuple[int, ...]
    logical_error_probability: float
    total_probability: float
    configuration_count: int
    tie_policy: str = "choose the smallest observable bit pattern; in binary ties choose 0"


def exact_posterior(model: CategoricalModel, *, tie_atol: float = 1e-15) -> ExactPosterior:
    """Exhaustively compute P(syndrome, observable) and the MAP decision per syndrome."""
    model.validate()
    observable_states = 1 << model.observable_count
    joint_acc: dict[int, list[float]] = {}
    total = 0.0
    enumerated = 0
    for _, probability, syndrome, logical in model.enumerate_configurations():
        bucket = joint_acc.setdefault(syndrome, [0.0] * observable_states)
        bucket[logical] += probability
        total += probability
        enumerated += 1
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-10):
        raise ArithmeticError(f"enumerated mass sums to {total}, not 1")

    joint = {s: tuple(p) for s, p in joint_acc.items()}
    decisions: dict[int, int] = {}
    conditional: dict[int, tuple[float, ...]] = {}
    ties = []
    risk = 0.0
    for syndrome, probs in joint.items():
        syndrome_mass = sum(probs)
        post = tuple(p / syndrome_mass for p in probs)
        conditional[syndrome] = post
        maximum = max(probs)
        maximizers = [logical for logical, p in enumerate(probs) if abs(p - maximum) <= tie_atol]
        decision = min(maximizers)
        decisions[syndrome] = decision
        if len(maximizers) > 1:
            ties.append(syndrome)
        risk += syndrome_mass - probs[decision]
    return ExactPosterior(joint=joint, decisions=decisions, conditional=conditional,
                          tie_syndromes=tuple(sorted(ties)),
                          logical_error_probability=risk, total_probability=total,
                          configuration_count=enumerated)


def decoder_risk(joint: dict[int, tuple[float, ...]], decisions: dict[int, int]) -> float:
    """Unconditional logical-observable error probability for a deterministic decoder."""
    risk = 0.0
    for syndrome, probabilities in joint.items():
        predicted = decisions[syndrome]
        risk += sum(p for logical, p in enumerate(probabilities) if logical != predicted)
    return risk
