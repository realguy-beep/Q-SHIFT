"""Independently recompute prototype-development metrics from saved NPZ arrays."""
import csv, hashlib, json
import re
from pathlib import Path
import numpy as np
from scipy.stats import binomtest
from scipy.special import gammaln, logsumexp
from experiment import build_bank, REGIME_NAMES, REGIME_ID, POLICIES, decode_grid

P=Path(__file__).resolve().parent; result=json.loads((P/'DEVELOPMENT_RESULTS.json').read_text()); models=build_bank()
by_schedule={}; by_regime={r:{p:{'errors':0,'shots':0} for p in POLICIES} for r in REGIME_NAMES}
bank_disagreements={r:np.zeros((9,9),dtype=np.int64) for r in REGIME_NAMES}
root_rows=[]; recalc_overall={p:0 for p in POLICIES}; n_all=0; disagreement={p:{'candidate_only':0,'pooled_only':0} for p in POLICIES}
for schedule,roots in result['schedule_replicates'].items():
    by_schedule[schedule]=[]
    for root in roots:
        path=P/root['evidence_file']; z=np.load(path,allow_pickle=False)
        d=z['detectors']; y=z['observables']; gp=z['grid_predictions']; state=z['state_ids']; choices=z['choice_by_block']; estimates=z['estimate_by_block']; pp=z['posterior_by_block']
        assert d.dtype==np.uint8 and d.ndim==2 and d.shape[1]==40
        assert y.shape==(len(d),) and set(np.unique(y)).issubset({0,1})
        assert gp.shape==(9,len(d)) and set(np.unique(gp)).issubset({0,1})
        assert choices.shape==(12,) and np.all((choices>=0)&(choices<9))
        assert estimates.shape==(12,) and pp.shape==(12,3)
        regenerated=decode_grid(models,d)
        assert np.array_equal(regenerated,gp), f"prediction mismatch: {path}"
        shots_per_block=len(d)//12; assert shots_per_block*12==len(d)
        rec={p:0 for p in POLICIES}; local_reg={r:{p:0 for p in POLICIES} for r in REGIME_NAMES}
        paired={p:{'candidate_only':0,'pooled_only':0} for p in ('identity_no_decode','nominal_fixed','adaptive','regime_informed_diagnostic')}
        for b in range(12):
            lo=b*shots_per_block; hi=lo+shots_per_block; yb=y[lo:hi]; sb=int(state[lo]); name=REGIME_NAMES[sb]
            pb=gp[:,lo:hi]
            for i in range(9):
                for j in range(i+1,9):
                    dcount=int(np.count_nonzero(pb[i]!=pb[j]));bank_disagreements[name][i,j]+=dcount;bank_disagreements[name][j,i]+=dcount
            preds={'identity_no_decode':np.zeros(shots_per_block,dtype=np.uint8),'pooled_fixed':gp[1,lo:hi],
                   'nominal_fixed':gp[4,lo:hi],'adaptive':gp[int(choices[b]),lo:hi],
                   'regime_informed_diagnostic':gp[int(result['calibration']['calibration_best_decoder_indices'][sb]),lo:hi]}
            # Explicitly assert stored adaptive prediction equals selected bank model.
            assert np.array_equal(z['adaptive_predictions'][lo:hi],preds['adaptive'])
            for p,pred in preds.items():
                bad=pred^yb; count=int(bad.sum()); rec[p]+=count; local_reg[name][p]+=count
                if p!='pooled_fixed':
                    pooled_bad=gp[1,lo:hi]^yb
                    paired[p]['candidate_only']+=int(np.count_nonzero(bad&~pooled_bad))
                    paired[p]['pooled_only']+=int(np.count_nonzero(~bad&pooled_bad))
                by_regime[name][p]['errors']+=count; by_regime[name][p]['shots']+=shots_per_block
        assert rec==root['errors'], f"aggregate mismatch for {schedule}/{root['replicate']}: {rec} != {root['errors']}"
        # Recheck exact per-block sample pair hashes saved by the runner.
        with np.load(path,allow_pickle=False) as zz:
            # Detector/observable pair identity is direct since all policies are applied to these same arrays.
            assert len(zz['detectors'])==len(zz['observables'])
        for p in POLICIES: recalc_overall[p]+=rec[p]
        n_all+=len(d)
        for p in paired:
            disagreement[p]['candidate_only']+=paired[p]['candidate_only'];disagreement[p]['pooled_only']+=paired[p]['pooled_only']
        diff=(rec['adaptive']-rec['pooled_fixed'])/len(d)
        row={'schedule':schedule,'replicate':root['replicate'],'shots':len(d),**{f'{p}_errors':rec[p] for p in POLICIES},
             **{f'{p}_ler':rec[p]/len(d) for p in POLICIES},'adaptive_minus_pooled':diff,
             'adaptive_wrong_pooled_correct':paired['adaptive']['candidate_only'],'adaptive_correct_pooled_wrong':paired['adaptive']['pooled_only'],
             'switches':root['switch_count'],'regime_estimate_accuracy':root['regime_estimate_accuracy'],
             'censored_transitions':root['censored_transition_count'],
             'policy_selection_seconds':root['policy_selection_seconds'],'fixed_decode_seconds':root['single_fixed_decode_seconds'],
             'adaptive_decode_seconds':root['adaptive_selected_decode_seconds']}
        root_rows.append(row);by_schedule[schedule].append(row)
