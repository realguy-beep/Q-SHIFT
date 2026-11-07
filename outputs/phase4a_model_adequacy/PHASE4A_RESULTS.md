# Phase 4A results

Status: **completed**.

Shot counts: `{'template': 450000, 'calibration': 1200000, 'validation': 600000, 'test': 1800000, 'noiseless_diagnostic': 256}`. Wall time 4.88 s; peak process memory 140.7 MiB.

Failures/stopping reasons: []

## Validation

| Condition | Shots | Raw | Fixed | Calibrated | Informed | Calibrated difference | Exact paired p |
|---|---:|---:|---:|---:|---:|---:|---:|
| data_heavy | 200000 | 20432 | 2725 | 2795 | 2795 | 70 | 0.0326709 |
| nominal | 200000 | 12137 | 964 | 964 | 964 | 0 | 1 |
| measurement_heavy | 200000 | 7094 | 372 | 321 | 321 | -51 | 1.08091e-06 |

All rates, Wilson intervals, paired intervals, seed-bootstrap intervals, per-seed counts and secondary adjusted p-values (test only) are preserved in RESULTS.json. Validation outcomes are screening evidence, not independent confirmation.

## Test

| Condition | Shots | Raw | Fixed | Calibrated | Informed | Calibrated difference | Exact paired p |
|---|---:|---:|---:|---:|---:|---:|---:|
| data_heavy | 600000 | 61451 | 8577 | 8599 | 8599 | 22 | 0.707578 |
| nominal | 600000 | 36729 | 2912 | 2912 | 2912 | 0 | 1 |
| measurement_heavy | 600000 | 21221 | 1118 | 940 | 940 | -178 | 5.60079e-23 |

All rates, Wilson intervals, paired intervals, seed-bootstrap intervals, per-seed counts and secondary adjusted p-values (test only) are preserved in RESULTS.json. Validation outcomes are screening evidence, not independent confirmation.

## Runtime boundaries

{
  "sampling_seconds": 0.26776779999818245,
  "decoding_seconds": {
    "fixed": 0.6451665000022331,
    "calibrated": 0.6760721999962698,
    "model_informed": 0.6385251000001517
  },
  "fit_seconds": 0.05528950000552868,
  "model_build_seconds": 0.2246834999996281
}

Decode times include all validation/test decoding for each model. Divide by the total completed validation/test shots for batched seconds/shot; this is not hardware latency. Calibration overhead is separately recorded. Model construction precedes fitting; specialists select from nine prebuilt models. Peak process working set includes Python and native allocations, but is not per-model memory.

Primary success gate: True.

## Detailed independent test analysis

All differences below are candidate minus fixed; negative favors the candidate. Intervals and rates use probability units unless stated otherwise.

### data_heavy

Raw observable error rate: 0.10241833.

| Decoder | Errors | Rate | Wilson 95% interval | Discordant: candidate-only / fixed-only |
|---|---:|---:|---|---|
| fixed | 8577 | 0.01429500 | [0.013997737352258486, 0.014598481993777598] | 0 / 0 |
| calibrated | 8599 | 0.01433167 | [0.014034024440431508, 0.014635527769429278] | 1578 / 1556 |
| model_informed | 8599 | 0.01433167 | [0.014034024440431508, 0.014635527769429278] | 1578 / 1556 |

**calibrated:** paired difference 0.00003667; paired approximate 95% CI [-0.0001462083004944858, 0.00021954163382781913]; seed-bootstrap mean 95% CI [-0.00018004166666666667, 0.00023999999999999998]. Exact paired p=0.70757787; seed sign p=0.82380295. Seed wins/losses/ties=9/11/0. Disagreement rate=0.00522333. Secondary Holm-adjusted paired p=1.0; sign p=1.0. Relative change vs fixed=0.256%.

**model_informed:** paired difference 0.00003667; paired approximate 95% CI [-0.0001462083004944858, 0.00021954163382781913]; seed-bootstrap mean 95% CI [-0.00017999999999999996, 0.00023499999999999997]. Exact paired p=0.70757787; seed sign p=0.82380295. Seed wins/losses/ties=9/11/0. Disagreement rate=0.00522333. Secondary Holm-adjusted paired p=1.0; sign p=1.0. Relative change vs fixed=0.256%.
### nominal

