# Secondary condition-level Welch/Holm validation

## Result: FAIL

The Stage 5 candidate’s existing one-sided Student-t/Welch-reference p-values followed by a four-test Holm adjustment were tested under ten complete-null synthetic root-effect families at n=1,210. Each scenario used 200,000 independent family replicates. The exact sampled seeds and family definitions are in `SECONDARY_HOLM_SEED_INVENTORY.json` and `SECONDARY_HOLM_CONFIG.json`.

| Null family | Rejected families / 200,000 | FWER | Simultaneous Wilson upper | Gate |
| --- | --- | --- | --- | --- |
| normal_q1_5 | 9,783/200,000 | 4.891% | 5.017% | PASS |
| normal_q2 | 10,001/200,000 | 5.000% | 5.128% | PASS |
| student_t5_q1_5 | 9,788/200,000 | 4.894% | 5.020% | PASS |
| student_t3_q2 | 9,564/200,000 | 4.782% | 4.906% | PASS |
| right_skew_lognormal_q1_5 | 18,763/200,000 | 9.381% | 9.551% | FAIL |
| right_skew_lognormal_q2 | 18,670/200,000 | 9.335% | 9.504% | FAIL |
| zero_inflated65_q1_5 | 9,723/200,000 | 4.861% | 4.987% | PASS |
| zero_inflated65_q2 | 9,723/200,000 | 4.861% | 4.987% | PASS |
| tied_asymmetric65_q1_5 | 13,672/200,000 | 6.836% | 6.983% | FAIL |
| tied_asymmetric65_q2 | 13,859/200,000 | 6.929% | 7.077% | FAIL |

The FWER upper-bound requirement was 5.2%. Both right-skew lognormal conditions and both tied/asymmetric conditions failed. In the right-skew 1.5× condition, FWER was 9.3815%; in the right-skew 2× condition it was 9.3350%. The tied/asymmetric rates were 6.8360% and 6.9295%. Normal, Student-t, and zero-inflated families passed the complete-null FWER check in this finite simulation.

The 160 marginal checks cover four condition variances × four Holm step thresholds × ten families. Their simultaneous Wilson bounds also fail in skew/tied cases. A concrete marginal failure is right-skew 1.5×, condition index 0, nominal step alpha .05: 13,985/200,000 (6.9925%), simultaneous one-sided upper bound 7.1901% versus the allowed 5.2%.

## Independent replay

`audit_holm_repair_v2.py` uses a separately written root-effect generator, p-value reconstruction, Holm step-down, and Wilson calculation. It matched all 160 marginal counts and all ten Holm familywise counts exactly. The audit completed 10 scenario replays and reported:

```json
{"marginal_pvalue_validity_pass": false, "complete_null_holm_fwer_pass": false,
  "all_scenarios_replayed": true, "all_marginal_counts_replayed": true}
```

The estimator is validated only for the finite families in this design exercise. These findings do not establish behavior on unmodeled distributions and do not justify replacing the current method post hoc. A new secondary-inference method would require a separately predeclared and validated prospective amendment before Stage 5 sampling.
