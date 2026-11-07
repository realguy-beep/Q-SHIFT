# Audit summary: correlation-aware decoding mechanism

## Decision

The saved 720,000-shot pilot supports a **condition-dependent association**, not a general mechanism. Correlation-enabled matching changed 1,343 of 720,000 pooled-fixed predictions. It improved aggregate LER by 183 residual errors, but the frozen practical-effect gate had already failed because the 95% interval upper bound did not reach −0.0002.

The two adverse conditions were X-memory/X-biased and Z-memory/Z-biased. Correlation-enabled decoding made more residual errors in 9/12 roots and 11/12 roots, respectively. The remaining four conditions favored it in 8–12 roots. The two adverse conditions use exactly the same model index as the corresponding pooled fixed decoder; therefore, model-index/label mismatch is not the cause of these harms. Per-cell and grouped interpretations are exploratory and multiplicity-unadjusted.

The decoder changes a sparse set of logical corrections while preserving the same DEM, graph, weights, detectors, observables, and test shots. Disagreement syndromes are typically nonempty and have about five triggered detectors, but their detector-time profiles overlap between helpful and harmful changes. Saved evidence has no latent Pauli outcomes or matching paths, so the physical cause cannot be identified.

The DEMs contain 564 separator tokens for X-memory and 572 for Z-memory, with counts unchanged across the three bias regimes within a basis. All use `approximate_disjoint_errors=True`. This makes the approximation a credible competing explanation, but no alternative conversion was tested. The audit therefore does not conclude that the observed interaction is physical, that the approximation caused it, or that the pattern generalizes beyond distance 3.

## Reproducibility and evidence checks

`analyze_saved_pilot.py` read the 72 original pilot NPZ files and saved Phase 2B DEM/circuit files. It verified condition/model-index metadata, identical pooled/regime predictions in the same-name cases, and exact per-stratum residual/error totals against the existing results. It wrote supporting CSV/JSON under this new audit directory only. `MANIFEST.json` hashes all audit outputs and the input checkpoints/source/evidence used. No simulation shots were generated, and no file under `outputs/correlation_pilot/` was changed by this audit.

The prior pilot independent audit had already re-decoded every stored prediction. This mechanism audit uses those verified predictions for new descriptive pattern analysis; it does not claim to recover latent fault histories.

During implementation, the first feature script assumed detector time coordinates 0–4. Parsing the saved Stim circuit showed the five-round memory has boundary detector coordinates at t=0 and t=5, with interior slices t=1–4. The script was corrected to include all six coordinate times and rerun successfully. No pilot file or result was changed.

## Next step

The proposed follow-up in `FOLLOWUP_PROTOCOL.md` uses fresh independent samples and two DEM conversion families, with an explicit pre-test feasibility gate. Its primary estimand is the difference in the basis–bias interaction between approximate and non-approximated disjoint-error DEMs. If a valid non-approximated matching model cannot be constructed for every condition, stop before sampling and redesign the reference approach. The protocol has not been executed.

## Files

- `MECHANISM_ANALYSIS.md` — direct observations and interpretation limits.
- `DISAGREEMENT_PATTERNS.md` — paired errors, root directions, and syndrome features.
- `BASIS_BIAS_INTERACTION.md` — effect table, root consistency, and mapping audit.
- `DEM_APPROXIMATION_LIMITS.md` — model metadata and approximation limits.
- `COMPETING_HYPOTHESES.md` — evidence for/against candidate mechanisms.
- `FOLLOWUP_PROTOCOL.md` — bounded prospective, not-yet-run design.
- `analyze_saved_pilot.py` and CSV/JSON outputs — reproducible read-only computation.
- `MANIFEST.json` — SHA-256 hashes of audit and input evidence.
