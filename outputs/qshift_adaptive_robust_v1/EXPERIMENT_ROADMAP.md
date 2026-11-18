# Experiment roadmap (each step needs its own owner authorization unless marked "authorized")

| Step | What | Data | Approx. cost | Decision it informs | Authorization |
|---|---|---|---|---|---|
| 0 | This milestone: audit, design, prototypes, synthetic tests, floor diagnostic on Stage S dev failures | existing dev arrays | done (167 s) | — | authorized, done |
| **1** | **Floor re-decode:** full 1.2 M Stage S dev shots with 2 pre-declared variants (min-sum 0.9; OSD_CS-40 + BP-200) | existing dev arrays, no sampling | about 30–45 min, 8 workers | H-F1: does a search variant lower the net floor without q=0 harm? | **needed** ("Run floor re-decode") |
| 2 | **Mismatch-robust learner on existing mismatch dev pools:** apply the robust scale (H-E1), then the Phase C learner, to `qshift_d5_model_mismatch_v1` Phase A pools (development data) | existing dev arrays | about 10 min | H-E1 on real circuit data: correct ≥ 20/24, false accepts ≤ 1/24 | **needed** |
| 3 | `DecoderProtocol` adapters for A_corr, L2 and the floor variant; Q wired to real decoders; deterministic tests on small DEMs | none | engineering | — | authorized (engineering) |
| 4 | **Dev sampling** for the broad benchmark: `suite.DEV`, about 6 conditions × 24 roots × small N | new Stim dev samples | about 1–2 h | controller thresholds, regime models, CUSUM delta | **needed** (new dataset) |
| 5 | **Val sampling and selections:** S\*, decoder variant, Q settings; projected eligibility; power and preflight | new val samples | about 2–4 h | everything frozen for eval | **needed** |
| 6 | Seal fresh eval geometries, freeze eval | none | — | — | **needed** (freeze sign-off) |
| 7 | **Frozen eval** (single attempt) + verification + second analysis | new eval samples | sized by protocol; hard cap frozen | Q1–Q3, G_AGG, G_EVERY, G_ADAPT, G_SAFE | **needed** (confirmatory run) |
| 8 | OOD run | new OOD samples | capped | generalization, reported separately | **needed** |
| — | Optional dependency: `beliefmatching` (pinned) for degeneracy-aware decoding, if step 1 shows the floor is degeneracy-dominated | — | install | H-F2 | **needed** (dependency approval with an install plan) |

**Stop rules:**
- If step 1 shows no net floor reduction **and** step 2 fails H-E1, the 95% broad target is reported as implausible with current methods. The program then pivots to the attribution study: how much of R is background inference, how much is calibration, and how much is adaptation.
- Step 4 does not start until steps 1–3 report.
