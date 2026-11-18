# Row/column-averaged MPS contraction ablation

## Hypothesis

qecsim documents that truncated row and column MPS contractions can yield different coset probabilities. Under X-biased code-capacity noise, its established averaged mode (`mode='a'`) may reduce orientation sensitivity relative to the already screened column mode (`mode='c'`).

## Fixed experiment

Use the same qecsim 1.0b9 `PlanarCode(d,d)`, d=3/5, p=.05, `BiasedDepolarizingErrorModel(bias=5, axis='X')`, and bias-aware `PlanarMWPMDecoder` comparator. Compare fixed `chi=16` MPS modes c and a on identical errors/syndromes. No chi search, p change, or new noise profile. Run 5,000 paired samples/distance. Preflight uses 100/distance. Seeds: preflight 2026113401/3402; main 2026113411/3412.

Report LER, paired CIs, exact McNemar comparisons, valid recovery, and relative decode time. Primary ablation is mode a versus mode c per distance; MWPM remains a secondary baseline. The averaged mode advances only if it lowers MPS errors at both distances without invalid recoveries; this is a development decision, not proof of circuit performance.

## Limits

Abort if preflight projects above 300 seconds or any recovery is invalid. This is perfect-syndrome code-capacity evidence. It does not address measurement noise or spacetime decoding in Q-SHIFT.
