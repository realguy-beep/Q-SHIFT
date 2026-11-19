# Empirical CUSUM threshold calibration: fast detection, mixed false-alarm evidence

## Question and frozen method

The fixed histogram likelihood CUSUM detected changes quickly but produced too many false switches. This follow-up kept its 32-bin probabilities fixed and calibrated one global threshold using new stable score streams only. It chose the smallest h >= log(200) meeting the predeclared nominal/shifted false-switch limits across X/Z profiles. It then evaluated on fresh stable and 101-segment alternating streams. The second stream repeated the calibration procedure with new calibration data and also scored the first threshold as a frozen secondary comparator.

No logical outcomes entered the sequential updates. The profile score uses detector-only features. These are simulator calibration-shot studies, not logical LER or hardware evidence.

## Initial calibration and validation

The first calibration selected h=8.5946. On independent validation, false-switch rates per 100k were 1.11 and 0.89 for nominal X/Z profiles, and 2.22 and 24.44 for doubled-measurement X/Z profiles. All transitions were detected; median delay was 46.5 shots nominal and 47 under measurement shift. The fixed advancement gate passed.

## Fresh calibration replication

Fresh calibration selected h=8.3273. On its independent validation, false-switch rates were 2.22/0.89 per 100k nominal and 2.89/28.89 shifted. Transition detection was 100%, with median delay 44/41 shots. The recalibrated procedure missed the strict shifted-Z false-switch limit of 25, so the independent procedure-level gate failed.

On this same fresh validation stream, the original h=8.5946 produced 2.22/0.67 nominal and 2.00/23.78 shifted false switches per 100k, with median delays 45.5/42.5 shots. That frozen threshold met the operating limits twice, but this secondary comparison does not convert the predeclared recalibration replication into a pass.

## Decision

Keep empirical threshold calibration as an unresolved, narrow simulator lead: both the original and fresh recalibrated thresholds detected changes quickly, and the original threshold met limits on two validation streams. But the threshold-selection procedure did not pass its independent replication gate; the fresh shifted-Z rate was slightly too high, and selected h varied from 8.595 to 8.327. Do not claim robust false-alarm control across recalibrations, and do not tune again on these streams.

The two streams used 8.404M unique detector-score samples total (4.202M each). An initial guard error replayed the first calibration seeds; those samples are counted once. No confirmatory/sealed data were accessed.
