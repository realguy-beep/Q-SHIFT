# Phase 2C-R1 deterministic validation record

## Commands and scope

Run from repository root:

```text
python outputs/qshift_advanced_decoder_research_v2c_review/guard_distribution_review.py
```

The analysis uses Stim 1.16.0 circuit/DEM construction and deterministic parity expectation/covariance algebra. It constructs deterministic single-fault signatures and calls SciPy chi-square distribution functions only for explicitly counterfactual calculations. It uses no Stim sampler, random generator, decoder, logical outcome, model training, seed inventory or protected data. Runtime was about 32 seconds on the recorded run.

## Reproduced guard calculations

- Central cutoffs: `χ²_44(.99)=68.7095129693`, `χ²_45(.99)=69.9568320658`.
- Exact-categorical truth with exact reference covariance: under nominal `(.008,.003)`, projected whitened covariance eigenvalues span `.81113–1.00203` (mean `.98275`); under mismatch `(.008,.006)`, span `.82625–1.71386` (mean `1.19519`). Thus the mismatch alternative is not identity-whitened.
- At mismatch, exact-circuit null-grid fit is `p_b=.0083`, discrete-grid population energy q **.03782529/shot**. Continuous tangent projection gives essentially the same energy **.03782528/shot**. `Nq` is **37.8253** and **378.253** at N=1,000 and 10,000; these values are not realized T statistics.
- Only under the counterfactual identity-covariance continuous-fit model does SciPy's noncentral-χ² survival function give rejection sensitivity **.79787** at N=1,000 and approximately 1 at N=10,000. The actual Candidate D false-alarm probability and power are reported as **undetermined**.
- Approximate-DEM reference and data cases yield similar but distinct values; all combinations are retained in `guard_distribution_results.json`.

## Candidate A population-limit reproduction

The R1 routine explicitly follows the source estimator's five knots, fixed `.003` measurement assumption, linear interpolation and `.00001` burst search. It substitutes exact expectation templates and population-limit pooled feature scales for finite calibration batches. Exact-template fits were `.00800` nominal, `.01091` at measurement mismatch, `.00513` when actual p_m=0, and `.01484` when actual p_m=.010. DEM-template results were `.00801`, `.01092`, `.00513`, `.01485`. Phase 2C's A-labeled `.0001`/bilinear row returned `.0080`, `.0109`, `.0051`, `.0148`, respectively. This confirms the reported bias direction while correcting the implementation-equivalence description.

## Gate-rate sensitivity

Rescaling only the existing balanced categorical P1/P2 channels produced local burst/measurement/gate derivative column cosines `.443/.321/.841` and 45×3 Jacobian singular values `47.139, 7.132, 3.228`. Fixed `.003` templates fitted exact categorical population truth at gate p `.002/.003/.004` as `(.0083,.0004)`, `(.008,.003)`, `(.0077,.0056)`. This validates a deterministic nuisance-confounding example, not the operating characteristics of a finite estimator.

## Independence and limits

Covariances are computed from Phase 2B parity moments. The direct distribution-function values are deterministic mathematical evaluations, not simulated outcomes. The covariance/chi-square derivation assumes IID shots and fixed covariance; the actual model's exact covariance differs from the reference, and the Phase 2C optimizer has a fixed finite grid. The algebra reuses the same single-fault masks as Phase 2B, so it does not independently validate Stim circuit compilation or physical-model adequacy. No finite-history alarm behavior, empirical size, detection probability or decoder performance is validated.
