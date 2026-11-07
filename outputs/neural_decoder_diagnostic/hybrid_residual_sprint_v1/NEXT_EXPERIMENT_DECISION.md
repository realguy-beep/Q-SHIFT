# Next-experiment decision

**Decision:** NO-GO for 10M/60M scaling.

Predeclared primary: `balanced_minibatch` / `60000` / `confidence_gate`. Mean root paired delta 0.0000%, 95% descriptive root-t interval [0.0000%, 0.0000%], root-bootstrap interval [0.0000%, 0.0000%], roots won/lost/tied 0/0/5, correction precision 0.000.

The gate requires a mean reduction of at least 0.0002, at least four favorable roots, bootstrap upper bound below zero, and correction precision above 0.5. All nine frozen comparisons are Holm-adjusted; with five roots, the smallest possible unadjusted exact sign-flip p-value is 0.0625, so this sprint cannot establish confirmatory significance. Preserve PyMatching as the default and keep the independent test sealed. A GO would only authorize designing a separately frozen confirmatory study.
