# NS-4A Future Execution Gate Checklist

**Current decision: NOT AUTHORIZED.** Every item below is a requirement for a later review, not permission to run now.

## Approval and branch

- [ ] Separate owner authorization explicitly names this protocol/config revision and shot budget.
- [ ] Current branch is based on approved NS-2D checkpoint `924746ee3851f7662365e7834f998159d1b286a7`; PR #2 remains open/draft/unmerged.
- [ ] No V2.4, Stage 5, sealed evaluation, or protected outcome access is requested or enabled.
- [ ] Research Codex HOLD remains recorded.

## Protocol and provenance freeze

- [ ] Review and approve `NS4A_SCIENTIFIC_PROTOCOL.md`, `proposed_config.json`, the statistical procedure, and the progression gate.
- [ ] Resolve the proposed runtime dependency discrepancy (NS-2D report lists NumPy 2.2.6 in the pinned lock but its runtime summary also recorded 2.5.3); capture actual environment.
- [ ] Freeze runner, source, config, analysis, and environment hashes before sampling; create a new seed inventory with exact values and deterministic derivation.
- [ ] Collision-screen all recoverable development/diagnostic/template/selection/bootstrap metadata without opening protected Stage 5 outcome files. Enumerate checked metadata paths and coverage gaps.
- [ ] Confirm unique partition/condition/root seeds; no shared stateful RNG or seed reuse across selection and evaluation.

## Model and circuit validation (no sampling)

- [ ] Construct each of the four DEM grid candidates from the specified Z-memory topology; verify 40 detectors, 1 observable, detector-order hash, observable semantics and circuit structure.
- [ ] Construct the six exact sampling circuits and verify topology and ordering compatibility without invoking a sampler.
- [ ] Run the unchanged NS-3B alias-collision guard for every candidate DEM. Any rejection blocks this design; no candidate may be dropped after seeing results.
- [ ] Verify DEM conversion flags exactly (`decompose_errors=True`, `approximate_disjoint_errors=True`) and record all DEM text/content hashes.
- [ ] Verify BM and matched-PM model identities reference identical selected DEM bytes, provenance, detector ordering and observable convention.
- [ ] Verify ordinary PyMatching uses correlations disabled at both construction and decode; correlation-enabled mode sets both true.
- [ ] Validate candidate selection ordering, equal-condition weighting and deterministic ties using synthetic arrays only.

## Leakage, pairing and audit controls

- [ ] Decoder constructor/decode inputs contain detectors only; evaluation labels and generating condition IDs are inaccessible through decoder APIs.
- [ ] Selection labels are used only for the predeclared pooled-PM model/mode choice. No evaluation labels enter model/threshold selection.
- [ ] All arms get byte-identical evaluation detector batches; record hashes, shapes, dtypes, order fingerprints, and no-mutation checks.
- [ ] Saved prediction auditor recomputes errors, paired discordances, per-root totals and the primary estimate independently from saved arrays.
- [ ] Root identity/condition/seed mapping is one-to-one; interrupted batches cannot be double-counted; outputs are atomic and hashed.
- [ ] Failure injection covers missing prediction, corrupt archive, duplicate root, interruption during write and restart behavior using disposable non-evaluation fixtures.

## Resource, stop and report

- [ ] Separately authorized end-to-end benchmark includes Stim sampling, 8-way selection decoding, decoder reconstruction, BM inference, scoring and disk I/O.
- [ ] Forecast and measured peak RSS below 2 GiB; at least 1 GiB free disk reserved; 30-minute wall cap enforced.
- [ ] Monitoring, finalization and independent audit are within the deadline and resource cap.
- [ ] Stop on any seed collision, alias rejection, identity/pairing mismatch, decode failure, leakage, hash failure, non-finite/invalid output or resource breach.
- [ ] A failed or ambiguous run is preserved and reported; no automatic rerun or seed substitution.
- [ ] Report negative and inconclusive results, all six conditions, all selection candidates, root variability and exact caveats.

## Hard boundary

Do not create a live authorization token, set an authorization flag true, invoke a sampler, access Stage 5 results, run training, or automatically advance to NS-4B under this document.
