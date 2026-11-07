# Reproduce the final evidence audit

Run from the repository workspace:

```powershell
python outputs/final_research_decision/audit_final.py
```

The script reads existing headroom JSON/CSV/NPZ files and saved DEMs, rebuilds candidate matching graphs, recomputes calibration choices and bootstrap frequencies, evaluates the predeclared gate, verifies paired error counts, and writes the independent JSON/CSV audit outputs. It does not call Stim samplers and does not generate simulation shots. It requires the repository's installed Stim, PyMatching, and NumPy packages.

The headroom phase's separate `audit_saved_pilot.py` independently re-decoded the saved candidate predictions from detector arrays. This final script verifies the corresponding audit status and hashes, then independently recomputes the NO-GO decision and finite-sample graph comparison.
