# NS-4A Supervisor Review #2 — Controlled Source Audit

**Status: audit-only; no experiment authorized.** Base checkpoint: `001026ab694eb57c8ba39c2fa1480cc0ff719e87`. PR #3 and its protocol files are unchanged. This report was prepared in a fresh blobless, shallow, non-cone sparse checkout. No Stage 5 access, sampling, training, model selection, or decoder evaluation occurred during this controlled recovery.

## 1. Evidence-boundary incident

### Previously reported exposure

The available command history identifies this post-publication command as the source of the accidental exposure:

```powershell
Get-Content outputs/phase4b_replication/run_phase4b.py | Select-Object -First 130; rg -n "def build|noise_model|p_gate|p_meas|data|measurement|NOISE" outputs/phase4a_integrity_reaudit/SCIENTIFIC_RECOMPUTATION.md outputs/phase4b_replication/run_phase4b.py outputs/phase4b_replication/PHASE4A_VALIDATION.md
```

It searched two prohibited Phase 4A documents: `outputs/phase4a_integrity_reaudit/SCIENTIFIC_RECOMPUTATION.md` and `outputs/phase4b_replication/PHASE4A_VALIDATION.md`. The search output displayed a matching line from the former that contained held-out outcome numbers; this report does not repeat them. It also returned matches from the latter validation document, whose contents were outside the authorized source list. The Phase 4B runner source was also included in that command, but it was not among the two identified prohibited result/validation files.

The command occurred after the NS-4A protocol commit and push and after PR #3 was created. The PR creation record is timestamped `2026-11-13T04:40:46Z`; the command followed it in the recorded tool sequence. The precise shell execution timestamp is not available in the retained output, so the chronology is established only to that sequence.

The prior agent reported that it did not use the displayed outcomes and made no protocol, configuration, model-selection, or sampling changes afterward. After the search, the recorded activity was read-only source inspection and Git metadata/status checks. That non-use statement is a self-report, not independent proof that no cognitive influence occurred. No contents of the two files were reopened, quoted, searched, or hashed for this audit.

No other outcome-bearing file access was identified in the available incident command record. However, a previous full-tree worktree was materialized at `qshift-ns4a-supervisor-audit`; its complete materialized-file inventory was not recorded, and it was not inspected for this report. Therefore, the exact set of other files materialized there remains unknown. This is a separate workspace-isolation concern, not evidence that their contents were inspected.

**Classification:** accidental historical-outcome exposure with reported non-use, pending supervisor assessment. This report does not certify harmlessness, non-influence, or complete non-access.

## 2. Sparse workspace verification

A fresh shallow partial clone was made from `codex/ns4a-pilot-protocol` at the exact checkpoint above with `--filter=blob:none --no-checkout --depth 1`. The clone recorded `remote.origin.partialclonefilter=blob:none` and `remote.origin.promisor=true`. Non-cone sparse-checkout patterns were then set to the five authorized paths. Before any source was read, a filename-only recursive listing, excluding `.git`, showed exactly:

1. `outputs/phase4b_replication/PHASE4B_PROTOCOL.md`
2. `outputs/phase4c_strong_baselines/PHASE4C_STAGE1_PROTOCOL.md`
3. `outputs/phase4c_strong_baselines/run_stage1.py`
4. `outputs/phase2b_pauli_bias/noise_model.py`
5. `outputs/phase3a_correlated_noise_preflight/simulator.py`

The listing matched the allowlist exactly. No other file content was read from the sparse workspace. After the source review, only the two new audit outputs in this directory were added to the sparse patterns. Input hashes and byte sizes are in `NS4A_AUDIT_INPUTS.json`; no hash was computed for a prohibited file.

## 3. Source-backed noise audit

### Rate asymmetry: native Stim depolarizing generator

