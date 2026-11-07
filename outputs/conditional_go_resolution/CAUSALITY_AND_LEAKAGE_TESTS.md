# Causality, leakage, and false-update tests

## Block timing contract

For block *t*, the active decoder is snapshotted before any block-*t* detector arrives. Only after that block is fully decoded and marked complete may a newly built immutable decoder be published for block *t+1*. The test fixture implements this boundary rule in [decoder_rebuild_fixture.py](decoder_rebuild_fixture.py).

The development selector’s API is `choose_from_detectors(det, profiles)`: it takes detector samples and a frozen detector-profile bank only. It has no logical-label argument. Calibration labels are discarded by the call site. Held-out samples are generated and scored only after the candidate index is selected. Evaluation observables are saved for scoring/audit but cannot influence the prior selection.

## Regression checks

`python -m unittest -v test_decoder_rebuild_fixture.py` — **5/5 passed**:

1. Expected 40-detector, one-observable schema and noiseless all-zero samples.
2. Independent reference DEM/matcher rebuild gives exact prediction equality.
3. Mid-block replacement is rejected; the next block sees the new version.
4. Reprocessing a block with radically changed future detector values cannot change which decoder was assigned to that block.
5. Out-of-order blocks are rejected.

The fixture does not simulate an actual concurrent QPU pipeline. It tests the Python-side version pinning and activation contract deterministically.

## Multiple checks and schedule-level false-update calibration

The original two-consecutive-95%-interval idea is not treated as a 5% familywise rule. Instead, this small development check uses a **schedule-maximum** statistic: for each stationary schedule, compute the maximum absolute studentized change over 40 detector marginals and all 9 overlapping trailing-window checks (4 completed blocks per window, 128 shots per block; 12 blocks total). A 95th-percentile threshold is estimated from 100 independent stationary calibration schedules, then evaluated once on a disjoint set of 100 schedules. The controller is limited to its first alarm/one accepted update per 12-block schedule for this check.

Observed result ([DEVELOPMENT_CHECKS.json](DEVELOPMENT_CHECKS.json), raw schedules and independent recomputation in [DEVELOPMENT_RAW_EVIDENCE.npz](DEVELOPMENT_RAW_EVIDENCE.npz) and [INDEPENDENT_VERIFICATION.json](INDEPENDENT_VERIFICATION.json)):

- Threshold: max statistic **4.8050**.
- Validation schedules with any threshold crossing: **2/100 = 2.0%**.
- Exact two-sided 95% binomial interval: **0.24%–7.04%**.
- Thus the observed rate is below 5%, but the interval includes rates above 5%; the calibration is **not sufficient to certify a 5% schedule-level false-update bound**.

The maximum-over-checks calibration explicitly accounts for overlapping windows and repeated looks within the fixed schedule. It does **not** validate an unbounded stream or repeated post-update resets. Before a multi-update policy is tested, the entire reset/update policy must be calibrated on independent stationary schedules, or a predeclared alpha-spending/always-valid procedure must be proven and tested for the actual dependent detector process. The present trigger statistic also uses detector-marginal Bernoulli approximations; it is not a general test of DEM identifiability.

## Independent evidence recomputation

The separate [verify_development_evidence.py](verify_development_evidence.py) did not import the experiment runner. It recalculated all 24 calibration selections, rebuilt all chosen and fixed PyMatching decoders, matched all 72 saved prediction arrays exactly, recomputed the 200 schedule maxima from saved detector matrices, and matched the false-update count. Result: **PASS**. This is independent recomputation of these development artifacts, not a validation of an adaptive performance claim.
