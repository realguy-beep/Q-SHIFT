# qshift_adaptive_robust_v1: adaptive and broadly robust QEC, milestone 0

This is a new research program, separate from every frozen study. It holds design, prototypes and development diagnostics only. **No new datasets were generated and no evaluation was run.**

Start with `DECISION_REPORT.md`. The other documents are:
- `BASELINE_AUDIT.md`: the evidence matrix and record discrepancies;
- `RESEARCH_QUESTIONS.md`: hypotheses with falsifiers;
- `LITERATURE_REVIEW.md`;
- `ADAPTIVE_ARCHITECTURE.md`;
- `BACKGROUND_ERROR_ANALYSIS.md`: dev-only floor diagnostic;
- `BROAD_NOISE_BENCHMARK.md`;
- `BASELINE_FAIRNESS.md`;
- `STATISTICAL_PROTOCOL.md`;
- `EXPERIMENT_ROADMAP.md`;
- `RISK_REGISTER.md`.

Code and data:
- `adaptive/`: estimation, change detection, regime classifier, causal controller (on `qshift_core_v1.controller`);
- `benchmark/`: endpoints and gates; draft suite;
- `tests/test_adaptive.py`: 21 deterministic tests on synthetic numpy data;
- `floor_diagnostic.py` → `results/floor_diagnostic/`, which reads Stage S **dev** arrays only.

```
python -m unittest discover -s outputs/qshift_adaptive_robust_v1/tests -v
```
