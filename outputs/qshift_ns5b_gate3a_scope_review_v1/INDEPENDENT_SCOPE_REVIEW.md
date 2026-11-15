# Independent NS-5B Gate 3A Scope Review

**Disposition: ACCEPT WITH CORRECTIONS** for a separately authorized, bounded Gate 3A mathematical review. This is not authorization to start Gate 3A and is not acceptance of the original full Gate 3 scope. The original retrieval record must continue to say that the 48-file REQUIRED set is incomplete.

## Executive assessment

The reconciliation memorandum makes the essential distinction correctly: a missing item in an operationally REQUIRED retrieval set prevents a claim of retrieval completeness, but it does not automatically invalidate every scientific derivation that can be checked from other evidence. Conversely, showing that some algebra can be reviewed without that item does not establish that the missing `prototype.py` was scientifically irrelevant. Its REQUIRED designation rationale is not in the available record.

A narrow audit is mathematically meaningful for abstract identities and conditional statistical arguments. As currently described, however, the proposed Gate 3A is not sufficiently specified to support source-dependent certificate or model-validity conclusions. It must define independent derivations, finite deliverables, acceptance labels, and explicit exclusions. The most important boundary is to separate (i) algebraic correctness, (ii) numerical reproduction, (iii) circuit/source fidelity, (iv) statistical guarantees under conditional assumptions, and (v) decoder utility. Evidence for one does not establish the next.

The missing file blocks conclusions about that file's behavior, equivalence, and original 48-item retrieval completeness. It does not make an abstract recurrence proof, e-factor derivation, or re-computation of a saved arithmetic expression impossible. It does block a complete reconstruction of any scientific path whose only authoritative definition resides in that file. `simulator.py` is relevant and cited in NS-5A, but must remain an explicitly named source under any amended scope; it is not a substitute or evidence of equivalence.

## Evidence base and limits

1. **Reconciliation memorandum:** `outputs/qshift_ns5b_protocol_reconciliation_v1/QSHIFT_NS5B_PROTOCOL_RECONCILIATION_MEMORANDUM.md`, commit `b4d55fa23c9cc3a3664375437c74243d40cc3ddc`. It records the source pin `5c8f8391491427fab16845282a5c8c540746b145`, supervisor tree identity `61dd70d2fe670114979b36bef2d806d7abc87883`, absence of the exact Phase 3A `prototype.py` at that tree, and the proposed partial scope.
2. **Original owner mission:** local attachment `Pasted text.txt`, SHA-256 `ca7db76b9355c93bee213eb7a541e1fb192787b8ae37c05ced42698631bfde79` as recorded by the memo. It calls for independent certificate reconstruction, source-level fault-support analysis, exact-circuit/DEM analysis, e-factor and delay verification, a conservative controller specification, symbolic controller checks, novelty review, and separate A–F decisions. It is an instruction document, not a versioned frozen protocol.
3. **Gate 2C closure addendum:** `QSHIFT_GATE2C_CLOSURE_ADDENDUM.md`, SHA-256 `84ef27c15eeebbd704ce73afcf1164342f505e6d5474a5fb6ce09bdeee53fec9`. It states 47/48 paths were retrieved; the exact `outputs/phase3a_correlated_noise_preflight/prototype.py` returned 404 and was absent from the listed parent directory; no alternate was substituted; `ORIGINAL_48_FILE_RETRIEVAL_COMPLETE = FALSE`. It also limits the provenance claim: connector response-to-saved-bytes consistency was checked, but independent path/tree/type proof was not available for the 46 other retrieved files.
4. **NS-5A mathematical audit:** all citations below refer to commit `5c8f8391491427fab16845282a5c8c540746b145`. Main evidence includes `outputs/qshift_ns5a_mathematical_audit_v1/INDEPENDENT_MATHEMATICAL_AUDIT.md`, `CLAIM_EVIDENCE_MATRIX.md`, `REMAINING_BLOCKERS.md`, and `CONTROLLER_STATE_MACHINE_SPEC.md`; relevant source evidence includes `outputs/phase3a_correlated_noise_preflight/simulator.py`, `PHASE3A_FINAL_REPORT.md`, `PHASE3A_MANIFEST.json`, and the method-landscape exact-envelope, feature-expectation, DEM-transfer, delay, and recurrence records included in the NS-5A source manifest.

