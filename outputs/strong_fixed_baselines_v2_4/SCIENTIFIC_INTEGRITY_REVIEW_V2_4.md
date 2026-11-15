# V2.4 read-only scientific integrity review

**Scope:** source, frozen configuration, protocol, seed metadata and audit-code inspection only. This is not a replay of experimental arrays. No V2 sampling or Stage 5 outcome access occurred.

The V2.4 review-only candidate freeze was created before this supplemental review note. This file is explanatory audit evidence, not an execution input; its SHA-256 is recorded in the root `REVIEW_HANDOFF.md`. The candidate freeze still binds all executable V2.4 sources, tests, protocol/runtime notes, original scientific inputs, and the V2.3 predecessor records.

## Findings

| Severity | Area | Finding and evidence | Consequence |
|---|---|---|---|
| **Critical — corrected in V2.4** | Duplicate completion/resume | The frozen V2 runner writes `sampling_completed` with `sampling_complete=True` (`outputs/strong_fixed_baselines_v2/run_development_v2.py:539-544`). V2.3 checked only two other strings. V2.4 rejects the actual state, every recognized success alias, and any truthy completion flag before provenance operations or dispatch (`outputs/strong_fixed_baselines_v2_4/run_development_v2_4.py:148-149, 183-205, 324-355`). A test exercises the frozen writer and another sends a synthetic valid authorization through the launcher; the latter verifies byte-identical run files and no provenance/dispatch calls. |
| **Medium — disclosed, not changed** | Information and compute fairness | The primary is adaptive minus pooled detector-calibrated fixed PyMatching (`outputs/strong_fixed_baselines_v2/PROSPECTIVE_REPLICATION_PLAN_V2.md:7`; `experiment_config_v2.json:98-101`). Both arms receive 1.2M total detector calibration shots, but pooled estimation aggregates them while adaptive uses 2,000 shots per root and builds root-specific models. The safety-static arm additionally uses 900k labeled selection/validation shots. These differences are disclosed in `FAIRNESS_AND_LEAKAGE_REVIEW_V2.md:19-29`. | Report the information aggregation, model-build count and compute imbalance if the experiment is ever separately authorized. Equal aggregate shots do not mean equal estimator variance or compute. |
| **Medium — coverage limit** | Seed collision history | The frozen inventory records checks against recoverable metadata and discloses that undocumented RNG use cannot be excluded (`FAIRNESS_AND_LEAKAGE_REVIEW_V2.md:31-35`, `PROSPECTIVE_REPLICATION_PLAN_V2.md:31-35`). V2.4 binds the existing inventory hash; it does not expand or reinterpret historical seed coverage. | Collision screening is not proof against unrecorded historical RNG use. No seed was regenerated in this correction. |
| **Medium — pending by design** | Independent results audit | The V2.4 auditor verifies the authorization chain and delegates saved-array re-decoding/metric reconstruction to the original independent V2 auditor (`audit_saved_arrays_v2_4.py:25-29, 39-92`). The V2 audit plan specifies exact archive, seed, paired-prediction and recomputation checks (`outputs/strong_fixed_baselines_v2/INDEPENDENT_AUDIT_PLAN_V2.md:9-21`). No V2 arrays exist in this no-sampling candidate. | Fixture compatibility is verified; no claim of real-array audit or empirical result is possible until an authorized run exists. |
| **Low — procedural limitation** | Approval identity | The approval is a local editable JSON record bound to an exact commit, source/config/freeze/inventory hashes and runtime fingerprint (`authorization_v2_4.py:35-55, 98-200`). As already noted in V2.3 documentation, this is procedural authorization rather than a cryptographic signature. | It relies on owner account and filesystem controls. No approval file was created here. |
| **No new leakage found by source inspection** | Label/condition access | Profile fitting receives independent templates; pooled and adaptive deployable estimators receive detector arrays (`run_development_v2.py:279-344, 451-506`; `FAIRNESS_AND_LEAKAGE_REVIEW_V2.md:11-17`). Evaluation arms share the same detector and observable sample; the privileged arm receives the generating probability explicitly and is labeled nondeployable (`run_development_v2.py:511-523`; fairness review lines 7-17). | This is a source-level finding, not empirical confirmation. The finite synthetic burst model does not establish performance under other noise families. |

## Interpretation

The V2.4 change is confined to authorization/resume safety; it does not alter the frozen V2 generator, model grid, decoder construction, allocation, primary contrast, bootstrap, or selection criteria. The original V2 freeze and V2.1–V2.3 freezes independently verify. V2.4's review-only candidate freeze records `sampling_authorized=false`, `sampling_performed=false`, and `sealed_test_access=false`.

The corrected status gate is suitable for the next supervisor review at source and fixture-test level. It is not permission to sample. The outstanding scientific limitations above remain, and future results would require the independent saved-array audit before interpretation.

## Reproduction

From the repository root:

```powershell
python -m outputs.strong_fixed_baselines_v2_4.candidate_freeze_v2_4
python -m unittest outputs.strong_fixed_baselines_v2_4.test_authorization_v2_4 -v
```

