# Family-wise shot budget for the 10,000× relative-LER target

## Calculation

The existing d9 mismatch screen observed 408/500,000 logical failures (LER .000816), with exact 95% lower endpoint .00073876. A 10,000-fold relative reduction therefore requires candidate LER <=7.3876e-8 when using that conservative baseline endpoint. Under IID Bernoulli shots, exact Clopper–Pearson upper bounds give:

| Candidate claims protected simultaneously | Candidate error allocation | Shots/cell for zero failures | Shots/cell allowing one failure |
|---:|---:|---:|---:|
| 1 | .05 | 40,550,810 | 64,213,866 |
| 6 | .05/6 | 64,804,412 | 92,691,979 |
| 12 | .05/12 | 74,186,986 | 103,371,225 |

For six cells, this is 388.8M total candidate shots with zero failures or 556.2M if one failure is allowed in each cell. If half the overall 5% error budget is reserved for baseline uncertainty and the other half is Bonferroni-split among candidate cells, the six-cell candidate requirements rise to 74,186,986 shots/cell for zero failures and 103,371,225 for one failure. For 12 claims (e.g., six cells across two roots), the corresponding per-cell counts are 83,569,560 and 113,923,575.

## Interpretation and limits

These are evidence budgets, not physical limits or proof of feasibility. They assume IID shots and a fixed, preselected decoder. They exclude baseline multiplicity across conditions, multiple roots unless explicitly counted, decoder/code selection, noise drift, and within-shot-stream dependence. The single-condition calculation is exactly the existing d9 budget; the new result quantifies only multiplicity scaling. No stochastic Q-SHIFT samples were generated.
