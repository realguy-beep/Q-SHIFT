"""Generate the human-readable reports from the saved deterministic results."""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "RESULTS.json").read_text(encoding="utf-8"))

def risk_table(rows, names):
    out = ["| Case | " + " | ".join(names) + " |", "|---|" + "---:|" * len(names)]
    for x in rows:
        vals = x.get("risk_by_decoder", {})
        out.append("| " + x["name"] + " | " + " | ".join("—" if vals.get(n) is None else f"{vals[n]:.8f}" for n in names) + " |")
    return "\n".join(out)

def write(name, body):
    (HERE / name).write_text(body.strip() + "\n", encoding="utf-8")

toy = R["historical_reproduction"]
categorical = R["categorical_seed_cases"]
fragments = R["reduced_surface_fragments"]
full = R["full_phase2b_structure"]
grid = R["separator_grid"]
exact_names = ["exact_categorical_map", "exact_independent_dem_map", "pymatching_standard", "pymatching_correlated", "separator_free_standard", "local_restricted_posterior"]
grid_diff = [x["separator_free_standard_risk"] - x["separator_standard_risk"] for x in grid]
grid_better = sum(x < -1e-12 for x in grid_diff); grid_tied = sum(abs(x) <= 1e-12 for x in grid_diff)

write("BASELINE_REPRODUCTION.md", f"""
# Baseline reproduction and evidence audit

## Scope and result

The deterministic runner reproduced the historical two-qubit categorical toy: exact categorical MAP risk **{toy['risk_by_decoder']['exact_categorical_map']:.4f}**, exact independent-DEM MAP risk scored on the categorical distribution **{toy['risk_by_decoder']['exact_independent_dem_map']:.4f}**, separator-bearing PyMatching **{toy['risk_by_decoder']['pymatching_standard']:.4f}**, and separator-free PyMatching **{toy['risk_by_decoder']['separator_free_standard']:.4f}**. The categorical and independent-DEM MAP decisions agree on all four syndromes. This confirms the prior finite example.

The new independent rescoring script checked **17** exact cases and all **64** grid cells, with **0 numerical mismatches**. The main suite records 8 fixed-seed categorical channel instances, a 64-cell exhaustive parameter grid, four reduced surface fragments, and structural-only regeneration of six Phase 2B circuit/DEM conditions. It generated **0 stochastic Phase 2B evaluation shots** and did not read Phase 2B full-test labels.

## Historical artifacts checked

`verify_inputs.py` reports PASS for 1,313 direct historical hash checks: categorical decoder feasibility (20), categorical inference (59), Phase 2B frozen manifest entries (182), Phase 2B pretest freeze hashes (47), recorded DEM-gate references/outputs (151), and decoder evidence manifests (1,005). It found no hash failures. The DEM-gate manifest contains 9 entries whose current hash agrees with a manifest-recorded `actual_sha256` rather than a separate original expected hash; they are consistent with that record, but provenance is weaker than a preexisting expected hash.

The Phase 2B manifest contains 182 listed files and is not an exact current inventory: `config - Copy.json` is an extra unmanifested copy with the same size and SHA-256 as `config.json`. No listed Phase 2B hash failed. The copy is an inventory caveat, not evidence of altered experiment data.

One provenance caveat: an earlier execution in this task invoked the historical categorical-feasibility manifest builder with a verify-looking argument; that script rewrites the manifest deterministically. Its listed scientific artifacts subsequently verify, but the byte-for-byte pre-invocation serialization of that manifest cannot be proven. No historical result, dataset, or source file was changed by this investigation.

## Reproduction commands

From the repository root, run `python -B -m unittest discover -s outputs/matching_representation_investigation -v`, then `python -B outputs/matching_representation_investigation/matching_investigation.py`, `python -B outputs/matching_representation_investigation/verify_results.py`, and `python -B outputs/matching_representation_investigation/verify_inputs.py`. The last check is read-only with respect to historical inputs and writes only its local `PHASE0_VERIFICATION.json` report.

## Environment and resources

Python {R['software']['python']}, Stim {R['software']['stim']}, PyMatching {R['software']['pymatching']}, NumPy {R['software']['numpy']}. Latest deterministic suite execution: {R['elapsed_seconds']:.3f} seconds; process peak working set {R['peak_memory']['peak_working_set_bytes'] / 1024**2:.1f} MiB. These measurements cover this bounded analysis job only.
""")

