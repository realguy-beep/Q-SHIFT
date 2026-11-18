# One shared flagged-syndrome selector across six d3 conditions

## Design

A single pooled L2 logistic model was fit to flagged cases from six independent 1M-shot training streams, then evaluated on six fresh 1M-shot validation streams. The feature set remained 40 detector bits plus correlated and ordinary matcher outputs (42 dimensions). Training observables were offline labels for flagged examples only. The six previous independent-replication models were also scored on the same validation samples as a specialized reference; they were not used to select or tune the pooled model. All circuits used gate/measurement p=.003 and bias ratio 10.

Two independent pooled train/validation efforts were completed. Each used 10k preflight, 6M training, and 6M validation samples. Both fixed gates required >=10% macro reduction against correlated matching, no condition harmed >5%, and full two-matcher-plus-classifier cost <2x.

## First pooled fit

Macro LER on validation was .0051555 for correlated matching and .0044093 for the shared model, a 14.47% reduction. The prior specialized models scored .0043043 on the same stream. The shared model's paired macro difference versus correlated matching was -.000746 (95% interval [-.000780,-.000712]); versus the specialized reference it was +.000105 (95% CI [.000087,.000123]). All six cells improved over correlated matching; the smallest reduction was 1.98%. Full inference cost was 1.361x. The frozen advancement gate passed.

Pooled training used 15,693 flagged examples (10,817 logical 0 and 4,876 logical 1). The fit converged. Projected train/validation sampling and matcher time was 13.2s; total elapsed time 16.7s.

## Fresh pooled replication

A new pooled fit on distinct training seeds achieved .0051753 correlated versus .0043958 shared macro LER (15.06% reduction); the specialized same-stream reference was .0042978. Shared minus correlated paired macro difference was -.0007795 (95% CI [-.000814,-.000745]); shared minus specialized was +.000098 (95% CI [.000081,.000115]). All six cells improved over correlated matching; the smallest reduction was 2.34%. Full inference cost was 1.359x. The gate passed again.

This pooled fit used 15,369 flagged training rows (10,588 logical 0 and 4,781 logical 1). Total elapsed time was 16.5s.

## Interpretation

One shared model can replace the six separately fitted models while retaining a >14% macro improvement over correlated matching on these six nominal d3 conditions, with comparable inference cost and fewer deployed coefficients. It is consistently somewhat less accurate than the specialized reference (about 0.00010 absolute macro LER on the paired streams). This was not a predeclared noninferiority comparison, so do not claim equivalence to specialized models. The result remains specific to six known nominal d3 simulator conditions. It does not solve unknown or shifted-profile model selection, and the separate d5 transfer screen was negative.

Two startup attempts stopped at import before sampling because the paired-statistics helper was imported from the wrong module; no samples were drawn in those attempts. The helper was added locally before both successful frozen runs. No confirmatory or sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_shared_selector.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_shared_selector_replication.py
```

The design and fresh-seed replication protocol are in the corresponding `*_protocol.md` files.


## Run metadata

The two runs used the reproduction commands from base revision `9c0ad07`, with Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, and PyMatching 2.4.0. Each JSON records runner, protocol, and specialized-model-source SHA-256 hashes. Peak RSS was not captured.


## Run metadata

The two runs used the reproduction commands from base revision `9c0ad07`, with Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, and PyMatching 2.4.0. Each JSON records runner, protocol, and specialized-model-source SHA-256 hashes. Peak RSS was not captured.
