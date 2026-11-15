# NS-5B Gate 3A — Proposed Bounded Mathematical Review

**Status: PROPOSED AMENDMENT — NOT AUTHORIZATION TO EXECUTE**

The full Gate 3 remains **HOLD**. This document proposes a separately bounded mathematical review (Gate 3A) for supervisor approval. Writing or publishing this amendment does not authorize source retrieval beyond existing evidence, code execution, tests, simulations, sampling, decoder evaluation, or access to sealed data.

## 1. Evidence basis and boundary

- Pinned source revision: 5c8f8391491427fab16845282a5c8c540746b145.
- Reconciliation memorandum: b4d55fa23c9cc3a3664375437c74243d40cc3ddc, outputs/qshift_ns5b_protocol_reconciliation_v1/QSHIFT_NS5B_PROTOCOL_RECONCILIATION_MEMORANDUM.md.
- Independent scope review: e9b569473234094934f488a54836bc535f49aff1, outputs/qshift_ns5b_gate3a_scope_review_v1/INDEPENDENT_SCOPE_REVIEW.md.
- Relevant NS-5A record: outputs/qshift_ns5a_mathematical_audit_v1/INDEPENDENT_MATHEMATICAL_AUDIT.md, with supporting CLAIM_EVIDENCE_MATRIX.md, REMAINING_BLOCKERS.md, CONTROLLER_STATE_MACHINE_SPEC.md, and SOURCE_HASH_MANIFEST.json.
- Relevant source paths identified in those records include outputs/phase3a_correlated_noise_preflight/simulator.py and outputs/phase2b_pauli_bias/noise_model.py. No substitution of one for another is permitted.

The supervisor-provided Git Data API report for the pinned revision states that the recursive tree had 2,485 entries, was not truncated, included simulator.py, and did not include outputs/phase3a_correlated_noise_preflight/prototype.py. This is recorded supervisor evidence, not a new independent tree verification in this amendment.

Gate 2C retrieved and verified 47 of the originally approved 48 paths against connector-reported blob identities. AGENTS.md additionally matched its previously approved blob SHA-1 and SHA-256. The exact prototype.py request returned 404 and the supervisor-provided tree report says that path is absent at the pin. The original retrieval-complete flag remains FALSE. The canonical bytes and rationale for the original 48-path allowlist were not independently available in the reviewed record. Therefore the reason prototype.py was designated REQUIRED remains UNRESOLVED. This proposal neither declares it redundant nor changes the original manifest or closure record.

The 47-file snapshot is potentially sufficient for a narrower mathematical review only where each proposed claim's evidence is actually present and independently hash-verified. It does not satisfy or waive the original full Gate 3 evidence requirement. The supervisor must decide whether Gate 3A is a substantive subset or whether the missing path blocks acceptance of any claim.

## 2. Proposed objective and scientific questions

Gate 3A would independently assess mathematical claims already made in the NS-5A audit, without evaluating decoder performance or asserting that the analytic model faithfully represents the complete Stim circuit.

Questions:

1. Are the stated detector-feature and burst-signature mappings internally correct for the exact pinned source semantics, including detector IDs/order, alternatives, and observable parity?
2. Does an independent derivation reproduce the categorical parity-character polynomial and every decision-critical Bernstein coefficient and enclosure?
3. Which controller statements are mathematical consequences of explicit assumptions, and which depend on unverified source-model transfer or implementation behavior?
4. What claims remain conditional, numerical-only, or unverified after those checks?

Gate 3A excludes experimental performance, accuracy, logical-error-rate benefit, physical attribution, and any inference about sealed independent-test results.

## 3. Review status vocabulary

Assign one status to every claim and subclaim:

- **PASS** — the specified criterion is met from the authorized, pinned evidence with an independently checkable derivation.
- **FAIL** — evidence contradicts the claim or the derivation fails its acceptance criterion.
- **CONDITIONAL** — the result holds only under explicitly stated assumptions; enumerate them.
- **UNVERIFIED** — required source, proof, independent reproduction, or provenance is unavailable.

A missing artifact is not a PASS, and a numerical agreement is not proof of model fidelity.

## 4. Independently reviewable mathematical claims

The claim identifiers below are the unit of review. Exact source paths and hashes must be recorded in the eventual evidence manifest before execution. If a source path cannot be established from the authorized 47-file snapshot and committed records, mark dependent claims UNVERIFIED and stop that subtask; do not search for substitutes.

