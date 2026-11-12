# NS-0 research decision

## Decision

**Do not authorize the full adaptive-decoder study yet.** First perform a separately approved, bounded static HAMLD reproduction and paired Q-SHIFT feasibility comparison. The key open question is whether a distinct inference method creates useful decoding headroom over strong fixed/static PyMatching on this circuit at all. An adaptive layer cannot be justified until that is answered.

## Confirmed limitations and unresolved questions

1. The asserted **21.9%** error reduction has no located source artifact or reproducible calculation in the accessible, non-protected repository. The documented nearest figure is 22.727% on four nonzero Phase 4 strata only; the all-cell Phase 4 aggregate is 19.661%. Exact original claim provenance remains unresolved.
2. The Q-SHIFT circuit is d=3/five rounds and synthetic. Phase 3A injects independent-per-round spatial X bursts on qubits 8 and 10; this is not hardware calibrated, temporally persistent, leakage or coherent crosstalk noise.
3. `PAULI_CHANNEL_2` is categorical at each gate, while Stim DEM conversion for matching uses `approximate_disjoint_errors=True`. A decoder scored on samples from the original circuit is not automatically exact under this approximate DEM.
4. Historical correlation-mode studies are small/incomplete for an inference claim. The explicit API flags can be activated, but output changes and net error changes in small pilots do not establish benefit.
5. Static calibrated Phase 4C evidence did not beat pooled fixed on its aggregate and calibration provenance was incomplete. It should not be used as evidence for adaptive superiority.
6. The prior CNN evidence is robustly cautionary but not a general no-neural theorem: representation/location mattered in development, yet all reported neural variants failed to beat fixed PM; later residual approaches tied or harmed and often selected no corrections.
7. HAMLD's paper has directly relevant small surface-code circuit-level evidence, but its own README limits the expected gain where data-qubit measurement syndromes are included and says real-time decoding is not yet met. Its build/interface and DEM fidelity must be checked.
8. Ising has a relevant local-plus-global design and a public repository, but its checkpoints are access-controlled/licensed separately, training is aimed at distance/repetition lengths matching receptive fields (R=9/13 for the public surface models), and the recommended training scale is substantial.
9. No dynamic decoder study should be interpreted as “causal change-triggering helps” unless every policy sees the same past detector data, decoder updates affect only future shots, static and EWMA/trailing/periodic baselines are competitive, and delay/switch cost are measured.

## Exact local repository and file trail

Repository `realguy-beep/Q-SHIFT`, origin `https://github.com/realguy-beep/Q-SHIFT.git`, Phase 3B base commit `5c8f50d00f003f3f79a3d07e00541ad2a3378523`.

Core implementation and proposals inspected:

- `AGENTS.md`
- `outputs/qshift_advanced_research_v3a/README.md`
- `outputs/qshift_advanced_research_v3a/DEVELOPMENT_STUDY_PROTOCOL.md`
- `outputs/qshift_advanced_research_v3a/VALIDATION_REPORT.md`
- `outputs/qshift_advanced_research_v3a/PHASE3B_READINESS_REPORT.md`
- `outputs/qshift_advanced_research_v3a/finite_history_study_config.json`
- `outputs/qshift_advanced_research_v3a/qshift_estimators.py`
- `outputs/qshift_advanced_research_v3a/run_finite_history_study.py`
- `outputs/qshift_advanced_research_v3a/analyze_finite_history_study.py`
- `outputs/qshift_advanced_research_v3a/generate_templates.py`, `template_bank_v1.json`, deterministic tests, and `benchmark_results.json`
- `outputs/phase2b_pauli_bias/noise_model.py`
- `outputs/phase3a_correlated_noise_preflight/simulator.py`, `PHASE3A_FINAL_REPORT.md`
- `outputs/stage4_noise_adaptive_development_v1/STAGE4_RESULTS.md`, protocol, result/audit summary and runner
- `outputs/phase4c_strong_baselines/PHASE4C_BASELINE_SELECTION.md`, `stage2/STAGE2_RECOVERED_RESULTS.md`, `STAGE2_RECOVERED_STATISTICS.md`, `STAGE2_RECOVERED_LIMITATIONS.md`
- `outputs/qshift_v2_dev_v1/REPORT.md`
- CNN stage-1/stage-2/stage-3 result and audit documents named in `PREVIOUS_NEURAL_FAILURE_AUDIT.md`
- `outputs/neural_decoder_diagnostic/autonomous_development/experiment.py`
- `outputs/neural_decoder_diagnostic/hybrid_residual_sprint_v1/post_run_audit/FINAL_RESEARCH_REPORT_AUDITED.md`
- `outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/POSITIONAL_CNN_REPORT.md`

No Stage 5 sealed outcome file, frozen evaluation seed list or protected test archive was read. No source/history outside the listed research scope was changed.

External primary repos/papers and source URLs are listed in `DECODER_LITERATURE_REVIEW.md` and `EXTERNAL_PROJECT_RECONSTRUCTION.md`. No external code was cloned, installed or executed.

## Next recommendation

1. Obtain a provenance pointer for the 21.9% claim, or correct project-facing summaries so only the fully specified 22.727% nonzero-stratum Phase 4 development metric (and 19.661% all-condition metric) is quoted with denominator, protocol and caveat.
2. Run deterministic compatibility/build review of the pinned HAMLD code and its Stim DEM input before requesting any generated data.
3. Submit the `RECOMMENDED_DECODER_PILOT.md` for separate approval. It is a static two-condition headroom screen, not a causal/adaptive or confirmation study.
4. If and only if a decoder demonstrates stable, practically meaningful development headroom, design a new adaptive trial with prespecified causal timeline, same detector access for all policies, cost accounting, independent stream clusters, and fresh development roots. Keep Stage 5 sealed.

## Status

NS-0 source audit and literature review complete. This branch contains research documents only. No training, sampling, decoder evaluation, seed creation, protected-data access, merge, or website change occurred.