write("DECOMPOSITION_DIAGNOSIS.md", f"""
# Decomposition diagnosis

## The two-qubit example

The toy DEM has two detectors, one logical observable, and six independent Bernoulli mechanisms. Two mechanisms contain a separator; the complete event `D0 L0 ^ D1` has total parity mask `{toy['dem_text'].splitlines()[2]}`. The exact enumerator treats each complete line as one event: it either occurs with its stated probability or does not. The separator partitions a *suggested graph decomposition*; it is not a second independent random event.

The matching graph imported from the separator-bearing DEM has two detector nodes and two boundary edges; the graph has no direct `D0`–`D1` logical edge for the relevant combined event. The resulting standard and correlation-enabled PyMatching predictions are identical on this toy. At syndrome 11, exact categorical MAP selects logical flip 1, whereas the separator-bearing matching graph predicts 0. Across the full distribution that yields risk 0.1128 rather than 0.0600. Correlation-enabled matching does not repair this particular decision.

Replacing the single complete event with a single graph edge `D0 D1 L0` preserves its Bernoulli probability and complete detector/logical mask in this two-detector case. This changes the graph presented to matching: the exact risk 0.0600 is recovered. This is a valid representation for this graphlike event, not evidence that all separator hints should be erased.

## Generalization boundary

The pattern recurs in a deterministic 64-point family built from the same 2-detector graphlike motif: valid separator-free matching has lower exact risk in {grid_better}/64 cells, ties in {grid_tied}/64, and is worse in 0/64. This is a structured family, not a random sample of Stim circuits. In the eight independent categorical chain toys, standard matching differs from exact MAP in 1–3 of four syndromes per case; separator-free matching reduces, but does not always eliminate, the disagreement. The two-decoder equivalence across a case does not establish equivalence in general.

The four-detector alternative-decomposition fixtures preserve the same full event distribution while changing the proposed partition. Standard/correlated matching can give different decisions for a changed partition. Candidate A rejects both because the complete event has four detector symptoms. Unchecked removal is only a diagnostic and is not a valid candidate method.

## Interpretation

The failure generalizes as **representation sensitivity in selected small graphlike cases**, not as a universal PyMatching defect or a universal benefit of separator removal. A separated DEM carries a decomposition hint that helps represent a hyperedge/correlated mechanism as graph components. Matching then optimizes under its graph construction and correlation procedure; that is not identical to exact summation over all logical classes. No software bug was demonstrated.
""")

write("GRAPH_SEMANTICS_VALIDATION.md", """
# Graph-semantics validation

Stim's DEM separator `^` is a marker for a suggested decomposition of one error mechanism's targets. It is not an event and does not introduce an independent probability draw. A DEM `error(p)` mechanism contributes a complete detector-flip set and observable-flip set; overlapping mechanisms combine by XOR. The independent exact enumerator in this work parsed each complete mechanism, XORed all detector and logical masks, and exhaustively summed outcome probabilities.

The PyMatching comparison used the same frozen DEM content with `enable_correlations=False` and `enable_correlations=True`. The latter invokes PyMatching's two-pass correlated matching for supported decomposable correlations. It is still a matching-based approximation, not exact posterior inference. The imported graph's nodes, edges, boundary edges, and logical IDs were inspected for the toy; on the original toy the direct logical D0–D1 edge was absent. On the separator-free valid toy it was represented as a graph edge with logical observable ID 0.

The exact comparison over all syndromes checked both the decoder's logical prediction and the posterior mass. Where syndrome probability is zero, it is not scored. Posterior ties use the deterministic smallest logical-mask integer. Maximum normalization discrepancy in independent probability routes was `4.44e-16`.

**Conclusion:** the two DEM forms encode the same complete Bernoulli event distribution in the tested rewrite, while creating different matching graphs and thus different decoder decisions. That difference reflects decoder representation/inference, not a changed physical channel. Stim's separator semantics are not violated by this behavior.
""")

cat_rows = []
for x in categorical:
    rr = x["risk_by_decoder"]
    cat_rows.append({"name": f"seed {x['seed']}", "risk_by_decoder": rr})
fragment_names = ["exact_independent_dem_map", "pymatching_standard", "pymatching_correlated", "separator_free_standard", "local_restricted_posterior"]
cat_table = risk_table(cat_rows, exact_names)
frag_table = risk_table(fragments, fragment_names)
grid_table = ["| p | q | r | Standard separated | Standard separator-free | Difference |", "|---:|---:|---:|---:|---:|---:|"]
for x in grid:
    d = x["separator_free_standard_risk"] - x["separator_standard_risk"]
    grid_table.append(f"| {x['p']:.2f} | {x['q']:.2f} | {x['r']:.2f} | {x['separator_standard_risk']:.6f} | {x['separator_free_standard_risk']:.6f} | {d:+.6f} |")
