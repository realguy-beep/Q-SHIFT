# Small nonlinear selector stopped on optimizer convergence

## Question

The flagged logistic selector uses a linear decision boundary over 42 syndrome/matcher features. This bounded screen tested one fixed 8-unit tanh MLP on the same disagreement subset to check whether a small nonlinear model could improve the held-out decoder.

## Outcome

The six-condition preflight completed (30,000 unique samples). During the first training condition, Z-memory/X-biased, the MLP reached the frozen 500-iteration L-BFGS-B limit and returned `STOP: TOTAL NO. OF ITERATIONS REACHED LIMIT`. The protocol required optimizer success before proceeding. The run stopped after 500,000 unique training samples; no validation samples were opened.

## Decision

This architecture is not ready under the fixed optimization budget. There is no accuracy comparison, and this does not show whether a converged MLP could outperform logistic regression. No iteration increase, architecture change, or tuning was performed on this stream. Total new unique samples: 530,000; cumulative Q-SHIFT development samples: 319,976,200. No confirmatory/sealed data were used.
