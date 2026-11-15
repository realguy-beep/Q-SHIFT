# Q-SHIFT NS-5B Protocol Reconciliation Memorandum

**Pinned source revision:** 5c8f8391491427fab16845282a5c8c540746b145  
**Supervisor-provided tree identity:** 61dd70d2fe670114979b36bef2d806d7abc87883  
**Disposition:** HOLD original full-scope Gate 3; propose separately scoped review only after supervisor scope decision.

## Source-document inventory and status

| Record | Classification | Identity / availability |
|---|---|---|
| Owner-supplied “NS-5B: Independent Certificate Reproduction & Safe Controller Design” attachment | Owner instruction / task scope, not a repository freeze | C:\Users\LENOVO\.codex\attachments\d796f6ef-fd01-4dd6-86c2-154410b4c0a5\Pasted text.txt; 10,888 bytes; SHA-256 ca7db76b9355c93bee213eb7a541e1fb192787b8ae37c05ced42698631bfde79. It identifies the pinned commit and defines Steps 1–8 and deliverables. |
| Original 48-path REQUIRED allowlist | Gate 2C operational retrieval authorization | Referenced in Gate 2C authorization records. No separately persisted canonical manifest bytes or digest were available in the records reviewed; no original digest is asserted here. The approved path list is preserved as historical scope and is not changed. |
| Gate 2C closure addendum | Local operational evidence record, not a repository scientific protocol | C:\Users\LENOVO\Documents\Codex\2026-11-14\QSHIFT_GATE2C_CLOSURE_ADDENDUM.md; 2,937 bytes; SHA-256 84ef27c15eeebbd704ce73afcf1164342f505e6d5474a5fb6ce09bdeee53fec9. It records 47 verified files, the prototype.py exception, provenance limits, and ORIGINAL_48_FILE_RETRIEVAL_COMPLETE = FALSE. |
| NS-5A mathematical audit reports and source manifest | Repository research evidence at the pinned revision, not the NS-5B protocol | Reviewed from the Gate 2C snapshot. Relevant paths and citations are listed below. |
| Supervisor Git Data API tree result | Supervisor-provided primary repository metadata | Tree SHA 61dd70d2fe670114979b36bef2d806d7abc87883; recursive listing count 2,485; truncated=false. The supplied result says simulator.py is present and prototype.py absent. I did not repeat the search. |

No separately versioned formal Gate 3 protocol artifact was located in the reviewed records; the owner-supplied NS-5B mission is the available specification. The mission is an instruction set, while the Gate 2C 48-path list controls retrieval scope. Neither should be silently rewritten.

## Gate 3 purpose and acceptance criteria

The mission’s scientific purpose is to determine whether the NS-5A mathematical and model-validity claims are independently reproducible and sufficient to support any later controller design. It requires claim classifications, explicit assumptions, a source-specific fault-to-detector mapping review, exact-circuit versus approximate-DEM analysis, e-factor and delay review, a conservative controller specification, deterministic symbolic controller checks, novelty assessment, and separate A–F readiness decisions. It prohibits sampling, stochastic simulation, decoder-performance evaluation, and protected-test access.

The mission establishes these work products and classifications, but it does not state that every item in the 48-path retrieval allowlist is itself a scientific pass criterion. The best-supported interpretation is that REQUIRED labels define the authorized retrieval checklist. Because the original per-file rationale was not available, this interpretation cannot establish why prototype.py was included or prove it was scientifically unnecessary. The retrieval exception remains administratively real and must remain disclosed.

## prototype.py designation and dependency analysis

The exact reason prototype.py was marked REQUIRED is **unresolved**. The NS-5B mission calls for “relevant simulator source” and independently reconstructing fault-to-detector support, but does not name this file. The available NS-5A records cite simulator.py for the burst signatures:

