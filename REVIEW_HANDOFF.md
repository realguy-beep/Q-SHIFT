# Q-SHIFT supervisor review handoff — V2 checkpoint 2

## Review state

- PR: [#1 — Strong fixed baselines for synthetic burst noise](https://github.com/realguy-beep/Q-SHIFT/pull/1), branch `codex/research-strong-baselines-v1`, base `main`.
- Supervisor review: [Review #2, comment 6796937443](https://github.com/realguy-beep/Q-SHIFT/pull/1#issuecomment-6796937443).
- Source revision reviewed: `5c3aaf48d5807a5dbdb33dc3c6a878c7e496a931`.
- V2 preparation commit: `9b72cb1140b067f6b8bde09f68c725e20f50254f`.
- Scope: V2 runner calibration-boundary test, corrected primary comparison, fairness/leakage review, collision-screened prospective inventory, review-only pre-sampling freeze, and fixture-tested independent audit tooling.
- **No V2 sampling was performed; `sampling_authorized` remains false. No sealed evaluation outcomes were accessed. PR remains unmerged.**

## Changes for Review #2

1. **Calibration integration test.** `run_development_v2.py::run_pooled_calibration_stage` now owns the collection boundary. It passes template `(probability, detector matrix)` batches only to template-profile fitting. It collects the final calibration stream as detector-only matrices, rejects archives containing observable labels, concatenates those matrices, and gives only that detector array to the pooled probability estimator. The mocked integration test exercises the runner orchestration without Stim and checks sampler arguments, fit inputs, estimator inputs, and the pooled matrix. Marker-only/ambiguous commits fail closed before sampling. The full runner still refuses before inventory or sampler access while authorization is false.
2. **Primary comparison.** The primary is now the equal-weight mean over `p > 0` of root-paired `adaptive − pooled detector-calibrated fixed PyMatching` LER. The `−0.0002` practical-benefit boundary is reported as a benchmark; this is a development study, with a descriptive root-stratified bootstrap interval and no confirmatory p-value.
3. **Safety arms.** The zero-burst no-harm selector and its validation fallback to nominal `p=0` remain intact. The safety-constrained static arm is retained as a secondary comparator. It is not substituted for the stronger pooled-fixed primary reference. Final `p=0` effects are reported for deployable arms and cannot alter choices.
4. **Fairness/leakage.** All five arms use identical evaluation detector/observable arrays. Shared independent templates are 60,000 shots. Pooled-fixed and adaptive each receive 1,200,000 final detector-calibration shots in total, but pooled-fixed estimates one global parameter while adaptive estimates per root; equal total shots do not imply equal information aggregation, estimator variance, decoder builds, or compute. The safety-static selector additionally receives 450,000 selection and 450,000 validation labeled shots; that imbalance is disclosed. No evaluation outcomes, generating labels, hidden event flags, or future samples enter deployable calibration or selection.
5. **Seed inventory.** `seed_inventory_v2_r2.json` screens 1,610 unique candidate seeds against 25 hash-verified allowlisted historical metadata sources plus 48 tracked seed inventory/manifest metadata files (29,128 large-integer tokens screened). It reports zero collisions among candidate streams and zero collisions against screened metadata. The 3,660,000-shot allocation is exact. The previous no-sample `seed_inventory_v2.json` remains preserved but is superseded and excluded from historical RNG screening. Historical coverage is explicitly incomplete: undocumented/unrecorded RNG use cannot be ruled out. Regenerating the inventory after the implementation commit produced byte-identical output.
6. **Prospective freeze and independent audit.** `PRETEST_FREEZE_V2.json` binds 20 source/configuration/protocol/test/auditor files and records `PRETEST_FREEZE_REVIEW_ONLY`, `sampling_authorized=false`, and `sampling_performed_at_freeze=false`. `audit_saved_arrays_v2.py` is separate from the runner/reporting code. It verifies committed archive hashes, metadata, detector/observable/prediction shapes, seed/root mapping, independently rebuilds the frozen decoder bank, re-decodes paired stored detector arrays, and reconstructs calibration and aggregate metrics. Fixture tests exercise its validation paths. There is no V2 run to audit yet; a real saved-array replay remains future work after separate authorization.

## Protocol summary

The candidate keeps the frozen distance-3, five-round rotated Z-memory circuit; native parameters and five burst probabilities; five paired decoder arms; 20 selection roots and 20 validation roots per condition; 120 evaluation roots per condition; 2,000 final calibration and 2,500 paired evaluation shots per root; 60,000 template, 450,000 selection, 450,000 validation, 1,200,000 final calibration, and 1,500,000 evaluation shots (3,660,000 total). No circuit, decoder, allocation, or statistical choice was changed during this checkpoint other than correcting the primary comparator to the supervisor-specified pooled-fixed baseline.

The bootstrap resamples independent roots within each nonzero condition and gives each of the four conditions equal weight. It is descriptive and conditional on these conditions; no generalization or statistical-superiority claim follows. The static selector's no-burst rule is based on selection/validation only, with no reselection on evaluation data.

## Reproduction and validation

Run from the repository root:

```powershell
python -m unittest outputs.strong_fixed_baselines_v2.test_pooled_calibration_v2 outputs.strong_fixed_baselines_v2.test_saved_array_audit_v2 outputs.strong_fixed_baselines_v2.test_seed_inventory_v2 -v
python -m unittest outputs.strong_fixed_baselines_v1.test_experiment -v
python -c "import sys;sys.path.insert(0,'outputs/strong_fixed_baselines_v1');import freeze_pretest;f=freeze_pretest.verify_freeze();print('V1 V14 records=',len(f))"
python -m outputs.strong_fixed_baselines_v2.freeze_pretest_v2
python outputs/strong_fixed_baselines_v2/build_review_manifest.py
```

Observed: V2 tests **19/19 passed**; V1 unit tests **16/16 passed**; V1 V14 freeze verified **15 records**; V2 review-only freeze verified **20 hashes**; Python compilation passed for runner, calibration helper, auditor, seed builder, freeze tools, and manifest builder. The mocked integration path did not call Stim sampling. Fixture-only auditor tests passed. The source review manifest hashes 22 current review files and 7 historical references and confirms the V1 runner still matches the V14 hash.

## Key SHA-256 values

- V2 review-only freeze: `820c1f648f7516b82d7f4b3e6dd4c3617909bc9f3c9c5d5d59371f2bf2c06531`
- Final seed inventory r2: `9f38d03d3315bf74e33e2a994446bc1e103b9e08827d8b1cc8553516fbdc72c7`
- V2 config: `8a3a3e2d8fb062852465696aed4601ae19df89708316cdaa51430d1021323860`
- V2 runner: `f55f616ea75aae12162e00b1bd4104a65924b2c3016cc910153e1e3b3564118b`
- Independent saved-array auditor: `0270033c5954e3c84c4a7e63aa26153d5a5fb5c797407591de93eccdcd99f0ec`
- Source review manifest: `e1fc7a07b30b439fd290cff60e1737215a9cee728e59eef68a1188bb3e2acbdf`

The complete 20-file freeze hash inventory is in `outputs/strong_fixed_baselines_v2/PRETEST_FREEZE_V2.json`; per-file metadata-source hashes and collision counts are in `seed_inventory_v2_r2.json` and `SEED_COLLISION_AUDIT_V2.md`.

## Preserved evidence and unresolved limits

- No tracked V1 or Stage 5 evidence path changed. The historical V1 runner remains hash-matched to V14 and its previously documented calibration deviation remains visible; V1 is not silently reclassified. Stage 5 result/outcome files were not accessed; only the specified Stage 5 seed metadata inventory and prior source metadata were used for collision screening.
- The V2 run directory is absent and no V2 arrays, estimates, predictions, or performance results exist. The independent auditor has only been validated on disposable synthetic fixtures, not a real saved run.
- Seed disjointness is verified only against recoverable, hash-verified metadata coverage; unrecorded RNG use is unknowable from these files.
- The plan is development-only and does not establish superiority, practical benefit, or confirmatory power. Resource/information differences remain as disclosed above.
- `sampling_authorized` must remain false until supervisor review and separate explicit owner authorization. Do not merge PR #1 or enable auto-merge.

## Requested next action

Supervisor review of this V2 candidate and its review-only freeze. No experiment launch is requested or authorized by this handoff.

## Supervisor Review #3 — V2.3 authorization candidate (2026-11-11)

### Review state and boundary

- PR: [#1 — Strong fixed baselines for synthetic burst noise](https://github.com/realguy-beep/Q-SHIFT/pull/1), branch `codex/research-strong-baselines-v1`.
- Supervisor Review #3: https://github.com/realguy-beep/Q-SHIFT/pull/1#issuecomment-6798467814.
- Exact reviewed starting commit: `98d7cc9ec77861e0421970ca47dfb9ea3044f5f7` (local `main` was not used or modified).
- V2.3 authorization implementation commit: `a0d80e9b458df1ebc93de27c927d83de9be23a9e` (`fix(research): add fail-closed V2 owner authorization`). This commit is on the existing research branch; handoff is committed separately after it.
- **No V2 sampling, Stage 5 sampling, sealed outcome access, real owner approval, or real run was performed.** V2 scientific config and all candidate freezes remain unauthorized (`sampling_authorized=false`, `sampling_performed=false`). PR remains open, draft, and unmerged.

### Corrections and discovered issues

1. The V2 freeze/config conflict was handled through a separate authorization layer. The original V2 scientific configuration (`8a3a3e2d8fb062852465696aed4601ae19df89708316cdaa51430d1021323860`) and freeze (`820c1f648f7516b82d7f4b3e6dd4c3617909bc9f3c9c5d5d59371f2bf2c06531`) remain unchanged and continue to require `sampling_authorized=false`. The new launcher requires an explicit local approval record bound to the exact clean commit, candidate/original freeze, config, seed inventory, frozen runner, launch/auth code, and runtime fingerprint; only after validation does it supply the original runner an in-memory config copy with the authorization guard enabled. The original runner and freeze verifier remain unchanged.
2. V2.1 exposed a real authorization-validator defect: it applied a 64-hex SHA-256 regex to the 40-hex Git commit ID. Its owner-approval path is unreachable. Its separately frozen candidate is preserved and **not repaired in place**; freeze SHA-256 is `b6274e67bd2fa413af084d12a79fd11d2c7dde55077d74e049675fe3081fbade` (15 hashes).
3. V2.2 separated commit-ID and SHA-256 validation, and its synthetic valid approval reached the mocked sampler, but the first full test run had one test assertion error: the mock was expected to receive two positional arguments although the call correctly included `shots`, `cfg`, and `labels=False`. V2.2 and its freeze remain unchanged; freeze SHA-256 is `bdd406f33b51853b1819522df7b222583649ed68b322fd57bd23c232cfb0e063` (17 hashes).
4. V2.3 carries the corrected authorization validation, fixes the mock assertion, uses separate `run_v2_3_token` and `OWNER_APPROVAL_V2_3_TOKEN.json` paths (covered by the pre-existing `*token*` ignore rule), and verifies/hashes its V2.2 predecessor. Its create-only candidate freeze is `dab92dadb57b4f1536ac0cbc2a14707ba5ac358c37594ea640f4a3e47d2206a2` (17 hashes). It is a review candidate, **not** owner authorization.
5. The auditor adapter verifies the approval receipt and execution identity and then calls the unchanged V2 saved-array auditor. The adapter has only been exercised using synthetic fixtures; no real V2 arrays exist to audit. No source-verification checks were relaxed.

### Authorization, runtime provenance, and remaining risks

- Missing/malformed/unapproved approvals fail before seed-inventory access or sampler invocation. Approval binds the precise clean Git HEAD, V2/V2.3 freezes, frozen scientific config/inventory/runner, launch and verifier hashes, and runtime fingerprint. Resume goes through the same gate; CLI exposes no authorization bypass; environment variables are ignored for authorization.
- Approval file is local-only and no real one was created. `.gitignore` uses the existing `*token*` rule for both approval and V2.3 run path. A JSON record is procedural, not a digital signature; `approved_by` is not independently authenticated by software and relies on account/filesystem access controls.
- Runtime observed during this review: Python 3.12.10; Windows 11 build 26300; Stim 1.16.0; PyMatching 2.4.0; NumPy 2.5.3. The launcher hashes these runtime versions and requires them to be installed; it does not install or pin dependencies. Any runtime/source/commit drift invalidates approval.
- Existing seed collision coverage is limited to recoverable metadata; undocumented RNG use remains unknown. Calibration/evaluation imbalance and the development-only statistical interpretation in V2 remain disclosed in the original protocol. A real-array independent audit and end-to-end runtime benchmark remain unperformed.
- The original V2, V1 and Stage 5 paths were not edited. Regression checks re-verified the V2 freeze, V1 V14 runner hash, and the Stage 5 seed-inventory metadata hash referenced by the V2 freeze. Only the Stage 5 seed metadata was checked; sealed outcomes were not accessed.

### Validation commands and results

From `C:\Users\LENOVO\Documents\QSHIFT-Research\Q-SHIFT`:

```powershell
python -m compileall -q outputs/strong_fixed_baselines_v2_3 outputs/strong_fixed_baselines_v2_1
python -m unittest outputs.strong_fixed_baselines_v2_3.test_authorization_v2_3 -v
python -m unittest outputs.strong_fixed_baselines_v2.test_pooled_calibration_v2 outputs.strong_fixed_baselines_v2.test_saved_array_audit_v2 outputs.strong_fixed_baselines_v2.test_seed_inventory_v2 -v
python -m unittest outputs.strong_fixed_baselines_v1.test_experiment -v
python -c "import sys;sys.path.insert(0,'outputs/strong_fixed_baselines_v1');import freeze_pretest;f=freeze_pretest.verify_freeze();print('V1 V14 records=',len(f))"
python -m outputs.strong_fixed_baselines_v2.freeze_pretest_v2
python -m outputs.strong_fixed_baselines_v2_1.candidate_freeze_v2_1
python -m outputs.strong_fixed_baselines_v2_2.candidate_freeze_v2_2
python -m outputs.strong_fixed_baselines_v2_3.candidate_freeze_v2_3
```

Results: V2.3 authorization/provenance tests **16/16 PASS**; original V2 regression tests **19/19 PASS**; V1 tests **16/16 PASS**; V1 V14 verified **15 records**; original V2 freeze verified **20 hashes**; V2.1 freeze **15 hashes verified**; V2.2 **17 hashes verified**; V2.3 **17 hashes verified**. Compileall passed. Synthetic positive-path test confirms the mocked sampler is invoked, checks the in-memory authorization guard is true while on-disk config and original freeze stay false, and produces no NPZ samples. Unauthorized, `--resume`, malformed, tampered, wrong-commit/hash, missing-identity, completed-run, duplicate-provenance and bypass tests are covered. V2.1's suite remains 13/15 due the commit-ID width defect; V2.2 remains 15/16 due the assertion-only argument mismatch documented above; these failures are retained as intermediate evidence and are not counted as V2.3 failures.

Precommit review staged 28 files (3,325 insertions), no file exceeded 2 MB, and the staged secret scan reported no findings. Paths were limited to `.gitignore` and versioned V2.1–V2.3 authorization candidates; no raw datasets, checkpoints, secrets, V1 results, Stage 5 outcomes or website worktree files were staged. The `.gitignore` change uses an existing broad `*token*` rule for the V2.2/V2.3 local approval and run paths without editing the V2.1-bound ignore file content after its freeze.

### Requested next action

Review V2.3 authorization and its 17-file candidate freeze. No Stage 5 work is authorized. **Do not launch V2 sampling** until a future supervisor review and separate explicit owner authorization; no real owner approval is present. Do not merge PR #1.


## Supervisor Review #4 — V2.4 duplicate-completion resume correction (2026-11-12)

### Review state and authorization boundary

- Repository: `realguy-beep/Q-SHIFT`; branch `codex/research-strong-baselines-v1`; PR [#1](https://github.com/realguy-beep/Q-SHIFT/pull/1), still open, draft and unmerged.
- Exact reviewed starting commit: `7488726c933de5e0d22909fd591914f32bf23b2c` (local branch and origin matched; initial worktree had only the new untracked V2.4 directory).
- Supervisor Review #4: https://github.com/realguy-beep/Q-SHIFT/pull/1#issuecomment-6799509232.
- **No V2 or Stage 5 sampling; no sealed outcomes; no actual owner approval; no merge.** V2.4 is a review-only authorization candidate and does not grant sampling permission.

### Blocker and correction

The V2.4 correction addresses the supervisor's exact blocker. The frozen V2 writer's actual success transition is `sampling_completed` with `sampling_complete=True` (`outputs/strong_fixed_baselines_v2/run_development_v2.py:539-544`). V2.3 checked only `complete` and `completed`, and its old regression fixture used only the artificial `completed` state. V2.3 and all its hashes remain unchanged.

V2.4 adds a strict status validator that rejects `sampling_completed`, recognized success aliases, or any `sampling_complete is True` before provenance creation/verification and before dispatch. It permits only `running`, `running_final_evaluation`, or `failed` records conforming to the actual V2 writer's schema and progress boundaries. Unknown, malformed, contradictory, expired, fully counted, or missing-status records fail closed. An incomplete resume requires `--resume`, matching existing execution identity and exact approval receipt; resume never repairs missing provenance. Fresh-run approval, frozen-hash/runtime checks, and the original in-memory authorization-guard design are retained.

The tests include a disposable fixture generated by the actual frozen V2 `write_status` function; the completed record is rejected. A second test uses a synthetic approval validated through V2.4 and confirms the rejected completed resume leaves all fixture files byte-identical, does not call provenance mutation, and does not dispatch. No Stim sampler is invoked.

### Files and review-only freeze

Added `outputs/strong_fixed_baselines_v2_4/` with:

- `run_development_v2_4.py`, `authorization_v2_4.py`, and `candidate_freeze_v2_4.py` — versioned gated launcher, schema validator, and chained freeze verifier.
- `create_pretest_freeze_v2_4.py` and `PRETEST_FREEZE_V2_4.json` — create-only review freeze.
- `audit_saved_arrays_v2_4.py` — V2.4 identity/freeze adapter over the unchanged independent V2 auditor.
- `test_authorization_v2_4.py` — 24 no-sampling tests.
- `AUTHORIZATION_PROTOCOL_V2_4.md`, `RUNTIME_PROVENANCE_V2_4.md`, and `SCIENTIFIC_INTEGRITY_REVIEW_V2_4.md`.

V2.4 freeze SHA-256: `0e3e4222e0b97c55f4cdeea0cd06dc2a2e2ba1dcb0deebd8f8e47fdceb977dfc`; it verifies 17 source/configuration/protocol/test/predecessor files. The list and individual digests are in `PRETEST_FREEZE_V2_4.json`. Key hashes include the V2.4 launcher `3036ec33c880754768eae30023fdb9a8ad679a1bbc0251bee47d88836acd93df`, authorization validator `ce86ebc4ca28d729727d7c994d56ca9b82af90137b9aa61aed13efca5d718b96`, candidate verifier `5dcb6c11cacf4add672a718bfa5ad8f70dc97a80c00948b2b827fc2948b974b4`, and test suite `7bf21ab9f2c8f48705f390ea11eea9f116010f221b130049c296bf56f5a787b8`. The supplemental scientific review note is explanatory audit evidence, authored after the freeze, and its SHA-256 is `2e3259fc31dbdf59ec36b4152a6430b9682067428764947fbd14a84a1b818193`; it is not an executable input.

Historical freezes were not changed and re-verified: V2 `820c1f648f7516b82d7f4b3e6dd4c3617909bc9f3c9c5d5d59371f2bf2c06531` (20 hashes), V2.1 `b6274e67bd2fa413af084d12a79fd11d2c7dde55077d74e049675fe3081fbade` (15), V2.2 `bdd406f33b51853b1819522df7b222583649ed68b322fd57bd23c232cfb0e063` (17), and V2.3 `dab92dadb57b4f1536ac0cbc2a14707ba5ac358c37594ea640f4a3e47d2206a2` (17). The V2 config still has `sampling_authorized=false`; V2.4 freeze records `sampling_authorized=false`, `sampling_performed=false`, and `sealed_test_access=false`. Neither `outputs/strong_fixed_baselines_v2/run_v2_4_token/` nor a V2.4 approval file exists.

### Validation performed

Runtime: Python 3.12.10; Windows 11 build 26300; Stim 1.16.0; PyMatching 2.4.0; NumPy 2.5.3.

Commands and observed results from repository root:

```powershell
python -m compileall -q outputs/strong_fixed_baselines_v2_4
python -m unittest outputs.strong_fixed_baselines_v2_4.test_authorization_v2_4 -v
python -m unittest outputs.strong_fixed_baselines_v2_3.test_authorization_v2_3 -v
python -m unittest outputs.strong_fixed_baselines_v2.test_pooled_calibration_v2 outputs.strong_fixed_baselines_v2.test_saved_array_audit_v2 outputs.strong_fixed_baselines_v2.test_seed_inventory_v2 -v
python -m unittest outputs.strong_fixed_baselines_v1.test_experiment -v
python -m unittest outputs.strong_fixed_baselines_v2_1.test_authorization_v2_1 -v
python -m unittest outputs.strong_fixed_baselines_v2_2.test_authorization_v2_2 -v
python -m outputs.strong_fixed_baselines_v2.freeze_pretest_v2
python -m outputs.strong_fixed_baselines_v2_1.candidate_freeze_v2_1
python -m outputs.strong_fixed_baselines_v2_2.candidate_freeze_v2_2
python -m outputs.strong_fixed_baselines_v2_3.candidate_freeze_v2_3
python -m outputs.strong_fixed_baselines_v2_4.candidate_freeze_v2_4
python -c "import sys;sys.path.insert(0,'outputs/strong_fixed_baselines_v1');import freeze_pretest;f=freeze_pretest.verify_freeze();print('V1 V14 records=',len(f))"
```

Observed: V2.4 tests **24/24 PASS**; V2.3 **16/16 PASS**; original V2 **19/19 PASS**; V1 **16/16 PASS**; V1 V14 **15 records verified**; original V2 freeze **20**, V2.1 **15**, V2.2 **17**, V2.3 **17**, and V2.4 **17 hashes verified**. Python compilation passed. V2.1's historical suite still has its documented **2 errors** (40-character commit ID checked as SHA-256 in its old validator); V2.2 retains its documented **1 mock-assertion failure** (the call correctly includes shots/config/`labels=False`, while the old assertion omits them). These versions and failure evidence were not changed. During V2.4 test-fixture setup, an initial mock fixture lacked the approval hash expected by the launcher; the fixture was corrected before freeze creation, then the final suite passed.

### Read-only scientific-integrity review and limitations

The separate `SCIENTIFIC_INTEGRITY_REVIEW_V2_4.md` records severity and exact source references. Source inspection found no new leakage or primary-comparator change: calibration is detector-only; evaluation arms share paired detectors/observables; only the explicitly privileged reference receives generating `p`; evaluation labels score results after selection freezes. Existing disclosed issues remain: pooled and per-root estimators aggregate equal total calibration shots differently and have different rebuild costs; the safety-static selector has 900k additional labeled selection/validation shots; recoverable historical seed screening cannot rule out undocumented RNG use; approval JSON is procedural, not signed; and no real arrays exist for an independent replay. The V2 development interval is descriptive, not confirmatory. No superiority claim is made.

V1, V2, V2.1–V2.3, and Stage 5 research files were not modified. The Stage 5 seed-inventory metadata hash was checked through the pre-existing metadata-only regression; no Stage 5 outcomes were opened. All V2.4 authorization uses synthetic temporary fixtures and mocked sampling only.

### Git and next checkpoint

- V2.4 source/freeze package commit: `e99c6dcac70194852ad70e8c0e892b631a01dde0` (`fix(research): reject completed V2 resumes in v2.4`). The handoff update is committed separately after this reviewed package.
- Final handoff commit and pushed branch head: reported in the completion response; PR head is updated by the fast-forward push.
- No force-push, merge, PR close, or auto-merge. PR #1 remains draft/open/unmerged.
- Recommendation: **NO-GO for V2 sampling at this checkpoint**. V2.4 removes the duplicate-completion resume blocker for supervisor review, but sampling still requires Supervisor Review #5 and separate explicit owner authorization. No independent real-array audit or empirical outcome exists.

## Supervisor Review — Core Upgrade v1 Corrections + NS-0 (2026-11-12)

### Review and scope

- Reviewed commit: `feb8c23715f0270e9c9ce1bb6444e414a26976bc`.
- Corrective implementation commit: `e65ccc0921f12f87a6d1ec5004a9660cdab3ef7a` on `codex/core-system-upgrade`.
- Changes are limited to `qshift_core_v1/evaluation.py`, `qshift_core_v1/controller.py`, deterministic regressions, and `outputs/core_system_upgrade_v1_1/` review/audit documentation. No sampling or training was authorized or performed.

### Requested corrections

1. `evaluate_paired` requires each decoder to return `DecoderPrediction`; it compares full prediction metadata against the registered metadata, detects metadata mutation during decode, and checks shape and runtime validity.
2. Existing schema-version-1 top-level `sample_sha256` and result fields remain. Additive identity metadata records shapes, dtypes, conventions, and decoder metadata, and explicitly disclaims provenance/leakage proof.
3. The controller accepts only nonnegative, strictly increasing block indices. `based_on_through_block` must be a nonnegative integer strictly before the current block. Invalid timing falls back to the registered fixed decoder; hysteresis and dwell remain.
4. A read-only V2.4 audit checked 17 entries: 13 expected-hash mismatches, all entries unchanged from the recorded base after newline normalization, and all authorization flags false. V2.4 remains HOLD; no historical freeze was rewritten.

### Validation

- `python -m unittest dashboard.tests.test_core_system_v1 -v` — **35 passed**.
- `python -m unittest dashboard.tests.test_dashboard.SeedAndConfigTests dashboard.tests.test_dashboard.MetricAndStorageTests -v` — **11 passed**.
- `python -m unittest dashboard.tests.test_dashboard.StructuredDecoderTests.test_qshift_stim_coordinates_make_expected_round_geometry dashboard.tests.test_dashboard.StructuredDecoderTests.test_residual_target_and_xor_correction_convention -v` — **2 passed**.
- `python -m compileall -q qshift_core_v1 dashboard\configuration.py dashboard\seed_protocol.py dashboard\simulator.py dashboard\tests\test_core_system_v1.py outputs\core_system_upgrade_v1_1` — passed.
- `node --check dashboard\static\app.js` and Python HTML parsing — passed.
- `audit_v2_4_hold.py`, `create_manifest.py`, and `verify_manifest.py` passed for the documented historical state. The historical expected-hash audit itself is explicitly **not** reported as a pass.

The deterministic PyMatching fixtures cover both explicit correlation modes and legacy Phase 2B behavior using supplied syndromes; no Stim sampler was invoked. No protected outcomes, research runs, Stage 5 evidence, or exhibition files were modified or accessed.

### Evidence hashes and handoff

- v1.1 engineering manifest SHA-256: `b70182b669fe8945fb5b2a2aca9556bef589ffd942782ff10a7d3aef223af3b7`.
- V2.4 HOLD audit JSON SHA-256: `22dccabcd80d98d0e1ba2d0c489803f4af194751fb4fc0f6ce226d3e19e16766`.
- Detailed reports: `outputs/core_system_upgrade_v1_1/CORRECTIVE_REVIEW_REPORT.md`, `V2_4_HOLD_CONFIRMATION.md`, `NS0_ENGINEERING_READINESS.md`, `UNRESOLVED_INTEGRATION_RISKS.md`, and `REPRODUCE.md`.
- NS-0 readiness is **CONDITIONAL**: flat same-order detector inputs can accept candidates; geometry-changing or history-based candidates need a separately versioned input/circuit-identity contract. No speculative architecture was implemented.
- No merge, expensive experiment, decoder-performance claim, or hardware claim.

### Next action

Stop for the next supervisor review. No research sampling is authorized.

## NS-4A — BeliefMatching development pilot protocol proposal (2026-11-13)

### Scope and status

- Prepared on branch `codex/ns4a-pilot-protocol`, based exactly on accepted NS-2D checkpoint `924746ee3851f7662365e7834f998159d1b286a7`.
- Research source reviewed: `codex/ns3b-beliefmatching-research` at `e4ff201e3db18a2d18e7474bef4a83542eaa3da8`; NS-2D PR #2 remains draft/open/unmerged.
- This is a proposed development-only protocol. `sampling_authorized=false`; no sampler, training, stochastic benchmark or protected Stage 5 outcome access occurred. V2.4 and Stage 5 restrictions remain unchanged; Research Codex remains HOLD.

### Proposal

- Compare NS-3B BeliefMatching with ordinary and correlation-enabled PyMatching plus one globally selected pooled-fixed PyMatching configuration. The primary BM/PM pair uses the same selected decomposed approximate DEM and declared noise provenance.
- Six Z-memory distance-3/five-round evaluation strata: balanced, X-biased, and Z-biased no-burst; balanced spatial X8/X10 burst at p=0.005, 0.010, and 0.015 per each of five MR boundaries. The 0.005/0.015 settings are proposed sensitivity points; the Phase 3A source accepts the range, but they have not been preflighted. Data-heavy and measurement-heavy channels are not in the inspected Phase 2B/3A generator and are excluded.
- Separate selection partition: 4 conditions × 8 roots × 2,000 shots = 64,000. Evaluation: 6 conditions × 10 independent roots × 4,000 shots = 240,000. Total proposed budget: 304,000 unique shots. This is not a power claim.
- Primary estimate: equal-condition mean of root-paired BM-minus-pooled-fixed PM LER differences. Root-stratified bootstrap interval and root-cluster sign-flip sensitivity; small-root/skew limitations are explicit. 45–50% relative reduction remains aspirational, not a gate.
- Future larger-development review gate requires integrity, favorable primary estimate/interval, and at least four of six favorable condition means. Passing only permits a new design review; it does not authorize execution or establish confirmation.

### Files added

- `outputs/qshift_ns4a_pilot_protocol/NS4A_SCIENTIFIC_PROTOCOL.md`
- `outputs/qshift_ns4a_pilot_protocol/NS4A_BASELINE_AUDIT.md`
- `outputs/qshift_ns4a_pilot_protocol/NS4A_STATISTICAL_DESIGN.md`
- `outputs/qshift_ns4a_pilot_protocol/NS4A_RESOURCE_ESTIMATE.md`
- `outputs/qshift_ns4a_pilot_protocol/NS4A_RISK_REGISTER.md`
- `outputs/qshift_ns4a_pilot_protocol/NS4A_EXECUTION_GATE_CHECKLIST.md`
- `outputs/qshift_ns4a_pilot_protocol/NS4A_SUPERVISOR_HANDOFF.md`
- `outputs/qshift_ns4a_pilot_protocol/proposed_config.json` — explicitly `NOT_AUTHORIZED_FOR_EXECUTION`, with no numeric seeds allocated.
- `outputs/qshift_ns4a_pilot_protocol/NS4A_REFERENCE_INPUTS.json` — source/protocol SHA-256 inventory.
- `outputs/qshift_ns4a_pilot_protocol/NS4A_PREPARATION_MANIFEST.json` — package hash/size inventory, excluding its own self-hash.

### Evidence and limitations

- Source review covered `outputs/phase2b_pauli_bias/noise_model.py`, `PHASE2B_PROTOCOL.md`, `NOISE_MODEL_SPECIFICATION.md`; `outputs/phase3a_correlated_noise_preflight/simulator.py`, `CORRELATED_NOISE_HYPOTHESIS.md`; and the NS-2D implementation/provenance/fixture documents and adapter source. NS-3B alias-collision and handoff materials were read from the separate research worktree. No outcome arrays were used to tune the proposal.
- Existing NS-2D fixed fixture is five manually specified detector rows, has no labels, and cannot establish accuracy, discordance, power, or scalable throughput. Timing projections are arithmetic from tiny fixtures only; full Stim end-to-end runtime and native RSS remain unknown.
- Before any later freeze: allocate and metadata-screen fresh seeds, resolve the NS-2D NumPy lock/runtime discrepancy, run deterministic all-condition DEM/order/alias checks, benchmark the actual end-to-end path under caps, and obtain separate sampling authorization. Any unsafe DEM or identity mismatch blocks this exact design; no condition may be dropped after results.
- `git diff --check` passed. A PowerShell static check parsed the proposed config and reference-input inventory, recomputed the 64,000 + 240,000 = 304,000 shot arithmetic, checked authorization flags, and verified 15/15 input and 10/10 output/handoff SHA-256 plus byte-size records. No automated suite was rerun because this checkpoint changes documents/configuration only; NS-2D deterministic test counts remain historical, not freshly rerun.

### Review state

Await supervisor review. No sampling, training, protected outcomes, merge, or automatic NS-4B progression is authorized.
