"""Supplemental selection-uncertainty and headroom summaries from frozen evidence."""
import json, sys
from pathlib import Path
import numpy as np

P=Path(__file__).resolve().parent; ROOT=P.parents[1]; PREV=ROOT/'outputs/prototype_development'
sys.path.insert(0,str(PREV))
from experiment import REGIME_NAMES, decode_grid
from decoder_bank import build_bank
models=build_bank(); z=np.load(PREV/'data/calibration_evidence.npz',allow_pickle=False)
calibration=[]
for r,name in enumerate(REGIME_NAMES):
    d=z['detectors'][r]; y=z['observables'][r]; pred=decode_grid(models,d); err=pred^y[None,:]
    assert np.array_equal(err,z['errors'][r])
    base=err[1].astype(float); entries=[]
    for i in range(9):
        candidate=err[i].astype(float); diff=candidate-base; se=float(diff.std(ddof=1)/np.sqrt(len(y)))
        entries.append({'decoder_index':i,'calibration_errors':int(err[i].sum()),'shots':len(y),'ler':float(candidate.mean()),
            'paired_delta_ler_vs_decoder1':float(diff.mean()),'approx_paired_95ci':[float(diff.mean()-1.96*se),float(diff.mean()+1.96*se)],
            'candidate_only':int(np.count_nonzero(err[i]&~err[1])),'decoder1_only':int(np.count_nonzero(~err[i]&err[1]))})
    calibration.append({'regime':name,'best_index_tie_lowest':int(np.argmin(err.mean(axis=1))),'models':entries})

head=json.loads((P/'ORACLE_HEADROOM.json').read_text()); n=head['A_best_global_fixed_errors']; total_shots=600000
oracles=[]
for label,key in [('A_best_global_fixed','A_best_global_fixed_errors'),('B_calibration_per_regime','B_calibration_selected_per_regime_errors'),
                  ('C_stage1_pooled','C_stage1_pooled_fixed_index1_errors'),('D_nominal','D_nominal_index4_errors'),
                  ('retrospective_per_regime_oracle','retrospective_oracle_per_regime_errors_total'),
                  ('retrospective_per_shot_oracle','retrospective_oracle_per_shot_errors_total')]:
    e=int(head[key]);oracles.append({'method':label,'errors':e,'shots':total_shots,'ler':e/total_shots,'headroom_vs_A_errors':n-e,
        'absolute_headroom_ler':(n-e)/total_shots,'relative_error_reduction_vs_A':(n-e)/n if n else None,
        'test_label_selection_used':label.startswith('retrospective')})
head['comparison_rates_and_descriptive_headroom']=oracles
head['calibration_selection_uncertainty']=calibration
head['hindsight_oracle_inference_note']='Hindsight oracles select and score using the same evaluation labels; reported headroom is descriptive and optimistic, without a confirmatory confidence interval.'
(P/'ORACLE_HEADROOM.json').write_text(json.dumps(head,indent=2)+'\n',encoding='utf-8')
(P/'CALIBRATION_SELECTION_UNCERTAINTY.json').write_text(json.dumps(calibration,indent=2)+'\n',encoding='utf-8')

# Decode equivalence classes observed on the fresh 600k paired evaluation sample.
rows=json.loads((P/'PHASE2A_RESULTS.json').read_text())['prediction_disagreement']
disagreement_totals=np.zeros((9,9),dtype=np.int64)
for regime,matrix in rows.items():disagreement_totals+=np.asarray(matrix,dtype=np.int64)
remaining=set(range(9));groups=[]
while remaining:
    i=min(remaining); g=[j for j in sorted(remaining) if i==j or disagreement_totals[i,j]==0]
    groups.append(g);remaining-=set(g)
equiv={'evaluation_shots':600000,'decoder_groups_identical_on_all_observed_samples':groups,
       'disagreement_counts':disagreement_totals.tolist(),'interpretation':'Finite-sample prediction equivalence only; it does not prove equality on all possible detector patterns.'}
(P/'OBSERVED_EQUIVALENCE_GROUPS.json').write_text(json.dumps(equiv,indent=2)+'\n',encoding='utf-8')

