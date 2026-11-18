# Independent research expedition log

## Checkpoint 0 — 2026-11-18

- Repository: `realguy-beep/Q-SHIFT`, published `main` revision `7cbc2e791a854e40ed4e840393fc8b4368d95ac2`.
- Original checkout `/workspace/Q-SHIFT` was clean on entry, branch `work`. Remote `main` resolves to the same revision. Claude's `codex/qshift-adaptive-robust-v1` remote branch resolves to `3a34a6abdeff0d3bb44386708f50fb645d5df686`. No checkout or modification of that branch occurred.
- Isolated worktree `/workspace/qshift-independent-research-v1`, branch `codex/qshift-independent-research-v1`, created from published main at the revision above.
- Runtime: Python 3.12.14, 5 CPU cores, 33 GiB RAM, approximately 60 GiB free workspace disk. No `nvidia-smi` executable or GPU observed.
- Available globally: NumPy 2.3.5 and SciPy 1.17.0. Stim, PyMatching, PyTorch, LDPC, Sinter, and NetworkX are not installed in the isolated worktree runtime. No packages have been installed. This means Stim-based experiment execution needs an isolated environment setup step before experiments.
- Read `AGENTS.md`, `RESEARCH_STATUS.md`, `EXPERIMENT_INDEX.md`, Phase 5D/5E findings and audits, and unified headroom audit summaries. No frozen test material was opened and no historical experiment was rerun.
- Current primary assessment from the inspected evidence: adaptive switching has not established superiority. Phase 5E ML and utility policies match pooled-fixed totals on the four short schedules, while hindsight is label-informed. Phase 4C Stage 2 has near-zero equal-regime primary effect (+0.00001556, reported p=0.6666) and missing calibration arrays. Existing source independently warns against scaling the current approach.
- No experiment has yet been run. No change to the previous cloud configuration draft or publication was made.
- Elapsed research time for this checkpoint was less than one hour. This is an interim checkpoint, not completion of the requested expedition.

## Next actions

1. Audit Stage E, Stage S, Stage 5, headroom feasibility, adaptive-robust latest materials, and relevant decoder implementations from source without opening any sealed evaluation material.
2. Complete a reference-checked literature survey and candidate matrix before selecting experiments.
3. Formalize the relative-reduction target and zero-failure sample bounds with reproducible code.
4. Decide whether an isolated CPU-only prototype is feasible and predeclare its development-only protocol before sampling.
5. Keep all files and generated outputs beneath this research directory. Do not access confirmatory data or change protected historical files.
- Existing-work audit found `outputs/research_direction_selection/` and `outputs/correlation_pilot/`. The pilot completed the exact 720,000-shot correlation-mode comparison proposed by the selection note, and its practical-effect gate failed. The raw pilot bundles are absent from this checkout. No repeat or post-hoc selector training was attempted.
- Found `outputs/correlation_mechanism_audit/FOLLOWUP_PROTOCOL.md`; its next experiment requires a non-approximated categorical DEM. My 6/6 deterministic Stim conversions failed because `PAULI_CHANNEL_2` requires the approximate-disjoint option. This closes that pretest gate without opening evaluation data.
- Existing `outputs/categorical_decoder_feasibility/` already exhaustively validates an exact decoder on small categorical toys and reports 2^609 full circuit assignments. I tested a distinct loopy categorical sum-product/Bethe prototype on those exact toys. It passed basic validation but performed poorly on one-qubit toy (LER 0.057354 vs exact MAP 0.002646, decision agreement 2/4) and matched exact MAP on the other toy (0.060000, agreement 4/4). The topology-dependent result is a negative feasibility result; no distance-3 sampling was run.
- Added tests `test_categorical_bp.py`; 2 tests passed. They validate outputs and invalid-input handling, not decoding performance.
- External literature endpoints: `export.arxiv.org` and `doi.org` failed with tunnel 403. Official Stim DEM format documentation at raw GitHub was accessible. Existing local reviews supply a detailed bibliography but cannot substitute for independent retrieval of inaccessible primary papers.
- Active hypothesis: direct categorical inference may need stronger structured elimination or correctly scoped local marginals; naive global parity BP is insufficient. Further circuit-scale testing is deferred until the method passes exact topology controls.
- Following the exact-DEM blocker, ran a deterministic Stim threshold scan at 0.001, 0.0018, 0.003, and 1.0. The 0.001 threshold failed on all biased cells due to a 0.00178571 event; all successful thresholds yielded identical per-condition DEM and matching graph hashes. No alternate model family exists at the tested probabilities, so no stochastic sensitivity comparison was launched.
- Derived an oracle selector ceiling from the paired pilot summary: for the existing off/on prediction pair, maximum label-aware relative reduction is 763/3,532 = 21.6% on that sample, leaving 2,769 shared failures. Recorded it as a descriptive development-sample constraint, not a population bound.
- Revisited the Bayes-risk definition as the correct logical-class ML benchmark. Full-circuit gap from PyMatching is still unknown because no validated full categorical posterior is available.

- Investigated tensor-network decoding with qecsim 1.0b9. Native planar MPS and MWPM returned valid codespace recoveries in a 100-shot/distance preflight. The exact untruncated d=5 MPS runtime projects beyond the 5-minute cap at the declared 5,000-shot count, so the full screen was stopped before sampling. Treat the small failure counts as timing-preflight artifacts only.

- New LDPC BP+LSD screen: all six distance-3 Phase 2B conditions accepted binary matrices built from the same approximate DEM used by the strong PyMatching comparator. On 5,000 original-circuit shots per condition, each tested LSD method produced 321 failures versus 138 for correlation-enabled PyMatching; all detector syndromes were reproduced. This is a bounded negative result, not a statement about other settings/distances.

- Tested fivefold-odds likelihood-ratio importance sampling for the fixed decoder under the approximate DEM surrogate. The weight estimator passed exhaustive three-event validation. Main and independent replicated screens showed lower estimated sampling error in 5–6/6 conditions (details in `rare_event_*.json`). This is a statistical-method result for the surrogate only; it does not reweight the original categorical circuit noise.
