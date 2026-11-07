# Representation rule clarification

This is an implementation-safety clarification to the predeclared Candidate A rule, added after the deterministic fixture run while checking PyMatching's boundary behavior. It does not alter any case, probability, score, test criterion, or decoder outcome in `CASE_PLAN.json`; none of the preregistered generated cases contains a logical-only event with zero detector flips.

The initial rule required each complete error event to have at most two detector symptoms. A targeted API check showed this condition alone is insufficient: a zero-detector event carrying `L0` is accepted by `Matching.from_detector_error_model` but creates no graph edge, so the logical-only uncertainty is not represented. Candidate A therefore also rejects any nontrivial event with zero detectors and nonzero observable parity. An event with zero detector and zero observable parity is a true no-op and may be dropped without changing P(detectors, observables).

The rule now is:

1. Compute complete event detector and observable masks by XOR across all targets and all separator groups.
2. Reject the model if any event has more than two distinct detector symptoms.
3. Reject the model if an event has no detector symptom but flips a logical observable.
4. For accepted events, preserve event probability and total parity mask; dropping only a zero-effect event is allowed.

This protects the transformation from silently erasing undetectable logical faults. The Phase 2B fragments and toy fixtures in the preregistered set contain no logical-only events, so the reported numerical results are unchanged by this clarification. The added regression test exercises the newly identified edge case.
