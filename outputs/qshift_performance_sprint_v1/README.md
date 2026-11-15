# Q-SHIFT Performance Sprint V1

This is a bounded synthetic development pilot on a distance-3 Stim surface-code circuit with a spatial pair-burst mechanism. It is separate from all frozen Stage 5 evidence and NS-5B Gate 3A. It does not establish physical-hardware performance or a deployable online controller.

Read EXPERIMENT_PROTOCOL.md before using run_pilot.py. The pilot is one-shot and refuses existing run data. Raw per-shot arrays are saved under the ignored samples directory and are intentionally not committed. Lightweight paired per-root results, audit records, configurations, hashes, and the scientific report are committed.

Environment: Python 3.12.10, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.5.3, psutil 7.2.2. No dependency installation is required by the scripts.

Commands from the repository root:

1. Run deterministic tests: python -m unittest outputs.qshift_performance_sprint_v1.tests.test_deterministic -v
2. Run sampler-free circuit/DEM preflight: python outputs/qshift_performance_sprint_v1/run_pilot.py --preflight
3. Generate the pre-sampling freeze: python outputs/qshift_performance_sprint_v1/freeze_manifest.py
4. Execute the explicitly authorized development pilot once: python outputs/qshift_performance_sprint_v1/run_pilot.py --execute-development-pilot
5. Independently reconstruct estimates and predictions: python outputs/qshift_performance_sprint_v1/audit_saved_arrays.py
6. Analyze verified saved arrays: python outputs/qshift_performance_sprint_v1/analyze.py

Raw archives are local and ignored by Git. Do not delete them after execution.