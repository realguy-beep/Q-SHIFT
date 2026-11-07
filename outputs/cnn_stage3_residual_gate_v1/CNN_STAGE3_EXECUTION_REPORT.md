# Q-SHIFT Stage 3 Execution Report

**Controller status:** failed; **recovery audit:** PASS; **development gate:** FAIL

- Unique simulated development shots: 200,000 / 200,000
- Independent roots: 5
- Completed model/root jobs: 5/5
- Independent-test access: false
- Python / PyTorch / Stim / PyMatching: 3.12.10 / 2.14.1+cu126 / 1.16.0 / 2.4.0
- CUDA device: NVIDIA GeForce RTX 4050 Laptop GPU; CUDA runtime: 12.6
- Active wall seconds: 33.91527759999735
- Measured CUDA training seconds: 18.623328699803096
- Peak process RSS bytes: 1478615040
- Peak CUDA allocated bytes: 25345536
- Free disk bytes at finalization: 273064861696
- Dry-run five-update seconds (same first 256 training shots): 0.8918717000051402
- Dry-run projected maximum CNN training seconds: 597.5540390034439
- Dry-run projected total wall seconds before validation overhead: 602.7011483832212

Commands executed before sampling: `python -m unittest outputs.cnn_stage3_residual_gate_v1.tests.test_stage3 -v`; `python outputs/cnn_stage3_residual_gate_v1/freeze_stage3.py --verify`; `python outputs/cnn_stage3_residual_gate_v1/run_stage3.py --validate-only`. The frozen runner executed `--run`; its file-path audit launch failed before importing the audit module. Recovery command: `python -m outputs.cnn_stage3_residual_gate_v1.audit_stage3_recovery_v1 --run-audit` (PASS).

This report does not claim independent confirmation, quantum-hardware integration, or superiority beyond the stated development gate.
