# Distance-5 intermediate syndrome schedule

## Hypothesis

The five-active-round plus four-idle d5 schedule did not improve over nine active rounds. An intermediate schedule with seven active rounds plus two idle cycles may retain enough repeated syndrome information while avoiding two active noisy gate layers. This is one mechanistically selected point, not a round-count sweep.

## Fixed design

- Use d5 Z memory under Z bias ratio 10, gate and measurement p=.003.
- Compare seven active rounds plus two data-idle cycles at p=.003 on 25 data qubits against the unchanged nine-active-round source circuit. Both use nine cycle units and preserve the same terminal readout basis.
- Build one correlation-enabled PyMatching decoder per arm from its own approximate DEM at threshold .0018.
- Use 1,000,000 fresh direct samples/arm. Preflight: 10,000/arm, seeds 2026114101/4102; main: 2026114111/4112. Report LER, Wilson intervals, independent RR and log interval, resource counts, and runtime.
- Advancement requires RR <=.90; the single cell also must have its 95% RR interval upper bound below 1 for a statistically supported gain. Otherwise stop this schedule branch.

## Stop rule

Check circuit shape (168 detectors for seven active rounds, 216 for nine), 25 idle data qubits twice, source-builder equality of the nine-round arm, terminal readout match, noiseless determinism, scalar/batch agreement, and projected runtime <=300 seconds. No sealed or confirmatory data are in scope.
