# Phase 5 development findings v3

Development-only; no confirmatory test run. Both policies used identical sampled detector/observable blocks per schedule. Utility estimated on separate 180,000 shots across three repetitions.

| Schedule | Policy | pooled | nominal | static | adaptive | oracle | switches | false | delay | censored |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| stationary | ml | 0.00513 | 0.00521 | 0.00521 | 0.00553 | 0.00521 | 2 | 1 | None | 0 |
| stationary | utility | 0.00513 | 0.00521 | 0.00521 | 0.00545 | 0.00521 | 1 | 1 | None | 0 |
| data_to_measurement | ml | 0.00806 | 0.00806 | 0.00708 | 0.00732 | 0.00708 | 2 | 0 | 1.0 | 0 |
| data_to_measurement | utility | 0.00806 | 0.00806 | 0.00708 | 0.00732 | 0.00708 | 2 | 0 | 1.0 | 0 |
| measurement_to_data | ml | 0.00659 | 0.00684 | 0.00708 | 0.00732 | 0.00659 | 2 | 1 | 1.0 | 0 |
| measurement_to_data | utility | 0.00659 | 0.00684 | 0.00708 | 0.00708 | 0.00659 | 2 | 1 | 1.0 | 0 |
| nominal_measurement_nominal | ml | 0.00439 | 0.00464 | 0.00464 | 0.00464 | 0.00464 | 1 | 1 | 1.0 | 0 |
| nominal_measurement_nominal | utility | 0.00439 | 0.00464 | 0.00464 | 0.00464 | 0.00464 | 1 | 1 | 1.0 | 0 |
| slow | ml | 0.00757 | 0.00749 | 0.00781 | 0.00789 | 0.00789 | 3 | 2 | 1.0 | 0 |
| slow | utility | 0.00757 | 0.00749 | 0.00781 | 0.00749 | 0.00789 | 1 | 0 | 1.0 | 0 |
| rapid | ml | 0.00635 | 0.00659 | 0.00700 | 0.00708 | 0.00659 | 5 | 5 | 1.9090909090909092 | 0 |
| rapid | utility | 0.00635 | 0.00659 | 0.00700 | 0.00692 | 0.00659 | 2 | 2 | 1.9090909090909092 | 0 |
| random | ml | 0.00920 | 0.00911 | 0.00863 | 0.00895 | 0.00887 | 3 | 2 | 2.8125 | 0 |
| random | utility | 0.00920 | 0.00911 | 0.00863 | 0.00920 | 0.00887 | 0 | 0 | 2.8125 | 0 |

Static comparator selects from first completed block and total rates include that prefix. Delay is regime-estimator accuracy, not decoder optimality. No adaptive superiority claim. Utility table has 3×9 errors; between-repetition SD saved in JSON.