**Manifest availability qualification:** The actual canonical bytes/digest of the original 48-entry REQUIRED manifest were not present in the inspected Gate 2C snapshot (the snapshot contained `AGENTS.md` only) or as a separately persisted manifest in the evidence described by the memorandum. I therefore cannot independently inspect its per-path rationale or confirm each entry. This is a documentary gap, not a basis to infer that `prototype.py` was accidental. The mission, closure record, and memorandum are available and were reviewed. No sealed independent-test evidence was opened.

## Claim and dependency matrix

| Claim/check | Depends on missing `prototype.py`? | What can be established now | Gate 3A boundary / evidence still required |
|---|---|---|---|
| Original 48-file retrieval completeness | **Yes, administratively** | Closure says 47/48; the set is incomplete | Preserve `FALSE`. No narrow audit can relabel it complete. Obtain the missing exact file or a supervisor-authored manifest amendment with provenance before making any completeness claim. |
| Behavior uniquely implemented by `prototype.py`; equivalence to `simulator.py` | **Yes** | Nothing about its code behavior can be inferred from its name or absence | Exclude claims about its behavior or equivalence. Only resolve through authenticated bytes/history or a documented owner explanation and a separately authorized source comparison. |
| Abstract parity-character expectation identity | No, conditional | The derivation in `INDEPENDENT_MATHEMATICAL_AUDIT.md` is algebraically valid for independent categorical sites with correct supports | Independently rederive and state all assumptions. This proves a formula conditional on the supplied support map; it does not verify circuit semantics. |
| Five burst-pair detector signatures | Not necessarily; source provenance is the issue | NS-5A names `simulator.py`, which inserts `CORRELATED_ERROR(p) X8 X10` after each `MR` boundary and reports `(8,10),(16,18),(24,26),(32,34),(36,38)` | A static reading/source assertion is not independent proof of Stim semantics. Reconstruct mapping from the exact circuit and fault propagation independently; exclude all claims that this validates the missing prototype. |
| Exact-circuit polynomial / continuous Bernstein envelope | Not necessarily for arithmetic; potentially for model identity and source mapping | Audit describes the formula and saved bounds, but says all 468 coefficients were not independently regenerated and support mapping remains conditional | Rebuild the polynomial from independently verified fault supports and channel probabilities; recompute every rational coefficient and enclosure. Without that, classify source-to-polynomial as conditional/partial. |
| Exact circuit to approximate DEM transfer | No direct dependency, but distinct model definition | Saved nominal mean mismatch is up to `3.27e-5`; finite screen contains an alternative point outside exact envelope | Do not transfer the exact-circuit certificate. A high-alternative violation challenges alternative separation/power transfer, not by itself null validity. A separate DEM-specific null bound and alternative separation need continuous proof. |
| Edge inversion / physical burst attribution | Not inherently | The independent-edge identity is valid under its graph factorization and lower branch | It recovers an effective shared-edge probability in that model; does not identify physical cause. Analyze nuisance aliases separately. |
| Local identifiability | No for the reported numerical calculation; yes for source semantics in general | 45-by-3 finite-difference Jacobian has reported rank 3 at one point | Numerical local-rank evidence only. Not global injectivity, finite-history accuracy, or robustness to matched-mask nuisance. |
| Fixed-parameter e-factor validity | No for abstract proof; source law required to instantiate `m0` | If `E[X_t|F_(t-1)]<=m0`, `X_t∈[0,1]`, fixed `m0>0`, fixed `0<=lambda<=1`, the factor is nonnegative and conditionally mean at most one | State conditional law explicitly. A marginal mean/certificate alone does not prove conditional validity under drift/adaptation. Source-dependent envelope cannot be asserted without model correspondence. |
| One-change recurrence and threshold arithmetic | No for algebra; yes for implementation provenance if reproducing a particular source | Prior `1/[s(s+1)]` and recurrence are algebraically checkable; checkpoint-133 threshold bug was corrected in new audit | Re-derive recurrence and 1/alpha threshold; any fixed-width implementation needs overflow/rounding proof. The historical wrong predicate stays disclosed. |
| Freedman delay calculations | No for abstract inequality; exact-model assumptions required for use | A sufficient bound may follow from range, conditional drift and variance bounds | Recalculate selected values and rounding; do not call it mean/observed delay or within-circuit latency. Current audit says full numeric table was not regenerated. |
| Controller transition logic | No for logical specification | State specification describes static fallback, next-shot boundary and external reset | Can review abstract transition invariants. No runtime safety, detector model validity, repeated-switch guarantee, or decoder benefit follows. No automatic bidirectional switching. |
| Decoder utility / adaptive improvement | Not established by either source | No NS-5A result establishes LER improvement | Outside deterministic Gate 3A scope; requires a separately authorized, paired development experiment after model validity and protocol freeze. |

