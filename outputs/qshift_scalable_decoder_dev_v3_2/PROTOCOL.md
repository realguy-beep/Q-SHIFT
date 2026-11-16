# Scalable decoder V3.2: compiled BP+OSD via `ldpc` (protocol)

**Committed before any V3.2 code or measurement.** `ldpc==2.4.1` was installed with owner approval; `ENVIRONMENT_DELTA.txt` records the exact pip delta, including the four transitive packages ldpc required. V3 (REVISE, `febae33e0`) and V3.1 (REVISE, `9cc0c2b80`) are unchanged.

## Scope

V3.2 replaces only the BP+OSD **implementation** with `ldpc.BpOsdDecoder` (C++), applied to the identical V3 parity-check matrix H, logical vector L and priors p from `bposd.dem_to_matrix(merge=True)`. The p=1 offsets are applied as in V3, and the prediction is the exact parity L·ê of ldpc's fault estimate.

**Frozen settings:**
- `bp_method='product_sum'`, `schedule='parallel'`, `max_iter=50`;
- `osd_method='OSD_CS'`, `osd_order=10`;
- `error_channel = p`.

ldpc has no message damping and its OSD-CS candidate set differs in detail, so predictions are **not** expected to equal V3's exactly. Agreement is reported, not forced.

## Gates

- **K1 (correctness):** on the V3 toy DEMs, every ldpc fault estimate is syndrome-consistent. On the real d=3/5/7 DEMs, pure burst syndromes decode to their logical effect, and the all-zero syndrome decodes to 0. The H/L contract is inherited from V3's C4.
- **K2 (d=3 quality):** on the same 72,000 already-exposed V1.5 rows at each root's frozen q̂, V3's d=3 quality criteria apply unchanged:
  - V3.2 − Astar 95% CI below 0;
  - gap recovery G ≥ 0.50;
  - q=0 no more than 0.05 pp above Astar.

  Agreement with V3 and with Bexact is reported.
- **K3 (feasibility):** on the same 200 deterministic syndromes per distance, measured as single-shot `decode` calls on one process:
  - the d=7 median is at most **50 ms/shot**;
  - peak traced memory is at most **1 GiB**. tracemalloc does not see C++ allocations, so process RSS is also reported.

## Decision

- **GO** (scalable-decoder development milestone): K1, K2 and K3 all pass.
- **REVISE:** K1 and K2 pass but K3 fails.
- **STOP:** K1 fails, or K2 fails because V3.2 is not better than Astar.

A GO concerns d=3 near-exactness on exposed data plus d=7 runtime and memory feasibility. It is **not** d≥5 accuracy evidence; that needs a separately authorized fresh-seed study.
