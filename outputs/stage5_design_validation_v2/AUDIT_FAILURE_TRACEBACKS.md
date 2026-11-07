# Preserved auditor failure tracebacks

These were implementation errors in the independent audit code. They occurred after the design simulation completed and did not modify simulation inputs/results or generate Stage 5 samples.

## Original frozen auditor invocation

Command: `python outputs/stage5_design_validation_v2/independent_audit.py`

```text
Traceback (most recent call last):
  File "outputs/stage5_design_validation_v2/independent_audit.py", line 157, in <module>
    main()
  File "outputs/stage5_design_validation_v2/independent_audit.py", line 135, in main
    gen=audit_generator()
  File "outputs/stage5_design_validation_v2/independent_audit.py", line 73, in audit_generator
    got=reference_draw(rng,family,np.asarray(means)[:,None],np.asarray(sds)[:,None],(4,250000))
  File "outputs/stage5_design_validation_v2/independent_audit.py", line 32, in reference_draw
    df = int(family[10:])
ValueError: invalid literal for int() with base 10: ''
```

## First separately versioned repair invocation

Command: `python outputs/stage5_design_validation_v2/independent_audit_repair_v1.py`

```text
Traceback (most recent call last):
  File "outputs/stage5_design_validation_v2/independent_audit_repair_v1.py", line 192, in <module>
    main()
  File "outputs/stage5_design_validation_v2/independent_audit_repair_v1.py", line 159, in main
    gen=audit_generator()
  File "outputs/stage5_design_validation_v2/independent_audit_repair_v1.py", line 73, in audit_generator
    got=reference_draw(rng,family,np.asarray(means)[:,None],np.asarray(sds)[:,None],(4,250000))
  File "outputs/stage5_design_validation_v2/independent_audit_repair_v1.py", line 40, in reference_draw
    conditional_sd = math.sqrt((sd*sd + mean*mean)/q - conditional_mean*conditional_mean)
TypeError: only 0-dimensional arrays can be converted to Python scalars
```

The repaired auditor used `family.removeprefix("student_t")` and NumPy's elementwise square root. Its successful output is `INDEPENDENT_AUDIT_RESULTS_V1.json`.
