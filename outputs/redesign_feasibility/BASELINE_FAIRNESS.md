# Baseline definitions and fairness controls

Every policy receives the **same test detector shots in the same order** and is scored against the same observable labels. Where a policy changes its selected matching model, it does not change the quantum circuit or the sampled errors. Save per-shot predictions so paired discordances can be independently recomputed.

| Comparator | Information received | Role and fairness rule |
|---|---|---|
| **Nominal fixed PyMatching** | One named nominal DEM/weight set; no drift signal | Familiar static reference. It cannot be the only baseline because it may be weak under the tested conditions. |
| **Strongest pooled calibration-selected fixed** | Independent calibration labels/outcomes during offline model selection; frozen before evaluation | Main fixed comparator. Select one model minimizing a predeclared equal-regime calibration LER over development/calibration regimes; use deterministic tie-breaking and never test outcomes. All test-time blocks use the same frozen model. This offline selection is not an online input. |
| **Offline regime-informed decoder** | True generating regime, available only to the evaluator | Nondeployable upper-reference. Use the regime-matched calibrated DEM/decoder frozen from independent calibration data. It cannot estimate any deployable-policy gain; label it privileged and never call it an adaptive system. |
| **Periodic causal recalibration** | Same completed earlier detector history, estimator, window/data budget and update-compute budget as online policy | Strong dynamic comparator. Re-estimate/update on a fixed cadence chosen on development data. Match the online method's total number of updates and calibration data volume as closely as possible; account for idle/update compute and latency. It receives no labels or future data. |
| **Online adaptive-weight decoder** | Same past detector stream as periodic policy; update trigger can use a frozen change detector or posterior uncertainty | Proposed policy. It may update earlier when a causal statistic signals relevant drift, but its update count and compute are capped to the periodic comparator's budget. It falls back to pooled fixed when evidence is insufficient. |
| **No-correction / identity scoring** | Predicts no logical-observable flip for each shot | Reference prediction `0` for every logical bit. It quantifies the cost of doing no logical-frame correction in the decoder evaluation. It is **not** a physical circuit with QEC removed and must not be described as such. |

## Selection and pairing

- Calibrate the pooled fixed decoder on development calibration data, with a frozen regime weighting and sample-size rule. Keep a distinct validation set for tuning the estimator, window and update trigger.
- The regime-informed reference may know the regime label solely to select among independently calibrated regime models; it must not refit on the final evaluation set.
- At inference, neither adaptive policy sees true regime, observable label, latent simulator parameters or current-block detector values before selecting the decoder for that block.
- Generate each dynamic schedule's detector/observable array once, then score every comparator against it. This paired design is valid because the studied interventions modify only the decoder; they do not modify physical noise.
- Report raw observable-flip rate, residual LER, shot-level paired discordances, root-level differences, estimator and decoder-switch delays, censored changes, switch counts, false switches and complete runtime.
- Report per-policy initialization/warm-up separately but retain it in the primary full-schedule operational comparison. Also report steady-period results descriptively.

## Equal-budget periodic baseline

The online policy cannot claim an adaptation benefit merely by recalibrating more often. For the initial pilot, use **256-shot blocks**, a frozen development-selected rolling window from `{4, 8, 16}` completed blocks, and a maximum of **one decoder reconstruction per four blocks**. Give both dynamic policies the same detector samples available at each update, the same estimator class, smoothing/prior, model-construction procedure, and maximum CPU/latency envelope. The periodic policy reconstructs at its fixed four-block cadence; the event-driven policy may spend the same update budget when a two-check uncertainty threshold signals relevant change. If the online policy uses an extra change-point detector, count that compute. A periodic policy must not receive fresh calibration circuits unavailable to online operation unless that resource is also charged to online and separately declared.

The true-regime decoder is a reference for opportunity, not a fair equal-information competitor. An oracle that sees future state or test labels is excluded from primary inference entirely.
