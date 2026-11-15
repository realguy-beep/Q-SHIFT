# Deterministic preflight results

**Classification:** sampler-free engineering and model feasibility only. No random detector events, training, performance evaluation, evaluation labels, Stage 5 material, or sealed outcomes were accessed in this preflight.

## Commands and results

- `python -m unittest discover -s outputs/qshift_correlated_decoder_feasibility_v1/tests -v` — 12 passed.
- `python -m compileall -q outputs/qshift_correlated_decoder_feasibility_v1` — passed.
- `python outputs/qshift_correlated_decoder_feasibility_v1/run_pilot.py --dry-run` — 0 sampler calls, 0 shots; three candidate q circuits and DEMs constructed.
- `python outputs/qshift_correlated_decoder_feasibility_v1/run_watchdog.py` — same sampler-free dry run completed.
- `python outputs/qshift_correlated_decoder_feasibility_v1/prepare_seed_inventory.py` — 65 unique new seeds; no collision against 108 numeric values in the named V1 development inventory; V1 inventory SHA-256 `8ac30550a9143895925678194e98e0631a50a507d1ff36e7c8eeb2ee8ba5ca63`.
- `python outputs/qshift_correlated_decoder_feasibility_v1/run_deterministic_preflight.py` — 5 distinct three-detector factor signatures, 40 detectors, one observable; 0 disagreements on 32 burst-only patterns; 88 disagreements across 600 algebraically constructed background-fault-plus-burst patterns; 0 sampler calls and no labels. A single local run measured 0.0312 s decoder/model construction, 0.8134 s for the 632-pattern deterministic comparison, and 0.8531 s end to end. This is a fixture timing, not throughput or LER evidence.

An initial `python -m py_compile .../*.py` command failed because PowerShell passed the wildcard literally; the corrected `compileall` command above passed. This did not execute sampling.

## Resource observations

At preflight time, Windows reported 3,902,599,168 bytes available RAM of 16,312,205,312 total and 260,876,689,408 bytes free on C:. A separate short-lived Python process measured 17,784,832 bytes RSS. These are point-in-time machine observations, not the pilot's peak memory or runtime. The pilot enforces a 600-second process-tree watchdog, samples current-process RSS at guard boundaries against 2 GiB, requires at least 1 GiB free disk, and caps run artifacts at 256 MiB. The RSS guard is sampled and is not a hard OS memory limit.

## Readiness and limits

The deterministic result establishes usable decoder decision sensitivity on constructed valid syndromes, not a lower error rate. The candidate remains synthetic and not hardware calibrated. Ten evaluation roots per condition make the paired root-bootstrap interval exploratory and potentially poorly calibrated. The bounded run may therefore be inconclusive; no claim of 50% reduction is presumed.
