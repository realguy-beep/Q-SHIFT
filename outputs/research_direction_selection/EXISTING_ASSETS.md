# Existing Q-SHIFT assets and evidence audit

**Audit date:** 2026-11-06  
**Scope:** Local research workspace under `outputs/`. This is a read-only inventory; no historical source, result, dataset, or manifest was changed.

## Repository shape

The available project is organized as phase-specific research directories rather than one consolidated Python package. Reusable source is mainly under `phase2b_pauli_bias/`, `phase2c_decoder_fidelity/`, `headroom_feasibility/`, `prototype_development/`, and `conditional_go_resolution/`. The workspace contains historical Phase 4 and Phase 5 records as well. There is no single canonical top-level `src/` tree in this checkout, so future work should import/copy deliberately from a named phase and record the source hashes instead of relying on an assumed project layout.

The installed local versions recorded during this audit are **Stim 1.16.0** and **PyMatching 2.4.0**.

## Reusable implementation and data

| Asset | What it provides | Relevance and caveats |
|---|---|---|
| `outputs/phase2b_pauli_bias/noise_model.py` | Stim rotated-memory X/Z circuits, native placement of categorical `PAULI_CHANNEL_1/2` noise at generated post-Clifford locations, fixed measurement flips, probability records | Reusable controlled noise model; its documented 10:1:1 bias is a sensitivity setting, not hardware characterization. |
| `outputs/phase2b_pauli_bias/decoder_bank.py` | Three-model bank in preserved composition-grid order; decomposed DEM construction; PyMatching correlated matching; batched logical predictions | The builder currently enables correlated matching for every candidate. It does not contain an uncorrelated ablation. It explicitly uses `approximate_disjoint_errors=True` for categorical channels. |
| `outputs/phase2b_pauli_bias/` | Calibration selections, paired held-out predictions/results, per-root evidence, six saved DEMs, circuit records, seed manifests, analysis audit | 1.2 million paired held-out shots across two memories and three composition regimes. Existing evaluation used correlated matching throughout, so it cannot answer the correlation-mode contrast. |
| `outputs/phase2c_decoder_fidelity/` | Source audit, exact small toy enumerator, sample-trained posterior surrogate, saved circuits/DEMs, paired comparison and verification scripts | Useful for explaining why the forest result was not an exact posterior benchmark. The forest had 2,579 errors versus 628 for Phase 2B matching on 120,000 pilot shots; it does not isolate DEM approximation as the cause. |
| `outputs/headroom_feasibility/` | Circuits and DEMs for X/Z memories at d=3,5,7 with rounds=d; native and biased banks; calibration/evaluation arrays, candidate predictions and paired root analysis | Reusable multi-distance circuit preflight and sample-analysis patterns. Its prespecified headroom gate was NO-GO: 36 cells, 14 specialist selections different from pooled, 7 lower evaluation point estimates, only one full cell gate pass and no replicated multi-regime/multi-distance pattern. |
| `outputs/prototype_development/` | Stim/PyMatching experiment loop, paired policy evaluation, schedules, tests and explanatory UI prototype | Useful execution/evaluation patterns. Its 50-root, 307,200-shot development report gave 1,989 pooled-fixed and 1,989 adaptive errors; it is exploratory and not evidence of improvement. The requested new interactive demo is out of scope. |
| `outputs/conditional_go_resolution/` | Safe PyMatching reconstruction fixture, block-boundary swap abstraction, causality tests and resource measurements | Supports rebuilding a matcher from a changed DEM and validating before activation. Tiny d=3 fixture median rebuild was about 2.29 ms; not a hardware deadline measurement. |
| `outputs/phase2a_decoder_specialization/`, `outputs/phase3b_independent_replication/`, `outputs/phase4a_model_adequacy/`, `outputs/phase4b_replication/`, `outputs/phase4c_strong_baselines/` | Historical selection, model-adequacy, replication and strong-baseline evidence | Preserve as separate estimands and protocols. Do not pool results across phases or retrofit a positive interpretation. |

## What the evidence already establishes

- Phase 2B kept total single- and two-qubit gate-fault probabilities fixed while changing the categorical Pauli composition; measurement flips stayed at 0.003. It compared the same detector samples across three decoder hypotheses. Pooled and regime-informed policies each made 5,532/1,200,000 errors, and the same model was selected across regimes within each memory basis.
- All Phase 2B bank models used Stim decomposition plus PyMatching correlated matching. The saved DEMs contain decomposition separators (564 in the X-memory DEMs and 572 in Z-memory DEMs), so there is a concrete feature to ablate; prior results did not test whether using it helped.
- Phase 2C confirms that DEM conversion of the custom categorical channels is an approximation, but its random-forest reference was much worse. It cannot establish that DEM information loss caused any observed decoder error.
- Phase 4C Stage 2 and Phase 5/headroom work did not establish adaptive superiority over the strong pooled baseline. The earlier calibration-vs-nominal positive result is a different comparator and must not be substituted for this question.
- The evidence matrix records the comparator distinction numerically: Phase 4A reported calibrated 940 vs nominal 1,118 errors/600,000; Phase 4B reported 1,008 vs 1,165/600,000, with a fresh-template protocol deviation; Phase 4C’s stronger pooled-fixed contrast was +1.556e-5 calibrated-minus-pooled LER, 95% interval [-4.889e-5,+7.667e-5], p=0.66658. These are different experiments and must stay separate.
- Phase 3B’s X-bias replication reported 43,673 fixed vs 43,675 specialist errors/600,000 (p=0.9374) in the synthesis record. Phase 4C Stage 2 test predictions were independently re-decoded, but calibration detector arrays are absent, so calibration fitting cannot be fully reconstructed.
- The strongest local asset is paired, independently seeded simulation and saved raw evidence. The main missing evidence for the selected direction is a same-DEM, same-sample correlated-matching-off versus correlated-matching-on comparison.

## Reuse rules

Future pilot code should be a new directory with a new configuration, seed inventory, and source hash record. Reuse the Phase 2B circuit/noise construction and raw analysis patterns by reference or copy with documented provenance. It must use one Stim sample bundle per condition/root for every decoder arm, preserve the observable labels, and keep inference at the independent-root level. Existing historical files remain read-only.

