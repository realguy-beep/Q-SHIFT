# Stage 4C — CNN Recommendation

**Recommendation: CNN DROP.**

| Frozen criterion | Result |
|---|---|
| primary delta at most minus 0.0002 | FAIL |
| primary bootstrap upper below zero | FAIL |
| primary signflip p below 0.05 | FAIL |
| at least 3 of 4 nonzero conditions favor cnn | FAIL |
| zero burst one sided upper within 0.0002 | PASS |
| cnn validation mae not more than 0.0005 worse than ridge | PASS |

Primary CNN minus Stage 4B profile effect: +0.004286%, 95% root-bootstrap CI [+0.000000%, +0.012857%], p=1.
Validation MAE: CNN 0.00226824; Ridge 0.00219433; profile 0.00225017.

This decision concerns only a detector-only estimator for the specified synthetic spatial-burst model. The true-probability PyMatching arm is a privileged reference. A CNN is not retained on architecture preference alone. If not kept, the simpler Stage 4B profile method remains the recommended estimator unless Ridge itself has a clear validated benefit.
The experiment is development-only, uses one frozen CNN training allocation and seven paired roots per condition, and does not establish hardware performance or independent confirmation.
