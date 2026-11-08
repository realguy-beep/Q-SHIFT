# Preserved first independent-auditor reporting failure

The first independent replay (`audit_holm_repair_v1.py`) completed the ten seeded scenario replays and all 160 marginal comparisons without raising a count-mismatch assertion. It then failed while assembling the final JSON report because its report used the original freeze schema key rather than the superseding repair-freeze key.

Command:

```powershell
python outputs/stage5_design_validation_v3_n1210/secondary_holm/audit_holm_repair_v1.py
```

Exact terminal error:

```text
Traceback (most recent call last):
  File ".../secondary_holm/audit_holm_repair_v1.py", line 101, in <module>
    if __name__=='__main__': main()
  File ".../secondary_holm/audit_holm_repair_v1.py", line 94, in main
    'frozen_inputs_verified':len(fr['secondary_design_input_sha256']),
KeyError: 'secondary_design_input_sha256'
```

The superseding freeze uses `repair_design_input_sha256` and `parent_and_failure_evidence_sha256`. The defect is in the audit summary field lookup after replay, not in the statistical test or its counts. No Stage 5 samples or sealed outcomes were accessed. The fix is separately versioned; the original and v1 repair auditors are retained unchanged.
