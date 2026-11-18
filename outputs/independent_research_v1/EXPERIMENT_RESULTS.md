# Experiment and evidence results

## New deterministic feasibility check

**Question:** Can Stim build a non-approximated detector error model for the Q-SHIFT categorical circuit so that the planned matched-DEM-family mechanism experiment is executable with PyMatching?

**Method:** In the isolated Python 3.12 environment, loaded the tracked Q-SHIFT Phase 2B circuit builder read-only and generated all six distance-3, five-round circuits (two memory bases by three Pauli-composition regimes). Called `circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=False)` for each circuit. No shots were generated and no outputs were written to the original Phase 2B directory.

**Result:** 0/6 conversions succeeded. All failed immediately with Stim `ValueError`: `PAULI_CHANNEL_2` requires `approximate_disjoint_errors=True` for error analysis. Runtime was under 0.01 seconds total. This deterministically confirms the pretest blocker described in the existing `outputs/correlation_mechanism_audit/FOLLOWUP_PROTOCOL.md`.

**Interpretation:** The proposed exact-vs-approximate DEM family cannot be implemented through this Stim circuit-to-DEM route for these categorical two-qubit channels. This does not establish that the approximation caused or did not cause the earlier correlation-mode interaction. It means the follow-up's primary contrast cannot be executed as written. A substitute must model categorical gate outcomes natively and be validated against the exact small-instance reference before sampling.

## Previously completed development evidence reviewed

The repository's separate `outputs/correlation_pilot/` is already a complete, independently rescored 720,000-shot development pilot. Its pooled fixed correlated arm had 3,349 errors and the uncorrelated arm had 3,532, with equal-stratum paired difference -0.00025417 and root-bootstrap 95% interval [-0.00035000, -0.00016250]. Its predeclared practical gate failed because the upper interval endpoint did not meet -0.0002. It is prior work, not an experiment run by this expedition. Its paired-error pattern is condition dependent and does not validate adaptive mode selection.

No confirmatory data were accessed. No experiment in this package establishes performance on an untouched test set or hardware.

## Categorical sum-product prototype on exact toys

**Hypothesis:** A loopy sum-product approximation over native categorical fault-location variables could preserve mutually exclusive Pauli outcomes while estimating logical-class probabilities, avoiding DEM splitting at the local channel level.

**Prototype:** `categorical_bp.py` keeps the outcome alphabet at each toy fault location and imposes detector and hypothesized logical parity checks. It compares Bethe partition estimates for logical 0 and 1. Tests use the existing independently validated one-qubit and two-qubit categorical toy models, then score BP decisions against their exhaustive exact posterior. No stochastic samples are used.

**Outcome:** The implementation returned normalized probabilities and converged on every toy syndrome, but its decoding quality is unacceptable on the one-qubit toy. It agrees with exact MAP on 2/4 syndromes and has exact-under-toy LER 0.057354 versus exact MAP 0.002646. On the two-qubit toy it agrees on 4/4 syndromes and has LER 0.060000, equal to exact MAP for that fixture. The same code therefore has a sharp topology-dependent result, not general validation.

The tests confirm interface, bounds, and full syndrome coverage. They do not certify algorithmic correctness or quality. The global observable-parity check creates additional loops. The hypothesis is rejected in this form. The result reinforces the need to validate posterior mass and logical decisions against exhaustive categorical references per topology before considering any circuit-scale approximation. No Q-SHIFT distance-3 experiment was run.