full_table = ["| Basis | Regime | Detectors | Mechanisms | Separator mechanisms | Support 3 or 4 | Matching graph nodes / edges |", "|---|---|---:|---:|---:|---:|---:|"]
for x in full:
    s=x["complete_event_detector_support_counts"]
    g=x["matching_graphs"]["standard"]
    full_table.append(f"| {x['basis'].upper()} | {x['regime']} | {x['detectors']} | {x['error_mechanisms']} | {x['separator_mechanisms']} | {s.get('3',0)+s.get('4',0)} | {g['nodes']} / {g['edges']} |")

write("GENERALIZATION_TESTS.md", f"""
# Preregistered deterministic generalization suite

The suite design and fixed seed list were saved in `CASE_PLAN.json` before decoder outcomes were generated. It uses exhaustive finite-state risk, not Monte Carlo: no confidence intervals or significance tests apply to these deterministic enumerations. The eight categorical cases use seeds 61001–61008 and two independent `PAULI_CHANNEL_2` categorical sites per case. The separate 4×4×4 parameter grid varies the event probability and two boundary-channel probabilities in a fixed two-detector graphlike motif. Surface fragments are truncated Phase 2B circuits at rounds 1 and 2; their reference is exact inference on the **independent DEM**, not the native categorical physical circuit.

## Independent categorical cases

Risk means the exact probability that the decoder's predicted observable correction is wrong under the categorical channel, summed over all syndromes. The separator-free column is included only because every complete event in these two-detector cases passes the graphlike validity checks.

{cat_table}

Across these cases, exact categorical and exact independent-DEM MAP decisions agree on every syndrome despite joint-distribution total-variation distances of approximately 0.0040–0.0075. Standard and correlation-enabled PyMatching make identical predictions in all eight cases. The local restricted posterior matches exact categorical MAP in all eight 4-syndrome instances because its selected subproblem covers all relevant events there. These are bounded fixtures, not evidence of full-circuit equivalence.

## Fixed graphlike parameter grid

All 64 cells preserve the same complete independent event distribution between the separator and separator-free forms. The full per-cell result is retained below and in `SEPARATOR_GRID.csv`.

{chr(10).join(grid_table)}

Separator-free standard matching improves exact risk in **{grid_better}/64** cells, ties **{grid_tied}/64**, and worsens in none; the improvement range is 0 to 0.19594 absolute in this purposely small toy family. This does not prove safe generality beyond the admissible graphlike motif.

## Reduced surface fragments: exact independent-DEM inference

| Fragment | Exact DEM MAP | Standard PM | Correlated PM | Valid separator-free PM | Local posterior | PM standard/correlated syndrome disagreements |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join('| ' + x['name'].replace('_',' ') + ' | ' + ' | '.join(f"{x['risk_by_decoder'].get(n, float('nan')):.8f}" if x['risk_by_decoder'].get(n) is not None else '—' for n in fragment_names) + f" | {x['disagreements_by_syndrome_count'].get('pymatching_correlated_vs_pymatching_standard','—')} |" for x in fragments)}

The one-round fragments have eight detectors and 256 possible syndromes. The two-round fragments have sixteen detectors and 65,536 syndromes, including many zero-mass syndromes. Decoder risks are weighted by exact positive-mass syndrome probability.

## Full Phase 2B structure-only regeneration

These six rows regenerate circuit and DEM structure only: no shots were generated and no Phase 2B test labels were read. Text contents match the saved circuit/DEM files; the historical Phase 2B manifest independently checks their raw file hashes.

{chr(10).join(full_table)}

For all six conditions the full event detector support includes four-detector hyperedges, so Candidate A rejects them. The 121 events with support 3 or 4 per condition are not eligible for the simple safe graphlike rewrite.
""")