- outputs/qshift_ns5a_mathematical_audit_v1/INDEPENDENT_MATHEMATICAL_AUDIT.md at 5c8f8391491427fab16845282a5c8c540746b145, lines 5, 15, 19, 33, 37, 51, 55, 59. Line 15 conditions the feature-law result on correct supports and says the shared support map did not independently validate Stim semantics. Line 19 attributes the five burst-pair supports to the simulator. Line 55 distinguishes the exact categorical circuit from the approximate DEM.
- outputs/qshift_ns5a_mathematical_audit_v1/CLAIM_EVIDENCE_MATRIX.md at the pinned revision, lines 5–13. Its burst-signature evidence row names simulator.py, the categorical feature source, and the feature artifact; it does not name prototype.py.
- outputs/qshift_ns5a_mathematical_audit_v1/SOURCE_HASH_MANIFEST.json at the pinned revision, lines 713–721. Its relevant Phase 3A input entry is outputs/phase3a_correlated_noise_preflight/simulator.py; no prototype.py entry appears in the recorded source inputs.
- outputs/qshift_ns5a_mathematical_audit_v1/REMAINING_BLOCKERS.md at the pinned revision, lines 7–9, retains support-map and DEM-transfer limitations.

The supervisor-provided complete recursive tree result establishes, for this reconciliation, that the exact prototype.py path is absent at the pinned commit. A different Stage 4 prototype.py is explicitly not a substitute. The tree result does not explain why the path was listed.

The word “prototype” in outputs/qshift_ns5a_mathematical_audit_v1/CHECKPOINT_133_CORRECTION_REPORT.md at the pinned revision, line 42, refers to fixed-point recurrence arithmetic; it is not a dependency on the missing Phase 3A file.

## Gate 3 dependency matrix

| Gate 3 check | Can proceed without this exact path? | Limitation |
|---|---|---|
| Evidence inventory and retrieval completeness | No, not as originally recorded | The original 48-item REQUIRED retrieval set remains incomplete. Record the absent path and supplied tree evidence; do not claim all 48 were retrieved. |
| Inspect or reproduce behavior uniquely defined by prototype.py; compare it to another implementation | No | Its bytes and per-file rationale are unavailable. No substitution or equivalence inference is valid. |
| Independently validate fault-to-detector support from the available simulator source | Potentially, under an amended scope | simulator.py is present and is the source cited by the NS-5A audit, but this does not establish equivalence to prototype.py. Any result must identify simulator.py as the inspected implementation and exclude claims about the missing file. |
| Re-derive abstract parity, recurrence, e-factor, and checkpoint-133 arithmetic | Yes, as a separately scoped mathematical review | Such results do not validate the physical/circuit source semantics or establish that source-derived assumptions hold. The existing audit’s conditional assumptions remain. |
| Exact-circuit certificate and continuous bounds | Partially | Algebra and coefficient arithmetic may be reviewed from available artifacts, but source-to-polynomial validity and support-map correctness remain conditional unless independently tied to the declared circuit generator. |
| Exact-circuit-to-DEM transfer | Potentially, but not because of prototype.py | Existing evidence already distinguishes the models and rejects unqualified transfer. Any further claim needs an explicit DEM-specific derivation, not a file substitution. |
| Controller specification, symbolic transitions, and literature/novelty review | Yes, as scoped reviews | They can assess logic and assumptions, but cannot establish detector semantics, statistical performance, decoder benefit, or physical validity. |

## Proposed scope amendment

Keep the original mission and 48-path allowlist unchanged as historical records. If the supervisor wants useful progress before resolving the missing source’s original rationale, authorize a separately labeled Gate 3A partial review with these boundaries:

1. Re-derive algebraic and fixed-point results from the available mathematical artifacts and independently written derivations.
2. Review simulator.py as the available circuit/noise source only if the separate authorization permits source inspection; do not describe it as a replacement for prototype.py.
3. Treat circuit-support, source-to-polynomial, and DEM-transfer claims as conditional unless independently established from the reviewed source.
4. Exclude any conclusion about prototype.py-specific behavior, equivalence, or completeness of the original 48-file evidence inventory.
5. Preserve the full Gate 3 as incomplete and require a later supervisor decision before widening the scope or making source-completeness claims.

This amendment would not authorize tests, code execution, experiments, or Gate 3 itself. Those remain separate decisions.

## Final recommendation

**HOLD** the original full-scope Gate 3 and any claim that its 48-file evidence requirement is satisfied. The missing file blocks file-specific inspection and source-inventory completeness, but the current documents do not show that every mathematical review depends on it. A narrowly scoped mathematical review is defensible only after the supervisor accepts the explicit exclusions above. Do not infer that prototype.py was redundant, and do not substitute simulator.py.

No source code, research results, manifests, or worktrees were modified. No code was executed; no tests or experiments were run; no Stage 5, incident-worktree, or sealed-test material was accessed.