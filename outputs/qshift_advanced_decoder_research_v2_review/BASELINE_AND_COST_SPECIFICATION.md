# Corrected Baseline, Identifiability and Cost Specification

This corrects the comparator and costing passages in `BASELINE_FAIRNESS_MATRIX.md`, `PHASE2_RESEARCH_PROTOCOL.md`, `PRE_REGISTRATION_DRAFT.md`, and `SUPERVISOR_REVIEW_REQUEST.md`. Original drafts remain unchanged.

## Primary pooled-static comparator

**Candidate p-grid:** `{0.000, 0.002, 0.004, …, 0.020}` (11 candidates). Build one ordinary-MWPM graph per grid point. Correlation-aware graphs, if evaluated, are a separate mode and obey the constructor/decode flag requirement.

**Calibration mixture:** generate an independent detector-only calibration allocation from each of the four primary schedule strata (abrupt up, abrupt down, smooth drift, transient), with identical detector-shot count per stratum. Concatenate and pool feature rows without exposing the schedule labels to the policy. This matches the primary estimand's equal scenario weights. Use 20 independent calibration roots/stratum for option A, 50 for B, 100 for C, with 1,000 detector shots/root. Calibration roots are separate from tuning and scored evaluation roots.

**Selection objective:** templates consist of 6,000 independent detector shots at each of the 11 p-grid points (66,000 total), under the frozen base circuit/mechanism. Form the pooled 45-feature mean from the calibration mixture and each p-template mean. Let feature scales be the pooled template SD across all grid points, floored at 0.001 exactly as `sqrt(max(var,1e−6))`. Choose the p minimizing the mean squared standardized feature residual across 45 features. Break numerical ties by the smaller p. No observable/logical label or evaluation sample enters the objective. Freeze floating-point tolerance before any run.

This is an operational, detector-only pooled compromise representing the equal-weight primary scenario mix. It is appropriate to ask whether adaptation helps beyond a static model fitted to that same detector information. It is **not** globally optimal, not necessarily the best fixed decoder under logical risk, and not an oracle. A supervised label-selected static candidate may be a secondary privilege-labeled comparator only; it cannot replace this primary.

## Tuning separation and causal information

Use independent tuning roots for all policy hyperparameters, including profile windows, EWMA alpha, periodic interval, change threshold, hysteresis, dwell and feature set. Tuning may use prespecified scripted scenario/change-time metadata to evaluate responsiveness and alarm rates, but no logical outcomes are needed or allowed for the primary-policy selection objective. No evaluation stream, detector row, observable, or outcome may be used to choose a p, threshold, hyperparameter, subgroup, or decoding mode. If tuning criteria are changed, the protocol and budget must be revised before evaluation.

All adaptive policies use detector rows strictly earlier than the decoded block; updates computed after block b first affect b+1. All policies receive the same detector rows, profile templates, calibration/tuning shot opportunities, p-grid/cache, update boundary and compute instrumentation. Graph decode flags are explicit at both construction and decode.

## Identifiability: what can be inferred

The current estimator observes 45 features: 40 detector bits and five pair co-firing indicators for detector pairs `(8,10)`, `(16,18)`, `(24,26)`, `(32,34)`, `(36,38)`. It does not observe fault-event indicators, logical labels, or p. Thus it can only infer a burst probability if distinct burst probabilities induce distinguishable distributions of those detector features under the assumed gate/readout model. The current one-parameter profile fit does not establish identifiability when measurement probability is misspecified or jointly unknown. A matching p estimate can reflect compensating measurement noise; good template fit does not prove physical causal attribution.

**Deterministic structural checks proposed (no Stim sampling):**

