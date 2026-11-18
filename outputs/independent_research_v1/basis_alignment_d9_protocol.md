# Distance-9 extension of known-profile basis alignment

## Question

The distance-7 screen found 5 failures for the aligned X-memory basis and 1,009 failures for mismatched Z-memory under X-biased ratio-10 noise, at 500,000 shots/cell. Test one larger matched distance to see whether this code/circuit configuration trend continues and how much the observed evidence can say about the aspirational 99.99% relative reduction.

## Fixed comparison

Use the same rotated surface-code circuit, correlation-enabled PyMatching decoder, gate and measurement p=.003, X-biased ratio 10, and Z-memory vs X-memory comparison as the d3/d5/d7 screens. Set d=9 and rounds=17. The X-memory arm is the known-profile aligned configuration; Z-memory is mismatched. Use independent source-circuit streams, 500,000 shots/arm. Seeds: 2026113001–3002 for 100-shot preflight; 2026113011–3012 for main.

Report failures/LER/Wilson intervals per arm, aligned/mismatched rate ratio with a conditional exact 95% interval that remains defined when aligned failures are zero, zero-failure one-sided 95% upper bound, matched qubits/detectors/two-qubit pair/round resources, sampling/decode time, and a comparison with the already recorded d3/d5/d7 observations. No threshold fit or adaptive claim. This is a fourth finite-distance point, not a threshold estimate.

## Stop and interpretation rules

Before main sampling verify both basis circuits are deterministic without noise, have equal physical resources and expected rounds, produce valid DEMs, and have scalar/batch decode agreement. Stop if the 100-shot preflight projects over 300 seconds. Do not use the preflight outcome rates for inference. The d9 sample may be too small to certify a 10,000-fold ratio; report the exact confidence bound as the result and do not extend shots after seeing failures. This is development-only and not confirmatory evidence.
