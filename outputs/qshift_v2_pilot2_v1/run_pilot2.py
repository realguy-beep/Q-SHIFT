"""Controlled, prequential Pilot 2 evaluation; all outputs are development-only."""
from __future__ import annotations
import csv, hashlib, json, os, platform, threading, time, tracemalloc
from pathlib import Path
import numpy as np, psutil, pymatching, stim
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
from outputs.stage4_noise_adaptive_feasibility_v1.prototype import DetectorProfileEstimator
from outputs.qshift_v2_pilot2_v1.controller import EventGLR, profile as pair_profile, snap, categories

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
POLS=['fixed_p0','static_dev','batch_profile','trailing_200','ewma_08','periodic_200','event_glr','oracle_true_p']
MODELS=[False,True]
BLOCK=50

class PeakRSS:
    def __init__(self): self.proc=psutil.Process(); self.peak=0; self.stop=False
    def run(self):
        while not self.stop:
            try: self.peak=max(self.peak,self.proc.memory_info().rss)
            except psutil.Error: pass
            time.sleep(.05)
    def start(self): self.thread=threading.Thread(target=self.run,daemon=True); self.thread.start()
    def close(self): self.stop=True; self.thread.join(); return max(self.peak,self.proc.memory_info().rss)

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def build(p, corr, meas=.003):
    c=build_spatial_burst_circuit(memory_basis='z',regime='balanced',distance=3,rounds=5,
       gate_p=.003,measurement_p=meas,bias_ratio=10,burst_probability=float(p))
    dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=True)
    m=pymatching.Matching.from_detector_error_model(dem,enable_correlations=bool(corr))
    return c,dem,m

def sample_from_plan(key, plan_by_key, corr=False):
    ds=[]; os_=[]
    for rec in plan_by_key[key]:
        c,_,_=build(rec['burst_p'],False,rec['measurement_p'])
        sampler=c.compile_detector_sampler(seed=int(rec['seed']))
        d,o=sampler.sample(int(rec['shots']),separate_observables=True)
        ds.append(d.astype(np.uint8)); os_.append(o.astype(np.uint8).reshape(int(rec['shots']),-1)[:,0])
    return np.concatenate(ds),np.concatenate(os_)

def get_grid_idx(p,grid): return int(np.argmin(np.abs(grid-float(p))))
def score_predictions(m,det,corr):
    return np.asarray(m.decode_batch(np.asarray(det,dtype=np.uint8),enable_correlations=bool(corr)),dtype=np.uint8).reshape(-1)

def discordance_counts(policy_errors, comparator_errors):
    a=np.asarray(policy_errors,dtype=bool); b=np.asarray(comparator_errors,dtype=bool)
    if a.shape!=b.shape: raise ValueError('paired error vectors must align')
    return (int(np.count_nonzero(a&b)),int(np.count_nonzero(a&~b)),int(np.count_nonzero(~a&b)),int(np.count_nonzero(~a&~b)))
def estimator_call(est,d): return float(est.estimate(np.asarray(d,dtype=np.uint8)))
def ewma_call(est,d,alpha=.08):
    f=np.asarray(__import__('outputs.stage4_noise_adaptive_feasibility_v1.prototype',fromlist=['detector_features']).detector_features(d),dtype=float)
    w=alpha*(1-alpha)**np.arange(len(f)-1,-1,-1); w/=w.sum(); obs=w@f
    grid=est.probabilities; dense=np.linspace(grid[0],grid[-1],int(round((grid[-1]-grid[0])/est.grid_step))+1)
    expected=np.column_stack([np.interp(dense,grid,est.means[:,j]) for j in range(est.means.shape[1])])
    z=np.mean(((expected-obs)/est.scales)**2,axis=1); return float(dense[np.argmin(z)])

