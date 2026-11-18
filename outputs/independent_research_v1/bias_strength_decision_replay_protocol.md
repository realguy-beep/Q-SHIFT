# Paired decoder-decision replay

## Question

The d3 frozen screen favored assumed ratio10 over ratio5, while d5 was near-neutral. The graph audit found matching topology unchanged. Decompose the same archived-seed streams into cases where both models succeed, both fail, ratio10 alone fails, ratio5 alone fails, or their predicted logical corrections disagree.

## Fixed reanalysis

- Replay the exact existing d3 seeds 2026112421–2026112436 and d5 seeds 2026112521–2026112536, 100,000 shots per cell, across actual ratios2/3.5/5/10 and both profile directions and memory bases.
- Rebuild only the frozen ratio5 and ratio10 matching models and replay the same Stim sampling seeds. Verify that reconstituted per-model error counts exactly match the archived d3 and d5 result artifacts; abort the analysis if any cell does not match.
- Report per-cell, per-actual-ratio, and per-distance counts for both-correct, both-wrong, ratio10-only failure, ratio5-only failure, predicted-correction disagreement, and accuracy conditional on disagreement (with a descriptive Wilson interval aggregated by distance). This is a paired error decomposition, not a new sample or an independent validation.
- As a secondary coarse diagnostic, bin detector Hamming weight as 1–2, 3–4, 5–8, and 9+ and report paired disagreement/fix/break counts per distance. Weight-zero syndromes cannot alter a correction and are recorded separately. Do not tune a selector or infer causality from these bins.
- Calculate the sample-specific oracle selector ceiling on the two outputs: the oracle is correct on every disagreement and still wrong whenever both fixed decoders fail. Report only as a descriptive ceiling for this observed sample, not a population bound.
- No new independent random seeds, model tuning, or significance claim. Cumulative unique sample count does not change.
