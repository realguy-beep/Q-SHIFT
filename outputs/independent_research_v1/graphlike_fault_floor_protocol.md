# Exact circuit-pattern lower bound from shortest graphlike errors

## Question

Can a minimum graphlike logical error from Stim be mapped back to mutually exclusive physical circuit fault outcomes, and does the probability of one such undetectable pattern provide a useful lower bound on optimal logical error for the aligned d3 X-biased reference cells?

## Frozen scope and method

Use the existing d3/five-round, X-memory, X-bias10, p=.003 CSS and native-XCX XZZX circuits. Call Stim `shortest_graphlike_error(ignore_ungraphlike_errors=True)`, map every returned DEM event to its physical circuit-error alternatives, and choose one maximum-probability assignment with no repeated physical noise location. Require the combined DEM detector parity to be zero and logical parity one. Enumerate the full independent circuit noise-event table and compute the exact probability of the selected physical pattern (selected outcomes at those locations, identity at every other event) and the all-identity pattern. The minimum of those two disjoint probabilities is a decoder-independent lower bound on logical error for the exact circuit noise model.

Report graphlike physical fault count, selected Pauli outcomes and probabilities, identity probability, lower bound, and ratio to the existing development LER reference. Stop if any DEM event lacks a physical realization, locations conflict, or parity validation fails. This is a single-pattern lower bound, ignores ungraphlike mechanisms by explicit flag, and is not a full-circuit logical-class posterior or a 10,000-fold impossibility proof. It uses no stochastic samples.
