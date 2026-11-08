# Q-SHIFT v2 Pilot 2 final decision

**Decision: NO-GO for launching the 11.736M-shot study on the current evidence.** This is a decision about readiness, not a claim that causal adaptation cannot work. The development pilot is not independent confirmation.

## Frozen decision-rule result

The LER GO rule required event GLR to have a 95% stream-cluster interval entirely below zero against both the development-selected static decoder and EWMA in at least one decoder mode. It did not:
- Ordinary: event vs static -0.0077 pp [-0.0144, -0.0010]; vs EWMA -0.0067 pp [-0.0163, 0.0029].
- Correlation-aware: event vs static 0.0005 pp [-0.0053, 0.0063]; vs EWMA -0.0135 pp [-0.0216, -0.0053].

The operational cost/accuracy comparison is promising: event was within the +0.10 pp noninferiority margin versus EWMA in both modes, used about 95% fewer graph switches, and used about 81% less online CPU per stream. But when the event-specific 6.922 CPU seconds of threshold calibration/tuning data generation and replay are charged to this 160-stream pilot, event has higher total CPU. The frozen protocol did not define the amortization horizon for this one-time cost. Since the cost GO rule says lower total CPU, the result is not sufficient to pass it without a predeclared cost accounting.

## Evidence and recommendation

- The event arm had 1,223 ordinary errors vs 1,239 static and 1,237 EWMA; with correlation-aware decoding it had 1,552 vs 1,551 static and 1,580 EWMA, each out of 208,000 scored shots. Effects are small; cluster intervals remain important.
- Selected GLR met its stationary calibration target (0.486 alarms/1,000 calibration shots) but showed 31 evaluation alarms in the three correctly specified stationary scenarios and 17 in the constant-burst measurement-mismatch scenario.
- Change response was 45 shots step-up, 95 step-down, and 40 transient, slower than EWMA on average.
- The independent audit passed after repairing paired contingency and derived CPU columns from the saved aligned outcomes. All failed execution/audit attempts and intermediate CSVs are retained.
- Retain static and EWMA as strong references. Keep the event controller as a development candidate, not a selected replacement. Do not launch the full study.

A follow-up should first freeze an explicit calibration amortization horizon and cost formula, retain paired per-shot outputs, and use the repaired contingency helper before any new sample. The current 298,500-shot pilot budget has been consumed; any further development sampling needs a separately approved allocation. No Stage 5 or sealed data were accessed.

## Reproducibility and source hashes

Branch/worktree: `qshift-v2-dev`; current base/commit is recorded in Git. Frozen config SHA-256: `b544eb48ec1898f4fe512abcdbc5ff1db6cf92ec0cc3b1102c7e91ebe9bccc0d`. Seed inventory SHA-256: `42591b54c87ce5f76981e5a62d69a7b48a2ea45d30305676e37c3abb782085ca`. Final repaired results SHA-256: `21019ef8ead24eae7c08597851d690961fedc0760ecfef5b7b41550bcf8ab6ca`. Paired archive SHA-256: `2283194834c8406ff7d468967b10c8712db72416143cef0bd24aa0e3184e25ed`.

Final source SHA-256:
- `prepare_pilot2.py`: `b1e2cdd59b5b7905ecf2922271df7e502f359996a60fab7eed16250f065a552c`
- `preflight_audit.py`: `69c2a362d6d1d82b37813d79b52b5889b2caa9134172633e4a6c00b6542521e9`
- `controller.py`: `e2533d8c7de8843f8014c5aa43b1723b50d60c73eb77406d70c5b2235a5f7fda`
- `run_pilot2.py`: `30769e3ee351388fe40eed60e8e6fa441e28b4f680c5e170921c4c93539fb6e7`
- `test_pilot2.py`: `53995b8837f90ddd62a37ef66991b4bbf7803df1009a188781dce35142fbd11d`
- `independent_audit.py`: `00f22965b1a3b0f403178ad4224de96296e811e4d939580f561927a5503b627e`
- `repair_paired_metrics.py`: `8e13328d82675da7ddccdf52ff81e07cdb93942b273576d01d6e34ba7386dbc9`
- `write_reports.py`: `b8b5522cb999b1b7f6bf694dde7167a06ce4876be086dbda9d4f149c30b6643f`

Astra research report input SHA-256: `7cad775dc7d6b58d5475bf4be43ae5845ef299ee1c7143211fdbfc19adef0656`. Pilot 1 report input SHA-256: `ab5ef9ba930338a0f597ece7bfcf93e2638a341de52e80176f403bf755aa495b`.

Commands: `python -m outputs.qshift_v2_pilot2_v1.prepare_pilot2 --freeze` (seed plan already frozen); `python -m outputs.qshift_v2_pilot2_v1.preflight_audit`; `python -m outputs.qshift_v2_pilot2_v1.test_pilot2`; `python -m outputs.qshift_v2_pilot2_v1.run_pilot2`; `python -m outputs.qshift_v2_pilot2_v1.repair_paired_metrics`; `python -m outputs.qshift_v2_pilot2_v1.independent_audit`. The repaired result file carries the original pre-repair hash and source-at-execution hash in `PILOT2_RUNTIME.json`.