write("REPRESENTATION_AWARE_MATCHING.md", """
# Candidate A — representation-aware matching

## Rule implemented

The transformation reads each complete DEM event after XOR-aggregating its detector and logical targets. It retains the event probability and complete parity masks. It accepts an event only if its distinct detector support is at most two and it is not a logical-only event (zero detectors with nonzero logical parity). A truly zero-effect event may be discarded. If any event violates these rules, the transformation rejects the whole DEM instead of dropping or splitting the unsupported event. Accepted outputs preserve the per-event independent distribution and therefore the joint detector/observable distribution.

This is a conservative graphlike rewrite. It does not claim a new matching algorithm. It is a preprocessing guard that can make an already graphlike complete event available as a direct edge/boundary edge, with the original event probability and observable IDs.

## Tests and limits

Automated tests verify per-event probability and parity preservation, rejection of detector hyperedges and logical-only events, and exact distribution equality on small models. The graphlike two-detector toy and all 64 grid cells pass. The two alternative four-detector decompositions are rejected even though each separator grouping contains pieces that look graphlike: the *complete event* still flips four detectors. All six full Phase 2B DEMs are also rejected for the same reason.

It is not valid to erase separators when an event has more than two detector symptoms. Doing so either loses targets, silently changes the full event, or yields a graph that does not encode that event. Therefore this candidate cannot be applied to the target Phase 2B circuit as-is.
""")

write("LOCAL_REFINEMENT_FEASIBILITY.md", """
# Candidate B — bounded local posterior refinement

For a queried syndrome, the prototype retains DEM mechanisms that touch an active detector plus detector-free mechanisms, enumerates those Bernoulli variables exactly, and conditions every omitted exterior mechanism to identity. It computes a normalized posterior over logical masks on that restricted model and chooses the smallest logical-mask integer on posterior ties (tolerance `1e-15`). If more than 12 mechanisms are selected, or the syndrome has no mass in the restricted model, it falls back to the standard matching prediction.

This is **exact only for the explicitly restricted, exterior-zero-conditioned model**. It is not the true local marginal of the full circuit because omitted exterior variables are not summed over. It uses no labels or future data.

On the toy and all eight categorical chains, it matched the exact MAP decisions on every syndrome. In each 8-detector/one-round surface fragment it evaluated 27 of 256 syndrome patterns and fell back on the other 229 (89.5%). The observed exact-DEM risk was 0.00092636 versus 0.00094767 for standard matching in Z memory, and 0.00095120 versus 0.00097326 in X memory. In both cases the valid separator-free matching result was lower still (0.00091733 and 0.00094939 respectively). The two-round fragments exceed this local event-cap regime and were not scored by this local method.

The enumerated work is `O(2^k (k + 2^m))` in a direct implementation for `k` retained Bernoulli mechanisms and `m` logical bits, with an explicit cap `k≤12` (4,096 configurations). Runtime for all 256 one-round syndromes was 4.42 ms for Z and 6.73 ms for X in this environment, including fallback decisions. The toy's maximum was 64 configurations per syndrome. These are small-case measurements only; no full-circuit throughput claim is made.
""")

write("BASELINE_COMPARISONS.md", """
# Decoder comparisons

| Decoder | Interpretation | What was compared |
|---|---|---|
| Exact categorical MAP | Best logical-observable posterior decision under the stated categorical channel | Exhaustive all-syndrome risk for toy chains |
| Exact independent-DEM MAP | Best posterior under mutually independent DEM mechanisms | Exhaustive toy and reduced-surface reference; on categorical cases, scored under the actual categorical channel |
| PyMatching standard | Matching prediction from the separated DEM | Same syndromes/models as the correlation-enabled arm |
| PyMatching correlated | PyMatching two-pass correlation-aware matching | Same DEM as standard PM; not exact Bayesian inference |
| Separator-free PyMatching | Graphlike full-event rewrite, only after support validation | Valid in toy and graphlike family; rejected for hyperedges |
| Local restricted posterior | Exact under exterior-zero conditioning | Compared syndrome-by-syndrome; fallback and cap behavior recorded |

## Main findings

On the historical categorical toy, exact MAP risk is 0.0600; standard and correlation-enabled matching are both 0.1128; valid separator-free matching is 0.0600. Across the eight categorical chain toys, standard and correlated matching predictions are identical in every case. Separator-free matching improves upon separated matching, but only matches exact MAP in two of eight cases; the bounded local method matches MAP in these tiny fixtures. This illustrates that matching decisions differ materially from posterior MAP in some bounded models, while the small rewrite is not a proven full-scale remedy.

For reduced exact-DEM surface fragments, standard and correlation-enabled predictions coincide on the one-round fragments. On two-round fragments, they disagree on 12,048 of 65,536 syndromes (Z) and 18,122 of 65,536 (X); logical risks are 0.001957 vs 0.001922 (Z), and 0.002213 vs 0.002808 (X). The latter is a regression for correlation-enabled matching in this exact-DEM finite fragment. These are deterministic DEM-model risks, not sampled categorical-circuit performance estimates.

All comparisons share the same probability models and enumerate feasible syndromes. There are no Monte Carlo error bars. The primary caveat is model: independent DEM mechanisms are not identical to native categorical Pauli channels in general, though the toy runs directly quantify categorical-vs-DEM differences.
""")