## Scientific purpose and scope critique

The mission's purpose is broader than “check the missing file.” It is to determine whether the NS-5A mathematical and model-validity claims are independently reproducible and sufficient to support any later controller design. Its tasks deliberately span formula reconstruction, the source-to-support map, exact categorical versus approximate DEM laws, e-factor and delay assumptions, controller logic, novelty, and distinct readiness decisions. It prohibits stochastic data generation and decoder performance evaluation.

The memo correctly notes that the mission does not expressly make each retrieval-manifest item a scientific pass criterion. But the memo cannot establish that the 48-entry designation was only administrative: the original manifest and per-entry rationale are unavailable. The defensible conclusion is narrower: **the closure record is administratively incomplete; the scientific consequences must be assigned claim by claim.** Gate 3A must not retroactively redefine the REQUIRED label or amend the original mission. It may propose a separate supervisor-approved scope that expressly excludes claims depending on the absent artifact.

The proposed Gate 3A is meaningful if it is a bounded independent derivation/reproduction of named mathematical claims. It is not sufficiently independent if it only rereads NS-5A outputs, repeats a computation using the same support table, or treats a second implementation sharing the same unverified support map as corroboration. It is not sufficiently bounded if it retains the entire original mission while silently dropping the source and novelty tasks. Before start, list each claim, method, artifact, pass/fail label, and exclusion in a short signed scope record. No source execution, tests, simulations, experiments, or Gate 3 authorization are implied by this review.

## Specific scientific objections and corrections

### 1. Operational completeness versus scientific acceptance

This distinction is correct in principle but overstated if read as a finding that the missing file is scientifically unnecessary. `REQUIRED` has an operational consequence: the approved retrieval set was not completed. Its scientific relevance is an unresolved dependency question because neither the canonical manifest rationale nor the file is available. Avoid both errors: do not declare all of Gate 3 impossible, and do not declare the file dispensable.

**Correction:** preserve `ORIGINAL_48_FILE_RETRIEVAL_COMPLETE = FALSE`; call the narrower work a new partial audit with no claim to satisfy the original retrieval scope.

### 2. Independent fault-to-detector support validation

NS-5A's character formula and direct-XOR check share the same support map, so their numerical agreement checks the algebraic implementation against itself, not whether the map matches the Stim circuit. The NS-5A report says the generator expects 40 detectors and one observable and attributes five supports to the simulator. The Phase 3A report describes a particular synthetic circuit and source; these facts are useful provenance but are not an independent semantic derivation.

Evidence adequate for a later deterministic support validation should include:

