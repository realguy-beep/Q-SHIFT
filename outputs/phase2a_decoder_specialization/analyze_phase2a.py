"""Independent raw-array verification and statistical analysis for Phase 2A."""
from __future__ import annotations
import csv, hashlib, json, sys
from pathlib import Path
import numpy as np
from scipy.special import gammaln, logsumexp
from scipy.stats import binomtest
import matplotlib.pyplot as plt

P=Path(__file__).resolve().parent; ROOT=P.parents[1]; PREV=ROOT/'outputs/prototype_development'
sys.path.insert(0,str(PREV))
from experiment import REGIME_NAMES, GRID, decode_grid
from decoder_bank import build_bank

def wilson(k,n,z=1.959963984540054):
    if n<=0: return [None,None]
    p=k/n; d=1+z*z/n; mid=(p+z*z/(2*n))/d; half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0.,mid-half),min(1.,mid+half)]

def exact_mcnemar(cand_only, base_only):
    n=int(cand_only+base_only)
    if n==0:return 1.0,0.0
    k=min(int(cand_only),int(base_only))
    lp=float(np.log(2)+logsumexp(gammaln(n+1)-gammaln(np.arange(k+1)+1)-gammaln(n-np.arange(k+1)+1)-n*np.log(2)))
    log10=min(0.0,lp/np.log(10)); return float(binomtest(cand_only,n,.5).pvalue),float(log10)

def holm(pvals):
    p=np.asarray(pvals,float); order=np.argsort(p); out=np.empty_like(p); running=0.0; m=len(p)
    for rank,idx in enumerate(order):
        running=max(running,(m-rank)*p[idx]); out[idx]=min(1.,running)
    return out.tolist()

def clustered_signflip(values, signs):
    x=np.asarray(values,float); obs=float(x.mean())
    if np.all(x==0):return obs,1.0
    null=(signs*x[None,:]).mean(axis=1)
    return obs,float((np.count_nonzero(np.abs(null)>=abs(obs))+1)/(len(null)+1))

def cluster_bootstrap(values, rng, draws=20000):
    x=np.asarray(values,float)
    if np.all(x==0): return [0.0,0.0]
    idx=rng.integers(0,len(x),size=(draws,len(x)))
    vals=x[idx].mean(axis=1)
    return [float(q) for q in np.quantile(vals,[.025,.975])]

