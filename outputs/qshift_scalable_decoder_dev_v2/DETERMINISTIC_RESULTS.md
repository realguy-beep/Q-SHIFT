# Deterministic comparison and feasibility results — V2

## V1.6b reproducibility closure

Existing committed evidence was inspected, not regenerated:

- `outputs/qshift_v1_6b_replay_verification_v1/REPLAY_REPORT.md` and `result.json`: 900 saved detector rows, 18 condition/root archives, 5,400 predictions across six arms, and zero bitwise disagreements. The replay checked 38 frozen source/configuration entries and 300 archive SHA-256/size records before replay. No evaluation observables were loaded. This was independent orchestration of the frozen decoder, not an independently implemented decoder.
- `outputs/qshift_v1_6b_calibration_reconstruction_v1/REPORT.md`: 340 calibration comparisons passed, including class/score/rate reconstruction from saved calibration detector arrays. That work shared the frozen circuit/DEM/exact-decoder components and was not a separate decoder implementation.
- Frozen pretest manifest: `outputs/qshift_correlated_decoder_v1_6b/PRETEST_FREEZE.json`, SHA-256 `8b054f01569fe07ad14f6200e55af78d60f9ce9b2ecb44b83a45ca24b3e0ce9f`, 38 source/configuration entries.

The calibration report records current-byte hashes for metadata that the original archive manifest did not bind separately:

| Condition | `device_learning.json` SHA-256 | `models_frozen.json` SHA-256 |
|---|---|---|
| known | `848173f0ee9e1701147c18c6ebb8fa973836c7e116c27d6a6232f27985cc0c7c` | `ceeeffcf12cd0af0a7c6658525f8df07a2d696c2a940388e5bc7fdef5eead03c` |
| hidden | `b9e7dd78353f70d82e4f87f17559bc715e69b309f41fe6a39634b7bc9d9683bb` | `a7a7cb732fa640e3b1de15ca7c763054fe9f451cd240de8a2e5217d7b1d58bd0` |

These hashes are prior reported current-file hashes, not new claims of historical identity. The values reconstructed consistently, but those metadata bytes were absent as separate entries in the original archive manifest. Full 576,000-shot prediction replay and an independently implemented decoder replay remain unverified; no additional saved evaluation arrays were opened here.

## V2 tests and exact small-model checks

Command: `py -3.12 -m unittest discover -s outputs/qshift_scalable_decoder_dev_v2 -p 'test_*.py' -v` — **12 passed**.

The tests use only tiny source-authored DEMs and exhaustive assignment enumeration (at most 12 mechanisms). They cover tree detector/logical marginals, a detector hyperedge, duplicate detector signatures and target parity, `^` separator semantics, correlated logical parity (where the approximation is explicitly shown to fail), p=0 removal, p=1 affine offsets, impossible syndromes, logical-only mechanisms, near-boundary finite values, fixed outputs, and invalid configuration/syndrome rejection.

Six safe V1.4 regression tests also passed; stochastic/RNG-generated fixture tests were excluded to preserve V2's no-random-generator protocol. `py_compile` passed for V2 implementation/reference/runner files.

## Six predeclared synthetic circuit fixtures

Each case uses six source-defined syndromes: the all-zero pattern and the first five analytically described burst-event supports. No detector sampler or random generator was called. d=3 was checked against the existing exact logical-class DEM decoder; d=5/7 were construction/convergence checks only.

| d | q | BP converged | Max final message residual | BP inference (s) | Construction (s) | Exact d=3 hard disagreements | Max `|P_BP(L=1)-P_exact(L=1)|` | End RSS (MiB, not peak) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 0 | 1/6 | 1.143e-4 | 0.712 | 0.0052 | 4/6 | 0.5818 | 80.5 |
| 3 | 0.01 | 6/6 | 9.890e-9 | 0.470 | 0.0053 | 0/6 | 0.00449 | 80.1 |
| 5 | 0 | 1/6 | 1.451e-3 | 2.662 | 0.0211 | n/a | n/a | 80.6 |
| 5 | 0.01 | 6/6 | 9.423e-9 | 2.136 | 0.0202 | n/a | n/a | 80.8 |
| 7 | 0 | 1/6 | 1.516e-2 | 7.298 | 0.0467 | n/a | n/a | 83.2 |
| 7 | 0.01 | 6/6 | 8.415e-9 | 6.546 | 0.0472 | n/a | n/a | 83.4 |

At d=3, the q=0 case produces four hard-decision disagreements and a maximum exact logical-probability error of 0.5818. At q=0.01, all six hard decisions agree, but the probability approximation still differs by up to 0.00449. Agreement on six fixed syndromes is not accuracy evidence. At d=5/7 there is no exact reference result in this work.

The optimized prefix/suffix parity product is algebraically the same update as V1's nested per-edge product but reduces work from quadratic to linear in each check degree. On the same fixed fixture batch, the observed V1-to-V2 inference times were about 7–10× lower across these single runs. This is an implementation timing observation, not a repeated benchmark or scientific-performance claim. Full six-case parent runtime was 33.39 s; summed BP inference was 19.82 s. RSS is the process working set sampled at exit, not a peak measurement or hard memory limit.

A separate repeatability check compared 102 model/convergence/prediction fields between post-fix and final-source fixture runs; **0 mismatches**. Timing and RSS were excluded as observational.

## Failure categories

- **Implementation defects repaired:** p=1 finite-prior approximation and missing impossible-syndrome detection; V2 empty-detector fast path dropping random logical-only parity.
- **Correct implementation, approximate inference:** detector updates agree with exact enumeration on trees; loopy factor graphs remain approximate even when the residual converges.
- **Fundamental/current-method limits:** product-of-marginals logical parity can badly miss joint logical-class probability; q=0 often does not reach the frozen residual tolerance by 50 updates; d=5/7 exact accuracy was not measured.
- **Unresolved cause:** current traces do not uniquely attribute q-dependent convergence to graph topology, probability weights, or their interaction.

No LER was calculated. No performance advantage is established.