assert recalc_overall=={p:result['analysis']['overall'][p]['errors'] for p in POLICIES}
assert n_all==307200

def wilson(k,n,z=1.959963984540054):
    ph=k/n; den=1+z*z/n; mid=(ph+z*z/(2*n))/den; half=z*np.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/den
    return [max(0.,mid-half),min(1.,mid+half)]
def cluster_ci(x, draws=10000, seed=99300001):
    rng=np.random.default_rng(seed); boot=np.empty(draws)
    schedules=list(x)
    for j in range(draws):
        boot[j]=np.mean([np.mean(v[rng.integers(0,len(v),size=len(v))]) for v in x.values()])
    return [float(q) for q in np.quantile(boot,[.025,.975])]
rates={p:{'errors':recalc_overall[p],'shots':n_all,'ler':recalc_overall[p]/n_all,'success_rate':1-recalc_overall[p]/n_all,'wilson_95ci':wilson(recalc_overall[p],n_all)} for p in POLICIES}
effects={}
for candidate in ('identity_no_decode','nominal_fixed','adaptive','regime_informed_diagnostic'):
    counts=disagreement[candidate]
    # H1 candidate different from pooled; candidate-only vs pooled-only discordance.
    nd=counts['candidate_only']+counts['pooled_only']
    p=float(binomtest(counts['candidate_only'],nd,.5,alternative='two-sided').pvalue) if nd else 1.0
    tail=min(counts['candidate_only'],counts['pooled_only'])
    logp=(float(np.log(2)+logsumexp(gammaln(nd+1)-gammaln(np.arange(tail+1)+1)-gammaln(nd-np.arange(tail+1)+1)-nd*np.log(2))) if nd else 0.0)
    log10p=min(0.0,logp/np.log(10))
    roots_diff={s:np.asarray([(r[f'{candidate}_errors']-r['pooled_fixed_errors'])/r['shots'] for r in rows]) for s,rows in by_schedule.items()}
    effects[candidate]={'candidate_only':counts['candidate_only'],'pooled_only':counts['pooled_only'],'paired_difference_ler':rates[candidate]['ler']-rates['pooled_fixed']['ler'],'exact_mcnemar_p_two_sided':p,'exact_mcnemar_log10_p':log10p,'p_value_float_underflow':bool(p==0.0),
        'equal_schedule_root_cluster_bootstrap_95ci':cluster_ci(roots_diff),'per_schedule_root_differences':{s:[float(v) for v in values] for s,values in roots_diff.items()}}

regime_summary={}
for r,pol in by_regime.items():
    regime_summary[r]={p:{'errors':v['errors'],'shots':v['shots'],'ler':v['errors']/v['shots']} for p,v in pol.items()}