- The exact pinned noiseless/circuit instruction stream, detector declarations, observable declarations, and relevant noise insertion locations, with hashes and unambiguous circuit identity.
- A fault-by-fault table for every categorical alternative used by the certificate: source operation/site, Pauli alternative, probability expression, detector mask, observable parity, and round/boundary.
- An independent Clifford/Pauli propagation derivation from circuit semantics to detector and observable flips, checked against an independently generated deterministic reference where feasible. Deterministic single-fault insertion/propagation is not stochastic sampling, but it requires separate task authorization and must not be represented as performed in this read-only review.
- Explicit handling of measurement/reset faults, repeated records, boundary mechanisms, mutually exclusive categorical alternatives, and any cross-site dependence.
- A check that detector ordering and observable convention are those used by the feature extractor and target decoder model. The 40-detector/one-observable dimensions alone do not prove ordering or parity semantics.

If the exact missing prototype was the source that defines any of these, its absence blocks reconstruction of that source's version. The available `simulator.py` can be validated as itself; it cannot repair provenance about the other file.

### 3. Source-to-polynomial construction and continuous bounds

The Bernstein convex-hull argument is sound for a polynomial that exactly represents the declared model over the whole rectangle. It does not establish that the polynomial came from the actual circuit, that all site probabilities and supports were included, or that an omitted mechanism is absent. NS-5A explicitly says all 468 coefficients were not independently regenerated and conditions the envelope on a fixed support map and affine channel probabilities.

A meaningful independent check must (a) derive the exact categorical site law from the pinned circuit/noise source, (b) derive the parity-character products from verified supports, (c) form the statistic polynomial by a second derivation, (d) use exact rational arithmetic for the complete coefficient set and parameter-variable transforms, and (e) verify every Bernstein coefficient / endpoint and outward rounding on the full parameter boxes. Report coefficient-level diffs and an independent hash/provenance chain. Point probes or a dense parameter grid cannot replace the continuous enclosure. If any derivation stage reuses the original support map without independent semantics, label the final certificate conditional on it.

### 4. Exact categorical circuit versus approximate DEM

Keep the transfer excluded from Gate 3A's acceptance claim. The categorical circuit and Stim DEM with `decompose_errors=True, approximate_disjoint_errors=True` are different distributions. The recorded nominal feature-mean difference and finite high-alternative screen show transfer is not automatic. A point outside the exact-circuit **alternative lower envelope** means that particular separation/power claim does not carry to the DEM at that point. It does **not** logically imply that the exact-circuit **null upper bound** fails for the DEM. Null validity and alternative separation must be evaluated separately.

A separately scoped deterministic DEM analysis is defensible in principle: define the exact DEM construction and disjoint-error approximation, derive its own induced categorical/independent mechanism law (or another exact law that matches its semantics), then certify continuous null and alternative bounds over the declared region. If the DEM mechanism law includes correlations, hyperedges, or decomposed choices that violate assumed independence, the derivation must model them rather than import the circuit formula. A finite grid alone is not a guarantee. Until an independent continuous DEM null bound is available, no DEM-level e-process guarantee may be claimed. Decoder-graph compatibility is another question and neither proves nor repairs alarm validity.

### 5. E-factor, delay, recurrence, and controller results reviewable without sampling

The following can be audited deterministically without stochastic simulation:

- Nonnegativity of `L_t=1+lambda*(X_t/m0-1)` for the stated parameter range and conditional expectation under a valid conditional null envelope.
- Ville/mixture recurrence algebra, prior normalization, threshold `1/alpha`, fixed-point lower-bound direction, boundary behavior, and integer-width/overflow conditions.
- A Freedman-style *sufficient* delay inequality conditional on prespecified increment range, conditional drift/variance premises, and sustained alternative; reproduce selected arithmetic with safe outward rounding.
- Symbolic controller transitions: observations from completed shot `t` can only alter policy for `t+1`; alarm causes static fallback/abstention, not inference of a new noise parameter; external reset is required before a new trusted epoch.

These do not establish that the physical process meets the conditional null, an actual false-alarm rate, average run length, realized delay, repeated-switch safety, latency, or LER benefit. The reported `239`/`0` corrected prefix crossings are deterministic fixture counts, not error probabilities. The currently unregenerated delay table and any production fixed-point arithmetic remain separate verification gaps.

## Claim classes that must remain separate

