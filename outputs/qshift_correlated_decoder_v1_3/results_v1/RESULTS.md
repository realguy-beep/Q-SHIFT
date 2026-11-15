# V1.3 results

**Frozen decision: GO_DEVELOPMENT_ONLY.** This is development evidence for one synthetic mechanism with oracle burst support. It is not confirmation, and it is not hardware evidence.

## Execution

| Item | Value |
|---|---|
| Frozen commit | `bd43689e169726c4be70115b4e761a13887e28d9` (clean tree, branch `codex/qshift-correlated-decoder-v1-3`) |
| Launch | `run_watchdog.py --execute`, single attempt `pilot_runs/attempt_001`, 2026-11-15 |
| Outcome | `completed`; watchdog lifetime 906.1 s (cap 3,000 s; preflight projection 966 s); runner 898.3 s; sampled peak RSS 94 MiB |
| Shots | 36,000 detector-only calibration + 288,000 paired evaluation = 324,000 new; 144 committed sampler calls |
| Time split | five-factor arms 888.4 s; matching arms 1.0 s; sampling 0.2 s; archives 2.0 s; models 1.1 s; analysis 0.6 s |
| Calibration gate | passed; mean q̂ 0.000006 / 0.010133 / 0.018573 |
| Frozen models | Astar ON q=0.00375; AstarAlt OFF q=0; A2sw τ=0.0005 (OFF on all 24 q=0 roots, ON on all 48 nonzero roots); BoffStatic q=0.01125 |

## Verification performed after the run

- Every one of the 144 calls is `committed`, and every archive SHA-256 matches its call record. Calibration archives hold only `detectors`. The manifest's analysis and CSV hashes match the files.
- Re-analysis with `analyze_saved.py --output-dir postrun_reanalysis_v1/` gives an `analysis.json` and `paired_results.csv` identical to the runner's.
- The frozen `recount_from_scratch.py` (NumPy only, no package imports, frozen before the run) matches `analysis.json` on every arm total and both co-primary estimates. Its output is in `recount_output.txt`.
- Not done: no independent replay of the decoders. Predictions are taken as saved.

## Arm error counts (96,000 evaluation shots per condition)

| Arm | q=0 | q=0.01 | q=0.02 | Nonzero equal-weight LER |
|---|---:|---:|---:|---:|
| **Astar**: matching ON, q=0.00375 | 786 (0.819%) | 1,146 (1.194%) | 1,527 (1.591%) | **1.392%** |
| AstarAlt: matching OFF, q=0 | 481 (0.501%) | 4,782 (4.981%) | 8,947 (9.320%) | 7.151% |
| **A2sw**: mode-switching matching | 481 (0.501%) | 1,338 (1.394%) | 1,639 (1.707%) | **1.551%** |
| B: frozen V1.2 B (residual ON) | 674 (0.702%) | 1,063 (1.107%) | 1,228 (1.279%) | 1.193% |
| Bstatic: frozen V1.2 (residual ON, 0.0025) | 788 (0.821%) | 992 (1.033%) | 1,189 (1.239%) | 1.136% |
| **Boff**: cost-consistent, per-root q̂ | **481 (0.501%)** | **635 (0.661%)** | **775 (0.807%)** | **0.734%** |
| BoffStatic: cost-consistent, q=0.01125 | 574 (0.598%) | 620 (0.646%) | 772 (0.804%) | 0.725% |
| Coff: cost-consistent, true q | 481 (0.501%) | 639 (0.666%) | 775 (0.807%) | 0.737% |

## Frozen endpoints

The table shows root-paired differences: equal-weight over q ∈ {0.01, 0.02}, 95% root-stratified bootstrap, 20,000 replicates. Negative favours Boff.

| Contrast | Estimate | 95% CI | Role |
|---|---:|---|---|
| **Boff − Astar** | **−0.658 pp** | [−0.703, −0.613] | co-primary ✔ |
| **Boff − A2sw** | **−0.816 pp** | [−0.869, −0.765] | co-primary ✔ |
| q=0 Boff − A2sw, 5th / 95th pct | | [0.000, 0.000] pp | safety ✔ (tolerance +0.05 pp) |