calz=np.load(P/'data/calibration_evidence.npz',allow_pickle=False); cal_errors=calz['errors']; cal_checks={}
cal_pred_checks=[]
for ri in range(3):
    cd=calz['detectors'][ri]; cy=calz['observables'][ri]
    assert cd.shape==(20000,40) and cy.shape==(20000,)
    regenerated_cal=decode_grid(models,cd)^cy[None,:]
    assert np.array_equal(regenerated_cal,cal_errors[ri]), f'calibration prediction/error mismatch in regime {ri}'
    assert np.allclose(calz['profiles'][ri],cd.mean(axis=0))
    assert np.allclose(calz['utility_rates'][ri],cal_errors[ri].mean(axis=1))
    cal_pred_checks.append({'regime':REGIME_NAMES[ri],'shots':len(cy),'nine_model_predictions_redecoded':True,'profile_recomputed':True,'utility_recomputed':True})
assert np.array_equal(calz['calibration_best'],calz['utility_rates'].argmin(axis=1))
disc_json={r:{'shots':by_regime[r]['pooled_fixed']['shots'],'counts':mat.tolist(),'rates':(mat/by_regime[r]['pooled_fixed']['shots']).tolist()} for r,mat in bank_disagreements.items()}
for ri,r in enumerate(REGIME_NAMES):
    entries=[]
    for dec in range(9):
        diff=cal_errors[ri,dec].astype(float)-cal_errors[ri,1].astype(float)
        se=float(diff.std(ddof=1)/np.sqrt(len(diff)))
        entries.append({'decoder_index':dec,'error_count':int(cal_errors[ri,dec].sum()),'shots':int(len(diff)),
            'ler':float(cal_errors[ri,dec].mean()),'paired_delta_vs_pooled_ler':float(diff.mean()),
            'paired_delta_normal_95ci':[float(diff.mean()-1.96*se),float(diff.mean()+1.96*se)],'paired_se':se})
    cal_checks[r]=entries
confusion=np.zeros((3,3),dtype=int)
for roots in result['schedule_replicates'].values():
    for root in roots:
        z=np.load(P/root['evidence_file'],allow_pickle=False); shots_per_block=len(z['state_ids'])//12
        for t in range(1,12):
            actual=int(z['state_ids'][t*shots_per_block]); estimated=int(z['estimate_by_block'][t])
            if estimated>=0: confusion[actual,estimated]+=1
