# 500k training shots retain the d3 selector's measured gain

## Question

Can the validated 1M-shot-per-condition training budget be halved without losing most of the flagged logistic selector's d3 utility? A prior 100k-prefix screen stopped on a predeclared fit-readiness floor; this prospective test chose one 500k prefix, five times larger, with fresh streams.

## Design

For each of six nominal d3 Phase 2B conditions, a single 1M training stream supplied nested 500k and 1M fits. All six 500k prefixes passed a >=100 flagged rows / two logical classes readiness check before any validation was opened. Both frozen fits were compared with correlation-enabled PyMatching on the same independent 500k validation shots per condition. Features, L2 objective, optimizer, and all gates matched the existing selector protocol. A second fresh-seed stream replicated the design without tuning.

## Results

| Stream | Correlated macro LER | 500k fit | 1M fit | 500k relative reduction | Gain retained vs 1M | Inference cost | Gate |
|---|---:|---:|---:|---:|---:|---:|---|
| Initial | .0051597 | .0043013 | .0043030 | 16.64% | 100.2% | 1.369x | Pass |
| Fresh replication | .0051410 | .0042613 | .0042470 | 17.11% | 98.4% | 1.355x | Pass |

Every condition improved over correlated matching in both streams; all paired intervals excluded parity. The smallest 500k cell gains were 3.85% initially and 4.92% in replication, above the -5% cell-harm limit. The one-million-shot models were effectively tied with the 500k fits in the first stream; in the second, the 1M fit was modestly better overall.

## Decision and limits

The 500k fit passes the frozen retention, macro-utility, cell-harm, and inference-cost gates on two streams. For this d3 simulator setup, 500k training shots per condition are an evidenced alternative to 1M, reducing labeled training data by half. The 100k stop remains valid: that prefix had one cell below the minimum flagged-row floor. This is not evidence for smaller budgets, d5 scaling, hardware utility, or unknown-profile transfer.

Across both streams the study added 18.06M unique circuit samples: 60k preflight, 12M training, and 6M validation. No confirmatory/sealed data were accessed.

## Reproduction

```sh
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_training_500k.py
MPLCONFIGDIR=/tmp/qshift-mpl .venv/bin/python outputs/independent_research_v2/fast_flagged_logistic_training_500k_replication.py
```
