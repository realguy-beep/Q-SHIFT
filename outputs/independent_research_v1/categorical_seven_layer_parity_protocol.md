# Exact seven-layer syndrome/logical-parity inference

## Hypothesis

The joint detector/logical state tensor carries a redundant logical dimension for MAP risk. For each compact syndrome `s`, propagate total probability `P(s)` and signed logical parity `Z(s)=P(s,L=0)-P(s,L=1)`. The exact logical-MAP risk of this isolated fragment is `sum_s (P(s)-abs(Z(s)))/2`. This halves the state dimension while retaining the full binary logical posterior.

## Scope and representation

Use the frozen forced-outcome signature map in `categorical_seven_layer_preflight.json`: the final seven `PAULI_CHANNEL_2` layers of the d3 five-round Z-memory, X-biased-ratio10 circuit (42 categorical locations; 20 compact detector bits). No other stochastic circuit locations are included. At each location, sum probabilities by detector mask for `P`; separately sum signed probabilities by detector mask, with sign `(-1)^logical_mask`, for `Z`. Identical detector signatures may be coalesced exactly. Do not prune or approximate mass.

The vectorized reference propagates P and Z by XOR convolution over all `2^m` detector states. The independent Walsh implementation multiplies the per-location transforms of the two detector kernels and applies inverse transforms, separately for P and Z. Numeric operation estimates use `2 * (locations+1) * states * m` Walsh butterflies and `2 * states * coalesced_detector_signatures` vector updates.

## Fixed resource caps and stop rules

Proceed only if detector states <=1,100,000; combined P/Z vector updates <=1,000,000,000; combined Walsh work <=2,000,000,000; estimated peak working memory <=1 GiB; and wall time <=300 seconds. The preflight estimate is 1,048,576 states, 788,529,152 updates, and 1,803,550,720 Walsh operations. Stop before inference if measured implementation estimates exceed any cap. Do not raise caps or alter the scope after observing results.

## Validation and endpoints

1. Check the parity method against the existing exact six-layer joint-signature result on its six-layer input: aggregate joint mass into P and signed Z, then require every state to agree within absolute `1e-12`; require the MAP risk to agree within `1e-12`.
2. On the seven-layer map, require vectorized P and Z to agree with their independent Walsh results within `1e-12`; require P total mass within `1e-12` of one, nonnegative P within tolerance, and `abs(Z)<=P` within tolerance.
3. Force 512 deterministic combinations of categorical outcomes through Stim and require detector/logical XOR signatures to match the stored map.
4. Report exact isolated-fragment MAP risk, reachable syndromes, runtime, memory estimate, and all validation metrics. This is not a full-circuit LER or decoder comparison.

No stochastic samples are generated. If any cap or validation check fails, stop and record a negative feasibility result without changing the protocol.