### C1 — Circuit identity, detector ordering, and fault-to-detector semantics

**Question.** Do the declared circuit identity, detector coordinates/order, single-location fault alternatives, detector supports, and observable parity agree with the pinned circuit/noise construction?

**Evidence named in the current record.** outputs/phase3a_correlated_noise_preflight/simulator.py; outputs/phase2b_pauli_bias/noise_model.py; NS-5A source hash manifest and mathematical audit. The absent prototype.py is not replaced.

**Method.** Independently derive detector responses from the declared stabilizer/circuit semantics using a separate symbolic Pauli/Clifford propagation or algebraic derivation. Build a table keyed by physical fault location and categorical alternative, with detector IDs and observable parity. Independently derive detector coordinate/order fingerprints from the pinned circuit declaration. Compare all entries, including no-event and logical-effect cases. A second computation that merely imports or reuses the same support table is not independent.

**Assumptions.** The identified circuit is the exact pinned circuit; detector and observable conventions are interpreted as documented; symbolic propagation follows the same measurement/reset conventions. These are explicit assumptions, not inferred metadata.

**Acceptance.** Every declared alternative is accounted for exactly once; detector supports and observable parity match an independent derivation; detector ID order and coordinate mapping are unambiguous; circuit/source hashes match the pinned evidence.

**Artifacts.** Source identity table; independently derived fault table; detector-order/coordinate table; observable-parity table; derivation notes; per-input hashes.

**Stop/fail.** Missing circuit source/identity, unresolved ordering, any unexplained mismatch, or inability to establish independent derivation => FAIL for a contradicted mapping, otherwise UNVERIFIED. Do not proceed to distributional calculations that depend on the unresolved mapping.

### C2 — Categorical parity-character and detector-moment identity

**Question.** Does the categorical independent-location model imply the stated parity-character expression and detector moments?

**Method.** Re-derive from the declared mutually exclusive alternatives at each location. For parity set A, independently derive
chi(A) = product over j of sum over o p[j,o] times (-1) raised to |A intersect S[j,o]|,
where S[j,o] is the detector support for alternative o at location j. Derive moments from these characters under the stated encoding, and independently enumerate small hand-checkable cases.

**Assumptions.** Location-level categorical alternatives are mutually exclusive; locations are independent under this analytic model; probabilities are valid and sum to one; supports from C1 are correct.

**Acceptance.** Algebraic derivation and hand cases agree exactly, including empty support and zero-probability alternatives. No source implementation is used as its own oracle.

**Artifacts.** Symbolic derivation, hand-case table, assumption list, and exact source/support identities.

**Stop/fail.** C1 unresolved or probability/alternative semantics unavailable => UNVERIFIED; a counterexample under the declared assumptions => FAIL.

### C3 — Five spatial-burst signatures

**Question.** Are the five source-declared paired detector signatures derived correctly from the pinned simulator?

**Evidence named.** outputs/phase3a_correlated_noise_preflight/simulator.py; the NS-5A audit reports pairs (8,10), (16,18), (24,26), (32,34), (36,38).

**Method.** Re-derive each event pattern from the exact burst injection locations and detector definitions; record absent detector events as zeros and preserve detector ordering. Check observable parity separately. Do not infer equivalence to any missing prototype.

**Assumptions.** The source-defined burst mechanism and circuit mapping are the object of review; findings are source-specific.

**Acceptance.** All five signatures and observable parities match an independent derivation and the source's declared indexing. The result must be labeled simulator-specific, not universal physical behavior.

**Artifacts.** Five-row location/alternative-to-signature table and derivation/hash record.

**Stop/fail.** Source location or detector semantics unavailable => UNVERIFIED; any mismatch => FAIL for that signature and all dependent claims.

### C4 — Edge-moment inversion

**Question.** Does the stated inversion recover the intended categorical parameters from the specified edge moments under its assumptions?

**Evidence.** NS-5A reports reference published_edge_moment_inversion_audit.py, but its repository-relative path and presence in the verified snapshot are not established here.

**Method.** First establish the exact source/proof path through the existing authorized snapshot. If unavailable, do not search or guess; mark C4 UNVERIFIED. If separately authorized evidence supplies it, independently derive the inversion and verify symbolic substitution and domain constraints.

