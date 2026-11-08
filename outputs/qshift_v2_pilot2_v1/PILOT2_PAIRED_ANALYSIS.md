# Q-SHIFT v2 Pilot 2 paired analysis

All estimates are development-only and use unconditional logical errors (decoder prediction XOR the shared observable). The two PyMatching modes replay the same detector/observable streams. There are 20 independent roots per scenario; shots within a stream are not treated as independent replicates.

## Aggregate arm results

| Policy | Ordinary errors / 208,000 | Ordinary LER | Correlation-aware errors / 208,000 | Correlation-aware LER |
|---|---:|---:|---:|---:|
| `fixed_p0` | 1,465 / 208,000 | 0.7043% | 1,849 / 208,000 | 0.8889% |
| `static_dev` | 1,239 / 208,000 | 0.5957% | 1,551 / 208,000 | 0.7457% |
| `batch_profile` | 1,236 / 208,000 | 0.5942% | 1,559 / 208,000 | 0.7495% |
| `trailing_200` | 1,229 / 208,000 | 0.5909% | 1,555 / 208,000 | 0.7476% |
| `ewma_08` | 1,237 / 208,000 | 0.5947% | 1,580 / 208,000 | 0.7596% |
| `periodic_200` | 1,232 / 208,000 | 0.5923% | 1,560 / 208,000 | 0.7500% |
| `event_glr` | 1,223 / 208,000 | 0.5880% | 1,552 / 208,000 | 0.7462% |
| `oracle_true_p` | 1,213 / 208,000 | 0.5832% | 1,544 / 208,000 | 0.7423% |

The privileged true-p row is nondeployable and is not a performance lower bound. Static p was selected independently for each decoder mode from 5,500 labeled development shots: p=.008 ordinary and p=.014 correlation-aware. The result selected p per mode was not selected on evaluation outcomes.

## Prespecified paired primary comparisons

The effect is the equally weighted eight-scenario average of stream-level paired LER differences. Intervals are two-sided 95% percentile intervals from 20,000 stratified cluster-bootstrap draws, resampling the 20 roots within each scenario; seed 8,820,261,108. Values below are percentage points (pp).

### ordinary matching

| Comparator | Event − comparator (pp) | 95% stream-cluster interval (pp) | Relative LER difference | Paired event-only / comparator-only errors |
|---|---:|---:|---:|---:|
| `static_dev` | -0.0077 | [-0.0144, -0.0010] | -1.29% | 17 / 33 |
| `ewma_08` | -0.0067 | [-0.0163, 0.0029] | -1.13% | 51 / 65 |

### explicit correlation-aware matching

| Comparator | Event − comparator (pp) | 95% stream-cluster interval (pp) | Relative LER difference | Paired event-only / comparator-only errors |
|---|---:|---:|---:|---:|
| `static_dev` | 0.0005 | [-0.0053, 0.0063] | 0.06% | 24 / 23 |
| `ewma_08` | -0.0135 | [-0.0216, -0.0053] | -1.77% | 31 / 59 |

Interpretation under the frozen LER rule: in ordinary mode, event GLR beats the static comparator by the interval criterion, but its interval against EWMA includes zero. In correlation-aware mode, event beats EWMA, but its interval against static includes zero. Thus no mode clears both co-primary LER comparisons. These are development intervals, not independent confirmation.

## Per-scenario event comparisons

Each scenario contains 20 roots × 1,300 scored shots. Entries show errors for event/static/EWMA and paired event-only versus comparator-only discordances (20 roots pooled). Descriptive scenario results are not separately powered.

