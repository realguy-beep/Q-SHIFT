# Codex Handoff Prompt — Q-SHIFT

You are continuing the Q-SHIFT research project. Read `MASTER_PROJECT_HISTORY.md`, `MASTER_RESEARCH_REPORT.md`, `METHODOLOGY_AND_LIMITATIONS.md`, `FAILED_AND_NEGATIVE_FINDINGS.md`, `CURRENT_PROJECT_STATUS.md`, `PHASE_4A_PROPOSAL.md`, `EXPERIMENT_REGISTRY.csv`, `RESULTS_MASTER.json`, and `FILE_INVENTORY.md` in this directory before acting.

## Research state

The project has not established a reproducible adaptive-decoding advantage. Repetition-code lookup policies did not beat fixed PyMatching; guarded adaptation selected fixed matching. Composition-specific PyMatching specialists failed the Phase 2 usefulness gate. A small Phase 3A X-specialist pilot advantage did not survive multiplicity adjustment and was not reproduced by the independent Phase 3B replication. Preserve all prior files and negative results.

## Required discipline

- Do not overwrite previous experiments or reports.
- Do not claim adaptive superiority, unseen-mixture generalization, or hardware integration without evidence.
- Use fixed detector/observable definitions and document every noise mechanism and probability convention.
- At inference, use detector information only; never pass logical labels or hidden noise labels unless a comparison is explicitly labeled oracle.
- Keep calibration, validation, and test seeds separate; pair decoders on the same test shots.
- Report raw and residual errors, paired differences, shot-level tests, seed-level intervals/tests, multiplicity handling, runtime, and memory limits.
- If specialists do not demonstrate credible independent benefit, stop before implementing a selector.
- Preserve failed and null findings.

## Authorization boundary

`PHASE_4A_PROPOSAL.md` is only a proposal. The user explicitly requested no new experiments during the master handoff and reserved Phase 4A for later approval. **Do not run Phase 4A or any other new experiment until the user explicitly authorizes it.** Continue only documentation, audit, or analysis that does not mutate prior research outputs when no such authorization is present.

## If Phase 4A is authorized

Create a separate `phase4a_model_adequacy` directory. Follow the frozen proposal, verify the circuit/DEM and injected-fault semantics first, then run a bounded paired specialist usefulness experiment on fresh seeds. Save configuration, source, raw shots, manifests/checksums, per-seed outcomes, aggregate statistics, figures, failed runs, and a report. Stop at the specialist gate if no credible gain appears. Never infer future permission from one approval beyond the scope the user grants.