**Assumptions.** Required edge moments are correctly mapped; denominator/domain restrictions and probability constraints hold.

**Acceptance.** Exact symbolic forward-substitution recovers all stated moments and the parameter domain is stated.

**Artifacts.** Source identity, derivation, domain conditions, exact substitution record.

**Stop/fail.** Missing exact path or formula => UNVERIFIED. Gate 3A does not authorize additional retrieval.

### C5 — Local identifiability

**Question.** Is the reported local rank result valid for the specified 45-feature mean map and parameter point/domain?

**Method.** Independently reconstruct the 45-feature map from C1/C2; calculate exact symbolic rank if tractable, otherwise use documented high-precision/numerical rank with conditioning and threshold sensitivity. Distinguish exact rank from numerical rank.

**Assumptions.** Feature map and parameterization are exactly as declared; local rank does not establish global identifiability or decoder utility.

**Acceptance.** Feature ordering, Jacobian, parameter point, arithmetic precision, rank method, singular values/conditioning, and sensitivity are all recorded. A numerical rank is labeled numerical, not exact.

**Artifacts.** Feature/Jacobian definition, calculation transcript, precision and threshold sensitivity.

**Stop/fail.** Missing parameterization or feature map => UNVERIFIED; unstable rank across justified precision/threshold range => CONDITIONAL or UNVERIFIED, never exact PASS.

### C6 — Exact categorical polynomial reconstruction

**Question.** Can the exact polynomial used for the categorical moment bound be independently reconstructed from the source-defined model?

**Method.** Rebuild from C1/C2 and the mathematical definitions, using exact rational arithmetic. Do not import the original polynomial generator as the derivation oracle. Record the coefficient basis/order, substitutions, normalization, and every rational coefficient. Compare to the published expression only after independent derivation.

**Assumptions.** C1 mapping, C2 independence/categorical semantics, parameter domain, and target event are correct.

**Acceptance.** Exact rational coefficient equality for the complete polynomial; independent derivation is auditable; all variable ordering and domains are explicit.

**Artifacts.** Derivation, canonical coefficient serialization, exact comparison record, input hashes.

**Stop/fail.** Missing source semantics or incomplete coefficient list => UNVERIFIED; any unexplained coefficient mismatch => FAIL.

### C7 — Decision-critical Bernstein coefficients and continuous enclosures

**Question.** Are all 468 decision-critical Bernstein coefficients and the claimed box-wide bounds correct?

**Method.** Independently reconstruct each coefficient exactly as a rational number from the polynomial and declared box/subdivision. Verify degree, basis, indexing, box endpoints, subdivision, and coefficient-to-cell mapping. Independently calculate continuous enclosures from Bernstein convex-hull bounds for every cell; report extrema, margins, and cells controlling each decision. Grid sampling may be diagnostic only and cannot replace the enclosure.

**Assumptions.** C6 polynomial, parameter box, Bernstein theorem conditions, and any subdivision are correct.

**Acceptance.** All 468 coefficients are present and exact; independent values match; every decision-critical cell has a valid enclosure and margin; no omission or post hoc box change.

**Artifacts.** Machine-readable 468-entry rational table, independent checker output, cell map, enclosure table, source/input hashes.

**Stop/fail.** Any coefficient absent, inexact, mismatched, or any claimed bound unsupported by a complete enclosure => FAIL for the affected bound, not silently rounded or waived.

### C8 — E-factor / supermartingale claim

**Question.** Is the claimed process an e-factor/e-process under the stated filtration and conditional null?

**Method.** State the filtration, predictable quantities, conditional null, and prove the conditional expectation bound step by step. Test boundary cases algebraically. Separate validity of the derived factor from whether the simulator/physical process satisfies the conditional null.

**Assumptions.** The required conditional-mean or conditional-distribution premise holds at every step, not merely marginally; adaptivity/measurability conditions hold.

**Acceptance.** A complete proof from explicit assumptions, including nonnegativity/integrability and conditional expectation bound, with the source of each premise identified. The result is conditional; it does not certify real data or the Stim/DEM process without a separate transfer proof.

**Artifacts.** Filtration table, proof, assumption-to-evidence table, boundary-case checks.

**Stop/fail.** Missing conditional premise or invalid inequality => FAIL for theorem as stated; if premise is only assumed => CONDITIONAL, not empirical validation.

### C9 — Recurrence, one-change guarantee, prior and threshold