| Scenario | Mode | Event errors | Static errors | EWMA errors | Event-only vs static / static-only | Event-only vs EWMA / EWMA-only |
|---|---|---:|---:|---:|---:|---:|
| stationary_p0 | ordinary | 141 | 145 | 139 | 0 / 4 | 4 / 2 |
| stationary_p008 | ordinary | 154 | 150 | 153 | 5 / 1 | 10 / 9 |
| stationary_p016 | ordinary | 153 | 157 | 164 | 1 / 5 | 5 / 16 |
| step_up | ordinary | 159 | 163 | 165 | 2 / 6 | 5 / 11 |
| step_down | ordinary | 136 | 135 | 138 | 5 / 4 | 8 / 10 |
| smooth | ordinary | 156 | 155 | 155 | 3 / 2 | 7 / 6 |
| transient | ordinary | 138 | 145 | 143 | 1 / 8 | 3 / 8 |
| measurement_mismatch | ordinary | 186 | 189 | 180 | 0 / 3 | 9 / 3 |
| stationary_p0 | corr-aware | 174 | 175 | 174 | 0 / 1 | 1 / 1 |
| stationary_p008 | corr-aware | 184 | 178 | 193 | 8 / 2 | 5 / 14 |
| stationary_p016 | corr-aware | 194 | 197 | 201 | 0 / 3 | 4 / 11 |
| step_up | corr-aware | 196 | 195 | 198 | 6 / 5 | 4 / 6 |
| step_down | corr-aware | 191 | 191 | 201 | 3 / 3 | 3 / 13 |
| smooth | corr-aware | 207 | 206 | 207 | 3 / 2 | 6 / 6 |
| transient | corr-aware | 194 | 196 | 196 | 2 / 4 | 2 / 4 |
| measurement_mismatch | corr-aware | 212 | 213 | 210 | 2 / 3 | 6 / 4 |

## Static-noise performance and alarms

For the event arm, evaluation false alarms are alarms during constant burst-p segments, including the constant-p measurement-mismatch scenario; smooth drift is not a constant-p false-alarm condition. In the three correctly specified stationary scenarios, it recorded 31 accepted alarms over 78,000 scored shots (0.397 per 1,000); by p, counts were 3/20 at p=0, 18/20 at p=.008, and 10/20 at p=.016. Under measurement mismatch it recorded 17 alarms over 26,000 shots (0.654 per 1,000), with burst p fixed at .008. The 20-stream stationary counts are imprecise.

Selected GLR C00 had threshold 4, four-block history, two-block dwell, zero hysteresis, 100-shot profile window, and `any5` pair summary. On separate stationary calibration data, it had 14 accepted alarms over 28,800 scored shots (0.486 per 1,000): 6/9,600 at p=0, 6/9,600 at p=.008, and 2/9,600 at p=.016. It met the frozen target of no more than 1 alarm per 1,000 pooled and at each p. All 24 candidates met eligibility; the selected one had the lowest tuning delay by the frozen tie-break rule.

Mean evaluation delay for event GLR was 45 shots after the step-up, 95 after the step-down, and 40 during the 100-shot transient (20 roots each; 50-shot blocks). The corresponding EWMA means were:
- step_up: 25.0 shots.
- step_down: 27.5 shots.
- transient: 15.0 shots.

Event GLR therefore used fewer cached models but responded more slowly than EWMA on the step-down. It recorded 163 graph switches across 160 streams (1.02 per stream); EWMA recorded 3,360 (21.0 per stream). Graph-switch savings alone do not establish a win.

## Limitations

- The 20 independent streams per scenario improve on Pilot 1 but still leave broad root-level uncertainty; several primary intervals are near zero.
- The static selection set has 500 shots per candidate burst p; selection is separate from evaluation but remains noisy.
- Noise is a synthetic distance-3, five-round Stim model. The measurement mismatch changes measurement-flip probability from .003 to .006; it is not hardware drift.
- The correlation-aware mode operates on the decomposed DEM approximation, not exact circuit-level maximum-likelihood decoding.
- The paired CSV was repaired after the independent audit found a `uint8` bitwise-negation error in derived contingency cells. Primary errors were independently checked against the unchanged paired archive. The original CSV and intermediate repair attempts remain preserved.
- Three execution/audit failures and their fixes are logged as artifacts. The successful evaluation used the same predeclared seed allocation; no new evaluation seeds were added.
- No Stage 5 outcomes or frozen evaluation seeds were opened, and no independent confirmation was conducted.
