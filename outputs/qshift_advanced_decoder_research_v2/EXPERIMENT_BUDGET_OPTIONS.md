# Experiment Budget Options

All counts are unique generated shots. Replaying common detector/observable arrays across policies and decoder modes does not multiply shot generation. Budgets include template, calibration/tuning, warm-up, and scored data. These are options for later review, not authorization to generate data.

| Design | Core allocation | Mismatch stress | Shared templates | Total unique shots | Use |
|---|---|---|---:|---:|---|
| A. Minimal feasibility | 5 core conditions × 20 streams × (1,000 warm-up + 1,000 scored) = 200,000 | 10 streams × (1,000 warm-up + 1,000 scored) = 20,000 | 60,000 | **280,000** | Plumbing, chronology, flag checks, gross effect only; primary scored=80,000 |
| B. Moderate development | 6 conditions × 50 streams × (1,000 warm-up + 2,000 scored) = 900,000 | Included as sixth condition | 6 × 20 tuning streams × (1,000 warm-up + 1,000 scored) = 240,000; 60,000 templates | **1,200,000** | Estimate discordance/ICC and refine design; not confirmatory |
| C. Larger confirmatory candidate | 6 conditions × 500 streams × (1,000 warm-up + 2,000 scored) = 9,000,000 | Included as sixth condition | 6 × 100 tuning streams × (1,000 warm-up + 1,000 scored) = 1,200,000; 60,000 templates | **10,260,000** | Candidate only if variance, resource and protocol gates pass |

## Precision and scientific value

The primary estimand uses four nonstationary conditions. A contributes 80,000 primary scored shots; B 400,000; C 4,000,000. The remaining scored shots estimate stationarity and mismatch harm as secondary outcomes. At planning discordance q=.006, A's approximate SE is .000274 even with independent shots and .000387 at within-stream ICC .001; it cannot resolve a 0.0002 practical effect. B gives .000122 iid and .000212 at ICC .001. C gives .000039 iid and .000067 at ICC .001, but rises to .000102 at ICC .003 and .000177 at ICC .01. These approximations ignore stream heterogeneity beyond ICC and do not establish power. See `STATISTICAL_FEASIBILITY.md`.

**Recommendation:** do not jump from A to C. If a separate allocation is approved, A is only a pipeline/variance reconnaissance and should be explicitly prevented from answering superiority. Use it only if it can estimate paired discordance, stream variance and measurement-mismatch confounding robustly enough to make a redesign decision. B is a more informative development option but still cannot establish the proposed practical effect under plausible ICC. C is currently not justified: prior Pilot 2 did not show a robust practical win, variance is not adequately known, V2.4 end-to-end runtime is unknown, and a highly dependent stream process could still defeat its precision.

## Resource estimates and uncertainty

Assuming 40 detector bits plus one observable stored as one byte each, the C candidate's full raw shot table is `10.26M × 41 B = 420.66 MB` decimal (about 401 MiB) before metadata, container overhead, or copies. If 8 policies × 2 decoding modes each store one byte prediction per shot, the conservative all-shot prediction store is 164.16 MB; raw plus these predictions is about 584.82 MB. Most predictions need only be retained for evaluation, reducing that estimate, but complete paired auditability may require aligned outcomes. Chunk arrays by stream and avoid concatenating all data into multiple in-memory copies.

Known system context: ~2.38 GiB free RAM, 2 GiB process RSS ceiling, 247.52 GiB free disk. These resources were previously reported; no V2.4 end-to-end benchmark establishes runtime or native matcher RSS. Pilot 2's reported 45.59 seconds / 129.2 MiB was from an earlier code path and cannot be extrapolated safely. Disk appears ample by raw-byte arithmetic; process RSS and runtime are unresolved. A future, separately approved resource preflight must measure peak RSS and end-to-end generation, graph construction, and replay time on the exact frozen implementation, with no Stage 5 or sealed evaluation material. It must be budgeted and approved independently; it is not part of this protocol draft.

## Budget decision gates

- Do not call A a powered efficacy pilot or use its noise conditions to redefine the scientific question.
- B requires a prespecified purpose and fresh development allocation; no automatic carry-forward from consumed Pilot 2 budget.
- C requires supervisor and owner approval after development estimates of paired discordance, stream-level heterogeneity, resource use, and the correlation-mode implementation audit. If sensitivity at q=.006, ICC=.003 is not adequate for the approved practical margin, revise or stop rather than silently expanding the shot count.
- Any budget counts include mismatch as a separate sixth stress condition; do not pool it into primary drift scenarios.
