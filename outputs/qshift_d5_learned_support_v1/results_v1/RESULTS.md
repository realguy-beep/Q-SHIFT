# d=5 learned burst support, Phase C: frozen evaluation results

**Overall verdict: CONFIRMED.** Both conditions are GO. Each passes the Bonferroni 97.5% CI and the q=0 safety check. Both are also non-inferior to the oracle-support L2s.

## How the run was done

- **Protocol:** `PHASE_C_PROTOCOL.md`, freeze `C_FREEZE.json` at commit `a857c975b106234bc5913751b56df3069521904d`.
- **Authorization:** the owner said "Run it, open seal" on 2026-11-17, which covered the single run and opening H's seal.
- **Run:** a single attempt from 12:54:44Z to 15:03:53Z on 2026-11-17, about 2.15 h of wall time on 8 workers.
  - The preflight projected 2.96 h, against a hard budget of 5 h.
  - The 144 root jobs plus 2 calibration jobs all returned rc 0. The slowest job took 537 s, well under the 3,600 s timeout.
  - Total job CPU time was 61,426 s.
- **Shots:** 1,200,096 evaluation shots, i.e. 24 roots × 8,334 shots per (condition, q), plus 27,000 calibration shots.

## Integrity checks

| Check | Result |
|---|---|
| HEAD equals the freeze; clean tree; every job re-verified the freeze hashes | passed (the launcher and each job enforce this) |
| Seeds, archive hashes, shot counts and recorded error counts (`c_analyze.py`) | passed |
| Second analysis | `ANALYSIS.json` and `paired_roots.csv` are byte-identical (sha256 `88b365de9483…`, `d89479eb258c…`) |
| Recount of all totals from the archives, plus a bit-identical re-decode of root 0 for every (condition, q) and every arm (`RECOUNT.json`) | passed: the totals match the analysis, and the re-decode of all 6 roots × 5 arms is bit-identical |
| H seal: the plaintext matches the commitment `080520ed8944…` and is in the committed pool | passed (`../HIDDEN_REVEALED_C.json`) |

## What the learner found

There was one calibration draw per condition, using 4,000 detector-only rows plus 500 labeled rows per q, and the threshold τ = 1,561.2.

| Condition | True support | Selected class | Δ | q̂ | Flip | Learned support | Correct |
|---|---|---|---|---|---|---|---|
| K | (23, 31, 34) | 790 (pure) | 12,668 | 0.0100 | 0, pure class | (23, 31, 34) | yes |
| H | **(12, 34, 40)**, sealed until this run | 216 (pure, singleton) | 13,645 | 0.0104 | 0, pure class | (12, 34, 40) | yes |

In both conditions the learned support equals the true support exactly. That is why the L2L and L2s predictions are identical, and likewise Astar_L and Astar.

**A coincidence, disclosed.** H differs by one qubit from the development surrogate M0 = (12, 34, 45), which was class 213 and was excluded from the H draw.
- The draw was uniform over 2,291 supports using OS entropy, and it was sealed before any Phase C sample.
- Nobody read the plaintext before this run.
- Still, H is a near neighbour of a development burst, not a structurally distant one.

## Error counts (out of 200,016 shots per cell)

| Condition | Arm | q=0 | q=0.01 | q=0.02 |
|---|---|---|---|---|
| K | **L2L** | 134 | 159 | 164 |
| K | L2s | 134 | 159 | 164 |
| K | **Astar** | 304 | 362 | 441 |
| K | Astar_L | 304 | 362 | 441 |
| K | A_nominal | 259 | 961 | 1,692 |
| H | **L2L** | 126 | 147 | 126 |
| H | L2s | 126 | 147 | 126 |
| H | **Astar** | 201 | 244 | 251 |
| H | Astar_L | 201 | 244 | 251 |
| H | A_nominal | 226 | 565 | 909 |

## Endpoints

The bootstrap is root-paired with 20,000 replicates. LER values are equal-weight over q = 0.01 and 0.02.

| | K | H |
|---|---|---|
| LER L2L / Astar | 8.07e-4 / 2.007e-3 | 6.82e-4 / 1.237e-3 |
| **Co-primary L2L − Astar** | −1.200e-3 | −5.55e-4 |
| 95% CI | [−1.317e-3, −1.085e-3] | [−6.40e-4, −4.70e-4] |
| Bonferroni 97.5% CI | [−1.335e-3, −1.067e-3]: passes | [−6.55e-4, −4.60e-4]: passes |
| q=0 safety (95th percentile of L2L − Astar) | −7.10e-4, which is ≤ 0: passes | −2.50e-4, which is ≤ 0: passes |
| Non-inferiority, L2L vs L2s (upper 95% bound / margin) | 0 / 2.02e-4: non-inferior | 0 / 1.71e-4: non-inferior |
| R = 1 − LER(L2L)/LER(Astar) | **59.8%** [55.8, 63.7] | **44.8%** [40.3, 49.3] |
| L2L − A_nominal, nonzero q | −5.82e-3 | −3.00e-3 |
| **Decision** | **GO** | **GO** |

L2L also beats Astar at q=0 in both conditions:
- K: −8.50e-4, 95% CI [−1.01e-3, −6.85e-4];
- H: −3.75e-4, 95% CI [−5.35e-4, −2.25e-4].

## What this means

At d=5 and p = 0.003, serial BP+OSD (L2) with a burst support **learned from about 13.5k calibration shots** cuts the logical error rate relative to correlated PyMatching given the **true** support:
- by about 60% for the known scaled_v1 burst;
- by about 45% for a sealed, previously unseen weight-3 burst.

For these two bursts, this removes the "burst-support oracle" caveat from the earlier d=5 results: Phase 2 at 65%, and the robustness study. The learned support was exact in both cases, so the learned-support decoder reproduced the oracle bit for bit.

## Claim boundaries

- **Scope:** simulation only, d=5, 5 rounds, `model_v14`, p = 0.003, weight-3 X-bursts.
- **Learning draws:** there was one per condition. The B2 development gate estimates learning reliability: 24/24 class, 24/24 no-burst, 100% flip. This evaluation's CI does not cover it.
- **Base noise model:** the learner and τ assume the true base model. Robustness to errors in that model, as on real hardware, is untested.
- **Comparator:** for H, Astar's q_dec of 0.0025 was transferred from scaled_v1 rather than re-selected for H.
- **H's location:** H is a one-qubit neighbour of the development surrogate M0 (see above).
- **Unchanged:** the d=7 STOP stands. Nothing here addresses d=7 or other code distances.
- **Independence:** this is not independent confirmation. It is the same team's pre-registered simulation.
