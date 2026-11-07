# Phase 0 — Baseline reproduction and preservation

## Integrity and software

Before analysis, `baseline_reproduction.py` verified all 12 local file hashes in the earlier `categorical_decoder_feasibility/MANIFEST.json` and all 8 read-only source-reference hashes recorded there. It then recomputed the toy comparisons into this new investigation directory and compared their risks with the saved `TOY_RESULTS.json`. No original result file was rewritten. The final new manifest separately hashes the prior manifest and cited source files.

Environment: Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3.

## Reproduced values

| Toy | Exact categorical MAP risk | Standard PyMatching risk | Correlation-enabled PyMatching risk |
|---|---:|---:|---:|
| Three independent one-qubit categorical locations | 0.002646 | 0.002646 | 0.002646 |
| Two adjacent two-qubit categorical locations | 0.060000 | 0.112800 | 0.112800 |

For the two-qubit toy at detector syndrome `11`, exact categorical MAP predicts logical flip 1; both saved PyMatching modes predict 0. All 64 and 256 categorical fault configurations were deterministically forced through Stim for the reference checks (320 checks total). The original eight tests passed in the earlier feasibility package; the new investigation's tests are also recorded in the final test log. These are deterministic circuit checks, not stochastic performance shots.

## Conventions

The toy prepares three qubits in `|000>`, measures `Z0 Z1` and `Z1 Z2`, and finally measures each qubit in Z. Detector bits are `D0=x0 XOR x1` and `D1=x1 XOR x2`; `L0=x0 XOR x1 XOR x2`. Stim detector column `j` maps to integer bit `j` (little-bit indexing), and `L0` is the sole observable bit. A decoder decision is its predicted logical-observable flip; residual failure is prediction XOR the true observable flip. The reported risk is the probability that this prediction is wrong.

## Development failures fixed before final results

- The first investigation scripts used an incorrect repository-root index and failed to import the old package. The paths were corrected; no historical files were changed.
- The first dense tensor variable-elimination test produced mass 1.7744 because factor axes were broadcast without transposing to the union scope. The test exposed the bug; axis ordering was fixed, and both heuristics now reproduce exhaustive posteriors and unit mass.
- An initial fault-extraction counter treated `II` as non-identity and reported 425 one-round checks instead of 401. Identity handling was corrected and the final saved count is 401.
- A first three-round run had no stage checkpoints and did not leave a completed result. Progress logging and effect-mask checkpointing were added; the subsequent run completed and saved evidence.
- The first aggregate summary invocation expected a differently named decision field in the controlled-variant JSON. The report script was corrected; the saved numerical results were unchanged, and the final aggregate audit passed.

These were implementation defects in this new feasibility work, not changes to the experiment or its historical evidence.

