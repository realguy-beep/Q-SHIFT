# Selective BP+LSD escalation: initial development screen

## Accuracy signal

On six fresh d3 conditions (100,000 samples each), the fixed hybrid routed a syndrome to BP+LSD only when correlation-enabled and ordinary PyMatching predicted different logical observables. It escalated 1,567/600,000 cases (0.261%). The equal-weight macro LER fell from .005253 to .004503, a 14.28% relative reduction. The hybrid had fewer observed failures in all six cells; per-cell reductions ranged from 4.1% to 39.5%. All escalated BP+LSD outputs reproduced their input syndrome.

This is a development signal, not confirmation. The largest gains occurred in three conditions, while the X-memory/Z-biased cell improved only 4.1%. Per-cell paired intervals and McNemar values are in the JSON result.

## Runtime failure

The hybrid requires both correlated and ordinary matching passes to form the syndrome-only flag, plus BP+LSD on the flagged subset. Corrected timing includes all three costs. Mean total decode time was 8.44x fixed correlation-enabled matching; the predeclared limit was 2x. Thus the candidate fails its advancement gate despite the LER reduction. BP+LSD's per-syndrome cost overwhelms the low escalation fraction in this implementation.

The likely next question is whether the accuracy signal replicates and is concentrated on the same ambiguity population. That would inform whether a faster local escalator is worth implementing, but it would not change the current runtime rejection. No parameter tuning or confirmatory evaluation has occurred.