| Evidence class | What it answers | Current state from NS-5A evidence | What it does not answer |
|---|---|---|---|
| Independent mathematical correctness | Are identities/theorems valid under stated assumptions? | Several core formulas and one-change recurrence were independently rederived in NS-5A | Whether assumptions match the actual circuit or device |
| Numerical reproduction | Do saved numeric artifacts follow from their formulas and rounding? | Some probes reviewed; 468 envelope coefficients and full delay table not independently regenerated | Model semantic correctness or statistical coverage |
| Model fidelity | Does the probability/support model represent the pinned circuit/DEM? | Source-specific synthetic mapping is asserted; independent Stim-semantic support validation remains open | Real hardware validity or decoder efficacy |
| Statistical guarantee | Does the process satisfy conditional null/alternative hypotheses and finite-horizon rules? | Conditional theorem is sound; required conditional envelopes and repeated-switch control not established for DEM/device | False alarm/delay measured in real operation |
| Decoder utility | Does the policy reduce logical error at acceptable cost? | No adaptive LER benefit established | Cannot be inferred from feature separation or e-factor alarms |

## Defensible Gate 3A boundaries

### In-scope, after explicit supervisor approval

1. Independent derivation of selected algebraic identities, including categorical parity expectations conditional on a stated support table, edge inversion assumptions, e-factor nonnegativity/conditional mean, one-change recurrence, threshold arithmetic, and selected delay inequalities.
2. Independent recomputation of selected and then all decision-critical numeric values, including rational coefficient and rounding checks, if source inputs required are available and authenticated.
3. Static/symbolic audit of `simulator.py` as the available pinned implementation, explicitly labeled and with no equivalence claim to `prototype.py`.
4. Independent source-to-support reconstruction only if exact circuit semantics are available and the work is explicitly included in the approved amended scope. If it cannot be done, source-dependent claims stay conditional.
5. Abstract controller invariants and state-transition review; no runtime/controller implementation claim.
6. A separately labeled DEM mathematical analysis only if it derives and certifies the DEM law itself; otherwise transfer remains out of scope and rejected as unsupported.

### Explicit exclusions

- Original 48-file retrieval completeness and any missing-file-specific behavior/equivalence.
- Any assumption that `simulator.py` substitutes for `prototype.py`.
- Hardware calibration, physical burst attribution, unrestricted nuisance robustness, and unmodeled correlated readout.
- Exact-to-DEM transfer absent a DEM-specific proof.
- Finite-history estimator accuracy, stochastic false-alarm/delay rates, repeated-switch guarantees, decoder LER/runtime benefit, and any experiment readiness beyond named mathematical prerequisites.
- Any sealed independent-test or Stage 5 evidence.

## Blocking corrections before Gate 3A may begin

These are scope/entry conditions, not requests to run work in this review:

1. **Supervisor-signed amendment:** explicitly authorize a *partial Gate 3A* while preserving the original mission and allowlist unchanged; state that full Gate 3 remains incomplete and retrieval is 47/48.
2. **Manifest treatment:** attach or identify the authoritative 48-path manifest and its rationale if available. If not, record that rationale as unresolved; do not represent the current summary as a verified reading of the manifest.
3. **Claim-level work plan:** list exact claims and source files, independent method, acceptance labels, numerical outputs to regenerate, and stop rules. Exclude the absent file's behavior and equivalence.
4. **Circuit-source gate:** before accepting any exact-circuit support/polynomial result, require an independent fault-propagation map tied to the pinned circuit and feature order. If the audit cannot obtain authoritative circuit semantics from permitted inputs, keep all affected claims conditional and do not report certificate validation as complete.
5. **Certificate reproducibility standard:** require full coefficient/continuous-bound rederivation or mark the affected certificate partially verified; grid checks are not acceptance criteria for a continuous proof.
6. **DEM separation:** explicitly keep exact-circuit and approximate-DEM guarantees separate. A DEM guarantee requires a separate named task with its own conditional-null proof and, separately, alternative-separation proof.
7. **Output/decision contract:** require each result to be labeled mathematical proof, independently reproduced arithmetic, source/model validation, statistical guarantee, or utility evidence; no aggregate “Gate 3 passed” label from a partial review.

