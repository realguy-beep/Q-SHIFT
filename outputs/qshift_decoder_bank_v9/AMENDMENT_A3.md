# PROTOCOL_DB8 amendment A3: U_FAR state

**Status:** approved by the project owner on 2026-11-24, after DB8 attempt 2 stopped (`RUN_ATTEMPT2.md`) and before any U_FAR data existed. `PROTOCOL_DB8.md` is unchanged. This amendment overrides its section 3 for U_FAR only.

## Why

The section 3 rule chose `X03`, support (3, 25, 34), as the far unknown state. That is the public label, outside the bank, nearest to a bank state other than A, whose λ is closest to E's λ of 95.5. Its correlated-matching decoder cannot be built, because pymatching rejects its decomposed error model. The ORACLE arm needs that decoder.

## Amended rule

Section 3's far-state rule gains two conditions, applied in its ranked order:

1. the state's decoders (`re1.decoders`) must build;
2. it must not be the base label of the out-of-catalog state UO (V01 + qubit 3), so that U_FAR and U_OUT do not share three qubits.

| Rank | Label | Support | Nearest bank state | λ | Result |
|---|---|---|---|---|---|
| 1 | X03 | 3, 25, 34 | OFF | 96.7 | skipped: decoders do not build |
| 2 | V01 | 1, 12, 38 | D | 93.4 | skipped: base of UO |
| 3 | **V06** | **1, 42, 47** | **B** | **93.0** | **selected** |

V06 is in the learner catalog. E, UO and UN are unchanged.

The ranking uses the same analytic stim detector rates as the original selection, with no sampling. `select_unknowns.py` implements the amended rule. It reproduces `SELECTION_A3.json`, which records the skipped labels. The original `SELECTION.json` is kept unchanged.

## Not changed

- the arms, decision rules A1–A4 and their thresholds;
- the episodes, their counts and onsets;
- the seeds (keyed by panel name, so U_FAR keeps its seeds) and the fidelity gate;
- the analysis.

ADVANCE still only permits writing a CF3 plan.

## Disclosure

Before this amendment, two run attempts produced outputs:

- attempt 1: 7 archives;
- attempt 2: 28 records and archives, for the non-null in-bank panels and U_E only.

None was opened or analysed, and none involves U_FAR. Attempt 3 re-runs all 64 episodes, and only attempt 3 is analysed.
