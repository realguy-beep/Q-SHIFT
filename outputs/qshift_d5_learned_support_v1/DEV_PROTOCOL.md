# d=5 learned burst support, Phase B: development gate protocol

**Pre-registered.** This protocol, `contract.py`, `DEV_SEEDS.json`, `gate_jobs.py` and `gate_aggregate.py` are committed before any gate sample is drawn. The owner authorized Phase B ("Approve Phase B") on 2026-11-17.

**Status:** development evidence only. These seeds are never reused for evaluation.

## Question

At d=5, p = 0.003, can the two-stage learner (`learner_d5.py`) find the true burst's signature class and logical effect from calibration-sized data? The calibration size is the one V1.6b used:
- 4,000 detector-only shots per q, pooled over q ∈ {0, 0.01, 0.02}, for 12,000 shots in total;
- plus 500 labeled shots per q, for 1,500 in total.

## Development bursts (fixed in `contract.BURSTS`)

| ID | True support | Class (CLASSES_D5.json) | Why it is included |
|---|---|---|---|
| SC | (23, 31, 34) | 790, pure, flip 0 | scaled_v1 family; used in Phase 2 and in Phase C condition K |
| CR | (25, 27, 29) | 901, pure, flip 0 | centre_row family (2-detector signatures) |
| M0 | (12, 34, 45) | 213, mixed, flip 0 | stage-2 stress test: the min-weight explanation (1, 23) has flip 1 |
| M1 | (1, 23, 45) | 223, mixed, flip 1 | stage-2 stress test: the min-weight explanation (12, 34) has flip 0 |

**How M0 and M1 are chosen:** take the first mixed class, in sorted signature order, that holds a weight-3 support with flip 0 (or flip 1). The true burst is the smallest such support. The choice does not depend on learner performance; it was made before any gate sample.

## Data per pool

Each pool draws one Stim sampler call per q with 4,500 shots:
- rows 0–3,999 are detector-only, and their labels are discarded unread;
- rows 4,000–4,499 are the labeled shots, used only by stage 2.

There are 24 pools per burst, plus 24 burst-free pools of 12,000 shots at q = 0 (for G2). That makes 312 sampler calls and 720,000 shots. Seeds are in `DEV_SEEDS.json`, namespace `qshift-d5-learned-support-dev-2026-11-17`. They are screened against 1,367 earlier values: every prior inventory, the robustness dev and eval seeds, and seed 1 (see the disclosure below).

## Learner (frozen in `learner_d5.py`, Phase A commit `45b0fe28d`)

**Stage 1:**
- `FastParityLearner` runs over all C = 1,003 classes.
- A class is accepted if Δ ≥ χ²₁(1 − 0.01/1,003) = 19.52.
- Otherwise the result is "no burst".

**Stage 2 (`learn_flip`):**
- For a pure class, the flip is taken directly from the class.
- For a mixed class, the labeled shots are decoded with L2 BP+OSD at prior 0.01 for each flip's representative. The flip with fewer errors wins, and a tie goes to the min-weight flip.

**Correctness:** a pool counts as correct when it selects the true class and the true flip. The representative support then has the same burst mechanisms as the true support.

## Gates (`gate_aggregate.py`)

| Gate | Rule |
|---|---|
| G1 | for every burst: class correct in ≥ 23 of 24 pools |
| G2 | q = 0 pools: "no burst" in ≥ 22 of 24 |
| G3 | for every burst: flip correct in ≥ 95% of class-correct pools. This is automatic for pure classes and reported as such; it is non-trivial for M0 and M1 |

**PASS** if G1, G2 and G3 all hold; otherwise **STOP**. A STOP ends the study before Phase C. A second gate at a larger calibration size would need a new pre-registration and a new owner OK, on fresh seeds.

**Reported, not gated:**
- the learning curve: class accuracy and the q = 0 "no burst" rate at 3k, 6k and 12k prefixes (equal rows per q);
- q̂ error against the pooled mean 0.01;
- wrong selections with their Δ;
- per-pool time.

## Deviations from the approved plan, declared before sampling

- **The 24k curve point is dropped.** Every pool is 12k, and pairing pools would need a second learner pass. The 3k, 6k and 12k points remain.
- **The plan's "L2 learned vs true support on 30k shots" check is replaced by an exact identity.**
  - When the class and flip are correct, the learned representative has the same DEM burst mechanisms as the truth. This is tested at d=3 in V1.6, and for CR's representative in this package's tests.
  - L2's predictions then coincide by construction, so decoding would add nothing.
  - Wrong selections are reported individually instead.
- **Two mixed-class bursts (M0, M1) are added,** so that stage 2 is actually exercised. Both known families fall in pure classes.
- **Disclosure:** before this pre-registration, one 12,000-shot Stim timing probe was drawn, with stim seed 1, SC support, q = 0.01. It measured learner speed (0.56 s per selection; it selected class 790). It is not gate data, and seed 1 is excluded from the screened set.

## Execution

1. **Rehearsal** (before the commit; not data): `python gate_jobs.py run rehearsal`, which runs 1 pool per burst plus 1 q = 0 pool on rehearsal seeds, then `python gate_aggregate.py rehearsal work/GATE_REHEARSAL.json`.
2. **Commit** this pre-registration.
3. **Gate:** `python gate_jobs.py run dev --workers 8`, then `python gate_aggregate.py dev DEV_GATE.json`.
4. **Record:** commit `results/gate_dev/pools/*.json`, `DEV_GATE.json` and `DEV_RESULTS.md`. Raw arrays stay in git-ignored `work/`.
