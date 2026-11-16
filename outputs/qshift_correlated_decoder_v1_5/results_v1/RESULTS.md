# V1.5 results

**Frozen decision: GO_DEVELOPMENT_ONLY. Target endpoint: TARGET_MET.** This is development evidence on fresh seeds for one synthetic d=3 mechanism with oracle burst support. It is not confirmation, and it is not hardware evidence.

## Execution

| Item | Value |
|---|---|
| Frozen commit | `f6f5a4b4e587896fdcb65727bd763d4a61b0b061` (clean tree, branch `codex/qshift-correlated-decoder-v1-5`) |
| Launch | `run_watchdog.py --execute`, single attempt `pilot_runs/attempt_001`, 2026-11-16 |
| Outcome | `completed`; runner 1,947 s (cap 9,000 s; preflight projection 2,380 s); sampled peak RSS 94 MiB |
| Shots | 36,000 detector-only calibration + 288,000 paired evaluation = 324,000 new; 144 committed sampler calls |
| Time split | exact arm 1,631.5 s (about 5.7 ms/shot); five-factor arms 305.5 s; matching 0.6 s; sampling 0.2 s; archives 3.2 s |
| Calibration gate | passed; mean q̂ 0.000032 / 0.010133 / 0.018668 |
| Frozen settings | read unchanged from V1.3: Astar correlated q=0.00375; A2sw τ=0.0005 (23 roots OFF, 49 ON); BoffStatic q=0.01125. Bexact elimination width 11. |

## Verification after the run

- Every one of the 144 calls is `committed`, and every archive SHA-256 matches its call record. Calibration archives hold only `detectors`. The manifest's analysis and CSV hashes match the files.
- Re-analysis with `analyze_saved.py --output-dir postrun_reanalysis_v1/` gives an `analysis.json` and `paired_results.csv` identical to the runner's.
- The frozen `recount_from_scratch.py` (NumPy only, no package imports) matches `analysis.json` on every arm total and both co-primary estimates. Its output is in `recount_output.txt`.
- Not done: no independent replay of the decoders. Predictions are taken as saved.

## Arm error counts (96,000 evaluation shots per condition)

| Arm | q=0 | q=0.01 | q=0.02 | Nonzero equal-weight LER |
|---|---:|---:|---:|---:|
| Astar | 795 (0.828%) | 1,216 (1.267%) | 1,472 (1.533%) | 1.400% |
| A2sw | 479 (0.499%) | 1,387 (1.445%) | 1,607 (1.674%) | 1.559% |
| Boff | 466 (0.485%) | 704 (0.733%) | 735 (0.766%) | 0.750% |
| **BoffStatic** (reference) | 556 (0.579%) | 685 (0.714%) | 733 (0.764%) | **0.739%** |
| **Bexact** (candidate) | **374 (0.390%)** | **514 (0.535%)** | **527 (0.549%)** | **0.542%** |

## Frozen endpoints

Root-paired differences: equal-weight over q ∈ {0.01, 0.02}, 95% root-stratified bootstrap, 20,000 replicates. Negative favours Bexact.

| Contrast | Estimate | 95% CI | Role |
|---|---:|---|---|
| **Bexact − BoffStatic** | **−0.196 pp** | [−0.223, −0.172] | co-primary ✔ |
| **Bexact − Astar** | **−0.858 pp** | [−0.895, −0.820] | co-primary ✔ |
| q=0 Bexact − BoffStatic, 5th / 95th pct | | [−0.215, −0.164] pp | safety ✔ (tolerance +0.05 pp) |
| **Relative reduction vs BoffStatic** | **26.6%** | [23.7%, 29.7%] | target: lower bound ≥ 10% ✔ **TARGET_MET** |

GO conditions: both co-primary CIs lie below 0; BoffStatic has 1,418 nonzero errors (at least 100 required); Bexact beats BoffStatic at both nonzero q; the q=0 95th percentile is below +0.0005. All hold.

## Secondary (descriptive)

| Contrast / reduction | Estimate | 95% CI |
|---|---:|---|
| Bexact − Boff | −0.207 pp | [−0.235, −0.181] |
| Bexact − A2sw | −1.017 pp | [−1.062, −0.973] |
| BoffStatic − Astar (V1.3 replication) | −0.662 pp | [−0.700, −0.623] |
| Relative reduction, Bexact vs Astar | **61.3%** | [59.4%, 63.2%] |
| Relative reduction, Bexact vs A2sw | 65.2% | [63.3%, 67.2%] |
| Relative reduction, BoffStatic vs Astar | 47.3% | [45.0%, 49.4%] |

## Interpretation

1. **The V1.4B development finding replicates on fresh data.** The screens gave −23.7% (S1) and −24.3% (S2) vs BoffStatic; V1.5 gives −26.6%. Exact logical-class inference removes about a quarter of the best V1.3 decoder's remaining errors.
2. **Against the strongest static matcher, the reduction rises from 47% (V1.3) to 61%.** That is close to the ceiling estimated earlier for this regime: about 64% from the q=0 floor, and 68% at the V1.4 gate's d=3, p=0.003 cell.
3. **The gain is not burst-specific.** Bexact is better at q=0 as well: 0.390% vs 0.579% for BoffStatic and 0.485% for Boff. That matches V1.4B's diagnosis that about 80% of the recoverable gap is background inference (degeneracy and hyperedge splitting).
4. **V1.3's own result replicates:** BoffStatic − Astar = 47.3% here vs 47.9% in V1.3.

## Limits

- d=3 only. The exact elimination has width 11 here, but 28 at d=5 and 53 at d=7, so it is not scalable in this form.
- Exact only for the DEM: two-qubit channels are approximated as independent mechanisms (`approximate_disjoint_errors=True`).
- Oracle burst support: the exact burst mechanisms are in the decoder's DEM, and all five bursts are logically trivial.
- One synthetic mechanism and 24 roots per condition. There is no hardware and no latency claim (about 5.7 ms/shot in NumPy).
- Raw archives stay local in `pilot_runs/`, which is git-ignored. The JSON files in `run_records/` are byte copies. The committed `paired_results.csv` is stored with LF line endings by the package's `eol=lf` rule; the original has CRLF, SHA-256 `d1926f37664dd5b97989fba7bfde6d021d19f60d8dcff5719f05d8cfb03dad9b`, as recorded in `run_manifest.json`.
- The post-run privileged reference (`posthoc_reference.json`) is descriptive and not an endpoint; it is reported below.

## Post-run privileged reference (descriptive)

`posthoc_reference.py` decoded every saved evaluation archive with the exact DEM decoder at the **true** q. That makes it privileged and not deployable.

| | q=0 | q=0.01 | q=0.02 | Nonzero LER |
|---|---:|---:|---:|---:|
| R_true (true q) | 372 | 514 | 524 | 0.5406% |
| Bexact (detector-only q̂) | 374 | 514 | 527 | 0.5422% |
| Disagreements | 2 | 10 | 7 | 19 / 288,000 shots |

The deployable decoder is within 0.0016 pp of the DEM-exact ceiling. At d=3 under this DEM, **no further reduction is available from better inference or better q estimation**. Further gains would need a more faithful noise model in the decoder (exact categorical channels), larger codes with a scalable approximation, or a different noise regime.
