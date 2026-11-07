# Candidate A — representation-aware matching

## Rule implemented

The transformation reads each complete DEM event after XOR-aggregating its detector and logical targets. It retains the event probability and complete parity masks. It accepts an event only if its distinct detector support is at most two and it is not a logical-only event (zero detectors with nonzero logical parity). A truly zero-effect event may be discarded. If any event violates these rules, the transformation rejects the whole DEM instead of dropping or splitting the unsupported event. Accepted outputs preserve the per-event independent distribution and therefore the joint detector/observable distribution.

This is a conservative graphlike rewrite. It does not claim a new matching algorithm. It is a preprocessing guard that can make an already graphlike complete event available as a direct edge/boundary edge, with the original event probability and observable IDs.

## Tests and limits

Automated tests verify per-event probability and parity preservation, rejection of detector hyperedges and logical-only events, and exact distribution equality on small models. The graphlike two-detector toy and all 64 grid cells pass. The two alternative four-detector decompositions are rejected even though each separator grouping contains pieces that look graphlike: the *complete event* still flips four detectors. All six full Phase 2B DEMs are also rejected for the same reason.

It is not valid to erase separators when an event has more than two detector symptoms. Doing so either loses targets, silently changes the full event, or yields a graph that does not encode that event. Therefore this candidate cannot be applied to the target Phase 2B circuit as-is.
