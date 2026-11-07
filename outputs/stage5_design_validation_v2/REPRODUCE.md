# Reproduce Stage 5 design validation v2

Run from the repository root using the existing environment:

```powershell
python outputs/stage5_design_validation_v2/prepare_seed_inventory.py
python -m unittest outputs.stage5_design_validation_v2.tests.test_design_method
python -m py_compile outputs/stage5_design_validation_v2/prepare_seed_inventory.py outputs/stage5_design_validation_v2/design_simulation.py outputs/stage5_design_validation_v2/independent_audit.py outputs/stage5_design_validation_v2/freeze_candidate.py outputs/stage5_design_validation_v2/integrity.py
python outputs/stage5_design_validation_v2/freeze_candidate.py
python outputs/stage5_design_validation_v2/design_simulation.py --dry-run
python outputs/stage5_design_validation_v2/design_simulation.py
python outputs/stage5_design_validation_v2/independent_audit_repair_v1.py
```

The full statistical simulation is CPU-only and took about 790 seconds here. It uses deterministic PCG64 streams recorded in `DESIGN_SEED_INVENTORY.json`. It generates statistical root-effect arrays only, not Stim samples. The final independent audit repair file is separately hashed in the evidence manifest because it repairs two defects in the original frozen auditor without modifying that file. Never run the Stage 5 v2 sampling command as part of this reproduction.
