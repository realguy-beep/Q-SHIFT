# 100k-shot training efficiency screen stopped before an interpretable efficacy result

## Question

The leading d3 flagged logistic selector uses one million training shots per condition. This screen asked whether a 100k nested training prefix per condition produced at least 100 flagged examples with both logical classes, a conservative minimum for fitting its fixed 42-feature logistic model.

## Frozen procedure

We kept the six existing d3 Phase 2B conditions, the feature definition, L2 objective, and optimizer fixed. Each 1M seeded training stream contains the 100k candidate prefix. The independent validation stream was 500k shots per condition. The predeclared overall advancement gate also required the 100k model to retain 80% of the 1M model's absolute macro gain, reduce macro LER by at least 10%, avoid >5% cell harm, and stay below 2x inference cost.

## Outcome

Five 100k prefixes had at least 108 flagged examples. The X-memory/X-biased prefix had 93 flagged rows (73 logical 0, 20 logical 1), below the frozen 100-row minimum. The candidate therefore stopped at trainability and did not pass its gate. This is not evidence that the fitted model would miss the LER gate; no valid aggregate efficacy comparison was produced.

A runner-order defect caused validation to be entered for the first three conditions before the fourth condition failed the trainability check. Those partial validation results were not saved, are excluded from analysis, and are not being reconstructed. The run used 30k preflight shots, 4.2M unique training shots, and 1.5M unique partial-validation shots, for 5.73M new unique samples. The earlier 100k prefix probes were nested in these same streams and are not double counted. No confirmatory or sealed data were used.

## Interpretation

The tested 100k budget is too small to meet the chosen 100-flag trainability floor in every condition. The 1M model remains the validated operating point. Do not claim a learning-curve or accuracy comparison from this run. Any future sample-efficiency study needs a train-all-conditions gate before opening validation and a new predeclared training budget.

## Reproduction and audit

The exact as-run runner is preserved as `fast_flagged_logistic_training_efficiency.py`; the primary command is in the protocol. It is included to audit the partial execution and its ordering defect. The JSON records unique counts, the trainability failure, and hashes. No repeat was launched.
