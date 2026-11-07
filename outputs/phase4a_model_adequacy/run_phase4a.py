"""Frozen bounded Phase 4A study. Never imports or modifies historical runners."""
from pathlib import Path
import hashlib, json, time, sys, platform, itertools, csv, traceback
import numpy as np
import stim, pymatching
import ctypes
from types import SimpleNamespace
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT/'config.json').read_text())
NAMES = list(CFG['conditions'])
GRID = list(itertools.product(CFG['probability_grid'], repeat=2))
MODELS = ['fixed', 'calibrated', 'model_informed']
START = time.perf_counter()
class WindowsProcessMemory:
    def memory_info(self):
        class Counters(ctypes.Structure):
            _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
        kernel=ctypes.windll.kernel32;kernel.GetCurrentProcess.restype=ctypes.c_void_p
        fn=ctypes.windll.psapi.GetProcessMemoryInfo
        fn.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong]
        c=Counters();c.cb=ctypes.sizeof(c)
        if not fn(kernel.GetCurrentProcess(),ctypes.byref(c),c.cb): raise OSError('Cannot measure process memory')
        return SimpleNamespace(rss=c.WorkingSetSize,peak_wset=c.PeakWorkingSetSize)
PROC = WindowsProcessMemory()
PEAK = 0
TIMES = {'sampling_seconds': 0., 'decoding_seconds': {n:0. for n in MODELS}, 'fit_seconds':0., 'model_build_seconds':0.}
COUNTS = {'template':0, 'calibration':0, 'validation':0, 'test':0, 'noiseless_diagnostic':0}
R = {'status':'initializing', 'config':CFG, 'software':{'python':platform.python_version(), 'stim':stim.__version__, 'pymatching':pymatching.__version__, 'numpy':np.__version__}, 'validation':{}, 'calibration':[], 'validation_rows':[], 'test_rows':[], 'failures':[]}

class StopStudy(Exception): pass

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name, obj):
    p=ROOT/name
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def check_budget():
    global PEAK
    m=PROC.memory_info(); PEAK=max(PEAK,m.rss,getattr(m,'peak_wset',0))
    if PEAK>2*1024**3: raise StopStudy('Process memory exceeded 2 GB target')
    if time.perf_counter()-START>CFG['compute_wall_cap_seconds']: raise StopStudy('900-second conservative wall budget reached')

def circuit(g,m):
    return stim.Circuit.generated(CFG['circuit'],distance=CFG['distance'],rounds=CFG['rounds'],after_clifford_depolarization=g,before_measure_flip_probability=m)

def sample(c,n,seed,stage):
    check_budget(); t=time.perf_counter(); sampler=c.compile_detector_sampler(seed=seed)
    ds=[]; ys=[]
    for lo in range(0,n,CFG['batch_shots']):
        check_budget(); k=min(CFG['batch_shots'],n-lo)
        d,y=sampler.sample(shots=k,separate_observables=True)
        ds.append(d);ys.append(y[:,0]);COUNTS[stage]+=k
    TIMES['sampling_seconds']+=time.perf_counter()-t
    return np.concatenate(ds),np.concatenate(ys)

def decode(model,d,name):
    t=time.perf_counter(); parts=[]
    for lo in range(0,len(d),CFG['batch_shots']):
        check_budget();parts.append(model.decode_batch(d[lo:lo+CFG['batch_shots']])[:,0].astype(bool))
    TIMES['decoding_seconds'][name]+=time.perf_counter()-t
    return np.concatenate(parts)

def wilson(k,n):
    z=1.959963984540054;p=k/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den;half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [float(mid-half),float(mid+half)]

def paired(a,b,n):
    delta=(a-b)/n;se=np.sqrt(max(0,a+b-(a-b)**2/n))/n
    return {'candidate_only_wrong':a,'fixed_only_wrong':b,'difference_errors':a-b,'difference_rate':delta,'paired_ci95_approx':[float(delta-1.96*se),float(delta+1.96*se)],'mcnemar_p':float(binomtest(a,a+b,.5).pvalue) if a+b else 1.}

