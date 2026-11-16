# V1.6b results

**Frozen decision: GO_DEVELOPMENT_ONLY. Target endpoint: TARGET_MET.** This is development evidence on fresh seeds for two synthetic d=3 bursts, with the burst support **learned** from device calibration data. It is not confirmation, and it is not hardware evidence.

## Execution

| Item | Value |
|---|---|
| Frozen commit | `02b7aa276d8b3c4ba68824e7b4d839caac4178c8` (clean tree, branch `codex/qshift-correlated-decoder-v1-6`) |
| Launch | `run_watchdog.py --execute`, single attempt `pilot_runs/attempt_001`, 2026-11-16 |
| Outcome | `completed`; watchdog lifetime 8,715 s (cap 18,000 s); runner 8,711 s; peak RSS 141 MiB |
| Shots | 675,000 new shots in 300 committed calls: 2 conditions × (12,000 device detector-only + 1,500 device labeled + 72 × 500 calibration + 72 × 4,000 evaluation) |
| Time split | exact arms 7,886.5 s (about 6.8 ms/shot); five-factor 755.2 s; device learning 37.7 s; matching 1.9 s |
| **Runtime deviation** | The preflight projected 4,990 s, using 3.8 ms/shot for the exact decoder timed on 2,000 rows. The run measured about 6.8 ms/shot over 1,152,000 exact decodes, so the real run took **1.75× the projection**. It stayed within the cap, and the projection method should be revisited for future caps. |
| Hidden burst | Opened inside the run after the freeze and verified against commitment `caa9fd07…`. Support **X3 X5 X8** (signature class 9, logically trivial). |

## Verification after the run

- All 300 calls are `committed`, and every archive SHA-256 matches its call record. Device detector-only and per-root calibration archives hold only `detectors`. The manifest's analysis and CSV hashes match.
- Re-analysis with `analyze_saved.py --output-dir postrun_reanalysis_v1/` gives an `analysis.json` and `paired_results.csv` identical to the runner's.
- The frozen `recount_from_scratch.py` (NumPy only) matches `analysis.json` on every arm total and key contrast in both conditions. Its output is in `recount_output.txt`.
- The CSV is now written with LF line terminators, so `run_records/` holds byte copies.

## Learning outcome

| Condition | True support (class, flip) | Learned class | Learned flip | Device q̂ | Δ (threshold 11.58) | Flip log-LR (1 − 0) |
|---|---|---|---|---:|---:|---:|
| known | X8 X12 X15 (4, 0) | **4 ✔** | **0 ✔** | 0.0100 | 542.0 | −605.0 |
| hidden | X3 X5 X8 (9, 0) | **9 ✔** | **0 ✔** | 0.0097 | 520.1 | −656.6 |

Both bursts were learned exactly. The learned DEM therefore equals the true-support DEM, and the per-root q̂ is computed identically. As a result **Blearn's predictions equal Bexact_oracle's on every one of the 576,000 evaluation shots, and Astar_learned's equal Astar_oracle's.**

## Arm error counts (96,000 shots per condition × q)

**Known burst:**

| Arm | q=0 | q=0.01 | q=0.02 | Nonzero LER |
|---|---:|---:|---:|---:|
| A_nominal | 456 | 4,785 | 8,899 | 7.127% |
| Astar_oracle = Astar_learned | 802 | 1,174 | 1,514 | 1.400% |
| BoffStatic_oracle | 564 | 637 | 726 | 0.710% |
| Bexact_oracle = **Blearn** | **344** | **487** | **547** | **0.539%** |

**Hidden burst:**

| Arm | q=0 | q=0.01 | q=0.02 | Nonzero LER |
|---|---:|---:|---:|---:|
| A_nominal | 458 | 4,674 | 8,466 | 6.844% |
| Astar_oracle = Astar_learned | 659 | 777 | 848 | 0.846% |
| BoffStatic_oracle | 488 | 520 | 556 | 0.560% |
| Bexact_oracle = **Blearn** | **342** | **381** | **393** | **0.403%** |

## Frozen endpoints

These are root-paired, equal-weight nonzero estimates with 95% root-stratified bootstrap CIs (20,000 replicates). Negative favours Blearn.

| Endpoint | Estimate | 95% CI | Requirement | |
|---|---:|---|---|---|
| known: Blearn − Astar_oracle | −0.861 pp | [−0.907, −0.813] | CI < 0 | ✔ |
| known: Blearn − Astar_learned | −0.861 pp | [−0.907, −0.813] | CI < 0 | ✔ |
| known: Blearn − Bexact_oracle (oracle gap) | 0.000 pp | [0.000, 0.000] | upper < +0.05 pp | ✔ |
| known: q=0 safety (5th / 95th pct) | | [−0.524, −0.429] pp | 95th < +0.05 pp | ✔ |
| known: Astar_oracle nonzero errors | 2,688 | | ≥ 100 | ✔ |
| hidden: Blearn − Bexact_oracle | 0.000 pp | [0.000, 0.000] | upper < +0.05 pp | ✔ |
| hidden: Blearn − Astar_learned | −0.443 pp | [−0.480, −0.407] | upper ≤ 0 | ✔ |
| **Target:** known relative reduction vs Astar_oracle | **61.5%** | [59.1%, 63.8%] | lower ≥ 40% | ✔ **TARGET_MET** |

**Secondary (descriptive):**
- **Relative reduction vs Astar_oracle, hidden burst: 52.4%** [49.4%, 55.4%].
- Blearn − BoffStatic_oracle: −0.171 pp on the known burst and −0.157 pp on the hidden burst, so Blearn beats the best V1.3 decoder even though that decoder is given the true support.
- Blearn − A_nominal: about −6.5 pp in both conditions.

## Interpretation

1. **The learned-support decoder lost nothing relative to the oracle.** Device-level calibration (12,000 detector-only rows plus 1,500 labeled rows) identified both bursts exactly. Blearn matches Bexact_oracle on every shot, removing the "given the exact burst" caveat for these two bursts at this calibration budget.
2. **The V1.5 result replicates with learned support.** On the known burst, the reduction vs the strongest static matcher is 61.5% (V1.5: 61.3%, with oracle support). On the blindly chosen hidden burst it is 52.4%, smaller because static matching already copes better with that burst (Astar 0.846% vs 1.400%).
3. **Labels are essential, as predicted.** The flip log-likelihood ratios (−605 and −657) are decisive. Detector data alone could not have set the logical bit: both bursts share their signature class with supports of the opposite logical effect.

## Limits

- **Hypothesis space:** the learner is given the class of possible bursts (X-flips on at most 3 data qubits, one per round boundary). A burst outside that class would not be learned.
- **Labels required:** learning the logical effect needs a labeled device partition with a known logical preparation.
- **Scope:** d=3 only; exact only for the DEM (`approximate_disjoint_errors=True`); two synthetic bursts; 24 roots per condition × q. There is no hardware and no latency claim (about 6.8 ms/shot in NumPy).
- **Hidden-burst blindness:** the seal ensured the learner and decoder were frozen before the support was known. The support was drawn by the agent's own script, but it was never displayed and was hash-committed before any learner code existed.
- **Raw archives** stay local in `pilot_runs/`, which is git-ignored.
