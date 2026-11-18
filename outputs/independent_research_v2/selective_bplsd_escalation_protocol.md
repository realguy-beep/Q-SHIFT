# Selective BP+LSD escalation on matching disagreement syndromes

## Hypothesis

The prior full-stream BP+LSD screen was substantially worse than correlation-enabled PyMatching, but a fixed selector could use it only on syndromes where correlation-enabled and ordinary matching disagree. Those disagreement syndromes are a predeclared ambiguity flag; no outcome labels are used in the routing decision.

## Frozen policy and evaluation

- Six d3 Phase 2B conditions: both memory bases crossed with X-biased, balanced, and Z-biased profiles; p=.003 and bias ratio 10.
- Primary decoder: correlation-enabled PyMatching from the same approximate DEM. Reference comparator: ordinary PyMatching using the same graph. Flag iff their predicted logical observables differ. On flagged cases only, replace the primary output with LDPC 2.4.1 `BpLsdDecoder` using `minimum_sum`, scaling .9, max_iter 200, `LSD_CS`, order 0, bits_per_step 1. On unflagged cases keep the primary output. The policy uses syndrome/model outputs only; observables score offline.
- Both matching models and BP+LSD use the same DEM generated with `decompose_errors=True`, approximate threshold .0018. Check the BP+LSD fault estimate reproduces the syndrome; invalid output counts as failure.
- Fresh direct samples: 100,000/condition; preflight 2,000/condition. Preflight seeds 2026114201–4206; main seeds 2026114211–4216. Report flag rate, escalation count, conditional error rates on flagged/unflagged cases, overall LER, paired deltas/McNemar versus the fixed correlation-enabled baseline, syndrome validity, runtime, and memory.
- Advance only if the hybrid reduces equal-weight macro LER by >=10%, no condition is harmed by >5%, all escalated solutions reproduce the syndrome, and total decode time is <2x fixed correlation matching.

## Stop rules and scope

Preflight must pass circuit geometry/noiseless checks, stable zero-syndrome BP+LSD outputs, scalar/batch agreement, and projected runtime <=300 seconds. This is a development-only routing feasibility test, not a new BP+LSD parameter search, a confirmatory evaluation, or evidence of hardware deployment value.