md=['# Q-SHIFT Phase 2A findings','',
    '## Executive finding','',
    'The nine candidate DEMs share the same detector graph topology and have nine different edge-weight fingerprints. On the fresh paired evaluation set, they form six observed logical-prediction equivalence groups: '+', '.join('{' + ','.join(map(str,g)) + '}' for g in groups)+'. These are finite-sample groups, not mathematical equivalence proofs.', '',
    'Calibration selected zero-based decoder-grid index 1 as the best global fixed model and index 1 in all three regimes. The fresh 600,000-shot evaluation therefore gives the same result for the calibrated per-regime policy and best global fixed decoder: 4,192 errors (LER 0.69867%) each. Headroom is exactly zero conditional on these selected indices; the paired bootstrap CI is [0, 0] and root sign-flip p=1. This is not an adaptive advantage.', '',
    '## Prior evidence integrity','',
    'The prior prototype manifest passed SHA-256 verification. All 50 prior evaluation bundles were independently decoded again. The 307,200-shot totals reproduced: identity/no decode 19,726 errors, pooled index 1 1,989, nominal index 4 1,976. Those already-inspected samples were not reused as the Phase 2A fresh evaluation.', '',
    '## Decoder graph and logical output behavior','',
    'All nine circuits produce 40 detectors and one logical observable; each matching graph has 142 edges and the same topology hash. The weighted edge graph differs in all nine configurations. Twelve matching edges carry logical fault ID 0 for each model. The stored arrays contain detector bits, observable labels, and predicted logical flips, not physical correction chains; this analysis does not infer physical corrections.', '',
    'Across 600,000 new shots, most tested pairs return the same predicted logical flip. The most distinct pair has under 1% disagreement in data-heavy noise; disagreement is lower in nominal and measurement-heavy noise. Full regime-stratified counts, candidate-only errors, baseline-only errors, error-indicator correlations, and syndrome signatures are in `DECODER_DISAGREEMENT.csv` and `SYNDROME_DISAGREEMENT_PATTERNS.json`.', '',
    '## Regime specialization and uncertainty','',
    '| Regime | Calibration-selected model | Fresh-evaluation lowest point-rate model (retrospective rank only) | Fresh LER for calibrated model | Interpretation |','|---|---:|---:|---:|---|',
    '| data-heavy | 1 | 3 | 1.4125% | Candidate 3 point estimate is lower, but its root-level comparison does not survive Holm correction. |',
    '| nominal | 1 | 1 | 0.488% | Same model wins calibration and evaluation. |',
    '| measurement-heavy | 1 | 2 | 0.1955% | Candidate 2 point estimate is lower, but does not survive Holm correction. |','',
    'Calibration margins are small: zero-based decoder-grid index 1 ties index 2 in measurement-heavy noise and differs by only 0.005 percentage points from the closest point-rate competitors in data-heavy and nominal conditions. Paired calibration intervals and all model ranks are recorded in `CALIBRATION_SELECTION_UNCERTAINTY.json`. Fresh-test root-level comparisons used 20 roots per regime and a 24-test Holm family; no candidate showed a multiplicity-adjusted, credible improvement over the global fixed baseline. Some alternatives were significantly worse.', '',
    '## Oracle headroom','',
    f"The calibration-selected global model and calibration-selected per-regime policy both made {head['A_best_global_fixed_errors']:,} errors. A hindsight per-regime oracle selected separately using test labels makes {head['retrospective_oracle_per_regime_errors_total']:,} errors, a descriptive {n-int(head['retrospective_oracle_per_regime_errors_total'])}-error or {(n-int(head['retrospective_oracle_per_regime_errors_total']))/total_shots:.4%} LER headroom. The per-shot best-of-nine logical-prediction oracle makes {head['retrospective_oracle_per_shot_errors_total']:,} errors, a {n-int(head['retrospective_oracle_per_shot_errors_total'])}-error or {(n-int(head['retrospective_oracle_per_shot_errors_total']))/total_shots:.4%} headroom. These are unattainable diagnostics: they use the same evaluation labels to select and score the model and have no confirmatory interpretation.", '',
    '## Answers and next experiment','',
    '1. **Are the decoders genuinely distinct?** Using zero-based grid indices 0–8, they have distinct weights and DEM hashes but one shared graph topology. Six different logical-output behaviors were observed on these samples; three groups contain exact duplicates in the tested data.',
    '2. **Which performs best by regime?** Calibration chooses zero-based decoder-grid index 1 in every regime. Test-label point rankings favor index 3 in data-heavy, index 1 in nominal, and index 2 in measurement-heavy; the non-baseline rankings are exploratory and fail the predeclared multiplicity gate.',
    '3. **Does regime-informed selection beat the global model?** No. It selects the same index in every regime and ties exactly.',
    '4. **How much oracle headroom?** Zero for the deployable calibration-selected regime policy; positive only for test-label hindsight diagnostics.',
    '5. **Is this bank ready for adaptive QEC?** Not for demonstrating gains under these three scalar depolarizing/noisy-measurement settings. Weight tuning changes few logical decisions, and calibrated utilities do not select a regime-specific model.',
    '6. **Next experiment:** only after a separate protocol decision, use independently motivated hardware-calibrated Pauli bias or different syndrome-readout versus final-data-readout error rates. Freeze noise locations, candidate DEM construction, calibration roots, and held-out seeds before evaluation. Do not tune a controller on this Phase 2A test set.', '',
    'All results are simulation-only. Noise is stationary within each generated five-round circuit; this study does not test within-circuit changes or physical correction chains.']
(P/'PHASE2A_FINDINGS.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print('supplement created; equivalence groups',groups)
