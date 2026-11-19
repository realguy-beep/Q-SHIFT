# RE1: frozen evaluation of the mismatch-robust learned-support pipeline (pre-registered)

**Status: frozen** in `RE1_FREEZE.json`, committed before any RE1 study sample.
- **Authorized:** the build, approved by the owner on 2026-11-19 ("Approve, build it").
- **Not yet authorized:** the single run, "Run RE1", which must use `--open-hidden-seal` because R6 samples from the sealed H2.
- **Separately, after the run:** publishing anything about H2 needs "Open the RE1 seal".

**Source:** `PLAN_EVAL.md` (`33529d95c`). Everything in it applies except the deviations below.

## Build-time deviations from the plan

All were found during the build, before any study sample.

1. **No fake-sampler pass.** The plan listed a fake-sampler pass. It was replaced by the real-sampler rehearsal (1 root per condition on rehearsal seeds), together with a synthetic-archive analysis test (`tests/test_re1.py`). The rehearsal exercises the same pipeline more completely.
2. **q=0 safety margin.**
   - **What changed:** the margin is now `max(0.05 × LER_q0(A_nominal), 3 / N_q0)`, where N_q0 is the condition's q=0 evaluation shots (48,000, so the floor is 6.25e-5).
   - **Why:** in the Z-biased conditions the q=0 counts are tiny (E2E Mz: 2 errors for burst-free matching, 1 for BP+OSD, in 24,000 shots). A pure 5% margin is a fraction of one error there, so the gate would fail on noise alone.
   - **What this means:** harm below about 3 errors per condition at q=0 cannot be resolved, and that is stated as a limitation.
   - **Correction to the plan:** the plan called the A_nominal rule "the Phase C rule". Phase C compared against Astar. RE1 keeps the plan's burst-free comparator, A_nominal, because that is the meaningful "no harm when no burst" reference.
3. **Seal handling made explicit.** The jobs must read H2 inside the run, both to sample R6 and to build its oracle arms.
   - Eval records store R6's learned supports as `"SEALED"`.
   - The analysis reports only learned-exactly counts and error statistics, nothing that identifies H2.
   - The raw archives in git-ignored `work/` contain no supports.
4. **Recount is parallel.** The recount re-decodes root 0 of every condition end to end (calibration, fit, learning, decoding) in parallel, into a separate replay run directory. The plan did not specify this.

## Frozen elements

| Element | Content |
|---|---|
| Method | `estimate2.py` (B2), unchanged since `fe035cde7`; flag threshold 118.432; Phase C learner, τ = 1,561.218; L2 prior 0.01; Astar q_dec 0.0025 |
| Conditions | `re1_config.CONDITIONS`: R1–R6 gated, 12 roots each; X1 descriptive, 6 roots. Mismatch values were never used in development (asserted by a test) |
| Hidden burst H2 | Drawn 2026-11-19 by `re1_seal.py` from 1,998 candidates. Excluded: classes 213, 216, 223, 790 and 901; any support sharing ≥ 2 qubits with K, Phase C H, M0, M1 or CR; and the public rehearsal support (1, 3, 5). Commitment `HIDDEN_COMMITMENT_RE1.json` (sha256 `0387e18b80e4…`); plaintext outside git |
| Seeds | `RE1_SEEDS.json`: 474 study keys (78 roots × 6, plus 6 bootstrap seeds) and 42 rehearsal keys, screened against 4,254 prior values (every prior inventory, including `DEV2_SEEDS.json`) |
| Arms | L2L_R, plus S\* chosen per root from {Astar_Rm, Astar_Nm} by labelled calibration errors (a tie goes to Astar_Rm), L2s_true, Astar_true, L2L_N and A_nominal |
| Endpoints | NI: upper bound of L2L_R − L2s_true below 0.25 × the oracle LER. SUP: upper bound of L2L_R − S\* below 0. Both one-sided at α = 0.025/12. Safety: p95 ≤ 0 or ≤ the margin in deviation 2. Root bootstrap, 20,000 replicates, seeded from `re1:stats:<cond>` |
| Verdicts | CONFIRMED / PARTIAL / NOT_CONFIRMED / INCONCLUSIVE, as in the plan (`re1.analyze`) |

## Preflight (`RE1_PREFLIGHT.json`)

- **Source:** the rehearsal, with 7 roots running concurrently.
- **Inputs:** a fixed ≤ 47 s per root and ≤ 29.5 ms per BP+OSD arm per shot, which projects to 1,107 s per root against the 3,600 s job timeout.
- **Run length:** 78 roots in 10 waves on 8 workers is about **3.1 h**, or 3.8 h with a 1.25 factor, against the 5 h budget.
- **Consequence:** the pre-declared fallback (dropping L2L_N in R2 and R5) is **not** applied.
- **Caveat:** E2E ran 1.7× over its rehearsal estimate. That estimate came from a single-worker rehearsal; this one already includes contention.

## Execution (single attempt)

```
git checkout --detach <freeze commit>
cd outputs/qshift_adaptive_robust_v1
python re1.py run eval --expected-head <freeze commit> --open-hidden-seal --workers 8
python re1.py analyze eval <out1>
python re1.py analyze eval <out2>            # byte-identical
python re1.py recount eval <out1>/ANALYSIS.json --open-hidden-seal
git checkout codex/qshift-adaptive-robust-v1   # then commit results
```

**Safeguards:**
- A run needs a clean tree with HEAD equal to the freeze commit. Each job re-verifies every freeze hash.
- `RUN_STATUS.json` refuses a relaunch.
- There are no retries or seed substitutions. A failure is reported as a failure.

## Rehearsal (rehearsal seeds, public rehearsal support for R6; not data)

- The pipeline ran end to end for all 7 conditions.
- B2 learned exactly in the 6 in-family roots, and X1 was flagged.
- Analysis was byte-identical across two runs.
- The recount matched, and the root-0 re-decode was bit-identical for every condition.
- The rehearsal verdicts are meaningless at 300 shots per q.

## Claim boundary

As in `PLAN_EVAL.md`: simulation, d=5, weight-3 bursts, the stated mismatch range, and one hidden burst. X1 is a safe-fallback check only, not a decoding claim. R is expected at about 65%, so this study does not bear on the 95% target.
