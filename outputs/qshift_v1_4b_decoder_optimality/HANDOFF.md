# V1.4B agent handoff

- **Branch:** `codex/qshift-v1-4b-decoder-optimality` (worktree `qshift-v1_4b-decoder-optimality`), from `e2ffab43f`.
- **Status:** analysis and inexpensive development screen complete. **Decision: GO**, recommending a separately authorized V1.5 evaluation (see `DECISION.md` §6).
- **Read first:** `DECISION.md`, then `MATH_ANALYSIS.md`, `PREREGISTRATION.md` and `WORKLOG.md`.

## What exists

- `mld.py`: exact DEM logical-class decoder (variable elimination; width 11 at d=3). Tests: `tests/test_mld.py`.
- `candidate_c.py`: candidate C (negative result). Tests: `tests/test_candidate_c.py`.
- `screen_decode.py`, `analyze_screen.py`: screen pipeline. Per-shot output goes to `work/` (git-ignored, local only); summaries to `results/`.

## Reproduce (read-only on V1.2/V1.3 runs; no sampling)

```powershell
py -3.12 -m unittest discover -s outputs/qshift_v1_4b_decoder_optimality/tests -v
py -3.12 outputs/qshift_v1_4b_decoder_optimality/screen_decode.py S1 <V1.3 pilot_runs/attempt_001> all
py -3.12 outputs/qshift_v1_4b_decoder_optimality/candidate_c.py S1 <V1.3 pilot_runs/attempt_001> all
py -3.12 outputs/qshift_v1_4b_decoder_optimality/analyze_screen.py S1
```

S2 is the same with the V1.2 run directory. A full set takes about 2 h single-process; the work log records the 8-process split used.

## Do not

- Describe S1 or S2 as independent evidence.
- Reuse their seeds for V1.5.
- Call R_true "optimal" or an oracle: it is exact only for the DEM.
- Start V1.5 sampling without owner authorization.

## Open items

- V1.5 freeze and run, pending authorization.
- A scalable variant of B (BP+OSD, belief-matching or tensor networks) for d≥5. That needs installing software, which requires authorization.
- The size of the DEM's categorical approximation (item g) is unquantified.