**Question.** Do the stated recurrence and one-change/false-alarm-style bounds follow from the exact recurrence and assumptions?

**Method.** Independently derive recurrence algebra, initialization, threshold crossing, change-point indexing, optional-stopping/anytime argument if invoked, and dependence on prior pi, threshold 1/alpha, and checkpoints. Reconcile the documented checkpoint-133 correction without changing historical records.

**Assumptions.** The e-process assumptions in C8 hold; recurrence indexing and filtration are as stated.

**Acceptance.** Exact symbolic recurrence matches the declared algorithm; every indexing boundary and prior constraint is explicit; no marginal-only argument is presented as conditional validity. Reproduce deterministic sequence counts only as sequence counts, not as a false-alarm rate.

**Artifacts.** Recurrence derivation, boundary table, checkpoint-133 reconciliation, proof dependency graph.

**Stop/fail.** C8 invalid or indexing mismatch => FAIL/CONDITIONAL as appropriate; unresolved checkpoint semantics => UNVERIFIED.

### C10 — Fixed-point numerical implementation bounds

**Question.** Are the fixed-point lower bounds and integer-width/overflow claims correct?

**Method.** Independently bound rounding error over the declared operation sequence; verify signedness, intermediate width, saturation/wrap behavior, division and threshold comparisons; derive worst-case values symbolically. No executable runtime test is authorized by this proposal.

**Assumptions.** Implementation arithmetic model and operation sequence are exactly documented.

**Acceptance.** Every intermediate is within a proved range; rounding error bound is complete and conservative; comparisons preserve the stated implication.

**Artifacts.** Operation/width table, symbolic bound derivation, endpoint cases.

**Stop/fail.** Missing exact arithmetic specification or any overflow/rounding gap => UNVERIFIED or FAIL. Runtime behavior remains unverified without separately authorized deterministic tests.

### C11 — Delay bound

**Question.** Is the stated delay expression a valid sufficient conditional bound under its premises?

**Method.** Re-derive the inequality from the stated increments and assumptions; identify exact probability model and direction of each inequality. Distinguish a deterministic/conditional sufficient upper bound from expected or observed latency.

**Assumptions.** The required conditional drift, bounded increment, and parameter premises hold. No claim about actual false-alarm rates or mean detection delay follows from the formula alone.

**Acceptance.** Algebra and premise dependency are explicit; label only the proven bound. No interpretation as measured or expected latency absent separate proof/data.

**Artifacts.** Derivation, premise table, units and boundary checks.

**Stop/fail.** Missing premise or invalid inequality => FAIL for claimed theorem; unverified process transfer => CONDITIONAL.

### C12 — Symbolic controller boundary

**Question.** What controller behavior follows from the written state-machine/selection specification alone?

**Evidence.** outputs/qshift_ns5a_mathematical_audit_v1/CONTROLLER_STATE_MACHINE_SPEC.md; relevant exact implementation source identity must be separately established before any implementation claim.

**Method.** Model the written state machine symbolically over a finite abstract state space, including first block, previous-block-only selection, fixed fallback, dwell/hysteresis, reset, and every edge case in the specification. Report reachable states and invariants.

**Assumptions.** The written specification is the system being assessed. Do not claim implementation equivalence unless exact implementation source and a separate conformance check are available.

**Acceptance.** State/transition model and explored boundary cases are complete for the stated abstraction; any invariant is explicitly scoped to that abstraction.

**Artifacts.** Transition table, invariants, state-space/boundary coverage record.

**Stop/fail.** Missing specification detail => CONDITIONAL/UNVERIFIED; no code-level causal or deployment claim follows from this task.

## 5. Separate scientific validity layers

For each claim, report these five axes independently; do not collapse them into a single scientific PASS:

1. **Arithmetic correctness** — exact symbolic/algebraic derivation and exact-rational coefficient values.
2. **Numerical reproduction** — independently reproduced numerical rank, enclosures, and stated deterministic calculations with precision/conditioning.
3. **Model fidelity** — whether the source-defined categorical mechanism matches the intended circuit; this proposal can audit pinned source semantics but does not establish physical validity.
4. **Conditional statistical validity** — whether e-factor, recurrence, optional-stopping, and delay statements hold under explicit conditional assumptions.
5. **Decoder utility** — decoder accuracy, logical-error-rate benefit, comparative performance, hardware benefit. These are excluded and must be UNVERIFIED by Gate 3A.

