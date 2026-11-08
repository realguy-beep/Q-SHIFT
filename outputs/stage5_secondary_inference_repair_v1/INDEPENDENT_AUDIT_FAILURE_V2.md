# Preserved second independent-audit failure

`python outputs/stage5_secondary_inference_repair_v1/audit_secondary_v2.py` stopped at `reference-CDF fingerprints differ on independent replay`.

Full one-million-draw diagnostics subsequently showed the six sorted reference arrays were byte-identical for candidate and audit implementations. The actual defect was a comparison-schema mismatch: the candidate summary stored each fingerprint as `{family, n, sha256_sorted_t}`, while v2's independently reconstructed row omitted `n`; list-of-dictionary equality therefore failed despite identical hashes.

This is preserved as a reporting/audit implementation failure. `audit_secondary_v3.py` adds the missing replicate-count field and still independently regenerates the references and all validation statistics. The v3 audit must complete and match every saved count before any readiness decision.
