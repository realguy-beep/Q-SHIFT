# Q-SHIFT correlated decoder V1.6b

V1.6b is a fresh-seed evaluation of the exact decoder with **device-level learned burst support** (Blearn), on the known burst and on a sealed hidden burst. It is development-only. Read `EXPERIMENT_PROTOCOL.md`.

## Status

Frozen and ready; **not executed**. Zero V1.6b sampler calls. The hidden burst is still sealed. Execution requires the owner's separate sign-off.

## Verification (sampler-free)

```powershell
py -3.12 -m unittest discover -s outputs/qshift_correlated_decoder_v1_6b/tests -v
py -3.12 outputs/qshift_correlated_decoder_v1_6b/run_eval.py --dry-run --expected-head <FROZEN_SHA>
```

## Single evaluation (only after owner sign-off)

```powershell
py -3.12 outputs/qshift_correlated_decoder_v1_6b/run_watchdog.py --execute --expected-head <FROZEN_SHA>
py -3.12 outputs/qshift_correlated_decoder_v1_6b/recount_from_scratch.py outputs/qshift_correlated_decoder_v1_6b/pilot_runs/attempt_001
```

By default the run opens the sealed hidden burst from `C:\Users\LENOVO\Documents\Codex\qshift_v1_6_hidden_burst_SEALED.json`; `--sealed` overrides the path. It verifies the file against the committed SHA-256 before use.