write("COMPLEXITY_ASSESSMENT.md", f"""
# Complexity and resource assessment

## Measurements in this bounded investigation

- Latest end-to-end deterministic job: {R['elapsed_seconds']:.3f} s.
- Peak process working set: {R['peak_memory']['peak_working_set_bytes']:,} bytes ({R['peak_memory']['peak_working_set_bytes']/1024**2:.1f} MiB); below the 2 GiB limit.
- Standard/correlated graph builds on 40-detector, five-round DEMs: about 1.7–2.4 ms per graph in the current run (timing is environment-specific).
- 8-detector exact independent-DEM posterior: 256 syndromes, 29 mechanisms, 0.00091–0.00095 exact risk; local posterior enumerates up to 4,096 configurations and takes 4.4–6.7 ms for the full syndrome sweep.
- 16-detector exact DEM inference enumerated up to 65,536 syndromes for the reduced fragments. It is not a full 5-round decode benchmark.

## Scaling limits

Global exact inference over `m` detector bits stores a distribution with up to `2^m` syndrome states (and more if joint logical states are stored). The previous verified scaling investigation reported roughly 256 MiB at 24 detectors and estimated 64 GiB at 32 detectors; the 40-detector five-round case was estimated at 16 TiB for that representation and skipped. These are historical measurements/estimates from `categorical_inference_investigation`, not runs in this phase. Direct categorical fault-configuration enumeration grows exponentially with fault locations (the existing full five-round model is far beyond a feasible exhaustive loop).

Candidate A adds linear preprocessing over DEM events and no asymptotic decoding change, but only applies if every complete event is graphlike and not logical-only. Candidate B has an explicit local enumeration cap of 12 events, at most 4,096 Bernoulli configurations. Its current syndrome selection covers only 10.5% of one-round surface-fragment syndromes without fallback. No evidence establishes acceptable full distance-3/five-round decoding performance, let alone larger distances.

No stochastic simulation, Phase 2B test decoding, large parameter search, or >2 GiB job was run.
""")

write("NOVELTY_CHECK.md", """
# Novelty and prior-method check

This investigation does not support a publication-level novelty claim for either candidate.

Stim's documented DEM syntax defines `^` as a suggested decomposition marker, not a physical event. PyMatching already provides standard and two-pass correlation-aware matching for decomposable hyperedge information. Belief-matching and belief-find use belief-propagation information to improve graph-decoder weights/decisions; BP+OSD and related inference methods address broader non-pairwise decoding. Thus the present work is best described as a small implementation audit and feasibility study around representation sensitivity and a deliberately restricted local exact subproblem.

Potential engineering contribution: an explicit validation rule that only rewrites a DEM mechanism to a direct matching edge when its *complete* parity support is graphlike and preserves its probability and observable mask, while rejecting hyperedges and logical-only events. Candidate B demonstrates a small exact conditional calculation with a transparent boundary approximation and fallback. Neither is a demonstrated new decoder architecture.

References checked:

1. [Stim DEM file format](https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md) — separator and event semantics.
2. Higgott, [PyMatching: A Python package for decoding quantum codes with minimum-weight perfect matching](https://arxiv.org/abs/2105.13082), ACM TQC 3 (2022) — matching graph decoder.
3. Higgott et al., [Improved decoding of circuit noise and fragile boundaries of tailored surface codes](https://doi.org/10.1103/PhysRevX.13.031007), PRX 13, 031007 (2023) — belief-matching/belief-find.
4. Roffe et al., [Decoding across the quantum low-density parity-check code landscape](https://doi.org/10.1103/PhysRevResearch.2.043423), PR Research 2, 043423 (2020) — belief propagation plus ordered-statistics postprocessing.
5. Higgott and Gidney, [Sparse Blossom: correcting a million errors per core second with minimum-weight matching](https://arxiv.org/abs/2303.15933) — PyMatching v2 matching implementation context.

These references establish related techniques, not exhaustive priority or novelty. A broader literature review would be needed before any novelty claim.
""")