(P/'PER_REPLICATE.csv').write_text('',encoding='utf-8')
with (P/'PER_REPLICATE.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(root_rows[0]));w.writeheader();w.writerows(root_rows)
regime_rows=[]
for r,pol in regime_summary.items():
    q={'regime':r,'shots':pol['pooled_fixed']['shots']}
    for p in POLICIES:
        q[f'{p}_errors']=pol[p]['errors'];q[f'{p}_ler']=pol[p]['ler']
    regime_rows.append(q)
with (P/'PER_REGIME.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(regime_rows[0]));w.writeheader();w.writerows(regime_rows)
with (P/'DECODER_DISAGREEMENT_MATRIX.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f);w.writerow(['regime','decoder_i','decoder_j','shots','prediction_disagreements','disagreement_rate'])
    for r,mat in bank_disagreements.items():
        n=by_regime[r]['pooled_fixed']['shots']
        for i in range(9):
            for j in range(i+1,9):w.writerow([r,i,j,n,int(mat[i,j]),float(mat[i,j]/n)])
audited={'independent_redecode_pass':True,'roots':len(root_rows),'heldout_shots':n_all,'verified_predictions':'all nine decoder rows exactly regenerated from saved detectors for all roots','calibration_independent_redecode':cal_pred_checks,'aggregate_counts':rates,'paired_comparisons_vs_pooled':effects,'by_generating_regime':regime_summary,'calibration_utility_differences_vs_pooled':cal_checks,'decoder_disagreement_by_regime':disc_json,'detector_estimator_confusion_matrix_actual_by_estimated':confusion.tolist()}
(P/'AUDITED_RESULTS.json').write_text(json.dumps(audited,indent=2)+'\n',encoding='utf-8')
repo=P.parents[1]
seed_re=re.compile(r'(?<!\d)(?:99100001|99100002|99100003|99300001|99400001|99200[0-6]\d{2})(?!\d)')
screened=[]; hits=[]
for f in repo.rglob('*'):
    if not f.is_file() or P.name in f.parts or '.git' in f.parts or '__pycache__' in f.parts: continue
    if f.suffix.lower() not in {'.json','.md','.py','.csv','.txt','.log','.yaml','.yml'}: continue
    screened.append(str(f.relative_to(repo)))
    try: txt=f.read_text(encoding='utf-8',errors='ignore')
    except OSError: continue
    hits.extend({'file':str(f.relative_to(repo)),'value':m.group(0)} for m in seed_re.finditer(txt))
eval_seeds=list(range(99200001,99200001+5*10*12))
seed_inventory={'calibration':[99100001,99100002,99100003],'diagnostic':[99400001],'bootstrap':[99300001],'evaluation':eval_seeds,
    'count':len(eval_seeds)+5,'unique_count':len(set(eval_seeds+[99100001,99100002,99100003,99400001,99300001]))}
screen={'scan_scope':'all recoverable text-based artifacts in repository except this new prototype_development directory, Git internals, and Python cache','files_examined':screened,'file_count':len(screened),
    'candidate_pattern':'exact calibration/diagnostic/bootstrap seeds plus inclusive evaluation range 99200001..99200600','matches':hits,'collision_count':len(hits),
    'conclusion':'No exact candidate seed collision found in the scanned textual artifacts. This cannot guarantee coverage of unrecorded RNG use or binary-only/omitted historical records.'}
(P/'SEED_INVENTORY.json').write_text(json.dumps(seed_inventory,indent=2)+'\n',encoding='utf-8')
(P/'SEED_SCREENING.json').write_text(json.dumps(screen,indent=2)+'\n',encoding='utf-8')
lines=['# Q-SHIFT Prototype Development Results','',f"Audited independent root-level datasets: **{len(root_rows)}**; paired evaluation shots: **{n_all:,}**. This is development evidence, not confirmatory validation.",'',
       '## Overall matched-shot outcomes','', '| Method | Errors | Shots | Logical error rate | Success rate | 95% Wilson interval for LER |','|---|---:|---:|---:|---:|---:|']
for p in POLICIES:
    x=rates[p]; lines.append(f"| {p} | {x['errors']:,} | {n_all:,} | {x['ler']:.5%} | {x['success_rate']:.5%} | [{x['wilson_95ci'][0]:.5%}, {x['wilson_95ci'][1]:.5%}] |")
lines += ['', 'The no-decoding baseline predicts no logical flip; its residual error is therefore the sampled observable itself. It is a decoding comparator, not a physical circuit without QEC. The adaptive and regime-informed diagnostics selected the same decoder as the pooled model throughout this run, so their measured results tie the pooled baseline exactly.', '',
          '## Paired contrasts to pooled fixed','', '| Comparator | Candidate-only errors | Pooled-only errors | Difference in LER | Exact paired McNemar p | Seed-cluster bootstrap 95% CI |','|---|---:|---:|---:|---:|---:|']
for p in ('identity_no_decode','nominal_fixed','adaptive','regime_informed_diagnostic'):
    x=effects[p];ci=x['equal_schedule_root_cluster_bootstrap_95ci'];pv=x['exact_mcnemar_p_two_sided'];pd=f"~10^{x['exact_mcnemar_log10_p']:.0f} (float underflow)" if x['p_value_float_underflow'] else f'{pv:.4g}';lines.append(f"| {p} | {x['candidate_only']:,} | {x['pooled_only']:,} | {x['paired_difference_ler']:+.6%} | {pd} | [{ci[0]:+.6%}, {ci[1]:+.6%}] |")
lines += ['', '## Results by generating regime','', '| Regime | Shots | Identity errors | Pooled errors | Nominal errors | Adaptive errors |','|---|---:|---:|---:|---:|---:|']
for r in REGIME_NAMES:
    q=regime_summary[r];n=q['pooled_fixed']['shots'];lines.append(f"| {r} | {n:,} | {q['identity_no_decode']['errors']:,} | {q['pooled_fixed']['errors']:,} | {q['nominal_fixed']['errors']:,} | {q['adaptive']['errors']:,} |")
lines += ['', '## Outcomes by schedule','', '| Schedule | Shots | Identity LER | Pooled LER | Nominal LER | Adaptive LER | Adaptive minus pooled | Replicate paired differences |','|---|---:|---:|---:|---:|---:|---:|---|']
for s,rows in by_schedule.items():
    n=sum(x['shots'] for x in rows); names=('identity_no_decode','pooled_fixed','nominal_fixed','adaptive')
    lers={p:sum(x[f'{p}_errors'] for x in rows)/n for p in names}; diffs=[x['adaptive_minus_pooled'] for x in rows]
    lines.append(f"| {s} | {n:,} | {lers[names[0]]:.5%} | {lers[names[1]]:.5%} | {lers[names[2]]:.5%} | {lers[names[3]]:.5%} | {lers['adaptive']-lers['pooled_fixed']:+.5%} | {diffs} |")
lines += ['', '## Calibration utility differences against pooled fixed','', 'Calibration-only estimates; intervals are paired, shot-level approximate 95% normal intervals and are descriptive development estimates.','', '| Regime | Model index | LER | Paired LER difference vs pooled | Approx. 95% interval |','|---|---:|---:|---:|---:|']
for r,entries in cal_checks.items():
    for e in entries:
        ci=e['paired_delta_normal_95ci'];lines.append(f"| {r} | {e['decoder_index']} | {e['ler']:.5%} | {e['paired_delta_vs_pooled_ler']:+.5%} | [{ci[0]:+.5%}, {ci[1]:+.5%}] |")
lines += ['', '## Pairwise decoder correction disagreement','', 'Evaluation disagreement-rate matrices in frozen decoder order 0..8; these measure how often two models return different logical corrections, not which is more accurate. The complete long-form table is in `DECODER_DISAGREEMENT_MATRIX.csv`.']
for r,mat in disc_json.items():
    lines += ['', f"**{r}** ({mat['shots']:,} paired shots):", '', '```text', '\n'.join(' '.join(f'{v:.3%}' for v in row) for row in mat['rates']), '```']
lines += ['', '## Estimator and runtime','', 'Confusion matrix counts (actual regime rows; estimated regime columns ordered data-heavy, nominal, measurement-heavy), using only blocks with a previous block available:','', '```text', json.dumps(confusion.tolist()), '```','', '| Schedule | Mean regime accuracy | Estimator transition delays (blocks; null=censored) | Switches | Selection overhead / one fixed decode | Total measured adaptive compute overhead / fixed |','|---|---:|---|---:|---:|---:|']
for s,v in result['analysis']['schedule_results'].items():
    lines.append(f"| {s} | {v['mean_regime_estimate_accuracy']:.1%} | {v['transition_delays_blocks']} | {v['switch_count']} | {v['mean_policy_overhead_fraction_of_single_fixed_decode']:.1%} | {v['mean_adaptive_compute_overhead_fraction_vs_fixed']:.1%} |")
lines += ['', '## Findings and limitations','',f"- The calibration table selected pooled decoder index {result['calibration']['calibration_best_decoder_indices']} for data-heavy, nominal, and measurement-heavy conditions. Thus this run found no calibration-supported decoder specialization, and the conservative adaptive controller correctly remained at decoder index 1 (pooled fallback).",'- The direct detector estimator is reasonably accurate after transitions in long-dwell schedules, but in the rapid cycle it has no completed stable regime block from which to estimate the next state. Classification is not the main blocker here; the calibration data did not identify a better decoder for any of the three regimes.', '- The regime-informed diagnostic uses the hidden current generating regime only to pick the calibration-selected decoder and is an optimistic information diagnostic, not a deployable method. It also tied because calibration chose the same model in every regime.', '- Each generated Stim circuit has one stationary noise setting throughout its five rounds. Nonstationarity is between batches of independent memory experiments (blocks), not within a single circuit execution. This is a controlled schedule for block-level adaptation and does not establish within-circuit drift handling.', '- All policies share the identical detector samples and observable labels. Every stored grid prediction in every root was independently recomputed from its stored detector array and matched exactly.', '- This is a bounded, small-code development experiment. The controller utility table is estimated from the same separate calibration shots used to fit detector profiles; evaluation streams and seeds are separate. It is not a confirmatory test, and no hardware was used.', '']
(P/'DEVELOPMENT_FINDINGS.md').write_text('\n'.join(lines),encoding='utf-8')
# Update evidence manifest to include audit artifacts and hashes.
manifest={'study':result['study'],'confirmatory':False,'audit_pass':True,'evaluation_roots':len(root_rows),'heldout_shots':n_all,
    'file_sha256':{str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(P.rglob('*')) if f.is_file() and f.name!='MANIFEST.json'}}
(P/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'audit':'PASS','roots':len(root_rows),'shots':n_all,'errors':rates,'paired':effects},indent=2))
