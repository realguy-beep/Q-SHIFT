# NS-0 Supervisor Review — response

## Decision summary

**HAMLD recommendation: FIX before a decoder comparison.** A direct comparison using Q-SHIFT's decomposed PyMatching DEM is unsafe because the pinned parser collapses Stim `^` decomposition components. The undecomposed Stim DEM is a plausible HAMLD input path, but it has not been executed end-to-end. The published Python package cannot be imported in the present environment because its compiled extension is absent; the declared Python constraint and required Bazel toolchain also do not match. No decoder results or performance claim were produced.

The four Stage 4 percentages were traced as development-only results. The 21.9% claim remains **UNVERIFIED**. A strong static PM baseline must be tuned on an independent detector-only allocation; the proposed 240,000 evaluation shots omit this tuning cost and have only feasibility-scale root counts. Analytic sensitivity shows that a 0.0002 absolute paired LER effect has approximate power from 16% to 85% over plausible paired-disagreement and root-heterogeneity scenarios; the observed Stage 4 discordance scenario gives about 49% under the historical estimated variance component.

## New documents

- `NS0_PUBLICATION_AND_PROVENANCE_AUDIT.md`
- `HAMLD_IMPLEMENTATION_COMPATIBILITY.md`
- `HAMLD_DETERMINISTIC_PREFLIGHT.md`
- `HAMLD_FAIR_BASELINE_PROTOCOL.md`
- `NS0_PILOT_POWER_AND_RESOURCE_REVIEW.md`
- `SOURCE_MANIFEST.json`

The original eight NS-0 reports are preserved as historical evidence. The new review explicitly distinguishes source inspection, deterministic DEM construction, historical development data and inference. No sampling, training, logical decoder evaluation, protected Stage 5 access, seed creation, experiment authorization, pull request or merge occurred.

## Publication status

The already completed NS-0 evidence branch was published to `origin/qshift-ns0-research` at `fef7f72c9a997c5e6d99c10b59da30dfd6de1127`. This review package is to be committed and pushed as a new commit on that same branch only after integrity checks. No main, Phase 3B, frozen V2.4, PR #1 or website worktree change is included.

## Recommendation

Do not launch the proposed 240,000-shot decoder comparison or any larger study. First build the pinned package in a compatible environment or obtain a reviewed source fix, then prove the undecomposed DEM path with deterministic zero, single-fault, boundary, observable and multi-mechanism tests; document how its DEM differs from the PyMatching input. If this gate cannot be passed, pivot to a decoder whose Stim DEM semantics and interface can be verified without changing the scientific model. No automatic pilot authorization is granted.