The Phase 4C protocol defines the three rate pairs (gate, measurement): data-heavy `(0.006, 0.001)`, nominal `(0.003, 0.003)`, and measurement-heavy `(0.001, 0.006)`. Its term “data-heavy” is shorthand for higher post-Clifford gate-noise probability relative to measurement flips: the executable builder applies `after_clifford_depolarization` at one- and two-qubit Clifford locations, not a gate restricted to data qubits. `run_stage1.py:11` implements `circuit(g,m)` with the rotated Z-memory Stim circuit, distance 3, five rounds, native DEPOLARIZE1/2 and measurement-flip channels. The protocol records 40 detectors and one observable; source assertions check those dimensions (`run_stage1.py:14-15`). Phase 4B independently documents a measurement-heavy operating point `(0.001, 0.006)` (`PHASE4B_PROTOCOL.md:3`).

This is a rate-asymmetry family. It does not vary Pauli composition or add a cross-location event. The three rates are suitable for a controlled gate-versus-measurement sensitivity study, provided “data-heavy” is explained accurately.

### Pauli-composition bias: categorical gate channels

Phase 2B defines `x_biased`, `balanced`, and `z_biased` (`noise_model.py:10,18-25`). Its builder accepts separate `gate_p` and `measurement_p` inputs and defaults both to 0.003 (`:54-66`). It replaces generated DEPOLARIZE1/2 locations with PAULI_CHANNEL_1/2 probability tables (`:69-76`). The one-qubit channel redistributes a fixed total fault mass by axis weights; the two-qubit channel assigns mutually exclusive non-identity Pauli-pair outcomes with probabilities proportional to products of the axis weights (`:28-44`). In the implemented biased regime, the dominant axis weight is 10 and each other non-identity axis weight is 1. The source explicitly distinguishes within-gate categorical pair structure from independence across different gate locations (`:113`). Thus Pauli bias changes composition; it is not data-heavy or measurement-heavy rate asymmetry.

### Spatial burst: cross-location common cause

Phase 3A wraps the Phase 2B builder and accepts the Pauli regime, gate probability, measurement probability, burst probability, and pair (`simulator.py:21,24-42`). Its default pair is data qubits X8 and X10. At every `MR` boundary it inserts one simultaneous X error on the selected pair with the supplied per-boundary probability (`:54-64`). It requires the number of MR boundaries to equal the requested rounds and asserts detector/observable counts are unchanged relative to the base circuit (`:63-68`). The code describes events as independent between rounds and spatially correlated within each event (`:31-33`). This is a synthetic channel, not a hardware-calibrated or persistent-noise model.

Because the burst wrapper passes gate, measurement, and Pauli-regime parameters through to Phase 2B, rate asymmetry, Pauli composition and burst probability can be varied together within the Phase 2B/3A categorical-channel family. That is implementation capability, not a validated or scientifically frozen factorial design. Combining Phase 4C’s native depolarizing family with the Phase 2B categorical channel would be a separate model choice, not an already-defined single generator.

### Circuit, DEM, and compatibility limits

All reviewed paths target the rotated distance-3, five-round Z-memory topology for these study conditions. Phase 2B checks 40 detectors and one observable; Phase 3A checks that adding its event does not change those dimensions. These checks establish shape compatibility, not equality of detector-order or observable-semantic fingerprints across all conditions. A later preflight must compare exact identities and ordering.

The Phase 4C runner constructs DEMs with `decompose_errors=True` and ordinary PyMatching (`run_stage1.py:15`); the Phase 2B/3A matching helper uses `decompose_errors=True, approximate_disjoint_errors=True` (`simulator.py:79-93`) and documents why categorical two-qubit channels need that approximation. Those DEM representations cannot be pooled or assumed equivalent without an explicit new construction rule. The exact BeliefMatching alias guard and all-condition DEM acceptance are not established by the five authorized files; every proposed DEM must be checked under the unchanged guard before any future sampling. No DEM was built in this audit.

`run_stage1.py` contains calls to Stim sampling in its executable body. The file was inspected as source only and was not run. No sampler, decoder, or benchmark was invoked.

## 4. Design recommendation

**Keep the rate-asymmetry study and the spatial-burst/Pauli-composition study separate.** They change different physical assumptions and currently use different channel/DEM construction paths.

