# NS-4A V2 Integrated Runner — Engineering Report

## Status and scope

This milestone integrates the already approved deterministic NS-4A V2 modules into a resumable execution system. It does **not** authorize or perform the proposed experiment. The original V2 configuration remains `PROSPECTIVE_REVISION_NOT_AUTHORIZED`, with `sampling_authorized=false` and `sampling_performed=false`. No production seed inventory or owner approval record was created. Research Codex remains on HOLD.

The runner combines the six source-approved circuit/DEM conditions, the frozen twelve-candidate PyMatching grid, global selection scoring, five paired evaluation arms, the existing statistical analyzer, and the independent saved-array auditor. It preserves the six conditions, 64,000 selection / 240,000 evaluation / 304,000 total allocation, root schedule, DEM conversion flags, candidate/arm order, estimand, and statistical methods.

## Execution and evidence controls

- The default CLI mode is a deterministic dry run. It uses source-defined formula arrays and does not call a Stim sampler.
- The only production sampler call is `StimRootSampler.sample`, reached only after a separate final execution manifest and owner authorization validate and issue a private capability.
- Candidate selection runs on selection detector arrays; labels are consumed only after all twelve predictions are returned. The global winner and selection archive hashes are atomically committed before evaluation begins. Evaluation checks the frozen winner and does not change it.
- All five evaluation arms receive copies of the same detector rows. BeliefMatching is explicit opt-in and uses the selected concrete DEM and declared assumed-noise provenance also supplied to its matched PyMatching arm.
- Each root is recorded in-flight before sampling. A returned root is archived and committed transactionally. Recovery reuses only a complete hash-verified archive and commit marker for the exact root/seed. An interrupted sampler call without committed bytes is ambiguous and is rejected; it is never silently resampled.
- The independent auditor reopens every saved array and recomputes root errors, paired discordances, the selected candidate and the primary contrast. Statistical analysis consumes those recomputed per-root counts, not runner aggregates.
- The execution manifest must bind the final source, protocol, six DEM identities, runtime, seed inventory and historical-seed screen. Execution output is fixed to `outputs/ns4a_v2_integrated_runner_v1/production_run`.
- Cross-process directory locking is exclusive and fails closed. Stale locks are not automatically stolen.

## Deterministic validation

The full test suite retains the PR #9 deterministic tests and adds runner, authorization, transaction, recovery, and fixture integration coverage. It exercises all 48 selection roots, 60 evaluation roots, 12 candidates, five arms, archive writes, immutable winner freeze, recovery validation, and independent recomputation using deterministic source-defined fixture values only.

The separate CLI rehearsal is summarized in `DETERMINISTIC_REHEARSAL_RESULTS_FINAL.json`. It exercised 48 selection roots / 64,000 fixture rows and 60 evaluation roots / 240,000 fixture rows, all 12 candidates, all five arms, 108 archives, and the independent saved-array auditor. It completed in 77.52 seconds with 169,439,232 bytes process RSS and a 258,231,742,464-byte free-disk snapshot. It recorded zero Stim sampler calls and zero generated experimental events. The 304,000 fixture rows are **not experimental shots**; their labels are not Stim outputs and their error metrics must not be interpreted scientifically. Temporary root archives were removed after the rehearsal.

Reproduce from the repository root in the approved lock-matched Python 3.12.10 environment:

```powershell
$env:PYTHONPATH = "$PWD\outputs\ns4a_v2_deterministic_implementation_v1;$PWD\outputs\ns4a_v2_integrated_runner_v1"
python -m pytest -q outputs/ns4a_v2_deterministic_implementation_v1/tests outputs/ns4a_v2_integrated_runner_v1/tests
python outputs/ns4a_v2_integrated_runner_v1/build_source_manifest.py
python outputs/ns4a_v2_integrated_runner_v1/verify_source_manifest.py
python run_ns4a_v2.py --mode dry-run
```

The dry-run command is the default and sampler-free. `--mode execute` is deliberately blocked unless a separately authorized final immutable manifest, exact seed inventory and owner approval are supplied. This report does not provide or imply those materials.

Final automated validation: `44 passed in 71.30s`, including the full-roster deterministic rehearsal. Python compilation passed for the runner entry point, all integrated modules, and all integrated tests. The focused suite had passed before the final run; the full test command above is the final suite result.

## Environment and hashes

The isolated interpreter was Python 3.12.10. All 23 pinned distributions in the NS-3B lock were checked. Stim 1.16.0, PyMatching 2.4.0 and NumPy 2.2.6 matched. BeliefMatching was verified as a clean editable checkout at upstream commit `4458c278bbec273c8c1a26411dadccc49222f8ef`, with the expected origin and reviewed core-file LF digest. `SOURCE_HASH_MANIFEST_V2.json` contains 49 explicit source/configuration entries and its verifier checks every entry. Manifest SHA-256: `897ba2e57622be52c93c2a73859ef087688aea3472f86c7feb42b91a4c1e7f49`. Frozen V2 config SHA-256: `ae1725ef867dc5cffdccd109cfe774512078916473dc7a42bab7ec1943b83726`. Lockfile SHA-256: `403d567f1063e5406fac93e9292ddb43a5524c274992b9dff29d14ddf06a3fac`. Final fixture-summary SHA-256: `ddfced78a27310792ebff55bb0f5d9f495421a24914d881983ba1dbe0a81e3d9`.

## Measured fixture resources and limitations

The fixture rehearsal records its actual elapsed time, process RSS and free-disk snapshot in its JSON summary. These measurements cover synthetic array construction, decoder construction/inference, archive/checkpoint I/O, audit and analysis in this environment. They are not a production throughput benchmark and do not establish that a real 304,000-shot run will fit within the proposed 1,800-second / 2-GiB RSS / 1-GiB free-disk-reserve limits. Real sampler throughput and complete-workload resource use remain **UNKNOWN**.

The deadline is checked at controlled stage/root boundaries and persisted across restart. A synchronous Stim native sampling call cannot be forcibly interrupted safely by this Python runner; if it exceeds the deadline, the active root may finish before the runner stops. The in-flight transaction prevents claiming or duplicating an uncommitted root. Process termination during that call remains a manual recovery blocker. Windows filesystem durability is bounded by the underlying filesystem and OS guarantees; the runner verifies bytes and hashes but cannot guarantee hardware-level persistence.

No sampling, training, statistical performance experiment, protected-result access or Stage 5 access occurred in this implementation milestone. No decoder accuracy or superiority claim is made.
