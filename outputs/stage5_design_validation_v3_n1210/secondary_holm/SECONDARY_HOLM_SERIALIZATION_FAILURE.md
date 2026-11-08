# Preserved failed Holm-results write

The first frozen invocation completed all ten 200,000-replicate scenario-family calculations, printed the per-family rates, and then exited before writing `SECONDARY_HOLM_RESULTS.json`.

Command:

```powershell
python outputs/stage5_design_validation_v3_n1210/secondary_holm/validate_holm.py --run-secondary-mc
```

Failure:

```text
Traceback (most recent call last):
  File ".../secondary_holm/validate_holm.py", line 102, in <module>
    if __name__=='__main__': main()
  File ".../secondary_holm/validate_holm.py", line 100, in main
    tmp=HERE/'SECONDARY_HOLM_RESULTS.json.tmp'; tmp.write_text(json.dumps(result,indent=2)+'\\n',encoding='utf-8'); os.replace(tmp,HERE/'SECONDARY_HOLM_RESULTS.json')
  File ".../Python312/Lib/json/__init__.py", line 238, in dumps
    **kw).encode(obj)
  File ".../Python312/Lib/json/encoder.py", line 439, in _default
    raise TypeError(f'Object of type {o.__class__.__name__} '
TypeError: Object of type bool is not JSON serializable
```

The offender is a NumPy `bool_` in a pass/fail field. The statistical calculations completed; this is an output-serialization defect. No results JSON was committed, no Stage 5 or Stim shots were generated, and no sealed data were accessed. The original script and its first freeze remain unchanged. The repair is limited to converting boolean scalars to built-in `bool` before JSON serialization; all seeds, distributions, sample counts, thresholds, and test rules remain the same. The rerun uses the same deterministic streams and is a replay, not additional independent Monte Carlo evidence.
