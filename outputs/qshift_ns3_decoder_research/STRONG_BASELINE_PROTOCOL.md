# Proposed development-only comparison (not authorized or run)

## Arms and information access

1. **Primary static baseline:** PyMatching sparse blossom built from the established decomposed approximate DEM, with weights/configuration selected only on separate eligible development roots. Freeze graph and settings before scoring roots.
2. **Correlation ablation:** same decomposed DEM and weights, `enable_correlations=True` at both construction and decode versus false at both. Report if predictions coincide; do not count this as an independent algorithm when it does.
3. **Candidate:** pinned belief-matching implementation on an explicitly documented undecomposed DEM/model path. If both methods cannot receive semantically comparable model information, label the comparison algorithm-plus-representation and include a representation control. The current bare BP prototype is not yet suitable as the primary contender due runtime and loopy-graph uncertainty.
4. **Optional privileged reference:** true-parameter matching can be reported in a separate, clearly privileged arm only; it cannot be called deployable or used to tune the candidate.

## Data and analysis

- Generate each detector history once from a frozen development circuit/noise configuration and send the same detector bits to every decoder.
- Keep logical scoring labels separate from decoder input. Never provide labels, true hidden noise parameters, or post-transition future observations to an online method.
- Allocate independent root identities to development selection, tuning, and final development scoring. No held-out scoring outcomes may select weights, thresholds, stopping rules, or methods.
- Pair per-shot logical-error indicators and compute paired risk difference (candidate minus baseline), with root as the independent cluster. Report root-wise paired differences and a prespecified root-cluster bootstrap or t interval; also report raw discordant-pair counts. Freeze the number of roots and interval method before execution.
- Record unconditional LER, paired differences, nonconvergence/failure rate, decode latency distribution, peak resident memory, graph construction/tuning time, and all exclusions.
- Candidate practical margin for owner review: absolute paired LER improvement 0.0002. Its authorization/provenance is not verifiable from the source-limited NS-3A inputs, so the owner must affirm or replace it and freeze it before outcomes. Do not choose it from a pilot's scores.
- Seed manifests must be newly generated from an approved development-only namespace and checked for independence from every held-out and protected seed inventory. This proposal does not create any seeds.

## Staged authorization

First authorize only a small engineering pilot to validate runner, pairing, and failure logging—not to claim efficacy. After review, a separate development decoder-comparison authorization can test a frozen method set and practical margin. Independent confirmatory evaluation is a distinct later gate. Historical V2.4 remains HOLD; no approval is implied by this document.
