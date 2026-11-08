# Q-SHIFT v2 Pilot 2 runtime analysis

## Measured run cost

- Total runner wall time: 45.59 s; process CPU: 45.53 s.
- Evaluation replay: 37.53 CPU s for 160 streams, eight policies and two decoder modes.
- Cached decoder-bank construction: 0.281 CPU s (0.275 s wall); privileged exact-p graph construction added 0.469 CPU s.
- Profile template generation/fitting: 0.078 CPU s; static selection data generation 0.141 s and scoring 0.062 s.
- Stationary GLR and change-tuning data generation: 1.953 CPU s; 24-candidate detector-only calibration/tuning replay: 4.969 CPU s.
- Peak process RSS: 135,442,432 bytes (129.2 MiB); Python tracemalloc peak: 26,165,772 bytes (25.0 MiB). RSS is process-wide and cannot be attributed to a single C++ matcher.

## Per-stream online CPU comparison

For this paired two-mode replay, decoder time is summed across ordinary and correlation-aware modes; shared initial detector-profile calibration and policy adaptation are charged once per stream because the same detector-only decisions serve both modes. One-time graph-bank and template-training costs are shown separately above.

| Policy | Two-mode online CPU / stream (s) |
|---|---:|
| `fixed_p0` | 0.003027 |
| `static_dev` | 0.004785 |
| `batch_profile` | 0.004785 |
| `trailing_200` | 0.050293 |
| `ewma_08` | 0.051074 |
| `periodic_200` | 0.013672 |
| `event_glr` | 0.009863 |
| `oracle_true_p` | 0.002246 |

Online operational replay gives event GLR 80.7% lower CPU per stream than EWMA and 95.3% fewer graph switches (1.02 vs 21.45 per stream). Event-minus-EWMA LER is within the prespecified +0.10 pp noninferiority margin in both modes. This operational result depends on treating threshold/tuning data costs as one-time setup.

## Calibration-inclusive sensitivity

Event-specific candidate-tuning replay and stationary/tuning data generation cost 6.922 CPU s. Across 160 streams, that is 0.043262 s per stream if charged to this run. Including shared profile and graph-bank setup, event totals 8.859 CPU s and EWMA 8.531 CPU s. Event is 3.8% higher on this strict pilot-horizon all-in accounting. Online savings amortize the event-only setup after about 168 streams if calibration remains valid and reusable.

The frozen protocol separated one-time calibration/training costs from replay costs but did not explicitly state whether the decision-rule CPU comparison should amortize event-only GLR tuning over future streams. These accounting views cannot be collapsed into a post-hoc GO claim. This ambiguity is carried into the final decision.

## Instrumentation limits

- Decoder CPU uses `time.process_time()` around batch decode calls; estimator, GLR, and graph-selection sections are timed separately. Timer overhead and machine scheduling are not subtracted.
- Peak RSS is sampled process-wide every 50 ms; it is a reliable run-level bound, not per-arm memory attribution.
- The evaluation includes shared profile initialization per stream. It excludes hardware communication and live calibration data acquisition latency.
- Software: Python 3.12.10, NumPy 2.5.3, Stim 1.16.0, PyMatching 2.4.0, psutil 7.2.2. Platform: Windows-11-10.0.26300-SP0.
