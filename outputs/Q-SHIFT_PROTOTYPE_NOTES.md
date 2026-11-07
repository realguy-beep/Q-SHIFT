# Q-SHIFT prototype update

## Current prototype

For this exact Stim repetition-memory circuit, the decoder input is eight detector bits, so the input space has only 256 possible patterns. `qshift_prototype.py` therefore uses a smoothed lookup table of `P(L0 flip | detector pattern)` instead of an unnecessarily large random forest. It selects a correction threshold on independent validation shots and reports residual logical-observable errors on the same held-out test shots used by PyMatching.

`qshift_mixed_regime_test.py` tests a more useful configuration: one lookup table and one threshold trained across the three simulated noise settings. The simulator's noise setting is not supplied as a feature. Its current defaults are 2,000,000 training shots and 300,000 validation shots per setting (6,000,000 and 900,000 total), followed by 2,000,000 shared test shots per setting.

## Results from two distinct experiments

The first per-regime table run is in `qshift_prototype_results.json`. Its test counts were:

| Noise setting | Pattern decoder | PyMatching |
|---:|---:|---:|
| 0.001 | 13 / 1,000,000 | 11 / 1,000,000 |
| 0.003 | 87 / 1,000,000 | 96 / 1,000,000 |
| 0.006 | 292 / 1,000,000 | 373 / 1,000,000 |

The mixed-regime run is in `qshift_mixed_regime_results.json`:

| Noise setting | One mixed-regime pattern table | PyMatching |
|---:|---:|---:|
| 0.001 | 15 / 2,000,000 | 21 / 2,000,000 |
| 0.003 | 161 / 2,000,000 | 178 / 2,000,000 |
| 0.006 | 598 / 2,000,000 | 710 / 2,000,000 |

The paired test indicates that the mixed model had fewer residual errors in this run at all three settings. The improvement is small at the lower settings and larger at 0.006. These are single seeded batches, so treat them as promising evidence, not a general performance claim. The lookup model is not a universal replacement for matching: it has only been tested on this circuit, this depolarizing channel, and regimes represented during training. The held-out test is fresh, but the settings themselves are familiar.

## Reproduce or add a seed

Install `stim`, `pymatching`, and `numpy` in the chosen Python environment, then run:

```powershell
python qshift_mixed_regime_test.py --seed 20261108 --output qshift_mixed_regime_seed_20261108.json
```

For a quick smoke-sized run, pass smaller positive values to `--train-each`, `--validation-each`, and `--test-each`. Do not use such small runs to make performance claims. All split batches use derived, recorded seeds, and test shots are shared between the learned decoder and PyMatching.

## Next scientific checks

1. Repeat several independent seeds and aggregate paired error differences with uncertainty before claiming an improvement.
2. Test an unseen intermediate noise setting (for example 0.0045) using the mixed-regime model without exposing the noise value.
3. Include a wider set of circuit distances, rounds, and noise mechanisms. The eight-bit lookup will not scale to large detector spaces.
4. Compare latency and memory against PyMatching and keep simulator-only observable labels out of runtime inputs.
5. Only after simulation validation, define hardware telemetry and a fixed-vs-adaptive policy. No hardware connection or adaptive advantage is claimed here.
