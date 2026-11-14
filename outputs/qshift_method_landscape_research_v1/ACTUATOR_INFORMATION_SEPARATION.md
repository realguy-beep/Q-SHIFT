# Actuator and information-set separation: detector feedback in adaptive QEC

**Status:** deterministic structural reasoning from source inspection and primary-paper methods; not a performance result.

## The control loop in the 2026 Willow RL paper

Sivak et al. (2026) use the average error-detection-event rate as a surrogate objective to change physical pulse/control parameters. The control action changes the quantum process and hence can change the distribution of future detectors. Their decoder-prior steering is described separately and relies on logical-error-rate estimation; the article notes that this is not straightforward to scale to real-time operation. These are two distinct actuators and two different feedback objectives.

## The decoder-only action in current Q-SHIFT

The inspected Q-SHIFT estimator / decoder prototype separates the modules:

- `outputs/stage4_noise_adaptive_feasibility_v1/prototype.py:43` defines the detector-profile estimator.
- `outputs/stage4_noise_adaptive_feasibility_v1/prototype.py:108` builds a circuit and a PyMatching graph for a supplied assumed burst probability; `:126` decodes an already supplied detector array.
- `qshift_core_v1/controller.py` accepts a detector-provenance estimate/proposal and applies selection/fallback logic; it does not itself alter the circuit noise process.

Under the current software-only decoder-selection architecture, for physical noise state `theta_t` and decoder choice `a_t`:

`P(D_t, O_t | theta_t, a_t) = P(D_t, O_t | theta_t)`

provided `a_t` only changes the decoder graph used to interpret an already generated shot. Thus `E[D_t | theta_t, a_t]` is invariant to decoder choice. The detector-rate reward in the hardware RL control paper cannot, by itself, rank cached decoder graphs in this decoupled simulator: it can estimate/model the noise state, but decoder utility needs (i) a valid noise-to-decoder decision rule or (ii) an outcome/utility signal.

This is a causal factorization implied by the current code interface and task definition, not a theorem about all QEC deployment. If decoder latency or a correction policy feeds back into the physical circuit, then the action may affect future detector distributions; that would be a different closed-loop simulator and estimand.

## Research consequences

1. Keep physical-control RL, physical-parameter estimation, and decoder-prior selection as separate method classes.
2. A detector-only estimator can be scientifically useful even when decoder output has no causal effect on detector features; it must still establish identifiability under its noise family.
3. To claim an adaptive *decoder* benefit, compare paired logical outcomes after predictions are frozen. Detector statistics alone cannot demonstrate that one decoder choice reduces logical errors.
4. Information parity should state whether a method sees detector bits, all raw measurement readouts, logical labels, hardware control telemetry, or decoder soft outputs.
5. A detector-rate controller is only a physical-control comparator if Q-SHIFT exposes a physical-control action that changes the generating process. It is not a valid baseline for a pure decoder-weight switch.

## Scope / evidence limits

The identity above assumes the decoder action is downstream-only and that no real-time feed-forward into gates/measurements is changed by the action. It does not establish the optimality of the Q-SHIFT estimator, its finite-history accuracy, alarm calibration, or any logical-error benefit. No samples, shots, decoder outcomes or protected data were accessed.
