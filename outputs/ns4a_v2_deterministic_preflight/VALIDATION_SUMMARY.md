# Validation Summary

| Check | Result |
|---|---:|
| Exact base commit / preflight branch | PASS |
| Non-cone sparse allowlist | PASS |
| V2 authorization remains false | PASS |
| Circuit construction / expected dimensions | 6/6 PASS |
| DEM conversion with V2 settings | 6/6 PASS |
| Unchanged BeliefMatching alias guard | 6/6 PASS |
| Ordinary PyMatching construction + deterministic fixture decode | 6/6 PASS |
| Correlation-enabled PyMatching construction + deterministic fixture decode | 6/6 PASS |
| Detector-order and observable-semantics identity consistency | PASS |
| BM assumed-model/DEM identity parity contract checks | 6/6 PASS; runtime binding not verified |
| BM registration/construction | 0/12; BLOCKED because pinned dependency is absent |
| Deterministic shape/order/opt-in/failure-isolation fixtures | PASS |
| Sampler calls / shots / labels / model selections | 0 / 0 / 0 / 0 |
| Stage 5 access | None |

Overall preflight: **BLOCKED_BELIEFMATCHING_DEPENDENCY**. This is not a sampling authorization or scientific result.

Commands from the sparse worktree root:

```powershell
python -m py_compile outputs/ns4a_v2_deterministic_preflight/run_deterministic_preflight.py
python outputs/ns4a_v2_deterministic_preflight/run_deterministic_preflight.py
python outputs/ns4a_v2_deterministic_preflight/record_source_inventory.py
```

The runner command is deterministic-only and does not invoke Stim sampling. It constructs circuits and DEMs and uses only fixed synthetic detector arrays for decoder interface checks. The inventory command reads only the explicit local input allowlist and two exact blobs at the recorded upstream commit.