Raw observable error rate: 0.06121500.

| Decoder | Errors | Rate | Wilson 95% interval | Discordant: candidate-only / fixed-only |
|---|---:|---:|---|---|
| fixed | 2912 | 0.00485333 | [0.0046806279968238645, 0.005032378914350504] | 0 / 0 |
| calibrated | 2912 | 0.00485333 | [0.0046806279968238645, 0.005032378914350504] | 0 / 0 |
| model_informed | 2912 | 0.00485333 | [0.0046806279968238645, 0.005032378914350504] | 0 / 0 |

**calibrated:** paired difference 0.00000000; paired approximate 95% CI [0.0, 0.0]; seed-bootstrap mean 95% CI [0.0, 0.0]. Exact paired p=1; seed sign p=1. Seed wins/losses/ties=0/0/20. Disagreement rate=0.00000000. Secondary Holm-adjusted paired p=1.0; sign p=1.0. Relative change vs fixed=0.000%.

**model_informed:** paired difference 0.00000000; paired approximate 95% CI [0.0, 0.0]; seed-bootstrap mean 95% CI [0.0, 0.0]. Exact paired p=1; seed sign p=1. Seed wins/losses/ties=0/0/20. Disagreement rate=0.00000000. Secondary Holm-adjusted paired p=1.0; sign p=1.0. Relative change vs fixed=0.000%.
### measurement_heavy

Raw observable error rate: 0.03536833.

| Decoder | Errors | Rate | Wilson 95% interval | Discordant: candidate-only / fixed-only |
|---|---:|---:|---|---|
| fixed | 1118 | 0.00186333 | [0.0017573542441362416, 0.001975690953332579] | 0 / 0 |
| calibrated | 940 | 0.00156667 | [0.0014697335046707388, 0.0016699821582163723] | 80 / 258 |
| model_informed | 940 | 0.00156667 | [0.0014697335046707388, 0.0016699821582163723] | 80 / 258 |

**calibrated:** paired difference -0.00029667; paired approximate 95% CI [-0.0003567189110023128, -0.00023661442233102048]; seed-bootstrap mean 95% CI [-0.0003666666666666667, -0.00022166666666666667]. Exact paired p=5.600789e-23; seed sign p=4.0054321e-05. Seed wins/losses/ties=19/1/0. Disagreement rate=0.00056333. Secondary Holm-adjusted paired p=primary; no secondary adjustment; sign p=primary diagnostic. Relative change vs fixed=-15.921%.

**model_informed:** paired difference -0.00029667; paired approximate 95% CI [-0.0003567189110023128, -0.00023661442233102048]; seed-bootstrap mean 95% CI [-0.0003683333333333333, -0.00022333333333333333]. Exact paired p=5.600789e-23; seed sign p=4.0054321e-05. Seed wins/losses/ties=19/1/0. Disagreement rate=0.00056333. Secondary Holm-adjusted paired p=2.800394477205387e-22; sign p=0.0002002716064453125. Relative change vs fixed=-15.921%.

## Measured overhead

- fixed: 0.2688 microseconds/shot, batched validation and test calls combined.
- calibrated: 0.2817 microseconds/shot, batched validation and test calls combined.
- model_informed: 0.2661 microseconds/shot, batched validation and test calls combined.
- Calibration marginal scoring: 0.9215 ms per 20,000-shot calibration batch, excluding calibration sampling and template construction.
- No adaptive switching was implemented; switching overhead and adaptation delay are not applicable.
- Templates and calibration are additional offline work. Decode-only timing must not be presented as the complete calibration-inclusive cost.

## Saved-artifact verification

Recomputed residuals and discordant counts from all 120 saved validation/test bundles; reconciled aggregates and exact paired p-values; verified 223 original artifact hashes and the frozen source/config/method hashes. This audit did not resample or rerun decoding.
