# Correction 1 to IDENT1 stage 1: the moments are not exact for the circuit

Added after stage 1. No frozen file or result is changed. Found by Claude, the author of IDENT1, while reviewing ROB1; not an independent audit.

**What was wrong.** `PROTOCOL_IDENT1.md`, `measures.py` and `STAGE1_RESULTS.md` describe exact moments. They are exact for Stim's detector error model, but `moments.py` builds that model with `approximate_disjoint_errors=True`. The circuit has 400 `PAULI_CHANNEL_2` noise operations whose outcomes exclude each other; the option treats them as independent. (Its 120 `PAULI_CHANNEL_1` operations have equal probabilities and Stim converts them exactly. An earlier local draft of this note wrongly counted them.) This was not disclosed. The brute-force test used a toy detector error model, so it could not detect it.

**Size.** Every channel has equal probabilities, so `DEPOLARIZE1/2` of the same total gives a model that Stim builds in strict mode. Differences between the two models, at p₀ and q = 0.01, for OFF and bank states A-D only:

| F1 feature | Largest rate difference | In binomial standard deviations (n = 2,000) |
|---|---|---|
| Single detector | 4.3e-5 | 0.010 |
| Pair co-firing | 1.0e-5 | 0.005 |

The largest relative difference in a pair rate is 0.21%. The largest parity difference is 1.6e-4. For comparison, an earlier estimate of 5.2e-5 for single detectors was approximate and is replaced by this table.

**Effect.** These shifts are small beside the stage 1 separations, and no reading is changed here. The stage 1 values of J and M2 were **not recomputed**, so their exact change is unknown. ROB1 uses the strict model.