def main():
    cfg=json.loads((P/'config.json').read_text()); selection=json.loads((P/'SELECTION.json').read_text())
    seed_manifest=list(csv.DictReader((P/'SEED_MANIFEST.csv').open(encoding='utf-8')))
    assert len(seed_manifest)==60 and len({int(x['seed']) for x in seed_manifest})==60
    models=build_bank(distance=cfg['distance'],rounds=cfg['rounds'])
    nreg=3; roots=20; nd=9
    per_seed=[]; regime_errors=np.zeros((3,9),dtype=np.int64); regime_shots=np.zeros(3,dtype=np.int64)
    pair_counts={r:np.zeros((9,9),dtype=np.int64) for r in range(3)}
    candidate_only={r:np.zeros((9,9),dtype=np.int64) for r in range(3)}
    baseline_only={r:np.zeros((9,9),dtype=np.int64) for r in range(3)}
    error_corr={r:np.zeros((9,9),dtype=float) for r in range(3)}
    pattern_counts={r:{i:{} for i in range(9) if i!=1} for r in range(3)}
    # Raw evidence is independently decoded here; runner counters are not used.
    for entry in seed_manifest:
        r=int(entry['regime_index']); root=int(entry['root_index']); seed=int(entry['seed'])
        z=np.load(P/entry['file'],allow_pickle=False); d=z['detectors']; y=z['observable']; pred=z['predictions']
        assert int(z['regime_id'])==r and int(z['root_index'])==root and int(z['seed'])==seed
        assert d.shape==(10000,40) and d.dtype==np.uint8 and y.shape==(10000,) and set(np.unique(y)).issubset({0,1})
        assert pred.shape==(9,10000) and pred.dtype==np.uint8 and set(np.unique(pred)).issubset({0,1})
        regen=decode_grid(models,d)
        assert np.array_equal(regen,pred),f"fresh prediction recompute failed for {entry['file']}"
        err=pred^y[None,:]; counts=err.sum(axis=1).astype(int); regime_errors[r]+=counts;regime_shots[r]+=len(y)
        row={'regime':REGIME_NAMES[r],'regime_index':r,'root_index':root,'seed':seed,'shots':len(y)}
        row.update({f'decoder_{i}_errors':int(counts[i]) for i in range(9)})
        row.update({f'decoder_{i}_ler':float(counts[i]/len(y)) for i in range(9)})
        row['global_fixed_errors']=int(counts[int(selection['best_global_index'])]); row['selected_regime_errors']=int(counts[int(selection['best_per_regime_indices'][r])])
        per_seed.append(row)
        for i in range(9):
            ei=err[i].astype(float)
            for j in range(9):
                ej=err[j].astype(float)
                pair_counts[r][i,j]+=int(np.count_nonzero(pred[i]!=pred[j]))
                candidate_only[r][i,j]+=int(np.count_nonzero(err[i]&~err[j]))
                baseline_only[r][i,j]+=int(np.count_nonzero(~err[i]&err[j]))
                if i==j or ei.std()==0 or ej.std()==0: error_corr[r][i,j]=1.0 if i==j or np.array_equal(ei,ej) else 0.0
                else: error_corr[r][i,j]+=float(np.corrcoef(ei,ej)[0,1])
        packed=np.packbits(d,axis=1,bitorder='little')
        for i in range(9):
            if i==1: continue
            disagree=pred[i]!=pred[1]
            for ix in np.flatnonzero(disagree):
                key=bytes(packed[ix]).hex(); v=pattern_counts[r][i].get(key)
                if v is None: v=[0,int(d[ix].sum()),int(pred[i,ix]),int(pred[1,ix])]
                v[0]+=1; pattern_counts[r][i][key]=v
    assert regime_shots.tolist()==[200000]*3

    # Per decoder/regime rates with shotwise Wilson intervals and root-level variation.
    regimes_rows=[]; comparisons=[]; comp_family=[]
    sign_rng=np.random.default_rng(cfg['analysis']['sign_flip_seed']); signs=sign_rng.choice(np.asarray([-1.,1.]),size=(cfg['analysis']['sign_flip_draws'],roots))
    boot_rng=np.random.default_rng(cfg['analysis']['bootstrap_seed'])
    per_root_rates={(r,i):np.asarray([x[f'decoder_{i}_ler'] for x in per_seed if x['regime_index']==r]) for r in range(3) for i in range(9)}
    baseline_idx=int(selection['best_global_index'])
    for r in range(3):
        for i in range(9):
            n=int(regime_shots[r]); k=int(regime_errors[r,i]); diffs=per_root_rates[(r,i)]-per_root_rates[(r,baseline_idx)]
            ci=cluster_bootstrap(diffs,boot_rng)
            co=int(candidate_only[r][i,baseline_idx]); bo=int(baseline_only[r][i,baseline_idx]); mp,logp=exact_mcnemar(co,bo)
            p_cluster=None; q_holm=None
            if i!=baseline_idx:
                obs,p_cluster=clustered_signflip(diffs,signs); comp_family.append({'regime':REGIME_NAMES[r],'decoder_index':i,'p_raw':p_cluster,'paired_delta':obs,'ci':ci,'candidate_only':co,'baseline_only':bo})
            regimes_rows.append({'regime':REGIME_NAMES[r],'regime_index':r,'decoder_index':i,'gate_probability':GRID[i][0],'measurement_probability':GRID[i][1],
                'shots':n,'errors':k,'ler':k/n,'wilson95_low':wilson(k,n)[0],'wilson95_high':wilson(k,n)[1],
                'mean_root_ler':float(per_root_rates[(r,i)].mean()),'sd_root_ler':float(per_root_rates[(r,i)].std(ddof=1)),
                'paired_delta_ler_vs_global_fixed':float(diffs.mean()),'paired_root_bootstrap95_low':ci[0],'paired_root_bootstrap95_high':ci[1],
                'candidate_only_vs_global':co,'global_only_vs_candidate':bo,'exact_mcnemar_p_shot_descriptive':mp,'exact_mcnemar_log10_p_shot':logp,
                'root_cluster_signflip_p':p_cluster,'holm_adjusted_p_24_family':None})
    adjusted=holm([x['p_raw'] for x in comp_family])
    for i,x in enumerate(comp_family):x['p_holm']=adjusted[i]
    lookup={(x['regime'],x['decoder_index']):x['p_holm'] for x in comp_family}
    for row in regimes_rows:
        row['holm_adjusted_p_24_family']=lookup.get((row['regime'],row['decoder_index']))

    # Five prescribed comparisons plus two retrospective, explicitly unattainable references.
    g=baseline_idx; per_idx=np.asarray(selection['best_per_regime_indices'],dtype=int)
    errors_matrix=np.zeros((3,9),dtype=int); oracle_per_regime=np.zeros(3,dtype=int); oracle_per_shot=np.zeros(3,dtype=int)
    oracle_details=[]
    for r in range(3):
        # per-seed raw arrays are reloaded; no evaluation labels influence A/B selection.
        files=[x for x in seed_manifest if int(x['regime_index'])==r]
        all_err=[]
        for entry in files:
            z=np.load(P/entry['file'],allow_pickle=False); e=z['predictions']^z['observable'][None,:]
            all_err.append(e)
        e=np.concatenate(all_err,axis=1); errors_matrix[r]=e.sum(axis=1)
        oracle_per_regime[r]=int(e.sum(axis=1).min()); oracle_per_shot[r]=int(e.min(axis=0).sum())
        oracle_details.append({'regime':REGIME_NAMES[r],'shots':int(e.shape[1]),'evaluation_label_hindsight_best_decoder':int(np.argmin(e.mean(axis=1))),
            'hindsight_best_decoder_errors':int(e.sum(axis=1).min()),'per_shot_oracle_errors':int(e.min(axis=0).sum())})
    global_errors=int(errors_matrix[:,g].sum()); perreg_errors=int(sum(errors_matrix[r,per_idx[r]] for r in range(3)))
    primary_seed_diffs=[]
    for r in range(3):
        root_lers=[]
        for entry in [x for x in seed_manifest if int(x['regime_index'])==r]:
            z=np.load(P/entry['file'],allow_pickle=False); y=z['observable']; pred=z['predictions']
            root_lers.append(float(np.mean((pred[per_idx[r]]^y)))-float(np.mean(pred[g]^y)))
        primary_seed_diffs.append(np.asarray(root_lers))
    primary=np.mean([x.mean() for x in primary_seed_diffs])
    boots=np.empty(cfg['analysis']['bootstrap_draws'])
    rng=np.random.default_rng(cfg['analysis']['bootstrap_seed'])
    for b in range(len(boots)):
        boots[b]=np.mean([x[rng.integers(0,len(x),size=len(x))].mean() for x in primary_seed_diffs])
    primary_ci=[float(x) for x in np.quantile(boots,[.025,.975])]
    primary_signs=sign_rng.choice(np.asarray([-1.,1.]),size=(cfg['analysis']['sign_flip_draws'],roots))
    # Stratified sign flip for equal-regime primary; here selected B and A are equal model indices.
    if all(np.array_equal(x,np.zeros_like(x)) for x in primary_seed_diffs): primary_p=1.0
    else:
        null=np.mean([primary_signs*x[None,:] for x in primary_seed_diffs],axis=0)
        primary_p=float((np.count_nonzero(np.abs(null)>=abs(primary))+1)/(len(null)+1))
    oracle={'global_fixed_index':g,'per_regime_calibration_indices':per_idx.tolist(),
        'A_best_global_fixed_errors':global_errors,'B_calibration_selected_per_regime_errors':perreg_errors,
        'C_stage1_pooled_fixed_index1_errors':int(errors_matrix[:,1].sum()),'D_nominal_index4_errors':int(errors_matrix[:,4].sum()),
        'A_and_B_primary_equal_regime_ler_difference_B_minus_A':float(primary),
        'primary_seed_cluster_bootstrap_95ci':primary_ci,'primary_stratified_root_signflip_p':primary_p,
        'retrospective_oracle_by_regime':oracle_details,'retrospective_oracle_per_regime_errors_total':int(oracle_per_regime.sum()),
        'retrospective_oracle_per_shot_errors_total':int(oracle_per_shot.sum()),'oracle_not_deployable':True,
        'evaluation_root_seed_differences_by_regime':[[float(v) for v in x] for x in primary_seed_diffs]}
    (P/'ORACLE_HEADROOM.json').write_text(json.dumps(oracle,indent=2)+'\n',encoding='utf-8')

    # CSV evidence tables.
    with (P/'PER_REGIME_DECODER_RESULTS.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(regimes_rows[0]));w.writeheader();w.writerows(regimes_rows)
    seed_rows=[]
    for r in range(3):
        for root in range(roots):
            z=np.load(P/next(x for x in seed_manifest if int(x['regime_index'])==r and int(x['root_index'])==root)['file'],allow_pickle=False)
            y=z['observable']; pred=z['predictions']
            for i in range(9):seed_rows.append({'regime':REGIME_NAMES[r],'root_index':root,'decoder_index':i,'shots':len(y),'errors':int(np.count_nonzero(pred[i]^y)),'ler':float(np.mean(pred[i]^y))})
    with (P/'PER_SEED_RESULTS.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(seed_rows[0]));w.writeheader();w.writerows(seed_rows)
    dis_rows=[]
    for r in range(3):
        n=int(regime_shots[r])
        for i in range(9):
            for j in range(i+1,9):
                dis_rows.append({'regime':REGIME_NAMES[r],'decoder_i':i,'decoder_j':j,'shots':n,'prediction_disagreements':int(pair_counts[r][i,j]),'disagreement_rate':pair_counts[r][i,j]/n,
                    'candidate_only_errors_i':int(candidate_only[r][i,j]),'candidate_only_errors_j':int(candidate_only[r][j,i]),
                    'error_indicator_correlation':float(error_corr[r][i,j]/roots)})
    with (P/'DECODER_DISAGREEMENT.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(dis_rows[0]));w.writeheader();w.writerows(dis_rows)
    top_patterns={}
    for r in range(3):
        top_patterns[REGIME_NAMES[r]]={}
        for i,counts in pattern_counts[r].items():
            top=sorted(counts.items(),key=lambda x:(-x[1][0],x[0]))[:10]
            top_patterns[REGIME_NAMES[r]][str(i)]={'compared_to_decoder':1,'top_patterns':[{'packed_little_hex':k,'detector_indices':[j for j,v in enumerate(np.unpackbits(np.frombuffer(bytes.fromhex(k),dtype=np.uint8),bitorder='little')[:40]) if v],
                'disagreement_shots':v[0],'decoder_i_logical_prediction':v[2],'decoder_1_logical_prediction':v[3]} for k,v in top]}
    (P/'SYNDROME_DISAGREEMENT_PATTERNS.json').write_text(json.dumps(top_patterns,indent=2)+'\n',encoding='utf-8')

    # Machine-readable results and statistical report.
    result={'study':'Q-SHIFT Phase 2A','exploratory':True,'raw_array_audit_pass':True,'roots':60,'shots':600000,'prior_data_audit':json.loads((P/'PRIOR_DATA_AUDIT.json').read_text()),
        'calibration_selection':selection,'regime_decoder_results':regimes_rows,'paired_comparison_family':comp_family,
        'holm_family_size':len(comp_family),'oracle_headroom':oracle,'prediction_disagreement':{REGIME_NAMES[r]:pair_counts[r].tolist() for r in range(3)},
        'input_sha256':json.loads((P/'FREEZE.json').read_text())['input_sha256'],'software':json.loads((P/'FREEZE.json').read_text())['environment']}
    (P/'PHASE2A_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    md=['# Phase 2A statistical analysis','', '## Procedure','', 'Decoder performance comparisons use 20 independently seeded roots per regime. Each root contains 10,000 paired Stim shots decoded by all nine models. The primary estimates use equal regime weighting. Uncertainty for model differences is resampled at the root level; 24 candidate-by-regime comparisons use paired root sign-flip tests with Holm correction. Wilson intervals and exact shotwise McNemar probabilities are descriptive and do not replace root-level inference. The hindsight oracles are reported separately and never treated as available decoder policies.','',
        f"## Main headroom comparison",'',f"Calibration chose global index {g} and per-regime indices {per_idx.tolist()}. A had {global_errors:,} errors; B had {perreg_errors:,}. Equal-regime B−A LER difference = {primary:+.6%}; seed-cluster bootstrap 95% CI [{primary_ci[0]:+.6%}, {primary_ci[1]:+.6%}], stratified root sign-flip p={primary_p:.4g}. Since A and B use the same index in all regimes, their predictions and errors are exactly equal in this experiment.",'',
        '## Paired bank comparisons vs selected global fixed','', '| Regime | Candidate | Error delta LER | Candidate-only / baseline-only | Root sign-flip p | Holm p | Root bootstrap 95% CI |','|---|---:|---:|---:|---:|---:|---:|']
    for x in comp_family:md.append(f"| {x['regime']} | {x['decoder_index']} | {x['paired_delta']:+.6%} | {x['candidate_only']}/{x['baseline_only']} | {x['p_raw']:.4g} | {x['p_holm']:.4g} | [{x['ci'][0]:+.6%}, {x['ci'][1]:+.6%}] |")
    (P/'STATISTICAL_ANALYSIS.md').write_text('\n'.join(md)+'\n',encoding='utf-8')

    # Figures.
    fig,axs=plt.subplots(1,3,figsize=(14,4.7),sharey=True)
    labels=[f'{i}\n({a:g},{b:g})' for i,(a,b) in enumerate(GRID)]
    for r,ax in enumerate(axs):
        rates=regime_errors[r]/regime_shots[r]; lo=[];hi=[]
        for i,k in enumerate(regime_errors[r]):
            ci=wilson(int(k),int(regime_shots[r]));lo.append(rates[i]-ci[0]);hi.append(ci[1]-rates[i])
        ax.bar(np.arange(9),rates,yerr=[lo,hi],capsize=2,color=['#087f8c' if i==g else '#8297a5' for i in range(9)])
        ax.set_title(REGIME_NAMES[r]);ax.set_xticks(np.arange(9),labels,fontsize=7);ax.set_xlabel('Grid index (gate, measurement)');ax.grid(axis='y',alpha=.25)
    axs[0].set_ylabel('Logical error rate');fig.suptitle('Fresh paired evaluation by regime (error bars: shotwise Wilson 95% CI)');fig.tight_layout();fig.savefig(P/'PHASE2A_DECODER_LER.png',dpi=180);plt.close(fig)
    vals=[global_errors/600000,perreg_errors/600000,sum(int(errors_matrix[r,4]) for r in range(3))/600000,oracle_per_regime.sum()/600000,oracle_per_shot.sum()/600000]
    names=['Best global\ncalibration','Per-regime\ncalibration','Nominal\nfixed','Regime hindsight\n(test labels)','Per-shot oracle\n(test labels)']
    fig,ax=plt.subplots(figsize=(9,4.5));ax.bar(np.arange(5),vals,color=['#24496b','#008b8b','#7895aa','#db9b3d','#b55b5b']);ax.set_xticks(np.arange(5),names);ax.set_ylabel('Logical error rate');ax.set_title('Calibration-selected headroom vs unattainable test-label diagnostics');ax.grid(axis='y',alpha=.25);fig.tight_layout();fig.savefig(P/'PHASE2A_ORACLE_HEADROOM.png',dpi=180);plt.close(fig)
    print(f'Independent raw-array audit PASS; 60 roots, 600,000 shots; global={global_errors}; per-regime={perreg_errors}; primary={primary:+.6%} [{primary_ci[0]:+.6%},{primary_ci[1]:+.6%}]')

if __name__=='__main__': main()
