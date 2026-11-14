# False-switch risk analysis

## One alarm is not a switch guarantee

For one nonnegative e-process with a valid conditional null and threshold `1/alpha`, Ville controls the probability of ever crossing that threshold by `alpha`. For a start-time mixture, the prior weights sum to one, so the same single-process statement applies. This does not automatically control expected decoder switches, simultaneous up/down tests, alarm resets, repeated epochs, or an automatically selected graph.

## Invalid opposite-direction null

Suppose a low-state test falsely alarms and the controller labels the process high. The high-state downward statistic is justified only while its own high-regime null is true. A false state change does not make the physical process high; the opposite test can therefore run under an invalid null. Spending alpha at each reset does not cure a null that is false after a misclassification. An explicit state-reset authority or a single common-null construction is required.

## Indifference region and drift

The certified burst regions in the saved mean construction are low `p_b∈[0,.002]` and high `p_b∈[.010,.018]`, with measurement `p_m∈[.001,.005]` and gate `p_g∈[.002,.004]`. The interval `(.002,.010)` is not a validated decision region. Some subintervals have positive expected-log bounds for one direction; others remain unclassified. A controller must use `UNCERTAIN/STATIC_FALLBACK` throughout the indifference band. A finite list of endpoint/ramp calculations is not a continuous tracking theorem.

## Multiple directions and epochs

Running two tests each at alpha, or restarting one after every alarm, invalidates the single-process interpretation unless an explicit familywise/anytime allocation covers all episodes and each episode's null is valid. Candidate options include:

- one direction selected before monitoring and a single alarm;
- predeclared alpha spending across externally verified epochs with reset identity and proof that each new null holds;
- a common-null monitor that remains valid through all states, with a separate state estimator whose errors are controlled.

None is an implemented Q-SHIFT controller. A hard rate for graph switches, horizon-specific false-switch probability, or expected false-switch count has not been selected. Those are different objectives from average run length.

## Recommended safe fallback

Until controller mathematics and decoder utility are established, retain the strongest validated static PyMatching decoder. An alarm may trigger a human review or a separate calibration workflow; it must not automatically assert physical cause, update a matching graph, or claim improved LER. The fixed decoder's own model limitations must be documented, but it is the current safe comparison arm.

## Minimum evidence before a controller claim

1. Define the controlled error metric (ARL, fixed-horizon false alarm, or repeated-switch probability).
2. Specify trusted initialization and state/reset authority.
3. Prove each state-conditioned null, including after a previous alarm.
4. Allocate alpha across directions and episodes before monitoring.
5. Define the indifference-band action and abstention/fallback.
6. Bound calibration, DEM rebuild, and activation latency causally.
7. Prove exact-circuit/DEM model parity or use a law matching the deployed decoder.
8. Only then design a development-only paired decoder-utility experiment.
