# Reproduce the Stage 5 n=1,210 design validation

Run from the Q-SHIFT repository root with Python 3.12, NumPy 2.5.3, and SciPy 1.18.1 (the versions used for this evidence). The design simulations do not import Stim or PyMatching.

## Verify the current frozen evidence

    python -m unittest discover -s outputs/stage5_design_validation_v3_n1210/tests -v
    python outputs/stage5_design_validation_v3_n1210/design_mc.py --preflight
    python outputs/stage5_design_validation_v3_n1210/independent_audit.py
    python -m unittest discover -s outputs/stage5_design_validation_v3_n1210/secondary_holm/tests -v
    python outputs/stage5_design_validation_v3_n1210/secondary_holm/validate_holm_repair_v1.py --preflight
    python outputs/stage5_design_validation_v3_n1210/secondary_holm/audit_holm_repair_v2.py

The independent auditors replay saved statistical streams and write their audit JSON. The preflight commands do not run a full Monte Carlo and do not sample Stim shots.

## Re-run design simulations

Primary command:

    python outputs/stage5_design_validation_v3_n1210/design_mc.py --run-design-mc

Secondary Holm command:

    python outputs/stage5_design_validation_v3_n1210/secondary_holm/validate_holm_repair_v1.py --replay-secondary-mc

Both use frozen PCG64 seeds and atomically checkpoint per-cell summaries. To reproduce without rewriting this preserved record, copy the complete versioned directory, verify copied freeze inputs, and run commands in that copy. The independent audits write reports in their working directory.

## Seed provenance

DESIGN_SEED_INVENTORY.json contains 65 design-only streams. The secondary Holm inventory contains 10 additional streams. Their scripts hash and scan an explicit allowlist of recoverable nonsealed metadata plus parent design outputs. No sealed test folders, arrays, labels, or Stage 5 evaluation files were opened. The recorded coverage cannot establish undocumented historical RNG use.

## Scope guard

These scripts synthesize root-level paired LER-difference summaries for inference design assessment. They do not import the Stage 5 sampler and cannot generate evaluation shots. The 27.225M number is only a prospective Stage 5 allocation calculation. This NO-GO package does not contain or authorize a Stage 5 sampling runner.
