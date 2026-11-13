# NS-3A timing and artifact freeze

This addendum records the original NS-3A benchmark values without changing its source report, benchmark JSON, or results. At the start of NS-3B, the NS-3A manifest had 23 entries and all 23 SHA-256/size checks matched. Its 22 deterministic tests passed again (0.269 s in the verification run). Files in NS-3A remain untouched.

## Machine and versions

Windows 11 Home build 26300; Python 3.12.10 x64; Stim 1.16.0; NumPy 2.5.3; PyMatching 2.4.0; 16 logical CPUs; approximately 16 GiB RAM. Original output: `../benchmark_results_ns3a.json`.

## Exact timing records

All values are wall seconds from Python `time.perf_counter`; they are fixed-fixture measurements, not per-shot simulation costs.

| Operation | Recorded seconds | Unit / repetitions |
|---|---:|---|
| Build Q-SHIFT d3/r5 circuit | 0.0050735 | One circuit construction |
| Build undecomposed approximate DEM | 0.0006615 | One Stim conversion |
| Build decomposed approximate DEM | 0.0009199 | One Stim conversion |
| Parse undecomposed DEM into BP model | 0.0060877 | One parse |
| PyMatching ordinary graph construction | 0.0013555 | One construction, `enable_correlations=False` |
| PyMatching correlation-enabled graph construction | 0.0015834 | One construction, flag true |
| BP inference | 0.5206044 | **One batch of 5 rows**, 50 BP iterations; diagnostics included |
| PyMatching ordinary inference | 0.000008800 | **Mean per 5-row batch**, 3 repeats |
| PyMatching correlation-enabled inference | 0.000010267 | **Mean per 5-row batch**, 3 repeats |

Derived only to show scale: BP was about 0.104121 s per row as a batch average; ordinary/correlation-enabled PyMatching were about 1.76/2.05 microseconds per row as batch averages. These are not separately measured single-row timings.

## Timing interpretation

The benchmark used a five-row deterministic batch: zero plus four selected single-mechanism syndromes. The PyMatching timings are native `decode_batch` calls with Python call/conversion overhead. BP is a pure-Python dictionary/list message-passing implementation, so its timing includes substantial Python-level iteration and allocation overhead; the measured code does not time `FactorGraphBP` graph-object construction separately. The reported BP model parse time is not decoder construction time. Timings were collected outside `tracemalloc`; memory tracing was a separate run. Python peak allocation does not include native C++ memory.

Do not compare NS-3A's Python BP timing directly with NS-3B's official belief-matching timing as an algorithm-only comparison: NS-3B uses compiled LDPC/PyMatching components, a decomposed DEM and a different BP schedule/decoder architecture. Both are deterministic inference timings, not accuracy evidence.
