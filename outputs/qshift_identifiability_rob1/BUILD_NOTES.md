# ROB1 build notes

Built from protocol draft 2 on the owner's "Build ROB1". **Not run.** The protocol, code and tests have one author (Claude) and no independent review.

- **No ROB1 value for an unknown X was computed.** The end-to-end test uses the four bank states as targets, F0 only. The stage 1 check repeats known SEEN values with the old model. The T1 variance and T2 probability checks on SEEN classes run inside `rob1.py run`, before any result is written; if one fails, only `CHECK_FAILED.json` and the progress log exist.
- **Tests:** 15 pass. The first run had two failures and one error, all kept here:
  1. The toy found that Stim converts one-qubit channels exactly; only `PAULI_CHANNEL_2` was approximated. `CORRECTION_1.md` and section 4 were corrected (wording only).
  2. The circuit builder refuses q > 0.02. ROB1's bank grid reaches 0.04, as approved, through the additive burst model; the full-circuit check sets the burst probability after building. **q = 0.04 is outside the range the original circuit code was declared for.**
  3. The dropped-grid-point mutation did not change the test data's answer. The data was changed so that it does. No measure changed.
- **T1 uses direct covariances in blocks of 468 models**, not the 32-term expansion, so the expansion check compares the direct value with a full exact circuit model instead.
- **Edge ends in T2:** if several grid points set the same end, the end counts as an edge end when any of them is at the edge.
- **Timing** (`TIMING.json`, random matrices): T1 under F1 about 16 minutes for both grids, 2 GB for the stored statistics; T2 about 2 minutes. Pair results, checks and JSON add to this. The required second run doubles it. The 4-hour and 8 GB limits are applied from outside, as in IDENT1.
- **Not covered before the run:** run-to-run repeatability (needs two runs) and peak memory under F1.
