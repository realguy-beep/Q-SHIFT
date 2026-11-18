# Sequential calibration reuse horizon replay

## Question

Can the SPRT's roughly 25-shot calibration cost be amortized enough to beat static memory-basis throughput when the inferred X/Z profile remains stable for more than one 100-attempt logical block?

## Frozen replay

Recreate the exact same calibration streams (seeds 2026115401/5402) and logical failure blocks (seeds 2026115611–5614) from the direct end-to-end screen. Add no new random streams. Compare reuse horizons of 1, 10, and 100 consecutive 100-attempt blocks per calibration decision (100, 1,000, and 10,000 logical attempts/dwell), selected because prior fixed-calibration work tested these orders of dwell. At each horizon, use the first calibration decision in each group and hold its selected basis for the entire group. Compare SPRT, fixed LDA and Gaussian-LLR decisions at 25/100/500 calibration shots, static X/Z, and the profile oracle. Charge each policy its actual calibration shots per decision and report LER, correct outputs per total circuit shot, and a bootstrap over independent profile-job groups.

This is a deterministic reanalysis/replay of already counted sample streams. It assumes the two synthetic profiles remain fixed for the selected dwell and does not measure change-point detection, hardware drift, or arbitrary-state logical performance.