def score(seed,name,y,preds):
    residual={k:y^v for k,v in preds.items()};fixed=residual['fixed']; n=len(y)
    row={'seed_root':seed,'condition':name,'shots':n,'raw_errors':int(y.sum()),'decoders':{}}
    for k,v in residual.items():
        a=int(np.count_nonzero(v & ~fixed));b=int(np.count_nonzero(~v & fixed))
        row['decoders'][k]={'errors':int(v.sum()),'rate':float(v.mean()),'wilson95':wilson(int(v.sum()),n),'disagreements':int(np.count_nonzero(preds[k]!=preds['fixed'])),**paired(a,b,n)}
    return row

def raw(stage,seed,name,d,y,preds=None):
    p=ROOT/'raw'/f'{stage}_{seed}_{name}.npz'; p.parent.mkdir(exist_ok=True)
    values={'detectors_packed_little':np.packbits(d,axis=1,bitorder='little'),'detector_count':np.array(d.shape[1]),'observable_audit_only':y}
    if preds: values.update({f'prediction_{k}':v for k,v in preds.items()})
    np.savez_compressed(p,**values)

def aggregate(rows):
    out={};rng=np.random.default_rng(CFG['bootstrap_seed'])
    for name in NAMES:
        rr=[r for r in rows if r['condition']==name]
        if not rr: continue
        n=sum(r['shots'] for r in rr);out[name]={'shots':n,'seeds':len(rr),'raw_errors':sum(r['raw_errors'] for r in rr),'decoders':{}}
        for k in MODELS:
            errors=sum(r['decoders'][k]['errors'] for r in rr)
            a=sum(r['decoders'][k]['candidate_only_wrong'] for r in rr);b=sum(r['decoders'][k]['fixed_only_wrong'] for r in rr)
            diff=np.array([r['decoders'][k]['difference_rate'] for r in rr])
            boot=diff[rng.integers(0,len(diff),size=(CFG['bootstrap_resamples'],len(diff)))].mean(axis=1)
            neg=int((diff<0).sum());pos=int((diff>0).sum())
            out[name]['decoders'][k]={'errors':errors,'rate':errors/n,'wilson95':wilson(errors,n),'disagreements':a+b,**paired(a,b,n),'seed_differences':diff.tolist(),'seed_bootstrap_mean_ci95':np.quantile(boot,[.025,.975]).tolist(),'seed_wins':neg,'seed_losses':pos,'seed_ties':len(diff)-neg-pos,'seed_sign_p':float(binomtest(neg,neg+pos,.5).pvalue) if neg+pos else 1.}
    return out

def holm(values):
    order=np.argsort(values);out=[0.]*len(values);prev=0.
    for rank,i in enumerate(order): prev=max(prev,min(1.,values[i]*(len(values)-rank)));out[i]=prev
    return out

