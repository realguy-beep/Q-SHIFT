# Preserved first independent-audit failure

`python outputs/stage5_secondary_inference_repair_v1/audit_secondary.py` completed its calibration replay and stopped at the assertion `reference-CDF fingerprints differ on independent replay`.

The cause was a floating-point generation-path mismatch in the zero-inflated normal reference only: the runner generated standard normals and then divided by `sqrt(.35)`, while the first auditor requested a Normal distribution with that scale applied inside NumPy. Both represent the same distribution, but the tiny rounding difference changed the byte fingerprint. The other five shape fingerprints matched. This is an audit reproducibility assertion failure, not evidence of corrupted simulation output; it is retained rather than overwritten.

The independent replay was corrected in `audit_secondary_v2.py` to use the same deterministic standard-normal variates and post-generation scaling while keeping its own sampling, statistic, CDF, Holm and Wilson implementations. The v2 audit must still reproduce all counts exactly before the method is accepted.