Also report two separate labels where relevant: (a) categorical simulator/source fidelity and (b) exact-circuit-to-DEM transfer. Gate 3A may not use an alternative-envelope violation alone as proof that a null is invalid. Exact circuit-to-DEM transfer is explicitly excluded and remains UNVERIFIED unless separately authorized and proved.

## 6. Proposed task sequence

Sequence tasks to avoid repeated work:

1. **Evidence gate:** verify only the already retrieved 47-file snapshot against its preserved per-file records; record the missing path and exact provenance limits. Do not retrieve more files. If the scope reviewer cannot access a needed exact source, mark only affected claims UNVERIFIED.
2. **Source semantics:** finish C1 and produce one canonical independent support/order/observable table. Reuse that table as evidence—not code—for downstream derivations.
3. **Algebra:** C2 and C3, then C4 only if its exact source/proof is among authorized material, then C5.
4. **Bounds:** C6 once, then C7’s complete exact 468 coefficient reconstruction and continuous enclosure.
5. **Controller math:** C8 then C9, C10, C11 and C12, clearly tracking dependencies. No execution or simulation.
6. **Independent review:** a second reviewer checks derivations from the evidence package, not by importing the first reviewer’s generator. Record disagreements and unresolved assumptions.
7. **Disposition:** each claim gets PASS/FAIL/CONDITIONAL/UNVERIFIED and axis labels; no roll-up to full Gate 3 approval. Return to supervisor for a separate decision.

If a task fails or is blocked, stop dependent tasks; do not silently narrow acceptance criteria or substitute evidence.

## 7. Acceptance criteria and evidence package

A Gate 3A proposal is complete only if the supervisor can approve a finite, bounded claim set, exact input corpus, methods, and stopping rules. If later authorized, the execution report must provide:

- Claim/evidence matrix with per-claim statuses and five validity axes.
- Exact source/provenance manifest for all inputs actually reviewed.
- Independent support/order/observable tables and derivations.
- Exact polynomial and all 468 rational Bernstein coefficients, with continuous box enclosures.
- Conditional proofs and dependency/assumption graph for C8–C11.
- Symbolic controller model and explicit abstraction boundary for C12.
- Failure/deviation log and independent reviewer record.
- Explicit unverified items, especially missing prototype.py, exact-circuit-to-DEM transfer, decoder utility, and any physical validity claims.

No experiment, random-event generation, sample allocation, or test execution is part of Gate 3A.

## 8. Stop conditions

Stop the affected task (and all dependent tasks) if any of the following occurs:

- Exact authorized source path is missing, hash/provenance cannot be checked, or source identity conflicts with the pin.
- Any out-of-scope filename/content, Stage 5 material, or sealed result is exposed.
- Detector/observable ordering, circuit identity, fault alternatives, or parameters are ambiguous.
- Independent support derivation cannot be made independent of the source mapping.
- A polynomial/coefficient is missing, mismatch occurs, coefficient count differs from 468, or a continuous enclosure cannot be justified.
- Conditional theorem premises are absent or only marginal claims support them.
- A requested claim would require code execution, sampling, decoder evaluation, Stage 5 access, or unapproved retrieval.
- Any required source for a claim is only presumed present; do not guess or substitute.

Failures are preserved and reported; do not repair historical records or redefine the claim after seeing the result.

## 9. Explicit exclusions and interpretation limits

Gate 3A, if separately authorized, does **not**:

- Complete the original 48-file retrieval (ORIGINAL_48_FILE_RETRIEVAL_COMPLETE = FALSE).
- Resolve why prototype.py was in the REQUIRED list or establish that it is redundant.
- Amend original manifests, Gate 2C records, or frozen protocols.
- Prove categorical source fidelity to real devices or establish exact circuit-level stochastic validity.
- Prove transfer from categorical circuit probabilities to approximate DEM behavior.
- Establish decoder accuracy, utility, LER benefit, practical superiority, hardware validation, or competition readiness.
- Inspect, access, summarize, or test against sealed independent-test outcomes.
- Authorize Gate 3A execution, full Gate 3, sampling, implementation changes, or future experiment progression.

**Decision requested from supervisor:** approve, reject, or request revision of this bounded claim set and evidence boundary. Gate 3A remains unauthorized until a separate explicit authorization.