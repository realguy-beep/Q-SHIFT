# Leave-one-regime-out transfer of the relative-choice classifier

## Design

Each fold held out one entire Pauli regime (X-biased, balanced, or Z-biased). A shared logistic classifier trained on the other two regimes across both memory bases, using only flagged 40-bit detector vectors and the target `correlated_wrong`. It then chose between correlated and ordinary matching for the held-out regime's two memory-basis conditions. Matchers were built from each held-out profile's own nominal noise graph, so this tests transfer of the learned selector across regimes, not graph mismatch. Every held-out cell was evaluated once per stream.

There were three fresh models per full run: 12M total fold-training samples and 6M held-out validation samples, plus 60k preflight. A second complete run used distinct seeds. The gate required at least 10% macro improvement over correlated matching, no condition harmed by more than 5%, <2x inference cost, and positive macro change within every held-out regime.

## First stream

Equal-cell macro LER was .005136 for correlated matching and .004551 for leave-one-regime-out selection, an 11.39% reduction. Paired macro difference was -.000585 (approximate 95% CI [-.000619,-.000550]); the full-profile relative-choice reference was .004491, and specialized per-condition models were .004277. Full inference time was 1.354x. Held-out regime reductions were 9.63% for X-biased, 17.60% for balanced, and 4.97% for Z-biased. All six cells improved by point estimate; the smallest gain was 0.74%. The gate passed.

## Independent fresh-seed replication

Macro LER was .005188 correlated and .004590 leave-one-regime-out, an 11.52% reduction. Paired macro difference was -.000598 (95% CI [-.000632,-.000563]); the all-profile relative reference was .004545 and specialized reference .004327. Cost was 1.360x. Held-out regime reductions were 9.72% (X-biased), 17.67% (balanced), and 5.10% (Z-biased). All six cells again improved by point estimate; the smallest gain was 0.41%. The gate passed.

The selector trained without any labels from the held-out regime retained a positive gain in all three regime folds on both streams. It was less accurate than the all-profile and specialized references, particularly in the near-neutral X-memory/Z-bias cell.

## Interpretation and limits

This is evidence that a shared relative-choice selector can transfer across the three tested nominal d3 profiles when the matching graphs remain profile-matched. It does not show that the profile itself is unknown to the decoder, that one fixed matcher works across regimes, or that transfer holds at other bias ratios, distances, or hardware. The d5 transfer screen remains negative. No confirmatory or sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_leave_profile_out.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_leave_profile_out_replication.py
```


## Run metadata

Both runs used the listed commands from base revision `38d7f17`, with Python 3.12, NumPy 2.5.5, SciPy 1.18.1, Stim 1.16.0, and PyMatching 2.4.0. The result JSONs record runner and protocol SHA-256 hashes. Peak RSS was not captured.