1. Reconstruct the detector error model deterministically for a symbolic grid of `(p_burst,p_measurement)` values with unchanged circuit topology; extract each mechanism's detector parity mask and probability expression. Do not call any sampler.
2. Derive exact expected single-detector and pair-cofire features from independent DEM mechanisms. For a binary parity subset A, its parity character is `χ_A=Π_m(1−2p_m)^{|A∩mask_m| mod 2}`; hence `P(parity_A=1)=(1−χ_A)/2`. For cofire `(i,j)`, `E[D_iD_j]=(1−χ_i−χ_j+χ_{i⊕j})/4`. Account explicitly for mutually exclusive/decomposed mechanisms; if the DEM approximation prevents exact original-circuit expectations, label results as DEM-level only.
3. Build the 45-vector expectation map `g(p_burst,p_measurement)` over the approved probability range. Compute symbolic or high-precision finite-difference Jacobian columns for each parameter. Rank deficiency means local non-identifiability; near-collinearity / large condition number means weak practical identifiability. Also test profile-distance collisions across grid pairs and boundary points.
4. Repeat with the currently assumed fixed measurement rate and with measurement rate free; compare the burst-only profile's bias direction under the misspecified p=.006 case. Inspect sensitivity to gate/readout uncertainty and feature scaling.
5. State limitations: local full-rank feature means are necessary, not sufficient for full-distribution identifiability; feature moments can collide even if higher-order distribution information differs. Exact distribution-level checks may require symbolic factorization or exhaustive model algebra, not sampled shots. Do not call one successful rank check “identified in data.”

**Independent mismatch stress:** fresh, independent roots with burst fixed at p=.008, generated measurement-flip probability p=.006 while the detector estimator/decoder model is fixed at .003. Keep its data out of primary calibration, tuning and four-scenario estimates. The online controller receives detector features only and never receives the actual p=.006 or the mismatch flag. Report separately LER difference, false alarms, graph updates, and profile behavior. This is a robustness stress, not a claim that all drift types are covered.

## Exact CPU accounting

Let H be the prespecified number of scored stream replays at the fixed per-stream shot length; H is a deployment horizon, not an evaluation sample size. For each policy j and mode m report CPU seconds separately as:

`C_jm(H) = C_template_shared,m + C_bank,jm + C_cal,j + C_tune,j + H × (c_profile,j + c_change,j + c_select,j + c_lazy_build,jm + c_decode,jm)`.

- `C_template_shared,m`: one-time profile-template construction/fitting used by the declared policy family; display once and state its allocation in every comparison.
- `C_bank,jm`: matcher build time for graphs policy j actually needs. For event/trailing/EWMA/periodic, a common cached p-grid bank may be shared and charged once to that adaptive family. For fixed static p, include its own single-graph build. Do not assign the adaptive graph-bank cost only to one adaptive policy or pretend a static one-graph decoder needs the whole bank.
- `C_cal,j`: detector calibration acquisition CPU/generation plus profile-fitting/selection CPU; separate acquisition from compute. If a calibration bundle is shared by methods, show common cost once and provide a consistent per-method allocation as a secondary view.
- `C_tune,j`: generation, scoring and selection CPU for the independent tuning set. Shared tuning stream generation is a common overhead, but policy-specific tuning calculations remain attributed to each method.
- Per-stream terms: profile update, change statistic, graph choice, any graph construction on a cache miss, and decoding. Also report wall time and peak process RSS; do not sum wall times as CPU.

For the direct event-versus-EWMA comparison on a shared adaptive bank, shared template/bank/calibration costs cancel only in an incremental-cost view; show them anyway. For event versus pooled-static, use each policy's actual bank requirement. Include common data-generation/scoring as a separate study overhead, not as decoder CPU. Report `C_jm(H)` and difference/ratio, not only online per-shot time.

## Deployment horizon and guard

Report sensitivity at **H=160** (the prior Pilot 2 evaluation stream count) and **H=1,000** (a proposed longer reuse scenario). These are sensitivity points, not claims about the owner's production usage. The owner must select the primary H from the intended number of stream episodes before outcome access; if no defensible H can be supplied, report the full cost curve and make no deployment-efficiency claim.

Proposed actionable cost gate: at the owner-frozen H, event-triggered ordinary mode must have `C_event(H) ≤ C_static(H)` and `C_event(H) ≤ C_EWMA(H)`, and remain within the approved RSS cap. It must separately satisfy the approved LER and stationary-harm rules. No graph-switch reduction substitutes for a failed CPU gate. Owner approval is required for H, whether acquisition/generation is charged in the deployment cost objective, the RSS cap, and whether equality or a fractional savings requirement is desired.

Historical Pilot 2 arithmetic: event-only tuning/calibration cost 6.922 CPU-s; online two-mode per-stream event 0.009863s versus EWMA 0.051074s; simple break-even `6.922/(0.051074−0.009863)=168.0` streams. At H=160 the event setup is not amortized, consistent with the saved report's +0.328s all-in comparison; at H=1,000 the simplified net event advantage is about 34.29 CPU-s. This is one historical path and must not be extrapolated to V2.4/new data.