def run():
    if (ROOT/'FREEZE.json').exists(): raise RuntimeError('Run already frozen; refusing to overwrite previous study')
    frozen={n:sha(ROOT/n) for n in ['config.json','PHASE4A_METHOD.md','run_phase4a.py']}
    save('FREEZE.json',{'files':frozen,'frozen_before_sampling':True})
    roots=[CFG['seed_roots']['start']+i*CFG['seed_roots']['step'] for i in range(CFG['seed_roots']['count'])]
    used=[root+off+ci for root in roots for off in CFG['seed_offsets'].values() for ci in range(3)]+[CFG['template_seed_start']+i for i in range(9)]+[CFG['noiseless_seed']]
    assert len(used)==len(set(used))
    historical=set()
    def collect(obj,key=''):
        if isinstance(obj,dict):
            for k,v in obj.items(): collect(v,k)
        elif isinstance(obj,list):
            for v in obj: collect(v,key)
        elif isinstance(obj,int) and 'seed' in key.lower(): historical.add(obj)
    for p in ROOT.parent.rglob('*.json'):
        if ROOT in p.parents: continue
        try: collect(json.loads(p.read_text(encoding='utf-8-sig')))
        except (ValueError,UnicodeError): pass
    historical.update(31503001+i+100*c for i in range(3) for c in range(4))
    historical.update(31604001+10000*i+101+100*c for i in range(20) for c in range(4))
    assert not set(used)&historical
    R['validation']['seed_audit']={'unique_stage_seeds':len(used),'historical_explicit_seed_values_checked':len(historical),'collisions':[],'note':'Scans explicit JSON seed fields and expands Phase 3A/3B derivations; not a proof against unrecorded historical seeds.'}
    ideal=circuit(0,0); ds,ys=sample(ideal,256,CFG['noiseless_seed'],'noiseless_diagnostic')
    assert ideal.num_detectors==40 and ideal.num_observables==1 and not ds.any() and not ys.any()
    R['validation']['ideal']={'detectors':40,'observables':1,'diagnostic_shots':256,'all_zero':True}
    cs={};matchers={};metadata={};t=time.perf_counter()
    for idx,pair in enumerate(GRID):
        c=circuit(*pair);assert str(c.without_noise())==str(ideal.without_noise())
        dem=c.detector_error_model(decompose_errors=True)
        model=pymatching.Matching.from_detector_error_model(dem)
        assert model.num_detectors==40 and model.num_fault_ids==1
        noise={}
        for inst in c.flattened():
            if inst.name in ('DEPOLARIZE1','DEPOLARIZE2','X_ERROR','Z_ERROR'):
                n=len(inst.targets_copy())//(2 if inst.name=='DEPOLARIZE2' else 1)
                noise[inst.name]=noise.get(inst.name,0)+n
                assert np.isclose(inst.gate_args_copy()[0],pair[0] if inst.name.startswith('DEPOLARIZE') else pair[1])
        assert noise.get('DEPOLARIZE1',0)>0 and noise.get('DEPOLARIZE2',0)>0 and noise.get('X_ERROR',0)+noise.get('Z_ERROR',0)>0
        cs[pair]=c;matchers[pair]=model
        p=ROOT/'models';p.mkdir(exist_ok=True)
        (p/f'grid_{idx}.stim').write_text(str(c));(p/f'grid_{idx}.dem').write_text(str(dem))
        metadata[str(pair)]={'circuit_sha256':sha(p/f'grid_{idx}.stim'),'dem_sha256':sha(p/f'grid_{idx}.dem'),'fault_locations':noise,'edges':model.num_edges,'python_wrapper_bytes_not_total':sys.getsizeof(model)}
    TIMES['model_build_seconds']=time.perf_counter()-t
    fixed=matchers[(.003,.003)]
    def edge_map(m): return {str((a,b)):float(attr['weight']) for a,b,attr in m.edges()}
    fe=edge_map(fixed)
    for pair,m in matchers.items():
        ee=edge_map(m);common=set(fe)&set(ee)
        metadata[str(pair)]['weights_vs_fixed']={'common_edges':len(common),'different_weights':sum(not np.isclose(fe[k],ee[k],rtol=0,atol=1e-12) for k in common),'max_absolute_change':max(abs(fe[k]-ee[k]) for k in common),'same_edge_keys':set(fe)==set(ee)}
    R['validation']['model_metadata']=metadata;R['validation']['preflight_passed']=True
    save('VALIDATION_CHECKPOINT.json',R['validation'])
    print('Preflight passed; generating frozen detector-marginal templates.',flush=True)
    profiles=[]
    for i,pair in enumerate(GRID):
        d,y=sample(cs[pair],CFG['shots']['template_per_grid_point'],CFG['template_seed_start']+i,'template')
        profiles.append((d.sum(axis=0)+.5)/(len(d)+1));raw('template',CFG['template_seed_start']+i,str(i),d,y)
    profiles=np.asarray(profiles);save('TEMPLATES.json',{'grid':GRID,'detector_marginals':profiles.tolist()})
    fitted={};recoveries={n:0 for n in NAMES}
    for root in roots:
        for ci,name in enumerate(NAMES):
            true=tuple(CFG['conditions'][name]);d,y=sample(cs[true],CFG['shots']['calibration'],root+100+ci,'calibration');raw('calibration',root,name,d,y)
            t=time.perf_counter();counts=d.sum(axis=0);scores=(counts*np.log(profiles)+(len(d)-counts)*np.log1p(-profiles)).sum(axis=1)
            fitted[root,name]=GRID[int(np.argmax(scores))];TIMES['fit_seconds']+=time.perf_counter()-t
            recoveries[name]+=int(fitted[root,name]==true)
            R['calibration'].append({'seed_root':root,'condition':name,'estimated_pair':fitted[root,name],'scores':scores.tolist()})
            d,y=sample(cs[true],CFG['shots']['validation'],root+200+ci,'validation')
            preds={k:decode(m,d,k) for k,m in [('fixed',fixed),('calibrated',matchers[fitted[root,name]]),('model_informed',matchers[true])]}
            R['validation_rows'].append(score(root,name,y,preds));raw('validation',root,name,d,y,preds)
        save('DEVELOPMENT_CHECKPOINT.json',{'calibration':R['calibration'],'validation_rows':R['validation_rows']})
    R['validation']['exact_calibration_recoveries']=recoveries
    R['validation_aggregate']=aggregate(R['validation_rows'])
    primary=R['validation_aggregate'][CFG['primary_condition']]['decoders']['calibrated']
    gates={'calibration':all(v>=CFG['calibration_min_exact_recoveries_per_condition'] for v in recoveries.values()),'disagreement':primary['disagreements']>=CFG['validation_min_primary_disagreements'],'validation_direction':primary['difference_errors']<0}
    R['validation']['development_gates']=gates
    save('VALIDATION_CHECKPOINT.json',R['validation'])
    print('Development gates: '+str(gates)+'; recoveries: '+str(recoveries),flush=True)
    if not all(gates.values()): raise StopStudy('Predefined development usefulness/calibration gate failed; no final test shots generated')
    save('FROZEN_FITTED_MODELS.json',{'fits':R['calibration'],'frozen_before_test':True,'original_file_hashes':frozen})
    assert all(sha(ROOT/n)==v for n,v in frozen.items())
    for root in roots:
        for ci,name in enumerate(NAMES):
            true=tuple(CFG['conditions'][name]);d,y=sample(cs[true],CFG['shots']['test'],root+300+ci,'test')
            preds={k:decode(m,d,k) for k,m in [('fixed',fixed),('calibrated',matchers[fitted[root,name]]),('model_informed',matchers[true])]}
            R['test_rows'].append(score(root,name,y,preds));raw('test',root,name,d,y,preds)
        save('TEST_CHECKPOINT.json',R['test_rows']);print(f'Test seed {root} checkpoint saved.',flush=True)
    R['test_aggregate']=aggregate(R['test_rows']);p=R['test_aggregate'][CFG['primary_condition']]['decoders']['calibrated']
    R['primary_success']=p['difference_rate']<=-CFG['primary_min_absolute_improvement'] and p['mcnemar_p']<CFG['primary_alpha'] and p['seed_bootstrap_mean_ci95'][1]<0
    secondary=[(n,k) for n in NAMES for k in MODELS[1:] if (n,k)!=(CFG['primary_condition'],'calibrated')]
    for field in ['mcnemar_p','seed_sign_p']:
        vals=[R['test_aggregate'][n]['decoders'][k][field] for n,k in secondary]
        for (n,k),adj in zip(secondary,holm(vals)): R['test_aggregate'][n]['decoders'][k][field+'_holm5']=adj
    R['status']='completed';check_budget()