def circuit_schedule(scenario, scored):
    if scenario=='stationary_p0': return np.zeros(scored)
    if scenario=='stationary_p008': return np.full(scored,.008)
    if scenario=='stationary_p016': return np.full(scored,.016)
    if scenario=='step_up': return np.where(np.arange(scored)<scored//2,.002,.018)
    if scenario=='step_down': return np.where(np.arange(scored)<scored//2,.018,.002)
    if scenario=='smooth':
        out=np.empty(scored)
        for lo in range(0,scored,50):
            hi=min(scored,lo+50); out[lo:hi]=.01+.008*np.sin(2*np.pi*((lo+hi)/2)/scored)
        return out
    if scenario=='transient':
        start=max(50,scored//2-50); return np.where((np.arange(scored)>=start)&(np.arange(scored)<start+100),.016,.002)
    if scenario=='measurement_mismatch': return np.full(scored,.008)
    if scenario=='tune_step_up': return np.where(np.arange(scored)<scored//2,.002,.018)
    if scenario=='tune_step_down': return np.where(np.arange(scored)<scored//2,.018,.002)
    if scenario=='tune_smooth': return np.array([.01+.008*np.sin(2*np.pi*(min(i+25,scored)/scored)) for i in range(0,scored,50)])
    if scenario=='tune_transient':
        start=max(50,scored//2-50); return np.where((np.arange(scored)>=start)&(np.arange(scored)<start+100),.016,.002)
    raise ValueError(scenario)

def run_event(det, pinit, candidate, likelihood, grid, est, warm):
    ev=EventGLR(grid,likelihood,pinit,candidate['threshold'],candidate['history_blocks'],candidate['min_dwell_blocks'],candidate['hysteresis'],candidate['pair_summary'])
    used=[]; endpoints=[]; alarms=[]; switches=[]
    all_d=np.concatenate([warm,det])
    for b,start in enumerate(range(0,len(det),BLOCK)):
        used.append(snap(ev.active_p,grid)); endpoints.append(len(warm)+start)
        block=det[start:start+BLOCK]
        t0=time.process_time()
        pnew,alarm,_=ev.observe(block,lambda end=len(warm)+start+len(block):estimator_call(est,all_d[max(0,end-candidate['profile_window']):end]))
        alarms.append(bool(alarm)); switches.append(ev.switches)
    return np.asarray(used),np.asarray(endpoints),ev,alarms,switches

def replay_stream(det,warm,obs,scenario,est,candidate,likelihood,grid,bank,static_selected,scored_n,oracle_cache,oracle_timing):
    """Decode each block first; only then ingest its detectors to update future settings."""
    all_d=np.concatenate([warm,det]); true_schedule=circuit_schedule(scenario,scored_n)
    init_t=time.process_time(); pinit=snap(estimator_call(est,warm),grid); init_cpu=time.process_time()-init_t
    event=EventGLR(grid,likelihood,pinit,candidate['threshold'],candidate['history_blocks'],candidate['min_dwell_blocks'],candidate['hysteresis'],candidate['pair_summary'])
    active={'trailing_200':pinit,'ewma_08':pinit,'periodic_200':pinit}
    adapt={p:{'estimator_cpu_s':0.,'change_detection_cpu_s':0.,'selection_cpu_s':0.} for p in POLS}
    decode_cpu={bool(c):{p:0. for p in POLS} for c in MODELS}; predictions={bool(c):{p:[] for p in POLS} for c in MODELS}
    graph_ids={p:[] for p in POLS}; decision_ends={p:[] for p in POLS}; alarm_blocks=[]
    for b,start in enumerate(range(0,scored_n,BLOCK)):
        stop=start+BLOCK; absolute=len(warm)+start; db=det[start:stop]
        p_now={'fixed_p0':0.,'static_dev':static_selected,'batch_profile':pinit,
          'trailing_200':active['trailing_200'],'ewma_08':active['ewma_08'],'periodic_200':active['periodic_200'],
          'event_glr':event.active_p,'oracle_true_p':float(np.mean(true_schedule[start:stop]))}
        for method in POLS:
            t0=time.process_time(); idx=get_grid_idx(p_now[method],grid); adapt[method]['selection_cpu_s']+=time.process_time()-t0
            graph_ids[method].append(idx); decision_ends[method].append(absolute)
        # The current block's predictions are committed in both decoder modes before controller updates.
        for corr in MODELS:
            for method in POLS:
                if method=='oracle_true_p':
                    exact=round(p_now[method],8); cachekey=(bool(corr),exact)
                    if cachekey not in oracle_cache:
                        tb=time.process_time(); oracle_cache[cachekey]=build(exact,corr)[2]; oracle_timing[0]+=time.process_time()-tb
                    m=oracle_cache[cachekey]
                else:
                    m=bank[(bool(corr),float(grid[graph_ids[method][-1]]))]
                t0=time.process_time(); pred=score_predictions(m,db,corr); decode_cpu[bool(corr)][method]+=time.process_time()-t0
                predictions[bool(corr)][method].extend(pred.tolist())
        # Now the just-decoded block's detector rows become available for subsequent blocks.
        end=absolute+len(db)
        if b+1 <= scored_n//BLOCK:
            t0=time.process_time(); active['trailing_200']=estimator_call(est,all_d[max(0,end-200):end]); adapt['trailing_200']['estimator_cpu_s']+=time.process_time()-t0
            t0=time.process_time(); active['ewma_08']=ewma_call(est,all_d[:end]); adapt['ewma_08']['estimator_cpu_s']+=time.process_time()-t0
            if end-len(warm) in (200,400,600,800,1000,1200):
                t0=time.process_time(); active['periodic_200']=estimator_call(est,all_d[max(0,end-200):end]); adapt['periodic_200']['estimator_cpu_s']+=time.process_time()-t0
            t0=time.process_time(); est_elapsed=[0.]
            def event_estimate(e=end):
                te=time.process_time(); val=estimator_call(est,all_d[max(0,e-candidate['profile_window']):e]); est_elapsed[0]+=time.process_time()-te; return val
            _,alarm_flag,_=event.observe(db,event_estimate)
            if alarm_flag: alarm_blocks.append(b)
            adapt['event_glr']['estimator_cpu_s']+=est_elapsed[0]
            adapt['event_glr']['change_detection_cpu_s']+=max(0.,time.process_time()-t0-est_elapsed[0])
    predictions={c:{m:np.asarray(q,dtype=np.uint8) for m,q in d.items()} for c,d in predictions.items()}
    diag={'event_alarms':event.accepted_alarms,'raw_glr_crossings':event.raw_crossings,'event_switches':event.switches,'alarm_blocks':alarm_blocks,
          'event_glr_cpu_s':adapt['event_glr']['change_detection_cpu_s']}
    return predictions,graph_ids,decision_ends,adapt,decode_cpu,diag,init_cpu,pinit
def policy_delay(policy_values, scenario, grid, scored):
    if scenario not in ('step_up','step_down','transient'): return None
    if scenario=='step_up': change=scored//2; post=.018
    elif scenario=='step_down': change=scored//2; post=.002
    else: change=max(50,scored//2-50); post=.016
    target=get_grid_idx(post,grid); before=get_grid_idx(.002 if scenario!='step_down' else .018,grid)
    starts=np.arange(0,scored,BLOCK)
    limit=change+100 if scenario=='transient' else scored
    for b,t in enumerate(starts):
        if t<change or t>=limit: continue
        idx=get_grid_idx(policy_values[b],grid)
        if abs(idx-target)<abs(before-target): return int(t-change)
    return int(limit-change) # right-censored; explicit censor flag is stored separately

def load_plan():
    config=json.loads((OUT/'PILOT2_CONFIG.json').read_text(encoding='utf-8'))
    inv=json.loads((OUT/'PILOT2_SEED_INVENTORY.json').read_text(encoding='utf-8'))
    by={}
    for r in inv['samples']: by.setdefault(r['sample_key'],[]).append(r)
    return config,inv,by

def main():
    wall0=time.perf_counter(); cpu0=time.process_time(); mem=PeakRSS(); mem.start(); tracemalloc.start()
    config,inv,plan=load_plan(); alloc=config['allocation']; grid=np.asarray(config['adaptive_graph_grid'],float)
    print(f"Pilot2 start: {sum(x['shots'] for x in inv['samples']):,} planned unique shots; seed inventory {len(inv['samples'])} sampler seeds")
    # Profile templates and fixed static-selection data are separate from calibration/evaluation.
    train0=time.process_time(); profile_batches=[]
    for p in config['profile_probabilities']:
        d,_=sample_from_plan(f'profile_p{p:.3f}',plan); profile_batches.append((p,d))
    estimator=DetectorProfileEstimator.fit(profile_batches); profile_cpu=time.process_time()-train0
    static_data_start=time.process_time(); static_data=[]
    for p in config['static_candidates']:
        d,o=sample_from_plan(f'static_p{p:.3f}',plan); static_data.append((float(p),d,o))
    static_selection_data_cpu=time.process_time()-static_data_start
    # Build shared matcher bank, explicit mode at construction and decode.
    build_wall=time.perf_counter(); build_cpu=time.process_time(); bank={}; graphbuild={}
    for corr in MODELS:
        for p in grid:
            a=time.process_time(); bank[(bool(corr),float(p))]=build(float(p),corr)[2]; graphbuild[(bool(corr),float(p))]=time.process_time()-a
    graph_bank_cpu=time.process_time()-build_cpu; graph_bank_wall=time.perf_counter()-build_wall
    static_selected={}; selection_counts={}; static_sel_start=time.process_time()
    for corr in MODELS:
        scores={float(p):0 for p in grid}
        for p,d,o in static_data:
            for modelp in grid:
                pr=score_predictions(bank[(bool(corr),float(modelp))],d,corr)
                scores[float(modelp)]+=int(np.count_nonzero(pr^o))
        static_selected[str(bool(corr))]=float(min(scores,key=lambda p:(scores[p],p))); selection_counts[str(bool(corr))]=scores
    static_selection_cpu=time.process_time()-static_sel_start
    # Candidate pair-category probability tables are trained only on profile detector data.
    likelihoods={c['candidate_id']:pair_profile(profile_batches,c['pair_summary'],grid) for c in config['candidates']}
    # Stationary calibration: detectors only; no labels read by controller or calibrator.
    caldata={}; tuningdata={}; calibration_sample_start=time.process_time()
    for p in config['false_alarm_p_values']:
        for r in range(12):
            d,_=sample_from_plan(f'cal_p{p:.3f}_r{r:02d}',plan); caldata[(float(p),r)]=d
    for sc in config['detection_tuning_scenarios']:
        key='tune_'+sc
        for r in range(6):
            d,_=sample_from_plan(f'{key}_r{r:02d}',plan); tuningdata[(sc,r)]=d
    calibration_sample_cpu=time.process_time()-calibration_sample_start
    tune_cpu_start=time.process_time()
    candidates=[]
    for cand in config['candidates']:
        fa={str(p):0 for p in config['false_alarm_p_values']}; rawfa={str(p):0 for p in config['false_alarm_p_values']}; den={str(p):0 for p in config['false_alarm_p_values']}
        for p in config['false_alarm_p_values']:
            for r in range(12):
                d=caldata[(float(p),r)]; warm=d[:200]; scored=d[200:]
                pinit=snap(estimator_call(estimator,warm),grid)
                _,_,ev,_,_=run_event(scored,pinit,cand,likelihoods[cand['candidate_id']],grid,estimator,warm)
                fa[str(p)]+=ev.accepted_alarms; rawfa[str(p)]+=ev.raw_crossings; den[str(p)]+=len(scored)
        rates={p:fa[p]/den[p]*1000 for p in fa}; pooled=sum(fa.values())/sum(den.values())*1000
        eligible=pooled<=1.0 and max(rates.values())<=1.0
        delays=[]
        for sc in config['detection_tuning_scenarios']:
            for r in range(6):
                d=tuningdata[(sc,r)]; warm=d[:200]; scored=d[200:]
                pinit=snap(estimator_call(estimator,warm),grid)
                vals,_,_,_,_=run_event(scored,pinit,cand,likelihoods[cand['candidate_id']],grid,estimator,warm)
                delay=policy_delay(vals,sc,grid,len(scored)); delays.append(delay)
        candidates.append({**cand,'false_alarm_counts':fa,'raw_glr_crossing_counts':rawfa,'stationary_exposure_shots':den,'false_alarm_per_1000':rates,
            'pooled_false_alarm_per_1000':pooled,'eligible':bool(eligible),'mean_tuning_delay_shots':float(np.mean([x for x in delays if x is not None])),
            'tuning_delay_values':delays})
    candidate_tune_cpu=time.process_time()-tune_cpu_start
    eligible=[x for x in candidates if x['eligible']]
    if eligible: chosen=min(eligible,key=lambda x:(x['mean_tuning_delay_shots'],sum(x['false_alarm_counts'].values()),x['candidate_id']))
    else: chosen=min(candidates,key=lambda x:(max(x['false_alarm_per_1000'].values()),x['mean_tuning_delay_shots'],x['candidate_id']))
    (OUT/'PILOT2_TUNING_CANDIDATES.json').write_text(json.dumps({'candidates':candidates,'selected':chosen,'eligible_count':len(eligible)},indent=2),encoding='utf-8')
    # Evaluation streams are generated once per stream, then replayed across every policy/mode.
    scenarios=config['allocation']['evaluation_scenarios']; reps=alloc['evaluation_replicates']; scored_n=alloc['scored_shots_per_evaluation_stream']; warm_n=alloc['warmup_shots_per_evaluation_stream']
    streams=[]; predarr=[]; obsarr=[]; usedarr=[]; seenarr=[]; diagarr=[]; rows=[]; oracle_cache={}; oracle_timing=[0.]
    runtime_policy={p:[] for p in POLS}; eval_cpu_start=time.process_time()
    for sc in scenarios:
      for rep in range(reps):
        key=f'eval_{sc}_r{rep:02d}'; det,obs=sample_from_plan(key,plan); warm=det[:warm_n]; ds=det[warm_n:]; ys=obs[warm_n:]
        if len(ds)!=scored_n or len(ys)!=scored_n: raise RuntimeError('scored/calibration separation mismatch')
        corr_preds,graph_ids,input_ends,adapt_cpu,decode_cpu,detail,initial_cpu,pinit=replay_stream(ds,warm,ys,sc,estimator,chosen,likelihoods[chosen['candidate_id']],grid,bank,static_selected['False'],scored_n,oracle_cache,oracle_timing)
        # Replay adaptive policies once on common observations; static selection is decoder-mode-specific.
        # For the explicitly correlation-aware mode, only static_dev can differ, so patch that cached arm from its own selected p.
        static_patch_cpu=0.
        if static_selected['True'] != static_selected['False']:
            corr=True; vals=[]
            for b,start in enumerate(range(0,scored_n,BLOCK)):
                m=bank[(corr,float(static_selected['True']))]
                tb=time.process_time(); vals.extend(score_predictions(m,ds[start:start+BLOCK],corr).tolist()); static_patch_cpu+=time.process_time()-tb
            corr_preds[True]['static_dev']=np.asarray(vals,dtype=np.uint8)
        pred_modes=np.stack([np.stack([corr_preds[bool(c)][m] for m in POLS]) for c in MODELS])
        base_idx=np.array([[graph_ids[m][b] for b in range(26)] for m in POLS],dtype=np.int16)
        used_idx=np.stack([base_idx.copy(),base_idx.copy()])
        used_idx[1,1,:]=get_grid_idx(static_selected['True'],grid)
        inends=np.array([input_ends[m] for m in POLS],dtype=np.int32)
        errors=np.count_nonzero(pred_modes ^ ys[None,None,:],axis=2)
        switches=np.count_nonzero(used_idx[:,:,1:]!=used_idx[:,:,:-1],axis=2)
        oracle_ps=np.array([float(np.mean(circuit_schedule(sc,scored_n)[b*BLOCK:(b+1)*BLOCK])) for b in range(26)])
        oracle_switches=int(np.count_nonzero(np.round(np.diff(oracle_ps),8)!=0))
        switches[:,POLS.index('oracle_true_p')]=oracle_switches
        for ci,corr in enumerate(MODELS):
            for mi,method in enumerate(POLS):
                errmask=pred_modes[ci,mi]^ys; err=int(errmask.sum())
                evdelay=policy_delay([float(grid[x]) for x in used_idx[ci,mi]],sc,grid,scored_n)
                isdynamic=sc in ('step_up','step_down','transient')
                censored=bool(isdynamic and evdelay==(scored_n-(scored_n//2 if sc in ('step_up','step_down') else max(50,scored_n//2-50))))
                false_alarm_n=detail['event_alarms'] if method=='event_glr' and (sc.startswith('stationary_') or sc=='measurement_mismatch') else 0
                adap=adapt_cpu[method]
                shared=initial_cpu if method in ('batch_profile','trailing_200','ewma_08','periodic_200','event_glr') else 0.
                row={'scenario':sc,'replicate':rep,'stream_key':key,'correlation_decode':bool(corr),'policy':method,
                    'errors':err,'scored_shots':scored_n,'ler':err/scored_n,'decoder_cpu_s':decode_cpu[bool(corr)][method]+(static_patch_cpu if corr and method=='static_dev' else 0.),
                    'shared_initial_calibration_cpu_s':shared,'estimator_cpu_s':adap['estimator_cpu_s'],
                    'change_detection_cpu_s':adap['change_detection_cpu_s'],'graph_selection_cpu_s':adap['selection_cpu_s'],
                    'graph_switches':int(switches[ci,mi]),'accepted_alarms':detail['event_alarms'] if method=='event_glr' else 0,
                    'raw_glr_crossings':detail['raw_glr_crossings'] if method=='event_glr' else 0,
                    'false_alarms':false_alarm_n,'detection_delay_shots':evdelay if isdynamic else '',
                    'detection_delay_censored':censored if isdynamic else '',
                    'static_selected_p':static_selected[str(bool(corr))],'initial_profile_p':pinit,
                    'selected_glr_candidate':chosen['candidate_id'],'end_to_end_cpu_s':decode_cpu[bool(corr)][method]+shared+sum(adap.values())}
                for j,comp in enumerate(POLS):
                    cvals=(pred_modes[ci,j]^ys).astype(bool)
                    both,aonly,conly,neither=discordance_counts(errmask,cvals)
                    row[f'both_error_vs_{comp}']=both
                    row[f'policy_only_error_vs_{comp}']=aonly
                    row[f'comparator_only_error_vs_{comp}']=conly
                    row[f'neither_error_vs_{comp}']=neither
                rows.append(row)
        streams.append((sc,rep,key)); predarr.append(pred_modes); obsarr.append(ys.copy()); usedarr.append(used_idx); seenarr.append(inends); diagarr.append(detail)
        if len(streams)%16==0: print(f'replayed {len(streams)}/{len(scenarios)*reps} evaluation streams')
    eval_cpu=time.process_time()-eval_cpu_start
    # CSV results and aligned shot-level lossless paired outcomes.
    result_path=OUT/'PILOT2_RESULTS.csv'
    with result_path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    np.savez_compressed(OUT/'PILOT2_PAIRED_OUTCOMES.npz',predictions=np.stack(predarr),observables=np.stack(obsarr),
        stream_scenarios=np.array([s for s,_,_ in streams]),stream_replicates=np.array([r for _,r,_ in streams]),
        stream_keys=np.array([k for _,_,k in streams]),policy_names=np.array(POLS),decoder_modes=np.array(MODELS),
        oracle_graph_probabilities=np.stack([np.array([float(np.mean(circuit_schedule(sc,scored_n)[b*BLOCK:(b+1)*BLOCK])) for b in range(26)]) for sc,_,_ in streams]),
        graph_indices=np.stack(usedarr),decision_input_end=np.stack(seenarr),block_start=np.tile(warm_n+np.arange(26)*BLOCK,(len(streams),len(POLS),1)),
        warmup_shots=warm_n,scored_shots=scored_n)
    # Calibration/tuning trace and compact run metadata.
    with (OUT/'PILOT2_TUNING_CANDIDATES.csv').open('w',newline='',encoding='utf-8') as f:
        keys=list(candidates[0]); w=csv.DictWriter(f,fieldnames=keys); w.writeheader();
        for c in candidates: w.writerow({k:json.dumps(c[k]) if isinstance(c[k],(dict,list)) else c[k] for k in keys})
    peak=mem.close(); current,peak_py=tracemalloc.get_traced_memory(); tracemalloc.stop()
    runtime={'status':'completed','unique_shots_planned':alloc['planned_unique_shots'],'unique_shots_actual':sum(x['shots'] for x in inv['samples']),
        'evaluation_scored_shots_per_mode':len(streams)*scored_n,'streams':len(streams),'seconds_wall':time.perf_counter()-wall0,
        'seconds_process_cpu':time.process_time()-cpu0,'profile_training_cpu_s':profile_cpu,'static_selection_data_generation_cpu_s':static_selection_data_cpu,
        'static_selection_cpu_s':static_selection_cpu,'calibration_and_tuning_data_generation_cpu_s':calibration_sample_cpu,
        'candidate_calibration_and_tuning_cpu_s':candidate_tune_cpu,'graph_bank_cpu_s':graph_bank_cpu,
        'graph_bank_wall_s':graph_bank_wall,'oracle_extra_graph_cpu_s':oracle_timing[0],'evaluation_replay_cpu_s':eval_cpu,
        'peak_process_rss_bytes':int(peak),'peak_tracemalloc_bytes':int(peak_py),'python':platform.python_version(),
        'platform':platform.platform(),'numpy':np.__version__,'stim':stim.__version__,'pymatching':pymatching.__version__,
        'psutil':psutil.__version__,'config_sha256':sha(OUT/'PILOT2_CONFIG.json'),'seed_inventory_sha256':sha(OUT/'PILOT2_SEED_INVENTORY.json'),
        'results_sha256':sha(result_path),'paired_outcomes_sha256':sha(OUT/'PILOT2_PAIRED_OUTCOMES.npz'),
        'static_selected_p_by_mode':static_selected,'static_selection_error_counts':selection_counts,'selected_glr_candidate':chosen['candidate_id'],
        'calibration_training_cpu_s':profile_cpu,'calibration_tuning_cpu_s':candidate_tune_cpu,
        'selected_candidate_eligible':chosen['eligible'],'graph_bank_construction_cpu_by_mode_p':{f'{k[0]}:{k[1]:.3f}':v for k,v in graphbuild.items()},
        'source_hashes_sha256':{name:sha(OUT/name) for name in ['prepare_pilot2.py','preflight_audit.py','controller.py','run_pilot2.py','test_pilot2.py','independent_audit.py']},
        'input_report_hashes_sha256':{
          'pilot1_report':sha(Path(r'C:\Users\LENOVO\Documents\Codex\2026-11-08\correction-the-previous-q-shift-adaptive\outputs\Q-SHIFT_v2_development_pilot_report.md')),
          'astra_research_report':sha(Path(r'C:\Users\LENOVO\Documents\Codex\2026-11-08\correction-the-previous-q-shift-adaptive\outputs\Q-SHIFT_research_report_2026-11-08.md'))},
        'forbidden_data_access':{'stage5':False,'sealed':False}}
    (OUT/'PILOT2_RUNTIME.json').write_text(json.dumps(runtime,indent=2),encoding='utf-8')
    print(json.dumps(runtime,indent=2))
if __name__=='__main__': main()
