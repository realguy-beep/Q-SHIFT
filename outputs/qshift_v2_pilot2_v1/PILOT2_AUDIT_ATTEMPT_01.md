# Independent audit attempt 1 (preserved)

The first post-run audit stopped before writing an audit result because its independent paired-analysis implementation attempted to XOR arrays shaped `(streams, policies, shots)` and `(streams, shots)` without explicitly broadcasting the observable array over policies. The Pilot 2 result CSV, paired outcome archive, and runtime artifacts were not changed. No new shots were generated and no Stage 5/sealed files were accessed.

Correction: explicitly broadcast observables as `y[:, None, :]` in the audit's local recomputation. This is an audit-code defect only; the pilot outputs remain unchanged.
