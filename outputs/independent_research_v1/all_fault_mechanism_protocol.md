# All-location fault composition for decoder disagreements

## Question

The prior mechanism screen tracked only categorical two-qubit faults. Determine whether shared or ratio-sensitive logical failures also carry substantial one-qubit Pauli and explicit measurement-flip burden.

## Fixed scope

Use two existing high-LER d3 mismatched-basis conditions at actual bias ratio10 and p=.003: Z-memory/X-biased and X-memory/Z-biased. Decode each source-equivalent stream using the same frozen correlation-enabled matching models assumed at ratios5 and10. Instrument every independent `PAULI_CHANNEL_2` pair, `PAULI_CHANNEL_1` target, and explicit `X_ERROR`/`Z_ERROR` target with a private categorical flag; preserve every original detector/observable and all source probabilities. Use independent main seeds 2026113511/3512, 100,000 shots/condition. Preflight uses 5,000 instrumented and independent source shots/condition at seeds 2026113501/3502 and 2026113521/3522.

For groups both-correct, both-wrong, ratio10-fixes-ratio5, and ratio10-breaks-ratio5, report mean faults/shot by pair, one-qubit Pauli, and explicit measurement-error class, plus exact Pauli outcome totals. Also report the same-seed decoder disagreement and total failure counts. No causal attribution from raw counts alone.

## Validation and caps

Require a synthetic all-channel flag/Pauli mapping check, 120 two-qubit pair locations, <=100 one-qubit locations, <=100 explicit measurement targets, unchanged detector/observable counts, exact source p1/p2 probability preservation, and independent source-vs-instrumented LER within 4 combined standard errors in preflight. Stop if projected runtime exceeds 300 seconds or any support/mapping check fails. No sealed or confirmatory data; this is descriptive development fault composition, not a decoder comparison.

## Execution record

The preflight passed on both conditions: 120 two-qubit pairs, 40 one-qubit locations, unchanged 40-detector/one-observable source layout, synthetic category mapping with zero mismatches, and source-versus-instrumented failure differences below 1.1 combined standard errors. Projected main sampling time was 7.71 seconds, below the 300-second cap. The fixed-seed 100,000-shot-per-condition run completed in 3.73 seconds. Results are in `all_fault_mechanism_results.json`.