write("FINAL_DECISION.md", """
# Final decision: PARTIAL

## Answers to the research questions

1. **Does the toy failure generalize?** Representation sensitivity recurs in eight categorical toy channels, a fixed 64-cell graphlike family, and exact-DEM surface fragments. It has not been shown to generalize into a safe full-circuit fix.
2. **Can separator removal worsen decisions?** In the 64 preregistered *valid graphlike* grid cells it improved 59 and tied 5, worsening none. That narrow result does not establish universal safety. For complete events with >2 detector symptoms or logical-only faults, erasure is invalid; this implementation rejects those cases. No valid full-surface separator-free comparison was possible.
3. **Can a principled representation avoid the toy failure?** Yes, in the limited case where the full event has ≤2 detector symptoms and is not logical-only: preserve its entire probability and parity mask as one graphlike mechanism. This exactly fixes the toy, but the Phase 2B five-round DEM contains many hyperedges, so the rule does not cover it.
4. **Can bounded local inference improve matching?** It agrees with exact MAP in tiny categorical toys, but in one-round surface fragments it has low syndrome coverage, falls back 89.5%, and is slightly worse than valid separator-free matching. No two-round/full-circuit result exists for the local method.
5. **What is the cost?** The complete bounded investigation took 4.53 s and peaked near 98 MiB. Local full-syndrome one-round sweeps took 4.4–6.7 ms with at most 4,096 local assignments. Exponential global exact inference is not feasible at 40 detectors in the previous state-vector implementation.
6. **Does either candidate justify a full decoder?** No. Candidate A is a conservative preprocessing guard but rejected all six target full-round DEMs. Candidate B is an instructive toy reference, but its restricted boundary assumption and low coverage prevent a credible full decoder claim.
7. **Best evidence-supported next direction?** Treat this as an implementation/representation audit, then evaluate established hypergraph/factor-graph or belief-based methods against carefully verified exact small cases before proposing a distinct decoder. Do not claim novelty or improvement based on this pilot.

## Decision rationale

**PARTIAL** is the correct gate: both candidate ideas are correct in clearly limited domains, with reproducible exact results and manageable toy-case cost, but neither demonstrates the required multi-instance full-circuit improvement, scaling, and semantic coverage for GO. It is not NO-GO because the diagnosis and graphlike rewrite are valid, useful engineering results; it is not GO because the central full-circuit mechanism remains unresolved.

No confirmatory experiment is authorized or was run. The work used no stochastic Phase 2B evaluation shots, did not access Phase 2B full-test labels, and preserves all prior negative results.
""")

write("REPRODUCE.md", """
# Reproduction guide

Run from the repository root in an environment with Python 3.12, Stim 1.16, PyMatching 2.4, and NumPy 2.5 (tested versions are recorded in `RESULTS.json`). No network access or new data download is needed once dependencies are installed.

```powershell
python -B -m unittest discover -s outputs/matching_representation_investigation -v
python -B outputs/matching_representation_investigation/matching_investigation.py
python -B outputs/matching_representation_investigation/verify_results.py
python -B outputs/matching_representation_investigation/verify_inputs.py
python -B outputs/matching_representation_investigation/verify_manifest.py
```

`matching_investigation.py` recreates only this investigation's deterministic outputs (`RESULTS.json`, `SEPARATOR_GRID.csv`, and `SURFACE_FRAGMENT_SUMMARY.csv`). `verify_results.py` independently rescales the stored exact references and predictions; `verify_inputs.py` checks historical hashes and writes only `PHASE0_VERIFICATION.json`; `verify_manifest.py` reads the local manifest and checks the covered local files. The 5.9 MB result JSON contains the bounded predictions and exact distributions needed for rescoring. No simulator shots or historical files are generated or changed.

`CASE_PLAN.json` was created before the analysis run and contains the fixed case/seed plan. The preserved `*_BEFORE_FIXTURE_CORRECTION` files are a diagnostic record of an initial fixture with unequal anchor distributions; they are excluded from the final planned comparison. `REPRESENTATION_RULE_CLARIFICATION.md` records the added logical-only-event rejection discovered during validation.

All reported risks are exact probability sums for the specific model named in each row. No Monte Carlo uncertainty estimates are applicable. Do not compare native categorical risk and independent-DEM risk as if they were the same noise law.
""")

print(json.dumps({"written": sorted(p.name for p in HERE.glob("*.md"))}, indent=2))