GO conditions: both co-primary intervals lie below 0; Astar has 2,673 nonzero errors (at least 100 required); Boff beats Astar at both nonzero q; the q=0 95th percentile is below +0.0005. All hold.

Relative nonzero LER reductions for Boff: 47.2% vs Astar, 52.6% vs A2sw, and 38.5% vs frozen V1.2 B.

**About the q=0 safety result:** it is an exact tie by construction, not an estimate. On every q=0 root Boff's q̂ rounds to the q=0 path (uncorrelated base matching), which is exactly A2sw's OFF branch. The predictions are identical (481 = 481), so the safety bound is trivially met. It shows no harm at q=0; it does not show a q=0 gain.

## Secondary contrasts (descriptive)

| Contrast | Nonzero estimate | 95% CI | q=0 estimate |
|---|---:|---|---:|
| Boff − B (value of the cost repair) | −0.459 pp | [−0.499, −0.420] | −0.201 pp |
| Boff − BoffStatic (value of adaptation) | +0.009 pp | [+0.002, +0.017] | −0.097 pp |
| Coff − Boff (is the true prior optimal?) | +0.002 pp | [−0.003, +0.007] | 0.000 pp |
| A2sw − Astar | +0.158 pp | [+0.125, +0.191] | −0.318 pp |
| Boff − AstarAlt | −6.42 pp | [−6.54, −6.29] | 0.000 pp |
| B − Astar (V1.2 replication on fresh data) | −0.199 pp | [−0.238, −0.158] | −0.117 pp |

## Interpretation

1. **The cost repair is the main effect.** Making the five-factor decoder's residual matching consistent with its cost model cut nonzero LER by 38.5% relative to frozen V1.2 B. The gap to the strongest matching baselines roughly doubled, from V1.2's 0.27 pp to 0.66 pp against the best static matcher.
2. **H1 is confirmed on fresh data.** With consistent costs, the true-q arm Coff is statistically indistinguishable from Boff (+0.002 pp, CI spans 0), and the selected static prior (0.01125) lies between the true nonzero values. V1.2's "smaller-than-true prior wins" anomaly came from the cost mismatch, not from the prior.
3. **Adaptation still adds almost nothing at nonzero q.** BoffStatic is marginally better than per-root Boff there (+0.009 pp, CI excludes 0 but is tiny). Adaptation helps at q=0 (−0.097 pp), where q̂≈0 sends Boff to plain uncorrelated matching. The useful role of q̂ is as a "burst present or absent" switch, not as a fine-grained rate.
4. **Mode-switching matching is a trade-off, not a stronger matcher.** A2sw wins at q=0 (−0.32 pp vs Astar) but loses at nonzero q (+0.16 pp), because per-root correlated matching at q̂ is worse there than the fixed static q. The frozen rule chose the static matcher as the harder nonzero comparator and the switching matcher as the harder q=0 comparator, and Boff beats both.
5. **The V1.2 result replicates on fresh data:** B − Astar = −0.20 pp (V1.2: −0.27 pp against its own Astar).

## Limits

- One synthetic common-cause X8 X12 X15 mechanism, five independent round events, d=3, five rounds, Z memory, p = 0.003.
- **The five-factor arms are given the exact burst support, and all five events are logically trivial.** This is the largest caveat. A deployed decoder would have to learn the support and, harder, the logical effect, which detector data cannot reveal. This is the V1.4 question.
- 24 roots per condition from one development study. There is no independent test set, no hardware, no other distance or basis, and no latency claim. The five-factor arms cost about 3.1 ms/shot for both families together, in Python.
- The selection set (V1.2 evaluation arrays) had already been analyzed. The planning diagnostics used V1.1 arrays that had been analyzed three times.
- Raw archives (`pilot_runs/`) are local and git-ignored. `run_records/` holds byte copies of the run's JSON/CSV files.
