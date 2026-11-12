# Corrected Budget Accounting

This corrects `outputs/qshift_advanced_decoder_research_v2/EXPERIMENT_BUDGET_OPTIONS.md`. Every count below is a proposed unique generated shot. No sampling occurred. Evaluation streams are independent of template, pooled-static calibration and tuning roots. No evaluation observations select any policy. Replaying one evaluation stream across policies and modes does not multiply generated shots.

## Fixed allocations used for arithmetic

- Template/profile set: 11 p-grid points `{0,.002,…,.020}` × 6,000 shots = **66,000**.
- Separate pooled-static calibration: four primary scenarios × C calibration roots/scenario × 1,000 detector-only shots/root. C=20/50/100 for A/B/C, respectively: **80,000 / 200,000 / 400,000**.
- Separate tuning: six strata (five core settings including one stationary setting, plus independent measurement-mismatch stress) × T roots/stratum × (1,000 detector warm-up + 1,000 tuning shots). T=10/20/100: **120,000 / 240,000 / 1,200,000**. Only detector features and prespecified schedule metadata enter hyperparameter choice; no evaluation data or logical labels.
- Evaluation: five core settings × E roots × (1,000 detector warm-up + scored shots), plus independent mismatch roots. Warm-up belongs to its own evaluation stream and is used only causally within that stream after every policy's parameters are frozen. E=20/50/500, scored=1,000/2,000/2,000, mismatch roots=10/50/500: **220,000 / 900,000 / 9,000,000**.

The exact probability levels, schedule lengths, stationary point(s), burst step times and feature template circuit remain owner freeze decisions. The arithmetic assumes exactly one stationary core setting and these root counts. Any additional stationary point or schedule adds its full allocation and must be recounted before approval.

## Recalculated totals

| Option | Evaluation | Static calibration | Tuning | Templates | Correct total | Primary four-stratum scored shots |
|---|---:|---:|---:|---:|---:|---:|
| A — minimal feasibility | 220,000 | 80,000 | 120,000 | 66,000 | **486,000** | 4×20×1,000 = 80,000 |
| B — moderate development | 900,000 | 200,000 | 240,000 | 66,000 | **1,406,000** | 4×50×2,000 = 400,000 |
| C — larger candidate | 9,000,000 | 400,000 | 1,200,000 | 66,000 | **10,666,000** | 4×500×2,000 = 4,000,000 |

Design A is no longer 280,000: the old total `200k core +20k mismatch +60k templates` omitted independent tuning and a separate pooled-static calibration. Design B/C previous totals also omitted the static calibration allocation and used a different template count. A's 20-stream four-scenario primary evaluation is only pipeline/gross-variability feasibility; it is not a powered pilot. B is development only. C remains unauthorized and not justified by current evidence.

## Data partitions and leakage prevention

Use four nonoverlapping root namespaces: templates; pooled-static calibration; method tuning; evaluation. A root belongs to one partition only. Tuning includes the stationary and mismatch strata so false-alarm and robustness hyperparameters are assessed before evaluation, but the online policies themselves see only the detector observations. Static calibration pools four primary conditions equally and hides source labels from the fit. Evaluation change schedules are known to the evaluator for metric calculation, never to a policy. An independent audit checks root uniqueness and chronology without opening any protected seed inventory; a custodian certifies separation if required.

The warm-up counted inside evaluation is not used for policy selection: it only initializes each already-frozen causal method on that stream. If desired inference is unconditional over warm-up history as well, the method's initial state is part of the stream outcome; do not condition away poor initialization. Tuning/calibration uncertainty is excluded from the proposed conditional evaluation interval unless the design adds outer bundles.

## Resource arithmetic (checked)

For C, 10.666M × 41 bytes (40 detector bytes + one observable byte) = 437,306,000 bytes = **437.306 MB decimal** raw if retaining all partitions in that format. Up to 16 one-byte policy/mode predictions per shot adds 170,656,000 bytes; combined lower-level table = **607.962 MB decimal** before metadata, multiple copies, Stim/PyMatching native allocations, logs or archive duplication. Prior Phase 2 arithmetic 10.26M×41B=420.66MB and +16B/shot=584.82MB is itself correct for that prior budget, but the corrected budget is larger. Chunk by stream and avoid full-array duplication.

Prior context is 2.38 GiB free system memory, 2 GiB process RSS ceiling and 247.52 GiB disk. No V2.4 end-to-end runtime benchmark was found. Pilot 2's 45.59s/129.2MiB cannot be projected. RSS and runtime remain unknown pending separate owner approval of a resource preflight. The no-benchmark restriction is observed here.
