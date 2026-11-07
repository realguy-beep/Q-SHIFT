# Q-SHIFT CNN Stage 1 — Preflight Results

## Outcome

**PASS for architecture and paired-decoder plumbing only. No training was run.** The check used a fresh 256-shot Stim sample under the Phase 3A synthetic spatial-burst condition and a separate 16-shot noiseless structure check. Independent-test samples were not generated or opened.

## Exact commands

From the repository root:

```powershell
python -m unittest discover -s outputs/cnn_architecture_stage1_v1/tests -v
python outputs/cnn_architecture_stage1_v1/run_preflight.py
```

Observed results: **6/6 unit tests passed**; preflight status `PASS_DIAGNOSTIC_ONLY_NO_TRAINING`. The runner returned exit code 0. It checked the actual distance-3, five-round rotated Z-memory detector geometry, 40 detectors, one observable, matching model construction, paired prediction shapes, residual-CNN forward outputs, and source/seed metadata. Candidate gradient checks use a small deterministic four-example fixture and do not train a model.

## Measured plumbing counts

- Correlated condition: gate p=0.003, measurement p=0.003, synthetic joint X burst on data qubits 8 and 10 with p=0.01 at each of five round boundaries.
- Paired diagnostic sample: **256 shots** from that correlated circuit, used unchanged by frozen no-burst PyMatching and burst-informed PyMatching.
- Frozen PyMatching: 1/256 logical failures on this diagnostic sample.
- Burst-informed PyMatching: 1/256; **0/256 prediction disagreements** with frozen PyMatching on this small sample.
- Noiseless check: 16 shots, zero nonzero detector bits and zero observable flips.
- Candidate models returned finite logits with shape `(256,)` on actual Stim detector rows. Both are marked untrained and not scored as decoders.
- Actual detector coordinate map: 40 unique IDs/coordinates on the sparse `(6,4,4)` grid with 40 occupied cells.
- Seed screen: 4 new diagnostic/model seeds, all unique and disjoint from 2,076 archived recoverable values and 9 explicitly recorded Phase 3A seeds; no collision.
- Parameter counts and CPU/CUDA batch-256 microbenchmarks are in `PREFLIGHT_RESULTS.json`: existing residual CNN 13,429 parameters / 18.733 µs per shot CPU / 3.651 µs CUDA; V2 13,041 / 18.375 µs CPU / 3.827 µs CUDA; factorized 12,653 / 16.055 µs CPU / 3.923 µs CUDA. The saved timing is the median across five short trial groups; it is one local microbenchmark observation, not a general throughput claim. CUDA peak allocated memory was about 10.2 MB per measurement, including model and batch tensors.

The 1/256 counts are plumbing diagnostics only. No uncertainty estimate, comparison claim, or performance conclusion should be drawn from them. Phase 3A's prior isolated-burst correlation check remains a synthetic mechanism validation; this run does not reproduce or extend it as a performance result.

## Tests and limitations

The six tests validate the actual Stim coordinate mapping, the two model output/gradient paths, finite values, reproducible initialization, PyMatching-conditioned residual labels and XOR correction semantics, and parameter budget bounds. The implementation is not integrated with the dashboard, is not trained, and has not been evaluated on any final-development or independent test partition. The microbenchmark measures inference only; it does not measure simulator throughput, training cost, or total application memory use.

## Reproducibility and evidence

Run `python outputs/cnn_architecture_stage1_v1/run_preflight.py` to regenerate the diagnostic from the frozen configuration and recorded seeds. The script saves hashes of its source/configuration inputs and hashes of the paired detector, observable, and prediction arrays in `PREFLIGHT_RESULTS.json`. `MANIFEST.json` covers the stage's lightweight code, reports, and metadata. The original Phase 2B, Phase 3A, and neural experiment evidence remains unchanged.
