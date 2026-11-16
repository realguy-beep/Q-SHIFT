# Scalable decoder V2: deterministic development package

This package investigates bounded sum-product belief propagation over the
independent mechanisms in Stim detector error models. It is a deterministic
development study only. It does not sample, train, evaluate held-out data, or
make a decoder-superiority claim.

## Reproduction

From the repository root, using the already installed Python 3.12 environment:

```powershell
py -3.12 -m unittest discover -s outputs/qshift_scalable_decoder_dev_v2 -p 'test_*.py' -v
py -3.12 outputs/qshift_scalable_decoder_dev_v2/verify_source_manifest.py
```

After a reviewed, intentional package edit and before publication, refresh the
inventory with `py -3.12 outputs/qshift_scalable_decoder_dev_v2/verify_source_manifest.py --refresh-reviewed`, then run the default verification command. The inventory excludes its own hash to avoid self-reference.

The recorded fixture diagnostics were run before this package was finalized.
Do not rerun `run_fixtures_v2.py` casually: it creates a new deterministic
diagnostic output and intentionally refuses to overwrite an existing one. The
committed fixture results are already preserved in this directory. The runner
constructs circuits and DEMs, but never calls a sampler or creates random
detector events.

The selected V1.4 regressions and fixture diagnostics are described in
`VALIDATION_SUMMARY.md`. `fixture_results_final.json` is the final-source
result; earlier outputs remain present to preserve the repair history.

## Interpretation

V2 fixed exact probability-boundary handling, impossible-syndrome checking,
and the disconnected logical-only mechanism path. It did not resolve the
loopy q=0 convergence failures. Its logical probability for connected logical
faults remains a product-of-marginals approximation. See `PROTOCOL.md`,
`ROOT_CAUSE_REPORT.md`, `DETERMINISTIC_RESULTS.md`, and
`NEXT_METHOD_RECOMMENDATION.md` before reusing the implementation.

No new dependencies were installed. The run used the environment versions
recorded in `VALIDATION_SUMMARY.md`; `ldpc` and `beliefmatching` were not
available. V1 and V1.6b evidence directories are historical and unchanged.