| Design | Scientific question | Information parity and primary contrast | DEM / confounding risk | Resource implication |
|---|---|---|---|---|
| **A. Rate asymmetry** | Does BM change relative to a calibration-selected static PM as gate-noise and measurement-flip rates move among the three documented pairs? | Use new independent selection roots to choose one global static PM model over the three rate conditions. Compare BM and PM using the exact same selected DEM/provenance and paired detector samples. Do not provide condition labels at decode time. | Native DEPOLARIZE family is simpler, but the NS-2D/BM-compatible DEM conversion must be explicitly selected and applied identically to both arms. The “data-heavy” label must not imply data-only faults. | Three condition strata; baseline scale is smaller than a broad factorial, though roots and paired shots must still be powered from pilot-free assumptions or justified precision targets. |
| **B. Burst / Pauli composition** | Does decoding respond to axis composition, a specified spatial common-cause event, or their interaction? | Either hold balanced Pauli composition fixed and vary burst probability, or fully cross 3 Pauli regimes × 4 burst levels. Select one pooled static PM model on separate calibration roots and give BM that exact DEM/provenance; no true burst/bias labels at inference. | Categorical two-qubit DEM approximation plus injected cross-location events; each DEM needs graph/alias checks. A full 3×4 factorial is needed to estimate bias-by-burst interaction. The existing 304k proposal has only three no-burst bias cells plus balanced-burst cells, so it cannot estimate that interaction. | A 3×4 design has 12 cells, twice the six evaluation strata in the current proposal at equal roots/shots. A combined 3-rate ×3-bias ×4-burst factorial has 36 cells, six times as many; multiplicity, selection uncertainty, and alias checks also grow. |

A single factorial is technically conceivable within the Phase 2B/3A parameterized generator, but the combined 36-cell design mixes rate asymmetry, Pauli composition, and spatial dependence. It would require a larger budget and explicit interaction estimands, baseline selection rules, DEM handling, and multiplicity plan. It is not a defensible interpretation of the current 304,000-shot proposal.

## 5. Review of the 304,000-shot proposal

The published proposal remains unmodified and unauthorized. Its 64,000-shot selection allocation and 240,000-shot evaluation allocation define a finite six-condition exploratory contrast: three no-burst Pauli-composition cells plus three balanced burst-probability cells. The equal-condition mean is mathematically well-defined for exactly those six cells. It is not a rate-asymmetry study, a complete bias-by-burst factorial, or evidence of generalization to arbitrary noise.

As a bounded exploratory algorithm comparison, the allocation can be retained for that finite mixed condition set only if the supervisor accepts the mixed estimand and the missing interactions are explicit. Ten evaluation roots per condition do not establish confirmatory power without root-level variance information. The eight-configuration pooled-baseline selection grid may be unstable; its candidate ranking must be reported, and selection uncertainty cannot be inferred from the current source-only audit. The primary BM-versus-pooled-PM contrast is fair in principle only if both use the exact same selected DEM, provenance, detector order and information, and the same paired arrays. Those runtime checks remain future gates.

The accidental exposure occurred after the protocol was committed and pushed; no later protocol/configuration edit or selection change was recorded. This timing means the committed selection rule predates the search. It does not establish that subsequent interpretation was uninfluenced. Preserve the incident disclosure and require independent supervisor review before using any outcome-based claim or authorizing sampling.

## 6. Remaining blockers and next gates

1. Supervisor adjudication of the historical-outcome exposure and the separate full-tree workspace-isolation uncertainty. Do not characterize the episode as harmless or cleanly uncontaminated.
2. Supervisor choice between (A) rate asymmetry and (B) burst/Pauli composition. Do not expand or silently rewrite the 304,000-shot proposal.
3. A no-sampling deterministic compatibility check for every selected circuit/DEM: dimensions, detector ordering, observable semantics, DEM conversion flags, PyMatching graph construction, and the unchanged BeliefMatching alias guard. This audit performed none of those constructions.
4. Independent collision-screened seed inventory, source/config freeze, end-to-end resource assessment, resumability, and a separate explicit sampling authorization.
5. If a factorial is desired, predeclare interaction estimands and multiplicity before sample allocation; do not describe the current six cells as a factorial.

**Boundary confirmation for this recovery:** only the five authorized source/protocol files were read in the sparse workspace. No restricted outcomes, Phase 4A result files, Stage 5 files, sampler, training, or decoder evaluation were accessed or executed during this recovery. Research Codex remains on HOLD.