def finish():
    R['shot_counts']=COUNTS;R['timings']=TIMES;R['wall_seconds']=time.perf_counter()-START;R['peak_process_bytes']=max(PEAK,PROC.memory_info().rss)
    save('RESULTS.json',R)
    with (ROOT/'PER_SEED_RESULTS.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['stage','seed_root','condition','decoder','shots','raw_errors','residual_errors','difference_errors','disagreements','candidate_only_wrong','fixed_only_wrong'])
        for stage in ['validation','test']:
            for row in R[stage+'_rows']:
                for k,v in row['decoders'].items(): w.writerow([stage,row['seed_root'],row['condition'],k,row['shots'],row['raw_errors'],v['errors'],v['difference_errors'],v['disagreements'],v['candidate_only_wrong'],v['fixed_only_wrong']])
    val=R['validation'];(ROOT/'PHASE4A_VALIDATION.md').write_text('# Phase 4A validation\n\nRead-only historical seed checks, circuit checks and development gates are recorded below. No final test data enter these gates.\n\n```json\n'+json.dumps(val,indent=2)+'\n```\n',encoding='utf-8')
    lines=['# Phase 4A results','',f"Status: **{R['status']}**.",'',f"Shot counts: `{COUNTS}`. Wall time {R['wall_seconds']:.2f} s; peak process memory {R['peak_process_bytes']/1024**2:.1f} MiB.",'',f"Failures/stopping reasons: {R['failures']}",'']
    for stage in ['validation','test']:
        agg=R.get(stage+'_aggregate',{})
        if not agg: continue
        lines+=['## '+stage.capitalize(),'','| Condition | Shots | Raw | Fixed | Calibrated | Informed | Calibrated difference | Exact paired p |','|---|---:|---:|---:|---:|---:|---:|---:|']
        for n,a in agg.items():
            d=a['decoders'];p=d['calibrated'];lines.append(f"| {n} | {a['shots']} | {a['raw_errors']} | {d['fixed']['errors']} | {p['errors']} | {d['model_informed']['errors']} | {p['difference_errors']} | {p['mcnemar_p']:.6g} |")
        lines+=['','All rates, Wilson intervals, paired intervals, seed-bootstrap intervals, per-seed counts and secondary adjusted p-values (test only) are preserved in RESULTS.json. Validation outcomes are screening evidence, not independent confirmation.','']
    lines+=['## Runtime boundaries','',json.dumps(TIMES,indent=2),'','Decode times include all validation/test decoding for each model. Divide by the total completed validation/test shots for batched seconds/shot; this is not hardware latency. Calibration overhead is separately recorded. Model construction precedes fitting; specialists select from nine prebuilt models. Peak process working set includes Python and native allocations, but is not per-model memory.','',f"Primary success gate: {R.get('primary_success','not assessed')}."]
    (ROOT/'PHASE4A_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    if R['status']=='completed':
        p=R['test_aggregate'][CFG['primary_condition']]['decoders']['calibrated'];conclusion='The prespecified primary usefulness gate passed.' if R['primary_success'] else 'The prespecified primary usefulness gate did not pass.'
        detail=f"Primary rate difference: {p['difference_rate']:.8g}; bootstrap 95% interval: {p['seed_bootstrap_mean_ci95']}; exact McNemar p: {p['mcnemar_p']:.8g}."
    else: conclusion='The study stopped before complete confirmatory evaluation.';detail='The stopping reason is recorded in RESULTS.json and PHASE4A_RESULTS.md. No positive confirmatory claim is justified.'
    (ROOT/'PHASE4A_INTERPRETATION.md').write_text('# Phase 4A interpretation\n\n'+conclusion+' '+detail+'\n\nThis tests calibrated static models under stationary calibration/test conditions. It does not test online switching, unfamiliar mixtures, calibration drift, hardware integration, or adaptive superiority. Native two-qubit depolarizing channels and five rounds differ from Phase 3B; results cannot be attributed solely to measurement noise by comparing across phases.\n\nTemplates are shared and finite; the fitting objective approximates detector correlations. All generating rates occur on the candidate grid. The informed reference knows true rates and remains an approximate matching decoder, not a proven lower bound on error. Fixed and specialist use the same ordinary matching algorithm. A uniform nominal model is a useful baseline, but superiority to every possible pooled fixed model is not established.\n',encoding='utf-8')
    next_step='Replicate with fresh template banks and off-grid rates; include a pooled calibrated fixed competitor before designing causal adaptation.' if R.get('primary_success') else 'Inspect calibration recovery and validation/test disagreement outcomes. Preserve this result; do not tune on these tests or build a selector. Any revised experiment needs a new frozen protocol and fresh final samples.'
    (ROOT/'PHASE4A_NEXT_STEPS.md').write_text('# Phase 4A next steps\n\n'+next_step+'\n\nNo selector or presentation was implemented. Stop at this phase boundary.\n',encoding='utf-8')
    save('MANIFEST.json',{'files':[{'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='MANIFEST.json' and '__pycache__' not in p.parts]})
    print('Finished: '+R['status']+'; shots '+str(COUNTS),flush=True)

if __name__=='__main__':
    if (ROOT/'FREEZE.json').exists(): raise SystemExit('Existing run: refusing overwrite')
    try: run()
    except StopStudy as e: R['status']='stopped_by_prespecified_rule';R['failures'].append(str(e))
    except Exception as e: R['status']='failed';R['failures'].append(str(e));R['traceback']=traceback.format_exc()
    finally: finish()