## Nonblocking improvements

- Provide a canonical, immutable copy and digest of the original 48-path manifest plus its per-path reason, if it exists; preserve the old closure record and add a transparent supplement rather than editing it.
- Distinguish an audit of the currently available `simulator.py` from retrieval of missing historical source; add exact-source hashes and circuit text to any future source table.
- Recompute the complete 468-coefficient envelope and the numeric delay table using independent arithmetic with outward rounding; record reproducible equations and coefficient-level diffs.
- Report sensitivity to boundary values, parameter-box corners, fixed-point width, overflow, and late-change prior penalties.
- Keep novelty assessment targeted and claim-specific; a partial mathematical audit cannot itself establish publication novelty.

## Future work outside this scope

- Any Stim stochastic sampling, Monte Carlo, finite-history accuracy study, false-alarm/delay experiment, decoder benchmark, LER comparison, or hardware/device claim.
- Runtime controller implementation, automatic switching, repeated-switch calibration, or production deployment.
- Any Stage 5/protected/sealed evaluation access.
- Full original Gate 3 completion unless the missing REQUIRED evidence is recovered or its status is resolved by an authorized provenance amendment.

These require separate authorization and a protocol suited to their respective estimands. None is approved by this scope review.

## Supervisor decision table

| Decision item | Review finding | Supervisor action needed |
|---|---|---|
| Can the original full Gate 3 be considered complete? | **No.** 47/48 retrieval only; scientific role of absent entry unresolved | Keep original gate on HOLD unless missing evidence or formal provenance resolution is supplied |
| Can a mathematically meaningful partial Gate 3A exist? | **Yes, conditionally.** Abstract identities and selected numerical arithmetic are separable from file-specific behavior | Approve only a claim-bounded amendment with the blockers above |
| Can `simulator.py` be used? | **Potentially, as itself.** It is the source cited by NS-5A; not a proxy/equivalent for missing `prototype.py` | Name it explicitly; require independent circuit-to-feature support validation for source-dependent claims |
| Can exact-circuit certificate be accepted from saved reports alone? | **No.** Support-map semantic independence and complete coefficient regeneration are unresolved | Require independent source map and full coefficient/enclosure reconstruction or retain conditional labels |
| Can exact-circuit guarantee be transferred to approximate DEM? | **No.** No transfer theorem or DEM-specific continuous null certificate; alternative screen is not enough to decide null validity | Keep excluded; commission separate DEM derivation if needed |
| Do e-factor/recurrent identities justify adaptive switching? | **No.** Conditional theorem and one-change recursion do not supply reset/repeated-switch safety or utility | Preserve static fallback and external reset; no automatic switching |
| Is decoder utility established? | **No.** No LER or deployment evidence | Requires a later independently authorized development experiment after model/protocol gates |
| Review disposition | **ACCEPT WITH CORRECTIONS** for a proposed narrower scope; **HOLD** execution pending all entry conditions | Supervisor to decide whether to authorize the amended Gate 3A; this reviewer does not authorize it |

## Unresolved questions

1. Why was `outputs/phase3a_correlated_noise_preflight/prototype.py` marked REQUIRED, and who/what made that designation?
2. Is there a canonical original 48-entry manifest with a digest and per-file rationale outside the inspected Gate 2C snapshot and recorded documents?
3. Does the missing file define circuit behavior, a separate implementation, or only an earlier/redundant prototype? No equivalence assumption is warranted.
4. Can exact pinned circuit semantics and every categorical alternative be independently reconstructed without that file, and can that reconstruction be tied to the exact NS-5A polynomial inputs?
5. What is the authoritative exact-circuit probability law for the envelope, including all channel/site probabilities and rectangle restrictions?
6. Does any continuous DEM-specific conditional-null envelope hold? The existing high-alternative violation does not answer this.
7. Are the conditional null and alternative assumptions valid over an indefinitely monitored sequence with changing regimes? What operational horizon, alpha spending, and reset contract would apply?
8. What fixed-width, persistence, overflow, and state-corruption behavior would a real controller use?
9. What is the operational policy-relevant endpoint for any later study, and what minimum LER benefit/cost threshold would justify adaptation?

