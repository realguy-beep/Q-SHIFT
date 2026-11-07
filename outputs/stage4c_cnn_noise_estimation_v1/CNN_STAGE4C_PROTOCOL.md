# Q-SHIFT Stage 4C — Frozen CNN Noise-Estimator Development Protocol

**Scope:** exploratory development only. No independent-test data are allocated, enumerated, opened, or used. This phase asks whether a small detector-only CNN estimates the synthetic burst probability well enough to improve adaptive PyMatching over the Stage 4B detector-profile estimator. It does not test hardware noise or establish an adaptive-decoding claim.

## Stage 4B evidence being extended

The prior Stage 4 development study used a rotated surface-code Z-memory circuit, distance 3, five rounds, 40 detectors, and one observable. Balanced gate depolarization and measurement noise were each 0.003; an independent synthetic simultaneous X error on data qubits 8 and 10 was injected after each of five MR boundaries with probability `p_burst` per boundary. This is a synthetic spatial common-cause stress model, not a calibrated hardware mechanism. The shared decoder conversion used `decompose_errors=True`, `approximate_disjoint_errors=True`, and `PyMatching(enable_correlations=True)`.

The Stage 4B detector-profile estimator used 45 detector-only features (40 marginal rates and five joint detector-pair rates), profile knots at p={0,0.01,0.02}, and grid resolution 0.00001. The Stage 4B independent audit passed exact re-decoding. Its development comparison reported 590/87,500 fixed-nominal errors, 474/87,500 profile-adaptive errors, and 476/87,500 privileged true-p errors. That result is preserved as historical development evidence. Stage 4C does not reuse its evaluation samples or its fitted profile batches: the same frozen estimator implementation is refit from Stage 4C's new training partition, shared with the CNN and Ridge.

## Research question and hypotheses

Primary hypothesis: a compact CNN that sees only an independent detector-calibration batch's actual Stim-derived time-space arrangement can lower paired logical-observable error relative to the refitted Stage 4B profile estimator on fresh, unseen nonzero burst probabilities.

The CNN estimates only `p_burst`; the estimated probability is inserted into the unchanged circuit/DEM builder and used to reconstruct PyMatching. The CNN never predicts a logical correction. A privileged true-p model is reference-only.

## Circuit and input representation

Use the exact Stage 4B generator and fixed parameters: balanced categorical gate noise 0.003, measurement noise 0.003, bias ratio 10, Z memory, d=3, r=5, burst pair (8,10), Stim DEM decomposition with `approximate_disjoint_errors=True`, and PyMatching correlations enabled. Circuit construction must retain 40 detector IDs and one observable across all p values.

The verified Stim detector coordinates are `[x,y,t]`. They map bijectively to a sparse `(time=6,y=4,x=4)` lattice by `(round(y/2), round(x/2), t)` with 40 occupied sites. CNN input has three channels: empirical detector firing rate at each occupied voxel; the empirical cofire rate for each of the five Stage 4B detector pairs copied to the two mapped endpoint voxels; and a binary occupancy mask. No detector is reordered or silently dropped. Each CNN training example summarizes a separate 250-shot detector-only batch.

## Models and training

1. **Stage 4B profile estimator:** the unmodified `DetectorProfileEstimator` implementation, freshly fit from all Stage 4C training batches at p={0,0.01,0.02}; inference receives one 2,000-shot calibration detector array only.
2. **Ridge baseline:** deterministic standardized Ridge regression over the same 45 batch-level detector features as the profile estimator. The alpha grid is {0.01,0.1,1,10}; validation MAE selects alpha, preferring smaller alpha on ties.
3. **CNN:** two 3D convolutions (3→4→4 channels, kernel 3, same padding, GELU), flattening of the real sparse time-space grid, a 16-unit GELU head, and sigmoid scalar output scaled to [0,0.02]. Approximately 7k parameters (exact count is recorded at execution). CPU-only, AdamW lr=0.003, weight decay=0.0001, MSE on p/0.02, batch size 32, maximum 400 epochs, early stopping after 30 epochs without validation-MAE improvement. The lowest validation MAE checkpoint is restored; earlier epoch wins ties. One deterministic model is trained, not an ensemble.

