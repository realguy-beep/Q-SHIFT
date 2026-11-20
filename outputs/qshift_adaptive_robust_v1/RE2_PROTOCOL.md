# RE2: frozen evaluation of the E1T pipeline with two new sealed bursts (pre-registered)

**Status: frozen** in `RE2_FREEZE.json`, committed before any RE2 study sample.

| Approval | Covers | Given |
|---|---|---|
| The owner keeps RE1's H2 seal unopened | RE2 never reads H2 | 2026-11-20 |
| "Revise per review" | `PLAN_RE2.md` revision 2 (`45c2c2a27`) | 2026-11-20 |
| "Approve, build it" | the build, the H3/H4 draw and seal, the seeds, the rehearsal, the preflight and the freeze | 2026-11-20 |
| "Run RE2" | the single run, with `--open-hidden-seal` (RE2's own seal) | not yet |
| "Open the RE2 seal" | publishing H3/H4 identities after the run | not yet |
| "Open the RE1 seal" | also triggers `re2_contamination.py` | not given |

**Source:** `PLAN_RE2.md` revision 2. Everything in it applies, except the build-time clarifications below.

## Build-time clarifications and deviations

All were found during the build, before any study sample.

1. **"No learning on a flag" for E1T.** E1T's consistency check (S2) is defined on the learner's accepted class, so the learner must run to compute the flag.
   - On a flag, its output is **discarded**: the decoder uses the nominal model with no burst.
   - This is BRT's and AD1's E1T exactly, and the decoding outcome is RE1's rule.
2. **The pool after the rehearsal bursts were removed.** The draw pools are **34 (H3)** and **146 (H4)** classes.
   - The rehearsal bursts are the lowest-index eligible class in each stratum: (7, 12, 25) for H3 and (1, 5, 7) for H4. Both are public.
   - Pool hash: `a4c5f513…fc6e` (`HIDDEN_COMMITMENT_RE2.json`).
   - Recomputed contamination probabilities (`results/re2/OVERLAP.json`):

     | | H3 | H4 | Either |
     |---|---|---|---|
     | Uniform prior | 2.9% | 3.2% | **6.0%** |
     | Worst case | 29.4% | 12.3% | **32.3%** |

     The plan figures were 2.9 / 3.2 / 6.0% and 28.6 / 12.9 / 31.5%.
3. **Hidden-burst records are scrubbed more thoroughly than RE1's.**
   - **What is kept:** p̂, b̂, the excluded count, the flags (S1, S2) and the learned/class-correct booleans.
   - **What is dropped:** the class index, flip, support and the excluded detector set. The detector set could locate the burst.
   - RE1 scrubbed only the support. See the note to the owner below.
4. **Preflight method:** the slowest rehearsal root × ⌈66 / 8⌉ waves × 1.25. Each BP+OSD arm is floored at RE1's 29.5 ms per shot. This is deliberately conservative.
5. **Distinctness test scope:** the test covers every fixed condition in DEV2, RE1, BRE, BRS and BRT, plus AD1's static and step levels (C0, D3, D4 at blocks 0 and 23). AD1's linear ramps pass through intermediate values by design and are not compared.

## Frozen elements

| Element | Content |
|---|---|
| Method | E1T (`estimate5`, on `estimate4.e1_with_set`); Phase C learner via `brt.learn`, τ unchanged; `learn_flip`; L2 prior 0.01; Astar q_dec 0.0025; decoders and sampling via `re1.decoders`, `re1.predict` and `re1.sample` |
| Calibration | per root, 4,000 unlabelled + 500 labelled rows per q at q ∈ {0, 0.01, 0.02}, so 12,000 + 1,500, pooled (RE1's recipe) |
| Evaluation | 4,000 shots per q per root; 12 roots per gated condition; 6 for X2 |
| Conditions | G1 p 0.0023 (K); G2 p 0.0032 Z6 (K); **G3 p 0.0028 Z4 (H3), R6's base model**; G4 p 0.00335 (H3); G5 p 0.0026 Z5 (H4); X2 p 0.003 X8 (K, descriptive) |
| Hidden bursts | H3 (footprint ≥ 25) and H4 (footprint ≤ 20), drawn 2026-11-20 by `re2_seal.py`, one uniform class each by OS entropy. Commitment `HIDDEN_COMMITMENT_RE2.json` (plaintext SHA-256 `85b556c1486ec9d5…`); plaintext outside git. RE1's seal not read |
| Arms | L2L_E; S\* from {Astar_Em, Astar_Nm} by labelled calibration errors, tie to Astar_Em; L2s_true (oracle); Astar_true; A_nominal; L2L_B2 (RE1's B2 pipeline, descriptive, G3 and G4) |
| NI (gated) | upper bound of L2L_E − L2s_true < max(0.25 × oracle nonzero-q LER, 10 / N_nz); NI_strict (RE1's rule) reported |
| SUP | upper bound of L2L_E − S\* < 0 |
| Safety (q=0) | p95 ≤ 0, or ≤ max(0.05 × LER_q0(A_nominal), 3 / N_q0) |
| Statistics | one-sided α = 0.0025 (0.025 / 10); root bootstrap, 20,000 replicates, seeded from `re2:stats:<cond>` |
| Verdicts | CONFIRMED / NOT_CONFIRMED / PARTIAL / INCONCLUSIVE, by RE1's logic (`re2.analyze`) |
| Seeds | `RE2_SEEDS.json`: 401 study keys (66 roots × 6, plus 5 bootstrap) and 36 rehearsal keys, screened against 10,487 prior values (through `AD1_SEEDS.json`) |
| Independence | Hidden-burst claims are conditional on H3/H4 being independent of RE1's H2: 94.0% under the draw distribution, at least 67.7% in the worst case. `re2_contamination.py` is frozen and runs only after "Open the RE1 seal". A contaminated burst's conditions (H3: G3, G4; H4: G5) are relabelled "not independent of RE1", its claim is withdrawn, and the verdict is restated without them |

## Preflight (`RE2_PREFLIGHT.json`)

- **Source:** the rehearsal, 6 roots concurrently.
- **Per root:**

  | | G1, G2, G5 | G3 | G4 | X2 |
  |---|---|---|---|---|
  | With L2L_B2 | about 750 s | 1,161 s | 1,110 s | 893 s |

- **Projection:** 66 roots in 9 waves on 8 workers is **2.9 h**, or **3.6 h** with contention, against the 5 h budget. The worst root is 1,451 s with contention, against the 3,600 s job timeout.
- **Consequence:** the pre-declared fallback (drop L2L_B2) is **not applied**.

## Rehearsal (rehearsal seeds and public rehearsal bursts; not data)

- **Run:** 1 root per condition, 300 evaluation shots per q, with full-size calibration.
- **E1T:** learned the burst exactly in all five gated conditions. p̂ was within 2% of the true p in every condition, and b̂ was 5.68 for Z6, 4.27 for Z4 and 4.97 for Z5. X2 was flagged and fell back to nominal, as designed.
- **B2 (RE1's estimator):** **flagged G3's large rehearsal burst**, the R6 failure mode, and learned G4's.
- **Reproducibility:** the analysis was byte-identical across two runs. The recount re-analysis was identical, and the root-0 re-decode was identical for all 6 conditions.
- **Verdicts are meaningless at 300 shots per q.** Most gated conditions show SUP = 0 errors against 0.

## Execution (single attempt)

```
git checkout --detach <freeze commit>
cd outputs/qshift_adaptive_robust_v1
python re2.py run eval --expected-head <freeze commit> --open-hidden-seal --workers 8
python re2.py analyze eval <out1>
python re2.py analyze eval <out2>            # byte-identical
python re2.py recount eval <out1>/ANALYSIS.json --open-hidden-seal
git checkout codex/qshift-adaptive-robust-v1   # then commit results
```

**Safeguards:**
- `studykit.require_frozen_head` runs in the launcher and in every job: expected head, clean tree and every frozen hash.
- `RUN_STATUS.json` refuses a relaunch.
- Records are write-once, with no retries and no seed substitutions.

## Note to the owner: RE1 record hygiene (found during this build; not inspected)

**What the code shows:** RE1's `root_job` scrubs only the `support` field of R6's learner records. It still writes `class_index`, `flip` and `class_correct`, for both the estimated-model and nominal-model learners, into `results/re1/records/`, which is committed and pushed.

**Why it matters:** if any R6 root's learner accepted a class, those fields could narrow down or reveal H2's class. Under the owner's decision to keep H2 sealed, I did **not** open those records to check. The auto-mode guard also blocked the read.

**What RE2 does:** it removes these fields for H3 and H4.

**Whether RE1's committed records need action** (they are frozen evidence and are not modified here) is the owner's decision.

## Claim boundary

As in `PLAN_RE2.md` revision 2. A CONFIRMED result would support the following, at d=5 in simulation on fresh seeds, with 12,000 + 1,500 calibration rows per root:
- the E1T pipeline decodes within 25% of the oracle, or within 10 errors per 96,000 shots;
- it beats the strongest deployable matcher;
- under p 0.0023–0.00335 and Z-bias 4–6;
- for K and two sealed, never-seen weight-3 bursts, one with a ≥ 25-detector footprint;
- conditional on H3 and H4 being independent of H2.

It would not bear on unseen-burst learning rates in general, out-of-range mismatch, X-bias or measurement-heavy noise, other burst weights, d ≥ 7, hardware, adaptivity, or the 95% target.
