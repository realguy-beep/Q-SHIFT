# Selected research direction

## Decision

**Primary: Direction B — controlled correlation-aware decoding comparison.**  
**Fallback: Direction C — code-distance and physical-noise operating limits.**  
**Direction A is deferred.**

This decision is specific to the next bounded research step. It does not terminate the Q-SHIFT project, declare any method superior, or claim a novel decoder.

## Why Direction B is selected

The prior work makes correlation-aware decoding an established area. The practical gap is narrower: Phase 2B already has a controlled categorical Pauli-noise simulator, paired X/Z memory data, frozen DEM candidates, and a reproducible PyMatching bank, but every candidate used PyMatching’s correlated mode. It therefore cannot tell whether the correlation-aware pass itself mattered. The saved decomposed DEMs contain hundreds of separator markers, confirming that the comparison is technically meaningful.

Turning the correlation option on and off while holding each DEM and its weights fixed creates a strong local ablation. It directly addresses a scientifically interpretable question and avoids mixing the algorithm effect with changes to noise assumptions or decoder weights. It is also feasible within existing Stim/PyMatching code and can be presented clearly to competition evaluators.

## Why C is the fallback

If the matched on/off results show negligible prediction and utility differences, do not add an adaptive selector. Reuse the already validated d=3/5/7 circuit infrastructure to map logical reliability against physical and measurement noise. Keep it explicitly as finite-distance simulation evidence; do not overstate a threshold result.

## Why A is not first

DEM approximation is documented and plausible, but Q-SHIFT lacks a strong exact or well-calibrated categorical-channel posterior reference. Phase 2C’s weaker random forest cannot establish that the approximation is what limited decoding. A is deferred pending a validated way to attribute distribution mismatch to logical-utility change.

## Claim boundary

Possible competition claim after the pilot: “In the tested Stim model, correlation-aware PyMatching [did/did not] change paired logical-observable error rates relative to the same approximate DEM decoded without correlation reweighting.” Do not claim the result generalizes to hardware, all correlation models, or adaptive decoding. A positive pilot is development evidence only and would need a new frozen independent replication before a confirmatory performance claim.

