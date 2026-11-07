# Final GO / NO-GO decision

## Decision: **NO-GO for the proposed online matching-weight adaptation study as framed**

### What was resolved

- The closest methods and supplementary/appendix material show that causal syndrome-history estimation and time-varying decoder-weight updates are established. The proposed broad algorithmic novelty claim is not supportable.
- PyMatching 2.4.0 can safely rebuild a matcher from a changed physical noise model. The tested atomic-swap approach preserves the current block’s decoder and activates a validated new model only after the block completes.
- A small empirical schedule-maximum trigger calibration was run on independent stationary schedules. It observed 2 false-update schedules out of 100 validation schedules, but the exact 95% interval was 0.24%–7.04%. The study therefore does not certify the desired 5% schedule-level false-update bound. It only calibrates one accepted update per fixed 12-block schedule; repeated post-update resets remain uncalibrated.
- Detector-only finite-grid fitting plus graph reconstruction altered predictions and modestly changed paired outcomes on common shots. The equal-regime paired effect was −0.0000916 LER, with a seed-stratified 95% interval of −0.000417 to +0.000234. This is inconclusive and below the prior 5% relative / 0.0001 absolute practical thresholds. No reliable decoder-utility advantage is established.

### Conditions still unresolved

1. No distinct algorithmic novelty remains for generic causal online matching-weight adaptation; the proposed equal-resource benchmark framing alone is not enough to assert publication-level novelty.
2. The update trigger’s independent validation interval crosses 5%, and its repeated-update behavior has not been calibrated.
3. No executed online-versus-periodic comparison exists with shared syndrome histories, estimator evaluations, rebuild budget, CPU, memory and activation latency.
4. The utility pilot is small, finite-grid, single-distance/single-basis and development-only; it did not establish a stable practically meaningful improvement.
5. Local rebuild latency/memory measurements do not establish hardware compatibility.

### Recommended disposition

Do not launch a full adaptive confirmatory experiment on the current hypothesis. Preserve existing Phase 1–5 and headroom evidence. If research continues, first reassess the candidate information/identifiability question in [REVISED_NOVELTY_CLAIM.md](REVISED_NOVELTY_CLAIM.md) against the literature, or treat Q-SHIFT as an open reproducibility benchmark rather than a new adaptive decoder algorithm. Neither route is approved as novel by this audit.

## Execution and evidence status

- No historical frozen file was modified.
- Small development checks generated **456,704** Stim shots under new screened seed IDs; no large confirmatory simulation was launched.
- The independent recomputation in [INDEPENDENT_VERIFICATION.json](INDEPENDENT_VERIFICATION.json) passed for all saved development arrays, decoder predictions, calibration selections, paired counts and stationary trigger maxima.
- Seed scan: 262 new stream IDs, no exact collision among **391** text-readable historical output files examined. Opaque binary archives were not scanned for embedded seed metadata.
