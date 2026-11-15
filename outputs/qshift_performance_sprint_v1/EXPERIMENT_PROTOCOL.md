# Q-SHIFT Performance Sprint V1 — Frozen Development Pilot

**Classification:** isolated synthetic development pilot. Not Gate 3A, not a continuation of NS-5B, and not a sealed or confirmatory evaluation.

## Question and estimands

On the distance-3, five-round rotated Z-memory Stim circuit with the documented synthetic spatial common-cause X burst on data qubits 8 and 10, does a detector-only calibrated burst profile improve decoding over one strong pooled fixed PyMatching model across the prespecified burst grid?

Primary contrast: equal-weight mean, across nonzero burst probabilities 0.004, 0.008, 0.012, and 0.016, of the root-paired logical-error-rate difference (calibration-profile PyMatching B minus pooled-fixed PyMatching A). Negative favors B. The zero-burst condition p=0 is a separate no-harm gate. The pilot does not test unseen probabilities, physical noise, temporal persistence, online controller switching, or hardware performance.

## Arms and information parity

All arms receive byte-identical evaluation detector arrays and predict the same Stim observable. The saved observable labels are used only after decoder predictions are complete.

- **A — pooled fixed PyMatching (primary baseline):** one static matcher for all conditions, built from a single burst probability estimate obtained by applying the frozen detector-profile estimator to the pooled detector-only calibration batches. This is a strong fixed baseline matched to the pilot's balanced condition mixture.
- **B — detector-calibrated profile PyMatching (candidate):** one matcher per evaluation root, built from the estimate produced using that root's separate detector-only calibration batch. The decoder receives only the resulting DEM and detector bits; no true evaluation p or logical label is passed to it.
- **C — true-p PyMatching (privileged reference):** matcher built using the simulation's true burst parameter for that condition. Oracle/reference only; excluded from the primary decision.
- **D — no-burst PyMatching (context baseline):** matcher built with p=0; descriptive comparison only.

A and B use the same detector-only estimator, identical supervised training data, and the same complete set of calibration samples. The only policy difference is pooling all calibration detector rows into one global estimate (A) versus retaining the preassigned calibration-batch groups and estimating per root (B). Calibration batch identity is available to both and is not a true p label. The regression estimator is trained only on detector rows and simulation-parameter p labels from the training partition; observable labels are discarded. That is simulator supervision, not an inference-time input. The true-p arm has an explicit information advantage.

## Noise and circuit

Use existing source at the pinned sprint base: outputs/phase2b_pauli_bias/noise_model.py and outputs/phase3a_correlated_noise_preflight/simulator.py. Circuit: Stim surface_code:rotated_memory_z, distance 3, rounds 5, balanced within-gate Pauli composition, gate-fault probability 0.003, measurement-flip probability 0.003, burst pair (8,10), and independent per-round burst probabilities [0, 0.004, 0.008, 0.012, 0.016]. Expected 40 detectors and one observable.

Stim DEM conversion is fixed at decompose_errors=True, approximate_disjoint_errors=True. All matchers use PyMatching enable_correlations=True at construction and decoding. The chosen pair is documented as graphlike in the existing Phase 3A source/protocol. The Pauli-channel DEM approximation remains a limitation; this pilot does not claim exact preservation of all mutually exclusive gate-channel probabilities.

## Allocation and seeds

- Estimator training: 1,000 detector shots at each of five p settings = 5,000.
- Separate calibration: 500 detector shots for each of 10 roots at each of five settings = 25,000.
- Paired evaluation: 2,000 shots for each of 10 independent roots at each of five settings = 100,000.
- Total ceiling and planned total: 130,000 unique Stim shots, 105 sampler calls.
- Seeds are generated deterministically from the frozen namespace and exact partition labels in seed_inventory.json. All 108 seed values (including the bootstrap stream) must be unique within this sprint. The inventory screens internal collisions only; no global historical or Stage 5 seed inventory is read.
- Training, calibration, evaluation, and bootstrap streams are disjoint by label and seed. Each root's calibration and evaluation seeds differ.

No evaluation setting or model is selected using evaluation observables. No post-hoc parameter, condition, root, threshold, or seed exclusions are permitted. A failed run is preserved and is not automatically retried.

## Frozen estimator and decoding

Use ridge regression on standardized 40-dimensional detector-bit rows, intercept included, L2 penalty alpha=10.0, target equal to the configured simulator burst probability, and output clipped to [0, 0.016]. The estimator is fit once on the 5,000 training detector rows. Calibration estimates are means of per-shot regression predictions. No logical observable is available to the estimator. Do not tune alpha or feature representation after seeing evaluation results.

Each DEM is built from the declared Phase 2B/3A circuit source with the corresponding assumed p. Hash the circuit text, DEM text, and decoder model record. All arms use identical Stim detector ordering D0..D39 and observable L0.

## Inference

Primary uncertainty: 100,000 root-stratified paired bootstrap replicates, independently resampling the 10 root clusters within each condition and equally weighting the four nonzero conditions. Report a two-sided percentile 95% interval. The no-burst safety gate uses the 95th percentile of the root-stratified bootstrap for the p=0 paired B-A difference. Shots within a root are not treated as independent inferential units.

Also report every condition and root, decoder error counts/rates, paired prediction disagreement, B-only errors and A-only errors, estimator bias/MAE, oracle results, sampling/decoding/construction time, and peak process working set. If A has fewer than 100 errors pooled over nonzero evaluation conditions, mark efficacy as underpowered and do not report a credible 50% reduction.

## Prespecified decision

- **GO (development evidence only):** at least 100 A errors across nonzero conditions; primary 95% interval entirely below zero; B point relative reduction at least 50%; B has lower point LER in at least 3 of 4 nonzero conditions; no nonzero condition has B-A harm above 0.0005; and the p=0 one-sided 95% bootstrap upper bound is below +0.0005.
- **NO-GO:** the primary 95% interval is entirely at or above zero, or the p=0 one-sided 95% lower bound exceeds +0.0005.
- **INCONCLUSIVE:** every other outcome, including insufficient baseline errors, wide intervals, failed/incomplete artifacts, or failure to meet the GO gate without meeting NO-GO.
- Oracle C and nominal D cannot turn an inconclusive/negative primary result into GO. Any GO is only a reason to design a separately reviewed confirmation study, not a scientific superiority claim.

The 50% figure is a prespecified target threshold, not an expected result.

## Resource and stopping limits

Maximum 600 seconds wall time; maximum measured peak process working set 1 GiB; maximum 128 MiB generated artifacts; require at least 1 GiB free disk at start and before each partition write. These are checked between bounded operations and do not constitute a hard OS memory limit. Stop on limit breach, sampler error, shape/identity mismatch, seed collision, unexpected existing output, or any evaluation-label use before all decoders return. Preserve partial files and mark incomplete; no automatic resume/retry. No Stage 5 path or data is used.