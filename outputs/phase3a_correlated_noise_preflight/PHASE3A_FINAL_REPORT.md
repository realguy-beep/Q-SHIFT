# Q-SHIFT Phase 3A — Final Report

## Decision summary

**Controller repair:** implemented as a separate, regression-tested future-run module. The frozen historical runner and verifier were not changed.  
**Correlated-noise preflight:** passed for a small synthetic spatial common-cause X-burst mechanism in a Stim rotated Z-memory circuit.  
**Production experiment:** not run. No Phase 3B samples, training jobs, or independent-test evaluations were launched.  
**Recommendation:** revise and narrow the Phase 3B framing before freezing it. The technically feasible study is a bounded test of whether a burst-inclusive DEM edge helps over the historical burst-blind PyMatching model, with a residual CNN on paired detector samples. It is not yet evidence that PyMatching's `enable_correlations` feature helps or that Q-SHIFT adapts to changing hardware noise.

## 1. Preserved history

The earlier 750K autonomous run remains recorded `completed`, with 50/50 jobs, five roots, and `independent_test_access=0`. Its 377 run-manifest entries were checked. All model/data/checkpoint/result entries match; one expected post-manifest difference exists in `controller.stdout.log`, which was empty when the run manifest was created and later contains a 2,745-byte completed-status record. This is explicitly classified and retained in the audit JSON.

The 1.665M-shot hybrid residual sprint remains `failed` in its historical `PROGRESS.json`; 30/30 job artifacts are present and all 292 hashes in its separate read-only audit manifest still match. Its original reports, selected weights, optimizer states, predictions, samples, and failure diagnosis were left unchanged. The prior independent audit remains present. The run failed because its original verifier required `completed` before the runner had committed that state. No historical run was resumed or rerun.

Seed metadata for collision screening was read from 31 historical seed-named JSON/CSV records; 6,520 unique recorded values were extracted. No sample arrays were opened by the seed scanner, and sealed independent-test path segments were skipped. No independent-test data or labels were accessed in Phase 3A.

## 2. Controller finalization repair

The new `phase3a_controller_repair/finalization_v1.py` provides a transactional pattern for future runs: progress enters `finalizing`, an evidence snapshot is saved, the independent scientific verifier runs before terminal success, evidence is rehashed, a complete manifest is atomically replaced and verified, and only then progress becomes `completed`. Interrupted finalization resumes only against an unchanged evidence snapshot. Missing or altered artifacts fail closed; successful repeated finalization is idempotent.

The 6 controller regression tests pass. They cover the `finalizing` state, completed-manifest verification, idempotent repeat, interruption recovery, corruption detection, missing files, and path escape. The original historical controller source was not edited or weakened.

## 3. Selected correlated-noise mechanism

The chosen mechanism is a **spatial common-cause X burst**: at each of five syndrome-round boundaries, a Bernoulli event can apply X simultaneously to neighboring data qubits 8 and 10. This adds dependence between distinct fault locations, which the original Phase 2B generator did not contain; its categorical two-qubit Pauli outcomes are correlated within each gate, but different gate locations are independent.

The physical motivation is shared-control/crosstalk bursts. The simulator implementation is a synthetic proxy, with independent bursts across rounds; it is not calibrated to hardware and does not represent coherent crosstalk, leakage, or temporal persistence. The preflight `p_burst=0.01` is a stress-test value, not a measured rate. Temporal persistence and correlated measurement faults are deferred because they need additional hidden-state/readout assumptions.

## 4. Fairness and DEM findings

The proposed arms are: (1) frozen Phase 2B burst-blind PyMatching; (2) burst-informed PyMatching built with the true synthetic event probability/location, labeled as a privileged reference; and (3) a residual position CNN trained on detector/observable samples and limited to detector inputs at inference. Within every condition/root, all policies must decode the same saved detector rows and be scored against the same observable labels.

The selected two-detector burst event is representable in graph matching. In a no-shot pair scan, 27/36 data-qubit pairs converted with graphlike decomposition, while 9/36 failed it with higher-order detector signatures. The selected pair adds five graphlike DEM records while preserving 40 detectors and one observable. Other pairs that fail are excluded; they are not rewritten into a different noise process.

Stim requires `approximate_disjoint_errors=True` for the Phase 2B categorical `PAULI_CHANNEL_2` mechanisms. Both matching arms use the same conversion (`decompose_errors=True, approximate_disjoint_errors=True`), and this modeling approximation is disclosed. PyMatching 2.4.0 built both correlation-option settings from the same burst-inclusive DEM. On the 256-shot smoke sample, correlation option on/off produced identical predictions; the burst-inclusive DEM differed from the frozen model on three shots. Thus the feasible matching comparator is burst-informed edge/weight modeling; the preflight does not support a claim that `enable_correlations` itself improves decoding.

## 5. Preflight outcome

The preflight passed the noiseless and zero-correlation limits, detector/observable checks, seed collision screen, paired prediction shape checks, and same-seed reproducibility. The isolated two-qubit fixture showed the intended correlation: at `p=0.1`, both measured locations flipped together in 201/2,048 shots, with zero discordances and sample correlation about 1. The burst-only distance-3 surface smoke produced nonzero detectors in 25/256 shots and no logical flips in that small sample. These are mechanism/plumbing checks, not performance findings.

The final regression commands passed 6 controller tests and 5 correlated-noise tests. The formal preflight ran in about 1.74 seconds, used 2,880 simulated shot draws including deterministic replays (2,592 distinct records), and the 36-pair DEM screen generated no shots. Four formal and four unit-test seeds were screened with zero collisions against 6,520 historical seed values and the preliminary smoke seed. Full details and hashes appear in `PREFLIGHT_RESULTS.md`, `PREFLIGHT_RESULTS.json`, `DEM_PAIR_SCREEN.json`, and `PHASE3A_MANIFEST.json`.

## 6. Phase 3B recommendation

**Recommendation: revise, then freeze only as a development feasibility study.** Use the current draft's narrow primary question: does adding the known graphlike cross-location burst event to PyMatching's DEM improve paired LER over the frozen burst-blind decoder under `p_burst=0.01`, and can a detector-only residual CNN learn corrections on the same samples? Keep the no-burst control and label burst-informed matching as privileged. Do not pitch the experiment as a test of the matching correlation toggle or as an adaptive-noise result.

The draft caps the complete new sample allocation at 300,000 shots, separates train/monitor/calibration/threshold/final-development streams, uses five roots per condition, specifies paired metrics and a conservative gate, and includes RTX 4050 resource limits. Five roots remain too few for confirmatory claims; any positive pilot would only justify designing a larger separately frozen study. The independent-test allocation remains sealed.
