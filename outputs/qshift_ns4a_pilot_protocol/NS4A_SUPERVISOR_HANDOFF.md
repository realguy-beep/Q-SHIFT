# NS-4A Supervisor Handoff

## Decision requested

Review this proposed, development-only BeliefMatching-versus-PyMatching pilot. **No sampling authorization is requested or implied by this submission.** NS-2D PR #2 remains draft and unmerged; Research Codex remains HOLD; V2.4 remains HOLD.

## Proposal at a glance

- Question: does fixed NS-3B BeliefMatching improve LER over one strong pooled-fixed PyMatching model when both use the same selected DEM and model provenance on paired samples?
- Six Z-memory d3/r5 strata: balanced, X-biased, Z-biased no-burst; balanced spatial X8/X10 burst p=0.005, 0.010, 0.015 per each of five MR boundaries.
- Selection: 8 roots × 2,000 shots in each of 4 selection conditions = 64,000 shots.
- Evaluation: 10 independent roots × 4,000 shots in each of 6 conditions = 240,000 shots.
- Total proposed unique shots: **304,000**. Ten roots × 4,000 shots/condition is an initial root-heterogeneity design, with an optimistic normal half-width near 0.00047 under hypothetical paired discordance `q=0.01` and between-root SD `tau=0.001`; neither value is measured. This is not a powered or confirmatory sample size.
- Primary: equal-condition-weighted root-paired BM-minus-pooled-fixed-PM LER difference. Root-stratified 100,000-resample interval; root sign-flip sensitivity with explicit symmetry caveat; Holm secondary family.
- Progressive gate can only recommend review of a larger development design; it cannot authorize it or establish adaptive superiority.

## Scope and evidence boundary

Prepared from the approved NS-2D checkpoint `924746ee3851f7662365e7834f998159d1b286a7` and the published NS-3B source `e4ff201e3db18a2d18e7474bef4a83542eaa3da8`. Existing NS-2D fixture is five deterministic detector rows with no labels; it is not pilot outcome evidence. The Phase 2B/3A noise source and protocols were inspected. No Stim sampler, stochastic benchmark, training, protected Stage 5 outcome file, or independent test was opened. No scientific source or historical freeze was modified.

The proposal intentionally excludes data-heavy and measurement-heavy conditions: those are not implemented in the cited Phase 2B/3A generator. The nominal-vs-burst mechanism is synthetic, location-specific, and independent across rounds. Results would not establish hardware behavior or a dynamic adaptive method.

## Blocking items before any later freeze

1. Generate concrete seeds and a complete collision audit from permitted metadata only. No numeric seed inventory has been allocated in this preparation package.
2. Resolve the dependency record discrepancy noted in the resource report.
3. Deterministically build and alias-check every proposed DEM and verify every sampling condition's detector/observable semantics. A failure blocks the design; no post-outcome exclusions.
4. Measure the actual end-to-end path, peak process RSS and disk behavior under a separately authorized disposable benchmark. Five-row timings cannot project sampler runtime or memory reliably.
5. Obtain separate explicit sampling authorization for a reviewed, hashed protocol/config/runner/auditor freeze. Current `proposed_config.json` is `NOT_AUTHORIZED_FOR_EXECUTION`.

## Preparation validation actually run

- `git diff --check` — PASS.
- PowerShell static validation parsed both JSON files, recomputed 64,000 + 240,000 = 304,000 from the allocation fields, checked all authorization flags remain false, and recomputed 15/15 reference-input and 10/10 package/handoff SHA-256 plus byte-size entries — PASS.
- No automated test suite was rerun because this checkpoint changes only protocol/report/configuration documents; prior NS-2D test counts remain historical evidence and are not claimed as freshly rerun.
- No Stim sampling, performance benchmark, training, or protected-outcome access occurred.

## Suggested review disposition

**Design review only; do not authorize sampling yet.** If the scientific scope, baseline selection rule, seed plan and resource gate are accepted, the next allowed action should be a no-sampling deterministic preflight and isolated end-to-end benchmark. That step itself must be separately authorized if it uses Stim sampling; use synthetic fixtures only until then.

## File index

- `NS4A_SCIENTIFIC_PROTOCOL.md` — scientific question, circuits, arms, partitions and boundaries.
- `NS4A_BASELINE_AUDIT.md` — source-backed baseline and noise audit.
- `NS4A_STATISTICAL_DESIGN.md` — estimand, paired inference, multiplicity and precision sensitivity.
- `NS4A_RESOURCE_ESTIMATE.md` — prior observations, scaling caveats and hard resource proposal.
- `NS4A_RISK_REGISTER.md` — risks and stop conditions.
- `NS4A_EXECUTION_GATE_CHECKLIST.md` — future approval gate; not currently passed.
- `proposed_config.json` — machine-readable, explicitly unauthorized proposal.
- `NS4A_REFERENCE_INPUTS.json` — SHA-256 inventory of the reviewed engineering and research source/protocol inputs; no outcome archives.
- `NS4A_PREPARATION_MANIFEST.json` — hashes and sizes for this package and the root review-handoff update; its own self-hash is intentionally excluded.
