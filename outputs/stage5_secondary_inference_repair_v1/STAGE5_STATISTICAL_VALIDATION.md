# Stage 5 statistical design validation after secondary-inference repair

## Decision scope

This report concerns readiness only. It does not authorize sampling. No Stage 5 evaluation shots were generated and no sealed historical test outcomes were accessed.

The 1,210-root-per-condition primary Endpoint B design remains the historical design: 27,225,000 total calibration/evaluation shots if later authorized; equal-weight mean of four nonzero-condition root-paired adaptive-minus-fixed LER differences; practical boundary `-0.0002`; planning alternative `-0.0003`; and the separate p=0 no-harm requirement. Primary critical values and gates were not changed in this repair.

## Prespecified validation workload

The repaired secondary procedure was validated on all six shape families at both 1.5x and 2x variability, with 200,000 independent validation replicates per family-scale cell. The study included:

- 192 marginal-size cells: 12 family-scale cases x four conditions x four Holm thresholds.
- 516 complete/partial-null Holm FWER cells: 12 family-scale cases x one complete-null configuration plus 14 nonempty proper true-null subsets x three false-null configurations.
- 12 simultaneous four-condition upper-bound coverage cells.
- 48 marginal coverage checks and 144 secondary-power rates in 24 scenario/effect pairs.
- One million calibration statistics per each of six reference families.

### Repaired secondary-inference gates

| Check | Prespecified acceptance rule | Worst validated result | Decision |
|---|---:|---:|---|
| Marginal size | simultaneous Wilson upper <= Holm step alpha + 0.002 | 0.050316 at alpha 0.05 (limit 0.052) | PASS |
| Complete/partial-null FWER | simultaneous Wilson upper <= 0.052 | 0.050444 (limit 0.052) | PASS |
| Four-condition simultaneous upper-bound coverage | simultaneous Wilson lower >= 0.94 | 0.957419 | PASS |
| Secondary power | Descriptive; no minimum power gate was frozen | weakest rate 0.74882 for lognormal 2x at -0.0003 | Reported, not gated |

The independent replay exactly reproduced six reference fingerprints, 192 marginal counts, 516 FWER counts, 12 coverage counts, and 24 power-scenario counts. A separate interval audit recomputed all Wilson intervals from the saved successes and trials, including the 144 displayed power rates, and verified the aggregate gate flags.

### Preserved primary design results

The earlier independent primary audit remains the source of the primary calibration and operating-characteristic result. Its design simulation used 100,000 replicates per cell. All 11 primary null cells passed. Worst one-sided type-I Wilson upper bound was 5.044%; lowest one-sided-coverage Wilson lower bound was 94.956%; lowest central-coverage lower bound was 95.815%.

The formal 1.5x planning-power gate at `-0.0003` passed in all five families; the weakest lower Wilson bound was 94.720%. The 2x sensitivity cells were also completed, including the previously missing zero-inflated case: zero-inflated 2x power was 82.440% (95% Wilson interval 82.203%–82.675%). The weakest 2x primary sensitivity was right-skew lognormal at 80.703% (80.457%–80.946%). The separate p=0 safety calibration, size, coverage, and safety-pass simulations passed their recorded gates; the eight simulated safety-pass cells were 100,000/100,000, each with Wilson lower bound 99.996%.

These are synthetic design simulations under the frozen root-effect families, not predictions of the eventual Stage 5 effect distribution.

## Preserved reporting correction

`SIMULATION_RESULTS.json` remains unchanged as the original run output. Its first report serializer used stale multiplicity counts for some Wilson bounds after the validation matrix grew to 12 family-scale cells. `SIMULATION_RESULTS_REANALYZED_V2.json` corrects only interval bounds and gate flags from the saved counts; it leaves all simulated counts, seeds, reference distributions, and statistics unchanged. The correction uses 192 marginal-size cells, 516 FWER cells, 12 simultaneous-coverage cells, 48 marginal-coverage cells, and 144 power-rate cells. Independent interval recomputation verified the corrected file. Earlier audit implementation failures V1–V3 are retained as historical records.

## Reproduction artifacts

- Full candidate replay: `audit_secondary_v4.py` -> `INDEPENDENT_AUDIT_V4.json`.
- Independent saved-interval recomputation: `audit_reporting_bounds.py` -> `INDEPENDENT_REPORTING_AUDIT.json`.
- Repaired counts and confidence bounds: `SIMULATION_RESULTS_REANALYZED_V2.json`.
- Prior primary design validation: `../stage5_design_validation_v3_n1210/STATISTICAL_VALIDATION_REPORT.md` and `INDEPENDENT_AUDIT.json`.