Training uses 120 independent 250-shot batches at each of p={0,0.01,0.02}: 90,000 shots. Supervised p labels are permitted only as training targets. Validation uses 60 independent 250-shot detector-only batches at each unseen p={0.005,0.015}: 30,000 shots. Validation p labels may select the Ridge alpha and CNN checkpoint only. No logical labels are generated for these partitions.

For each 2,000-shot evaluation calibration set, Ridge and CNN process eight disjoint 250-shot chunks and average their eight estimates. Stage 4B profile estimation processes the same 2,000 detector rows together. All methods receive the same calibration rows. No evaluation-shot detectors, labels, true p, event flags, or hidden regime IDs enter estimator inference.

## Evaluation allocation and pairing

Evaluation p values are {0,0.004,0.008,0.012,0.016}; each has seven new independent roots. Each root gets a separate 2,000-shot calibration detector stream and 2,500-shot paired evaluation stream. Five methods decode the identical 2,500 detector rows and are scored against the identical observable vector: fixed p=0, Stage 4B-profile estimate, Ridge estimate, CNN estimate, and privileged true p. Total evaluation use is 157,500 shots; total study use is **277,500 unique shots**, below the 300,000 hard ceiling.

Training, validation, calibration, evaluation, model-initialization, minibatch-order, bootstrap, and sign-flip RNG seeds are enumerated in `seed_inventory.json`. The prospective namespace is 4,230,000,001–4,230,000,554 inclusive, checked against the exact recoverable development-only metadata listed in `seed_audit.json`. This finite audit cannot rule out unrecorded RNG use. No sealed-test path is read.

## Selection, endpoints, and statistics

Checkpoint and Ridge-alpha selection use only validation data, before evaluation partitions are generated/scored. Calibration p estimation uses only the independent calibration detector rows. The primary estimand is the equal-weight mean of the four nonzero-p root-mean paired LER differences (CNN-assisted minus Stage 4B-profile-assisted). Root, not shot, is the inferential unit. A stratified root bootstrap resamples seven roots within each of the five p strata (20,000 draws; 95% percentile interval); one shared root-index cube is used for all paired decoder contrasts. A two-sided Monte Carlo root sign-flip test flips root differences independently within each p stratum (100,000 assignments; plus-one p; ties count as extreme). The fixed seeds are in config/inventory. One NumPy RNG stream is advanced in the written order: primary CNN−profile, then secondary CNN−fixed, CNN−Ridge, Ridge−profile. The three secondary equal-weight sign-flip comparisons receive Holm correction. Condition-level estimates and paired discordance counts are descriptive.

Noise-estimation performance reports signed bias and MAE across the seven roots within each p and overall, with descriptive stratified root-bootstrap intervals. p=0 is a no-harm control; its CNN−profile one-sided 95% upper bootstrap bound is reported. Shot-level resampling is not used.

**Minimum worthwhile advantage:** 0.0002 absolute LER (0.02 percentage points), retained from the prior Q-SHIFT development gate before Stage 4C evaluation. Keep the CNN only if all are true: (a) primary point estimate ≤−0.0002; (b) primary bootstrap upper bound <0; (c) sign-flip p<0.05; (d) at least three of four nonzero p condition means favor CNN; (e) p=0 one-sided upper bound ≤+0.0002; and (f) CNN's validation MAE is no more than 0.0005 absolute-p worse than Ridge's. Otherwise DROP if the evidence is clearly null/unfavorable, or INCONCLUSIVE if the uncertainty straddles the practical/no-harm boundary. In either case, retain the simpler profile estimator absent the predeclared CNN advantage. This small development study cannot justify independent confirmation by itself.

## Reproducibility and resource controls

Before any stochastic Stage 4C sample, the code/config/protocol/seed inventory/test hashes are written to `FREEZE.json`; the runner refuses to sample if any freeze hash changes. The independent auditor recomputes estimator outputs and all five PyMatching predictions from saved arrays. Raw detector/observable arrays and model weights stay local and ignored by Git; lightweight source, protocol, result summaries, audits, and SHA-256 metadata may be committed.

Hard stop: 1,800 seconds wall time, 2 GiB process RSS, or 300,000 unique generated shots. CPU only; no package installation or network required. Any missing seed record, pairing failure, invalid shape/value, or altered freeze stops execution. No independent-test data are touched.
