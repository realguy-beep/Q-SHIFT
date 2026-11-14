# Research Limitations and Independent Audit

## Scope and stopping

STOP was received on 2026-11-14. No new research tasks, literature searches, feasibility tests, tests, or experiments were started after that instruction. Final documents synthesize saved work through checkpoint 138. The original ledger has 138 checkpoints; the final stop handoff is documented in `RESEARCH_LOG.md` and `WORK_CHECKPOINT.json`.

## Evidence categories

- **Mathematical certificates:** exact rational polynomial/Bernstein bounds and conditional e-process results for explicitly declared categorical models and parameter rectangles.
- **Deterministic feasibility checks:** static source inspection, deterministic expectation calculations, exact finite-count enumeration, parameter-grid checks, abstract recurrence arithmetic, and code-level invariants recorded in the research log.
- **Literature claims:** reported as claims of the cited paper/source under that paper's model, code, distance, hardware, training, and evaluation conditions. They are not Q-SHIFT replications.
- **Untested hypotheses:** adaptive decoder utility, finite-history accuracy, false-switch behavior in a real controller, and any LER improvement.

## Method and paper counts

The final saved weighted scorecard contains **18 scored method/candidate rows**. This is the exact count under that operational definition; rows may be related variants or policy groups. The literature ledger is not a canonical one-paper-per-row bibliography: it includes duplicate status updates, grouped papers, code/source entries and citation-chain notes. An exact unique-paper count is therefore **not established** in the saved session; any precise unique count would require post-STOP reconciliation, which was not done. This is a recordkeeping limitation, not an assertion that papers were not reviewed.

## Critical audit note: checkpoint 133 threshold predicate

Final review identified that the explicit alpha crossing predicate in `efactor_fixedpoint_mixture_audit.py` used the wrong inequality scaling: it tested against `alpha` rather than `1/alpha`. Consequently, checkpoint 133's logged explicit threshold-crossing count must be treated as **invalid/unverified**. The separate pointwise comparison of the fixed-point lower value to the exact mixture was documented as correct, and its mathematical implication for arbitrary thresholds remains distinct, but the audit is not independently certified here. The pre-fix output is preserved as `EFACTOR_FIXEDPOINT_MIXTURE_AUDIT_PRE_THRESHOLD_FIX.json`; no fix/rerun was performed after STOP. The intended fixed-point audit of the checkpoint-138 lambda bank was not run. This defect materially limits claims about threshold behavior and must be resolved before implementation.

## Source and citation audit

`LITERATURE_DATABASE.md` and `SOURCE_VERIFICATION.md` contain citations and provenance gathered before STOP. Final packaging did not reopen external sources or verify new publication metadata. Sources tagged as preprints, abstracts, repository documentation, or paper claims retain those evidence labels. Coverage is broad but not exhaustive; fast-moving literature may be incomplete.

## Experiment and data audit from saved records

The saved research log and checkpoint record deterministic Stim circuit/DEM construction and deterministic feature-law calculations, including a deterministic support audit. They record **zero Stim sampling, zero detector-shot generation, zero Monte Carlo quantum-error experiments, zero decoder accuracy/LER evaluation, zero model training, zero production seed allocation, and zero Stage 5/sealed-outcome access**. No experiment authorization or freeze was created. No stochastic detector histories were used in the e-factor investigations; abstract factor sequences and exact algebraic/count enumeration are distinguished as deterministic constructions.

No changes were committed, pushed, merged, or made to frozen/protected files. The session's actual research repository was detached at review commit `f7f0fc167960e9499e40785a9b2262295bfecabc`; the only reported worktree change is the untracked research output directory. The separate active exhibition checkout was not modified. No PR was opened or changed.

## Limitations and incomplete areas

- No systematic, de-duplicated bibliography or reproducible search-query ledger sufficient for an exact paper count.
- No exhaustive coverage claim; recent literature may be incomplete.
- No independent external audit of mathematical certificates or code.
- Exact categorical law and approximate DEM are distinct. Finite DEM transfer has a counterexample; do not reuse circuit certificates for DEM streams.
- Finite-history estimator accuracy and boundary behavior are not established by population or asymptotic calculations.
- The robust e-factor covers only explicit model/nuisance rectangles; it is not a deployable controller.
- Bidirectional state machine, reset authority, middle-band behavior, repeated switch budget, and decoder action utility remain unresolved.
- Fixed-point threshold crossing from checkpoint 133 is not validated due to the defect above.
- No complete deployment runtime or full-study compute estimate was completed.
- No policy has demonstrated improvement over a strong static or periodic baseline.

## Final recommendation

**No-go for experiment readiness at this checkpoint.** The most useful next work after supervisor authorization is deterministic correction and independent audit of the fixed-point e-process implementation and controller-state design, followed by an explicitly bounded development-only study against equally informed baselines. Preserve failed artifacts. Never describe feasibility as superiority.
