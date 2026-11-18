# Research questions and hypotheses (prospective; nothing here has been tested on evaluation data)

The program asks whether a *deployable* adaptive Q-SHIFT controller reduces logical error rate across a broad, pre-specified benchmark, against strong static comparators with equal information. Each hypothesis states the test that would falsify it.

## Primary questions

**Q1 (broad aggregate).** On the frozen evaluation split of `BROAD_NOISE_BENCHMARK.md`, does the deployable Q-SHIFT controller (Arm Q) reduce the pooled weighted LER relative to the strongest *deployable* static comparator (Arm S*, chosen on validation data)?
- **H1a:** R_pool(Q vs S*) > 0, judged by the one-sided lower bound at α = 0.025.
- **H1b (the 95% goal):** R_pool ≥ 0.95, judged by the lower bound (**G_AGG**).
- **H1c (95% everywhere):** R_c ≥ 0.95 in every eligible condition, with Holm adjustment (**G_EVERY**).

**Q2 (adaptiveness).** Does adaptation add to a strong static decoder?
- **H2:** Q beats its own non-adaptive ablation Q0. Q0 is the same decoder family with a single pooled calibration fitted once on the same calibration budget.
- **Falsified if** the 95% CI for Q − Q0 includes 0 in the pooled endpoint.

**Q3 (safety).** On burst-free evaluation conditions, the 95th-percentile excess LER of Q over the nominal fixed decoder is ≤ 0.05 × LER(nominal) in every condition.

## Mechanism questions (development and validation only)

- **H-E1 (mismatch-robust estimation).** Under a base-p mismatch of ±17% and Z-bias 10, a robust per-class background-scale estimate restores burst-support learning.
  - **Target:** correct class ≥ 20/24 burst pools and false accepts ≤ 1/24 at q=0, where the Phase C learner got 0/24 and 24/24.
  - **Synthetic support only so far:** `tests/test_adaptive.py::EstimationTests`.
- **H-E2 (change detection).** A calibrated binomial CUSUM detects a ±17% step in background rate within ≤ 10 blocks of 200 shots, at an in-control median run length ≥ 200 blocks. Synthetic support only.
- **H-E3 (unknown-regime detection).** Out-of-family blocks are classified UNKNOWN, and the controller falls back. **Target:** fallback rate ≥ 90% on OOD validation blocks, with no switch to a non-fallback decoder on them.
- **H-F1 (background floor).** At p = 0.001, at least 18% of L2's failures are search-limited (dev data: 10/56). A pre-declared search variant reduces the net floor on full dev re-decoding with no q=0 harm. **Falsified if** the net change has a 95% upper bound ≥ 0 (`BACKGROUND_ERROR_ANALYSIS.md`).
- **H-F2 (degeneracy).** Most of the floor (dev: 46/56) is MLE-consistent. A degeneracy-aware decoder (an ensemble or belief-matching) reduces it where search variants cannot.

## Explicitly out of scope

- Hardware data.
- Real-time latency claims beyond measured CPU cost.
- Neural decoders, unless a hypothesis requires one. None does at present (see `ADAPTIVE_ARCHITECTURE.md` §Neural).
