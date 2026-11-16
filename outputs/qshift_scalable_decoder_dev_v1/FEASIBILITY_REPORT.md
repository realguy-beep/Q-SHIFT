# Deterministic feasibility result: REVISE

## V1.6b reproducibility closure

Existing evidence remains unchanged: 900 detector rows replayed with zero disagreements on six arms; 340 calibration comparisons passed. The replay reused frozen decoder code and the calibration reconstruction reused frozen DEM/circuit and likelihood code. Four model/device metadata files were not separately bound by the original run archive manifest; observed hashes and reconstruction corroborate current bytes, not their original historical identity. Full replay remains unverified. See `outputs/qshift_v1_6b_replay_verification_v1/REPLAY_REPORT.md` and `outputs/qshift_v1_6b_calibration_reconstruction_v1/REPORT.md`.

## Scientific assessment

V1.6b compares exact logical-class inference with matching while also using correlated DEM structure and per-root rate calibration; the 61.5% known-burst reduction cannot be assigned to adaptation alone. Exact-vs-five-factor, nominal-vs-informed matching, learned-vs-oracle support, and per-root-vs-static rate ablations each address different contributions, but the existing comparisons do not isolate all effects. The learned support requires 12,000 detector-only and 1,500 labeled device calibration rows per condition, plus 500 detector-only rows per root; static matching's parameter setting was frozen from earlier development. A fair future comparison should provide matched model information and calibration budgets, distinguish privileged true-support arms, and include stronger baselines. Results cover two synthetic d=3 X-bursts and an approximated DEM, not hardware, unseen noise families, independent confirmation or scaling.

BP+OSD and BeliefMatching are relevant candidates but their packages were absent in the current Python interpreter; installation was not attempted. The selected bounded sum-product BP prototype keeps each undecomposed DEM mechanism intact and approximates logical parity. It is not BP+OSD, BeliefMatching, or an independently exact decoder. Its unconstrained logical output factor creates no feedback to detector inference; the final parity product assumes BP's approximate factorized beliefs, so logical degeneracy/correlations can be poorly represented.

## Results

| d | q | Variables / detector edges | Converged / 6 | Inference seconds / 6 fixtures | End RSS MiB |
|---:|---:|---:|---:|---:|---:|
| 3 | 0 | 443 / 1,188 | 1 | 5.019 | 79.4 |
| 3 | 0.01 | 448 / 1,203 | 6 | 3.890 | 79.3 |
| 5 | 0 | 1,677 / 5,004 | 1 | 27.376 | 80.3 |
| 5 | 0.01 | 1,682 / 5,024 | 6 | 21.166 | 79.9 |
| 7 | 0 | 3,695 / 11,412 | 1 | 72.566 | 81.9 |
| 7 | 0.01 | 3,700 / 11,432 | 6 | 65.930 | 82.3 |

At d=3 the q=0 prototype disagreed with the frozen exact decoder on 4/6 fixture predictions; maximum posterior difference 0.5818. At q=0.01, predictions agreed on 6/6, maximum posterior difference 0.004486. Synthetic fixtures do not estimate LER. Six same-circuit/noise-parameter PyMatching models constructed; PyMatching receives a decomposed DEM and BP receives an undecomposed DEM, so representation parity requires careful reporting. These checks do not prove equivalent decoder information or fairness on a study.

All six deterministic unit tests passed (`py -3.12 -m unittest discover -s outputs/qshift_scalable_decoder_dev_v1 -p 'test_*.py' -v`). Fixtures were run with `py -3.12 outputs/qshift_scalable_decoder_dev_v1/run_fixtures.py`; saved results contain process wall times and outputs. Each subprocess completed below 120 seconds, total about 210 seconds wall. The reported memory is current process RSS at completion, not a measured peak or hard tree limit. Construction timing excludes circuit/DEM generation. Each process uses six source-defined syndromes; no random samples or evaluation archives were read.

## Gate and limitations

**REVISE:** q=0 nonconvergence and substantial d=3 exact-reference disagreement prevent a GO despite successful construction and valid output shapes. Computational performance is unsuitable for high-volume evaluation without optimization. No evaluation protocol is activated and no larger study should be launched on this prototype.

The implementation detects impossible syndromes only for disconnected detector checks; it cannot generally certify zero-probability combinations. Its numerical clipping also approximates extreme probabilities. It is experimental and must not silently substitute for the existing baseline. The test for duplicate logical faults confirms a simple degenerate toy model, not general loopy-graph accuracy. The finite 50-iteration cap and synchronous update rule were frozen before fixtures; no tuning was performed.

The originally executed fixture harness continued through all cases and saved incremental JSON. After it finished, the harness was hardened to refuse overwriting existing results and to stop after the first future subprocess failure; it has not been used to regenerate results. Its 120-second subprocess timeout was a direct-child limit, not a verified hard process-tree timeout. No command exceeded ten minutes.

## Next action

Consider a separately versioned deterministic repair focused on stable BP and logical-parity correlations, or evaluate pinned BP+OSD / BeliefMatching after separate dependency approval. Validate against exact d=3 and independent toy enumeration before planning a paired study. A larger stochastic experiment or independent confirmation requires its own frozen protocol and authorization.

## Checklist

☑ V1.6b closure reviewed; no repeat sampling.
☑ Protocol committed before prototype and fixtures.
☑ Prototype and six deterministic tests completed.
☑ Six d/q fixtures and baseline constructions checked.
☑ REVISE recorded; no follow-up sampling or freeze activated.
☑ Evidence and limitations prepared for local commit.