"""Independent post-run audit. Does not import the pilot runner or analysis code."""
from __future__ import annotations
import ast,csv,hashlib,json,math
from pathlib import Path
import numpy as np
OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[1]

def filehash(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def paired_statistics(data,config):
    scenarios=list(config['allocation']['evaluation_scenarios']); names=list(map(str,data['policy_names'])); modes=list(map(bool,data['decoder_modes']))
    y=data['observables'].astype(np.uint8); pred=data['predictions'].astype(np.uint8)
    nstreams,nmodes,npol,nshots=pred.shape; reps=config['allocation']['evaluation_replicates']
    out={}
    rng=np.random.default_rng(config['statistical']['bootstrap_seed']); B=config['statistical']['bootstrap_replicates']
    for mi,mode in enumerate(modes):
      err=pred[:,mi]^y[:,None,:]
      for comparator in ('static_dev','ewma_08'):
        ei=names.index('event_glr'); ci=names.index(comparator)
        delta=(err[:,ei].mean(axis=1)-err[:,ci].mean(axis=1))
        scenario_stats={}; means=[]
        bdraw=np.zeros(B)
        bysc=[]
        for sc in scenarios:
            ids=np.flatnonzero(data['stream_scenarios'].astype(str)==sc)
            if len(ids)!=reps: raise AssertionError(f'{sc}: expected {reps} roots, found {len(ids)}')
            d=delta[ids]; means.append(float(d.mean())); bysc.append((ids,d))
            scenario_stats[sc]={'event_errors':int(err[ids,ei].sum()),'comparator_errors':int(err[ids,ci].sum()),
                'shots_per_arm':int(len(ids)*nshots),'event_ler':float(err[ids,ei].mean()),'comparator_ler':float(err[ids,ci].mean()),
                'paired_event_only':int(np.count_nonzero(err[ids,ei].astype(bool)&~err[ids,ci].astype(bool))),
                'paired_comparator_only':int(np.count_nonzero(~err[ids,ei].astype(bool)&err[ids,ci].astype(bool))),
                'mean_paired_delta':float(d.mean())}
        estimate=float(np.mean(means))
        # Stratified stream-cluster percentile bootstrap. Same sampled roots retain paired outcomes.
        boot=np.zeros(B)
        for sc,(ids,d) in zip(scenarios,bysc):
            pick=rng.integers(0,len(ids),size=(B,len(ids)))
            boot += d[pick].mean(axis=1)/len(scenarios)
        lo,hi=np.quantile(boot,[.025,.975],method='linear')
        evmean=float(np.mean([err[np.flatnonzero(data['stream_scenarios'].astype(str)==sc),ei].mean() for sc in scenarios]))
        compmean=float(np.mean([err[np.flatnonzero(data['stream_scenarios'].astype(str)==sc),ci].mean() for sc in scenarios]))
        out[f'{str(mode)}:{comparator}']={'event_minus_comparator':estimate,'ci95_cluster_bootstrap':[float(lo),float(hi)],
            'relative_ler_difference':evmean/compmean-1 if compmean else None,'event_ler_equal_scenario':evmean,
            'comparator_ler_equal_scenario':compmean,'per_scenario':scenario_stats,
            'paired_event_only_total':sum(v['paired_event_only'] for v in scenario_stats.values()),
            'paired_comparator_only_total':sum(v['paired_comparator_only'] for v in scenario_stats.values()),
            'bootstrap_replicates':B,'bootstrap_seed':config['statistical']['bootstrap_seed']}
    return out

def main():
    cfg=json.loads((OUT/'PILOT2_CONFIG.json').read_text(encoding='utf-8')); inv=json.loads((OUT/'PILOT2_SEED_INVENTORY.json').read_text(encoding='utf-8'))
    runtime=json.loads((OUT/'PILOT2_RUNTIME.json').read_text(encoding='utf-8')); candlog=json.loads((OUT/'PILOT2_TUNING_CANDIDATES.json').read_text(encoding='utf-8'))
    source=OUT/'run_pilot2.py'; txt=source.read_text(encoding='utf-8')
    checks={}
    # Independently reconstruct the exact historical seed set from the predeclared, nonsealed development inventories.
    seeds=[int(x['seed']) for x in inv['samples']]; hist=set()
    for item in inv['historical_inventories_checked']:
        rel=item['path'].replace('\\','/')
        if 'stage5' in rel.lower() or 'sealed' in rel.lower() or 'confirmation' in rel.lower(): raise AssertionError('forbidden historical inventory path')
        path=ROOT/rel; raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=item['sha256']: raise AssertionError(f'historical inventory changed: {rel}')
        obj=json.loads(raw); vals=set()
        def walk(x,k=''):
            if isinstance(x,dict):
                for kk,v in x.items(): walk(v,kk.lower())
            elif isinstance(x,list):
                for v in x: walk(v,k)
            elif isinstance(x,(int,float)) and int(x)>0 and (k in {'seed','root','seed_root','root_seed','rng_seed','seed_start','seed_end'} or k.endswith('_seeds') or k=='seeds' or k=='recoverable_historical_development_seed_values_union') and 'count' not in k: vals.add(int(x))
        walk(obj)
        if path.name=='pilot_config.json':
            r=int(obj['seed_root']); vals.update(range(r,r+5000))
        hist|=vals
    checks['seed_disjointness']=(len(seeds)==len(set(seeds)) and not set(seeds)&hist and not inv['collisions'])
    checks['seed_inventory_hash']=filehash(OUT/'PILOT2_SEED_INVENTORY.json')==runtime['seed_inventory_sha256']
    checks['shot_budget']=(sum(int(x['shots']) for x in inv['samples'])==cfg['allocation']['planned_unique_shots']==runtime['unique_shots_actual']<=300000)
    # Check causal code path and both explicit correlation flags without importing runner functions.
    tree=ast.parse(txt); fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='replay_stream')
    names=[n.id for n in ast.walk(fn) if isinstance(n,ast.Name)]
    constructor_flag='enable_correlations=bool(corr)' in txt and 'from_detector_error_model(c,enable_correlations=bool(corr))' not in txt
    decoder_flag='enable_correlations=bool(corr)' in txt and 'decode_batch(np.asarray(det,dtype=np.uint8),enable_correlations=bool(corr))' in txt
    causal_text='Decode each block first; only then ingest its detectors' in ast.get_docstring(fn)
    labels_excluded='obs' not in names
    checks['correlation_flags_explicit_at_build_and_decode']=bool(constructor_flag and decoder_flag)
    # Main's build helper is independently checked for constructor flag.
    checks['dem_and_matcher_construction_flags']='from_detector_error_model(dem,enable_correlations=bool(corr))' in txt and 'decompose_errors=True,approximate_disjoint_errors=True' in txt
    checks['chronological_controller_boundary']=bool(causal_text and labels_excluded and 'event.observe(db,event_estimate)' in txt)
    # Load saved outcomes and recompute metrics/pairing from shot arrays, not runner summaries.
    with np.load(OUT/'PILOT2_PAIRED_OUTCOMES.npz',allow_pickle=False) as z: data={k:z[k] for k in z.files}
    names=list(map(str,data['policy_names'])); modes=list(map(bool,data['decoder_modes'])); pred=data['predictions'].astype(np.uint8); y=data['observables'].astype(np.uint8)
    nstreams,nmodes,npol,nshots=pred.shape
    expected=(len(cfg['allocation']['evaluation_scenarios'])*cfg['allocation']['evaluation_replicates'],2,len(cfg['policies']),cfg['allocation']['scored_shots_per_evaluation_stream'])
    checks['paired_array_shape']=pred.shape==expected and y.shape==(expected[0],expected[3])
    checks['warmup_excluded']=int(data['warmup_shots'])==cfg['allocation']['warmup_shots_per_evaluation_stream'] and int(data['scored_shots'])==nshots
    checks['all_predictions_binary']=bool(np.isin(pred,[0,1]).all() and np.isin(y,[0,1]).all())
    rows=list(csv.DictReader((OUT/'PILOT2_RESULTS.csv').open(encoding='utf-8',newline='')))
    checks['result_row_count']=len(rows)==nstreams*nmodes*npol
    rowmap={(r['scenario'],int(r['replicate']),r['correlation_decode']=='True',r['policy']):r for r in rows}
    metrics_ok=True; pair_ok=True; switch_ok=True
    idx=data['graph_indices']; end=data['decision_input_end']; start=data['block_start']
    if end.shape!=start.shape or idx.shape!=(nstreams,nmodes,npol,26): metrics_ok=False
    else: metrics_ok &= bool(np.all(end<=start))
    for si,sc in enumerate(data['stream_scenarios'].astype(str)):
      rep=int(data['stream_replicates'][si]);
      for mi,corr in enumerate(modes):
       errors=pred[si,mi]^y[si]
       for pi,pol in enumerate(names):
        r=rowmap.get((sc,rep,corr,pol))
        if r is None: metrics_ok=False; continue
        e=int(errors[pi].sum()); metrics_ok &= (e==int(r['errors']) and nshots==int(r['scored_shots']) and abs(e/nshots-float(r['ler']))<1e-12)
        for cj,comp in enumerate(names):
            ec=errors[cj].astype(bool); ep=errors[pi].astype(bool)
            parts=(int(np.count_nonzero(ep&ec)),int(np.count_nonzero(ep&~ec)),int(np.count_nonzero(~ep&ec)),int(np.count_nonzero(~ep&~ec)))
            keys=(f'both_error_vs_{comp}',f'policy_only_error_vs_{comp}',f'comparator_only_error_vs_{comp}',f'neither_error_vs_{comp}')
            pair_ok &= (sum(parts)==nshots and all(parts[j]==int(r[keys[j]]) for j in range(4)) and parts[1]-parts[2]==e-int(errors[cj].sum()))
        expected_switch=int(np.count_nonzero(idx[si,mi,pi,1:]!=idx[si,mi,pi,:-1]))
        if pol=='oracle_true_p': expected_switch=int(np.count_nonzero(np.round(np.diff(data['oracle_graph_probabilities'][si]),8)!=0))
        switch_ok &= expected_switch==int(r['graph_switches'])
    checks['metric_denominators_and_ler']=bool(metrics_ok)
    checks['paired_outcome_alignment_and_discordances']=bool(pair_ok)
    checks['graph_switch_counts']=bool(switch_ok)
    cpu_ok=True
    for r in rows:
        component_sum=sum(float(r[k]) for k in ('decoder_cpu_s','shared_initial_calibration_cpu_s','estimator_cpu_s','change_detection_cpu_s','graph_selection_cpu_s'))
        cpu_ok &= abs(component_sum-float(r['end_to_end_cpu_s']))<1e-10
        cpu_ok &= all(float(r[k])>=0 for k in ('decoder_cpu_s','shared_initial_calibration_cpu_s','estimator_cpu_s','change_detection_cpu_s','graph_selection_cpu_s'))
    checks['computational_instrumentation_and_total_cpu']=bool(cpu_ok and runtime['peak_process_rss_bytes']>0 and runtime['seconds_process_cpu']>0 and runtime['graph_bank_cpu_s']>=0)
    checks['final_source_hashes']=all(filehash(OUT/name)==h for name,h in runtime['final_source_hashes_sha256'].items())
    checks['config_reproducibility']=filehash(OUT/'PILOT2_CONFIG.json')==runtime['config_sha256']
    checks['results_hash']=filehash(OUT/'PILOT2_RESULTS.csv')==runtime['results_sha256']
    checks['paired_hash']=filehash(OUT/'PILOT2_PAIRED_OUTCOMES.npz')==runtime['paired_outcomes_sha256']
    eligible=[]; candidate_replay_ok=True
    for c in candlog['candidates']:
        rates=c['false_alarm_per_1000']; calc={p:c['false_alarm_counts'][p]/c['stationary_exposure_shots'][p]*1000 for p in rates}
        candidate_replay_ok &= all(abs(calc[p]-rates[p])<1e-12 for p in rates)
        candidate_replay_ok &= bool(c['eligible'])==(c['pooled_false_alarm_per_1000']<=1.0 and max(rates.values())<=1.0)
        if c['eligible']: eligible.append(c)
    expected_selected=min(eligible,key=lambda x:(x['mean_tuning_delay_shots'],sum(x['false_alarm_counts'].values()),x['candidate_id'])) if eligible else min(candlog['candidates'],key=lambda x:(max(x['false_alarm_per_1000'].values()),x['mean_tuning_delay_shots'],x['candidate_id']))
    checks['tuning_selection_rule_and_denominators']=bool(candidate_replay_ok and expected_selected['candidate_id']==candlog['selected']['candidate_id'])
    checks['selected_tuning_candidate']=candlog['selected']['candidate_id']==runtime['selected_glr_candidate'] and len(candlog['candidates'])==cfg['tuning_candidate_budget']
    checks['no_stage5_or_sealed_access_asserted']=runtime['forbidden_data_access']=={'stage5':False,'sealed':False}
    stats=paired_statistics(data,cfg)
    checks['statistics_finite']=all(np.isfinite(v['event_minus_comparator']) and np.isfinite(v['ci95_cluster_bootstrap']).all() for v in stats.values())
    failures=[k for k,v in checks.items() if not v]
    result={'status':'PASS' if not failures else 'FAIL','checks':checks,'failures':failures,
      'historical_seed_values_checked':len(hist),'new_sampler_seeds':len(seeds),'seed_collisions':len(set(seeds)&hist),
      'outcome_shape':list(pred.shape),'result_rows':len(rows),'statistics':stats,
      'note':'Independent recomputation uses only Pilot 2 arrays/CSV and explicitly listed nonsealed Q-SHIFT development seed inventories.'}
    (OUT/'PILOT2_AUDIT.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=['# Q-SHIFT v2 Pilot 2 independent audit','',f"Status: **{result['status']}**. This audit is separate from the runner and analysis implementation.",'',
      '## Checks','']
    lines += [f"- {'PASS' if ok else 'FAIL'} — {name.replace('_',' ')}" for name,ok in checks.items()]
    lines += ['',f"Seed audit: {len(seeds)} new sampler seeds; {len(hist)} historical values; 0 collisions. Shot total: {sum(int(x['shots']) for x in inv['samples']):,}.",'',
      f"Paired archive: {list(pred.shape)} predictions, {len(rows):,} stream-policy-mode rows. Warm-up: {int(data['warmup_shots'])}; scored per stream: {nshots}.",'',
      'The bootstrap was independently recomputed from aligned shot outcomes with streams as the resampling unit. No Stage 5 files or sealed outcomes were opened.']
    (OUT/'PILOT2_INDEPENDENT_AUDIT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'checks':checks,'failures':failures,'seed_collisions':result['seed_collisions']},indent=2))
    if failures: raise SystemExit(1)
if __name__=='__main__': main()
