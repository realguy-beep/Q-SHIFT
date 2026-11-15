# V1.1 deterministic preflight results

**No V1.1 sampler call or new shot was made during this preflight.**

## V1 preservation and reuse verification

- V1 completed commit: `0da212941ce4cce43cc4d27821e3a59c0acb6cd2`.
- V1 attempt source commit: `bfd971d06d0deadaac965086c3a6cbdca58eeb4b`.
- Original attempt remains `inconclusive_calibration_gate`; 33 calls and 18,000 shots are committed (3,000 training, 15,000 calibration, 0 evaluation).
- All 33 training/calibration archives passed SHA-256 and byte-count checks against the V1 status and failed-attempt evidence manifest. Combined archive bytes: 45,494.
- V1 evaluation directory is empty; no evaluation calls, archives, or outcomes exist.
- Seed keys mapped to the historical V1 inventory, with 33 unique training/calibration seeds. The V1.1 verifier reads archive bytes and ZIP member names only; it did not decompress either array.
- V1.1 subsequently loaded only `detectors` from the 33 archives. It did not read or copy the stored `observables` arrays.

## Repaired estimator and calibration gate

The corrected implementation stores NumPy `polyfit` output in the order `(slope, intercept)`. The fixed deterministic affine test proves the coefficient order; it would fail under V1's reversed assignment.

Using only the preserved V1 training detectors, the fitted feature-rate relation was:

- Training feature means at q=0, 0.01, 0.02: 0.0000, 0.0108, 0.0176.
- Corrected slope: 0.8800000000000001.
- Corrected intercept: 0.000666666666666673.

Using only the preserved calibration detector rows:

| q | mean q-hat | bias | root MAE | strict-order role |
|---:|---:|---:|---:|---|
| 0.00 | 0.0000152 | +0.0000152 | 0.0000152 | first |
| 0.01 | 0.0103788 | +0.0003788 | 0.0017727 | middle |
| 0.02 | 0.0190455 | −0.0009545 | 0.0009545 | last |

Strict condition-mean ordering `qhat(0) < qhat(0.01) < qhat(0.02)` passed. This passes the frozen feasibility gate; the small reused calibration sample and clipped estimates still leave material estimation uncertainty.

## Circuit, decoder, and synthetic fixture checks

- All three candidate circuits and decomposed DEMs construct with 40 detectors and one observable.
- Five distinct three-detector common-cause signatures were recovered from a deterministic DEM; each has zero logical-observable parity.
- All 92 planned decoder/reference objects constructed (global A, background matching, and 30 root-specific instances each for A2/B/C).
- The B/C shared-background optimization passed bit-for-bit comparisons against separately called B and C on deterministic fixtures, including q=0.
- On 632 algebraically constructed fault-combination patterns (32 burst-subset patterns and 600 background-fault-plus-single-burst patterns), predictions differed between B and A in 77/90/92 cases across q=0/0.01/0.02; B differed from A2 in 0/77/92. These are deterministic decision-sensitivity checks only and are not sampled data, accuracy evidence, or estimates of logical error rate.
- No logical labels were used in the preflight or fixture comparisons.

## Runtime and resource observations

Environment: Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3, psutil 7.2.2.

- 632 deterministic fixture rows, all candidate constructions: approximately 0.45 seconds construction.
- Worst observed per-row decoder timing: A 6.7 µs; A2 4.8 µs; paired B/C shared residual evaluations 1.25 ms.
- Projection for 60,000 rows used the maximum observed fixture cost per row, a 2× decoder inflation, a 4× Stim sampling inflation based on V1 calibration-call metadata, and a 45-second analysis allowance: approximately 197 seconds versus the unchanged 600-second wall cap.
- Projection is uncertain because algebraic detector fixtures are not representative of sampled syndromes. It is a feasibility screen, not a runtime guarantee.
- Observed preflight process peak working set: 91,844,608 bytes. A 2× working-set projection is 183,689,216 bytes, below the 2-GiB sampled process RSS ceiling and current available memory of 1,635,430,400 bytes. Free disk: 259,762,999,296 bytes, above the 1-GiB minimum.
- The RSS ceiling is sampled process memory, not hard OS-level process-tree enforcement.

During pre-freeze implementation, a temporary preflight check treated 2 GiB of available system memory as a requirement, although the frozen V1 limit is a sampled process RSS ceiling. That check stopped without sampling and was removed before freezing. The final preflight records available memory and checks a 2× margin on the measured process working set against current availability; it does not alter the 2-GiB process RSS limit.

## Deterministic validation

Command:

```powershell
py -3.12 -m compileall -q outputs/qshift_correlated_decoder_feasibility_v1_1
py -3.12 -m unittest discover -s outputs/qshift_correlated_decoder_feasibility_v1_1/tests -v
```

Result: compileall passed; 9 tests passed. Tests cover estimator coefficient order, estimation/clipping/order, invalid inputs, geometry/DEM/decoder shape, paired B/C equivalence, saved-array analysis, and default sampler-free runner routing.

## Gate result

The corrected calibration gate passed. The deterministic runtime projection, memory and disk preflight passed the existing bounds. No sampling occurred. The evaluation is not yet eligible to execute until the frozen source/protocol/seed package is committed, the checkout is clean at its exact commit SHA, the V1 reuse check passes again, and the final dry-run succeeds under the watchdog. Any prelaunch mismatch requires stopping; no source or design changes are authorized after the freeze.
