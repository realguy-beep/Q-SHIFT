# V1.2 results

**Frozen decision: GO_DEVELOPMENT_ONLY.** This is development evidence for one synthetic mechanism. It is not confirmation, and it is not hardware evidence.

## Execution

| Item | Value |
|---|---|
| Frozen commit | `b95687ccb451896dcb9963e4e2b261de97572204` (clean tree, branch `codex/qshift-correlated-decoder-v1-2`) |
| Launch | `run_watchdog.py --execute`, single attempt `pilot_runs/attempt_001`, 2026-11-15 |
| Outcome | `completed`; watchdog lifetime 509.7 s (cap 1,800 s); runner 507.1 s; sampled peak RSS 98 MiB |
| Shots | 36,000 detector-only calibration + 288,000 paired evaluation = 324,000 new; 144 committed sampler calls |
| Time split | five-factor arms 496.5 s; matching arms 1.7 s; sampling 0.2 s; archives 1.8 s; models 1.5 s; analysis 0.7 s |
| Calibration gate | passed; mean q̂ 0.000019 / 0.009299 / 0.019160 (MAE 0.000019 / 0.001698 / 0.000840) |
| Frozen models | pooled q̂ (A) 0.0097096; Astar q 0.005; Bstatic q 0.0025 |

## Verification performed after the run

- Persisted status, counts and identities: all 144 calls `committed`, and every archive SHA-256 matches its call record. Calibration archives contain only `detectors`. The manifest's analysis and CSV hashes match the files.
- Independent re-analysis: running `analyze_saved.py --output-dir postrun_reanalysis_v1/` on the completed run gives an `analysis.json` and `paired_results.csv` identical to the runner's.
- From-scratch recount: plain NumPy over the 72 `.npz` files, with no V1.2 imports, reproduces every arm's error totals and the co-primary point estimates.
- Not done: no independent replay of the decoders. Predictions are taken as saved.

## Arm error counts (96,000 evaluation shots per condition)

| Arm | q=0 | q=0.01 | q=0.02 | Nonzero equal-weight LER |
|---|---:|---:|---:|---:|
| A0 matching, q=0 | 656 (0.683%) | 5,061 (5.272%) | 9,034 (9.410%) | 7.341% |
| A matching, pooled q̂ | 951 (0.991%) | 1,306 (1.360%) | 1,616 (1.683%) | 1.522% |
| **Astar** matching, static 0.005 | 835 (0.870%) | 1,186 (1.235%) | 1,543 (1.607%) | **1.421%** |
| A2 matching, per-root q̂ | 656 (0.683%) | 1,289 (1.343%) | 1,597 (1.664%) | 1.503% |
| Bstatic five-factor, static 0.0025 | 777 (0.809%) | 973 (1.014%) | 1,177 (1.226%) | 1.120% |
| **B** five-factor, per-root q̂ | 660 (0.688%) | 1,002 (1.044%) | 1,204 (1.254%) | **1.149%** |
| C five-factor, true q (privileged) | 656 (0.683%) | 1,063 (1.107%) | 1,203 (1.253%) | 1.180% |

## Frozen endpoints

The table shows root-paired differences: equal-weight over q ∈ {0.01, 0.02}, 95% root-stratified bootstrap, 20,000 replicates. Negative favours the first arm.

| Contrast | Estimate | 95% CI | Role |
|---|---:|---|---|
| **B − Astar** | **−0.2724 pp** | [−0.3078, −0.2380] | co-primary ✔ |
| **B − A2** | **−0.3542 pp** | [−0.3995, −0.3115] | co-primary ✔ |
| q=0 B − Astar, 5th / 95th pct | | [−0.2115, −0.1541] pp | safety ✔ (tolerance +0.05 pp) |

GO conditions: both co-primary intervals lie below 0; Astar has 2,729 nonzero errors (at least 100 required); B beats Astar at both nonzero q; the q=0 95th percentile is below +0.0005. All hold.

Relative to Astar, B's nonzero LER is 19.2% lower (1.149% vs 1.421%).

## Secondary contrasts (descriptive)

| Contrast | Nonzero estimate | 95% CI | q=0 estimate |
|---|---:|---|---:|
| Bstatic − Astar (representation alone) | −0.3016 pp | [−0.3318, −0.2714] | −0.060 pp |
| B − Bstatic (value of per-root adaptation) | **+0.0292 pp** | [+0.0036, +0.0547] | −0.122 pp |
| B − A | −0.3729 pp | [−0.4130, −0.3349] | −0.303 pp |
| B − A0 | −6.19 pp | [−6.29, −6.09] | +0.004 pp |
| C − B | +0.0313 pp | [+0.0198, +0.0438] | −0.004 pp |

## Post-hoc robustness check (not a frozen endpoint)

`posthoc_oracle_static_matching.py` picked static matching q **in hindsight on the V1.2 evaluation data itself** (grid step 0.00125). The best value was q = 0.00375, with LER 0.809% / 1.169% / 1.555% across the three conditions. Against this oracle-tuned baseline, B − oracle = **−0.213 pp** nonzero (bootstrap 95% [−0.251, −0.175]) and −0.122 pp at q=0. This baseline is optimistically biased in its own favour, and B still beats it.

## Interpretation

1. **The five-factor representation beats every static or adaptive matching decoder tested,** including the hindsight-tuned one. Under this synthetic noise model, the gain comes from representing the three-detector burst as one factor. It does not come from estimating q: static Bstatic alone captures all of it.
2. **Per-root adaptation does not help at nonzero q.** B is slightly *worse* than Bstatic there (+0.029 pp, interval excludes 0). It helps only at q=0 (−0.12 pp), where its q̂≈0 lets it fall back to plain matching. This repeats the earlier Q-SHIFT finding that adaptive parameter estimation has little decision headroom.
3. **The "privileged" true-q arm is not an optimality reference.** C is worse than B at q=0.01 (+0.064 pp), and Bstatic at q=0.0025 beats both B and C at nonzero q. So the five-factor score (background matching weight plus burst log-odds) is miscalibrated relative to the true prior: it does better with a smaller-than-true burst prior. Why is untested; a likely candidate is weight-scale mismatch between the decomposed background DEM and the burst factors. This is a lead for a new, separately frozen study, not something to tune here.
4. **Fresh-data static selection was imperfect.** Astar (0.005, chosen on V1.1 data) is worse at q=0 than A0/A2 (0.870% vs 0.683%). The hindsight check shows this does not change the conclusion.

## Limits

- One synthetic common-cause X8 X12 X15 mechanism, five independent round events, d=3, five rounds, Z memory, p = 0.003.
- B is given the exact burst support and event signatures; that is a structural advantage no deployed decoder would have without learning them.
- 24 roots per condition from one development study. There is no independent test set, no hardware, no other distance or basis, and no real-time latency claim (B costs about 1.7 ms/shot here, in Python).
- The static selection reused V1.1 arrays that had already been analyzed.
- Raw archives (`pilot_runs/`, 1.4 MB) are local and git-ignored. The lightweight records under `run_records/` are byte copies of the run's JSON/CSV files.
