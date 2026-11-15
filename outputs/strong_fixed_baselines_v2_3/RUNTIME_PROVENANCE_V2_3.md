# V2.3 runtime provenance and independent-audit handoff

The V2.3 launcher writes create-only `EXECUTION_IDENTITY_V2_3.json` and the exact local approval bytes as `OWNER_APPROVAL_RECEIPT_V2_3.json` under `outputs/strong_fixed_baselines_v2/run_v2_3_token/` before dispatch. The local launch approval itself is not included in Git.

The identity records the reviewed commit; V2.3 and original V2 freeze hashes; unchanged config, inventory, and frozen-runner hashes; launcher/verifier hashes; owner, approval interval, and receipt hash; Python, OS/platform, Stim, PyMatching, and NumPy versions; and the runtime fingerprint. Missing required dependencies fail closed; no dependency is installed by the wrapper. The approval must match the runtime fingerprint.

Identity and receipt creation is exclusive and durable-flushed. A partial or conflicting record fails closed and requires manual inspection. Resume requires matching identity and exact approval receipt. The original V2 runner retains its own lock, checkpoint and scientific logic.

The read-only V2.3 audit adapter first checks identity/receipt, approval-time validity, current reviewed source identity, V2.3 freeze, and original V2 freeze; it then calls the original V2 saved-array auditor to verify/redecode arrays and recompute results. This adapter does not weaken the underlying auditor. Since no actual V2 run exists, verification is fixture-only; there is no real-array audit or performance benchmark.

Residual limits: the approval is procedural, not a signature; owner identity relies on access controls; exact commit and environment binding means source/environment changes require a new review; seed collision screening only covers recorded metadata; V2 statistical interpretation remains development-only; and no sampling is authorized by this candidate.
