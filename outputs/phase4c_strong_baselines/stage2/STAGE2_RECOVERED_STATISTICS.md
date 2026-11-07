# Recovered Stage 2 statistics

Equal-regime calibrated minus pooled fixed = 0.00001556. Regime-stratified bootstrap 95% CI [-4.88888888888889e-05, 7.666666666666668e-05]. Frozen sign-flip p=0.66658333. The primary evidence does not support calibrated superiority over pooled fixed.

| Regime | Calibrated | Pooled fixed | Difference | Relative reduction |
|---|---:|---:|---:|---:|
| data_heavy | 8459 | 8382 | 0.00012833 | -0.9186% |
| nominal | 2996 | 2949 | 0.00007833 | -1.5938% |
| measurement_heavy | 980 | 1076 | -0.00016000 | 8.9219% |

Secondary tests and Holm values: [
  {
    "comparator": "nominal_fixed",
    "candidate_only": 435,
    "comparator_only": 376,
    "mcnemar_p": 0.041618463016267315,
    "holm_p": 0.041618463016267315
  },
  {
    "comparator": "minimax_fixed",
    "candidate_only": 2600,
    "comparator_only": 2078,
    "mcnemar_p": 2.4367937836035176e-14,
    "holm_p": 7.310381350810552e-14
  },
  {
    "comparator": "condition_specific",
    "candidate_only": 1489,
    "comparator_only": 1691,
    "mcnemar_p": 0.00036321503306871873,
    "holm_p": 0.0007264300661374375
  }
]
