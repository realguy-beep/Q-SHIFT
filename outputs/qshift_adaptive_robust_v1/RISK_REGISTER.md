# Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **The 95% broad target is not reachable.** At p = 0.003 the floor caps R near 65% | high | the target gates fail | Report G_AGG/G_EVERY honestly. Keep high-risk conditions in eval and do not drop them. Make the primary claim H1a/G_ADAPT, not 95% |
| R2 | **Adaptation adds nothing over a strong static decoder** (history: Phase 4C, strong-fixed v1 null) | high | Q2 fails | G_ADAPT ablation (Q vs Q0) is a primary test. A null is a publishable negative |
| R3 | **Information leakage:** condition tags, true p or true support reach a deployable arm (it happened once: strong-fixed v1 pooled estimator) | medium | invalidates the comparison | API takes only `detectors` (tested); oracle arms in a separate module; an independent audit of the arm inputs before the freeze |
| R4 | **Unequal labels:** Q gets labeled calibration shots that comparators lack | medium | inflated gain | Fairness rule 2: labels to all calibrated arms or none |
| R5 | **Selection on eval:** variant or threshold chosen after seeing eval | low (process) | invalid | Freeze hashes, `--expected-head`, single attempt, logged val selections |
| R6 | **Near-zero-error conditions** make R unstable or undefined | high at p = 0.001 | noisy gates | Eligibility frozen from val projections; ≥ 30 projected S\* failures; undefined-replicate rule |
| R7 | **Synthetic tests over-state the prototypes:** independent Bernoulli data, linear rate model | high | H-E1–E3 fail on real circuits | Roadmap steps 2 and 4 test them on Stim dev data before any freeze |
| R8 | **Floor variants break successes at about 1e-4** (undetectable in 600 controls) | medium | a net-zero or negative effect | Full 1.2 M re-decode (roadmap step 1) with a paired CI before any selection |
| R9 | **Compute:** BP+OSD 5–30 ms/shot; d=7 is about 10× more | high | budget overrun, under-power | Preflight with a frozen hard cap; d=7 exploratory and capped; consider BP+LSD (latency) |
| R10 | **Novelty overlap** with Bhardwaj et al. 2025 (drift estimation) and Takou & Brown 2025 (correlator DEMs) | high | no novelty claim | Position as benchmark and attribution work; full-text review before any claim |
| R11 | **Pre-existing repository issues:** dashboard config hash mismatch; `beliefmatching` missing | known | blocked tests | Documented in `BASELINE_AUDIT.md` §3–4; owner decision; dependency request if needed |
| R12 | **Statistical approximations:** delta-method power, Wilson–Hilferty χ², independence in regime fit | medium | mis-sized study or miscalibrated UNKNOWN rate | Power is checked by a simulated preflight on val; the UNKNOWN rate is calibrated on val blocks |
