# Prospective stop/go criteria

These gates are proposals to freeze before any new sample generation. They are not results, and passing a software check is not evidence of improved logical performance.

## Gate 0 — Prior-art distinction

**Pass only if** a targeted full-text/supplement audit of the closest 2018, 2023 and 2026 studies confirms that the planned equal-information/equal-compute comparison against both the strongest pooled fixed and periodic recalibration has not already been reported in the proposed scope. If not distinct, record no novelty and stop or propose a different question. The online weight-estimation method itself is not novel.

## Gate 1 — Scientific and implementation integrity

Require correct noiseless circuit behavior, detector/observable dimensions, noise injection location, DEM-to-Matching construction, observable prediction convention, deterministic seed separation, and independent tests that all policies decode byte-identical sampled detectors. Verify the estimator has no access to hidden noise parameters, regime IDs, observables or future/current block samples. Reject any dynamic graph update that changes boundaries, fault IDs, decomposition semantics or correlation metadata unintentionally.

## Gate 2 — Identifiability

Require full rank and acceptable conditioning in the decoder-relevant parameter subspace at the intended window; finite-window intervals must distinguish changes with calibrated coverage. If not, increase the window only within the latency ceiling or stop. If fitted parameters are not identifiable but the model directly predicts useful weights with calibrated uncertainty, document that reparameterization before test freeze.

## Gate 3 — Independent utility headroom

Before testing adaptation, calibration/development roots must show a stable paired utility advantage for the proposed updated model over pooled fixed, with candidate ranking/weight uncertainty reported. Proposed initial practical threshold: at least 5% relative and 0.0001 absolute LER reduction; require the lower-confidence evidence to exceed the threshold under the chosen independent-root method. If a stronger static model closes the gap, stop adaptation work.

## Gate 4 — Latency and overhead

Prospective software gate: (a) update computation, including estimator and model reconstruction, completes before the next scheduled activation block at the 95th percentile; (b) total additional CPU time per scored shot, amortized over the schedule, is at most 10% versus pooled fixed; and (c) the online policy's maximum update count does not exceed the equal-budget periodic comparator. Report median and 95th-percentile update time and memory. These software limits do not establish hardware real-time operation. A hardware claim additionally requires a named platform deadline and timing measurement.

Maximum decoder activation delay: **one complete block after sufficient evidence is accumulated**. For transitions with no usable estimate within this cap, record a censored/nontracked event and count its error impact in the full-schedule endpoint.

## Gate 5 — Statistical evidence

Require independent-root power of at least 80% at two-sided `α=.05` for the frozen practical effect; final primary confidence interval and prespecified test must support benefit over pooled fixed and, for a continuous-adaptation claim, over equal-budget periodic recalibration. Secondary comparisons receive Holm correction. If feasible power exceeds the predeclared resource cap, do not run a confirmatory experiment.

## Stop conditions

Stop before final evaluation if any of the following occurs:

- no defensible difference from the nearest prior work;
- no decoder-relevant identifiability at feasible windows;
- no independent calibration headroom over pooled fixed;
- updates cannot be made without unverified graph/DEM changes;
- estimator delay exceeds expected dwell times;
- overhead exceeds the frozen cap;
- the powered design is infeasible under the agreed resource budget;
- seed, data separation, causality or evidence-integrity check fails.

These rules are asymmetric by design: no positive result is assumed, and a failure is a valid feasibility conclusion.