## Recommendation

**ACCEPT WITH CORRECTIONS** the *concept* of a partial, independently scoped mathematical Gate 3A, subject to the blocking entry conditions above. Do not accept the reconciliation memo as proving that `prototype.py` was merely administrative or scientifically unnecessary. Do not accept full Gate 3, certificate/source fidelity, DEM transfer, controller safety in deployment, or decoder utility on this record. Execution remains a supervisor decision and no Gate 3A is authorized by this report.

## Source references

All repository references below are pinned and should be read at the stated commit:

- Reconciliation: `outputs/qshift_ns5b_protocol_reconciliation_v1/QSHIFT_NS5B_PROTOCOL_RECONCILIATION_MEMORANDUM.md` — `b4d55fa23c9cc3a3664375437c74243d40cc3ddc`.
- NS-5A full mathematical analysis: `outputs/qshift_ns5a_mathematical_audit_v1/INDEPENDENT_MATHEMATICAL_AUDIT.md` — `5c8f8391491427fab16845282a5c8c540746b145`.
- Claim mapping: `outputs/qshift_ns5a_mathematical_audit_v1/CLAIM_EVIDENCE_MATRIX.md` — `5c8f8391491427fab16845282a5c8c540746b145`.
- Remaining mathematical/controller blockers: `outputs/qshift_ns5a_mathematical_audit_v1/REMAINING_BLOCKERS.md` — `5c8f8391491427fab16845282a5c8c540746b145`.
- Prospective controller specification: `outputs/qshift_ns5a_mathematical_audit_v1/CONTROLLER_STATE_MACHINE_SPEC.md` — `5c8f8391491427fab16845282a5c8c540746b145`.
- Exact available Phase 3A implementation: `outputs/phase3a_correlated_noise_preflight/simulator.py` — `5c8f8391491427fab16845282a5c8c540746b145`; inspect as this file only, not as the absent `prototype.py`.
- Phase 3A scope and disclosed limitations: `outputs/phase3a_correlated_noise_preflight/PHASE3A_FINAL_REPORT.md` — `5c8f8391491427fab16845282a5c8c540746b145`.
- Phase 3A source inventory: `outputs/phase3a_correlated_noise_preflight/PHASE3A_MANIFEST.json` — `5c8f8391491427fab16845282a5c8c540746b145`.
- Exact-certificate source/result records: `outputs/qshift_method_landscape_research_v1/EXACT_THREE_PARAMETER_EFACTOR_ENVELOPE.json` and `exact_three_parameter_efactor_envelope.py` — `5c8f8391491427fab16845282a5c8c540746b145`; their inclusion and hashes are recorded by `outputs/qshift_ns5a_mathematical_audit_v1/SOURCE_HASH_MANIFEST.json` at that commit.
- Gate 2C local addendum: `QSHIFT_GATE2C_CLOSURE_ADDENDUM.md`, SHA-256 `84ef27c15eeebbd704ce73afcf1164342f505e6d5474a5fb6ce09bdeee53fec9` (local evidence document, not a repository protocol).
- Original owner mission: local attachment hash `ca7db76b9355c93bee213eb7a541e1fb192787b8ae37c05ced42698631bfde79` (not a Git revision).

## Review actions and limits

This review read the pinned documents and source as text, inspected local Git/worktree metadata for the publication path, and created only this report. No source code, tests, simulations, experiments, sampling, or decoder evaluation were run. No sealed independent-test material was opened. The dirty assigned NS-5B worktree was left untouched; publication is isolated on a new branch based on the reconciliation commit. This report does not alter the owner mission, manifest, closure addendum, reconciliation memorandum, NS-5A audit, or frozen material.
