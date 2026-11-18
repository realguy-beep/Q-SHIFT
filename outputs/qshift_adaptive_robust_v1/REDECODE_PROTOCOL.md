# Roadmap step 1: full re-decode of Stage S development shots (pre-registered)

- **Authorized by the owner, 2026-11-18:** "Run floor re-decode".
- **What this commit fixes in advance:** this protocol and `redecode.py` are committed **before** any full re-decode output exists. Before this commit, only the smoke test had run: 500 shots × 3 configurations, into a scratch directory outside the repository.

## Data

- **Source:** all 1,200,000 Stage S development shots (`qshift_d5_lowp_regime_v1/work/dev`), at L10 (p = 0.001) and L15 (p = 0.0015), q ∈ {0, 0.01, 0.02}, 200,000 shots each.
- **Baseline:** Stage S's saved L2 error bits at the selected prior (0.001 for L10, 0.0025 for L15).
- **Excluded:** no sampling is done, and Stage E is not read.
- **Status of this data:** development data. It has already been used for the Stage S selection and for the floor diagnostic (56 failures and 600 controls, 18% overlap with this run's failure set by construction). A result here can **only** advance a variant to a validation screen on fresh seeds. It is never confirmatory.

## Variants (fixed; the same decoder DEM and prior as L2)

| ID | Change from L2 (product-sum, serial, max_iter 50, OSD_CS order 10) |
|---|---|
| V1_min_sum_0.9 | min-sum BP, scaling factor 0.9 |
| V2_osd_cs40_bp200 | max_iter 200, OSD_CS order 40 |

**Identity check.** Baseline L2 is re-decoded on the first 2,000 shots of every file and must be bit-equal to the saved Stage S error bits. If any check fails, the run is INVALID.

## Endpoints and decision rule (fixed)

**Per variant, per file:**
- errors;
- variant-only failures (b);
- L2-only failures (c);
- net = b − c.

**Pooled over the 6 files:**
- net, with a 95% interval from a paired multinomial bootstrap over i.i.d. shots (20,000 replicates, seed 20261119);
- a one-sided exact McNemar p-value.

There is one seed per file, so a root-cluster bootstrap is not possible. The shot-level interval treats shots as i.i.d., which they are within one Stim seed. This is a stated limitation.

**ADVANCE_TO_FRESH_VALIDATION** requires both:
- the upper end of the pooled net 95% interval is < 0;
- the pooled q=0 net (L10 q0 + L15 q0) is ≤ 0.

Otherwise the verdict is **DO_NOT_ADVANCE**.

**Overall verdict:**
- **H-F1_SUPPORTED** if either variant advances;
- otherwise **H-F2_FLOOR_DEGENERACY_DOMINATED**, which means search variants do not reduce the net floor.

**Additionally reported:** runtime by variant, the projected effect on R using Stage S Astar counts, and the per-file tables.

## Execution

- `python redecode.py run --workers 8`: 102 write-once tasks (25,000-shot chunks plus 6 identity checks), with raw error bits in the git-ignored `work/redecode`.
- `python redecode.py analyze` writes `results/redecode/REDECODE.json`.
- **Expected cost:** about 50–60 min wall time. The smoke test measured about 15 ms/shot for V2 and about 1.3 ms/shot for V1, single process.

The decision is reported whatever it is. No variant or threshold is changed after results are seen.
