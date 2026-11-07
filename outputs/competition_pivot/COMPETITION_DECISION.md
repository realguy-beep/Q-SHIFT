# Competition pivot decision

## Decision: **NO-GO for uncertainty-aware decoder selection as the next research hypothesis**

This decision applies only to the candidate approach in this folder. It does **not** terminate Q-SHIFT or invalidate its simulation, reproducibility, decoder-audit, and demonstration work.

### Why this candidate does not pass

1. **Insufficient novelty.** Per-syndrome ensemble decoder selection is established in the peer-reviewed surface-code literature. Confidence-based rejection and confidence-gated strong-decoder fallback are also established; 2026 preprints apply closely related confidence gates to meta-decoders and adaptive windows.
2. **Insufficient observable headroom.** Only 225/98,304 saved shots changed prediction between pooled and selected decoders. The always-adaptive net difference was nine errors, and the prior root-stratified interval includes zero.
3. **No useful confidence signal found.** Cross-root calibration utility prediction was weak (AUC 0.570; Brier worse than constant prevalence); the current-syndrome utility prediction was below-chance AUC (0.464); the calibration gate produced 686 errors versus 681 fixed, and the per-shot gate produced 684. The simple likelihood threshold selected the candidate for every disagreement and reduced to always-adaptive behavior.
4. **Cost and validation remain unfavorable.** Shot-level gating requires both decoder outputs; per-decoder native memory and runtime were not measured. The 24 roots are development evidence only and cannot serve as an independent final gate test after analysis.

### What remains useful for Q-SHIFT

- Keep the fixed decoder as the default and retain the gate only as a research prototype/competition replay.
- Use the saved evidence to demonstrate the distinction between “identifying a noise condition” and “predicting logical utility.”
- For a future research pivot, first seek a distinct scientific question such as conditions under which detector histories make decoder utility identifiable, and complete a literature review before implementation. This is a recommendation, not a claim of novelty.
- A later competition demo may present the failed gate honestly as a negative exploratory result; it must not claim adaptive superiority or safety guarantees.

### Scope and reproducibility

No simulation was run and no historical artifact was modified. The analysis is in analyze_existing_gate_opportunity.py; its recomputed data are in GATE_ANALYSIS_RESULTS.json, GATE_PER_ROOT.csv, and GATE_DISAGREEMENT_SUMMARY.csv. MANIFEST.json hashes all files in this new folder except itself.
