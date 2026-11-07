"""Freeze, validate prior evidence, then sample fresh Phase 2A evaluation roots."""
from __future__ import annotations
import csv, hashlib, json, platform, re, sys, time
from pathlib import Path
import numpy as np, stim, pymatching

P=Path(__file__).resolve().parent; ROOT=P.parents[1]
CFG=json.loads((P/'config.json').read_text()); PREV=ROOT/'outputs/prototype_development'
sys.path.insert(0,str(PREV))
from experiment import REGIME_NAMES, GRID, decode_grid, make_circuit

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def graph_record(i, params, circuit):
    dem=circuit.detector_error_model(decompose_errors=True)
    m=pymatching.Matching.from_detector_error_model(dem)
    edges=m.edges()
    top=sorted((min(-1 if u is None else int(u),-1 if v is None else int(v)),max(-1 if u is None else int(u),-1 if v is None else int(v))) for u,v,_ in edges)
    weighted=sorted(((-1 if u is None else int(u),-1 if v is None else int(v)),round(float(a['weight']),12),tuple(sorted(int(x) for x in a.get('fault_ids',set())))) for u,v,a in edges)
    edge_faults=[sorted(int(x) for x in a.get('fault_ids',set())) for _,_,a in edges]
    return m, {'index':i,'gate_probability':float(params[0]),'measurement_probability':float(params[1]),
        'dem_sha256':hashlib.sha256(str(dem).encode()).hexdigest(),
        'graph_topology_sha256':hashlib.sha256(repr(top).encode()).hexdigest(),
        'weighted_fault_graph_sha256':hashlib.sha256(repr(weighted).encode()).hexdigest(),
        'detectors':m.num_detectors,'matching_detector_nodes':m.num_nodes,'edges':m.num_edges,
        'boundary_edge_count':sum(u is None or v is None for u,v,_ in edges),
        'edges_with_nonempty_logical_fault_ids':sum(bool(x) for x in edge_faults),
        'logical_fault_ids_seen':sorted(set(x for fs in edge_faults for x in fs)),
        'unique_edge_weights_rounded_8dp':len(set(round(float(a['weight']),8) for _,_,a in edges)),
        'edges':[{"u":None if u is None else int(u),"v":None if v is None else int(v),"weight":float(a['weight']),"fault_ids":sorted(int(x) for x in a.get('fault_ids',set()))} for u,v,a in edges]}

def verify_prior():
    manifest=json.loads((PREV/'MANIFEST.json').read_text())
    changed=[]
    for rel,h in manifest['hashes_sha256'].items():
        f=PREV/rel
        if not f.exists() or sha(f)!=h: changed.append(rel)
    if changed: raise RuntimeError(f'previous development manifest mismatch: {changed[:5]}')
    # Build exact frozen candidates from the existing implementation.
    from decoder_bank import build_bank
    models=build_bank(distance=3,rounds=5)
    totals={'identity_no_decode':0,'pooled_fixed':0,'nominal_fixed':0}; shots=0; roots=0
    for f in sorted((PREV/'data').glob('eval_*.npz')):
        z=np.load(f,allow_pickle=False); d=z['detectors']; y=z['observables']; pred=decode_grid(models,d)
        if not np.array_equal(pred,z['grid_predictions']): raise RuntimeError(f'prior prediction mismatch: {f.name}')
        totals['identity_no_decode']+=int(y.sum()); totals['pooled_fixed']+=int(np.count_nonzero(pred[1]^y)); totals['nominal_fixed']+=int(np.count_nonzero(pred[4]^y));shots+=len(y);roots+=1
    if shots!=307200 or totals!={'identity_no_decode':19726,'pooled_fixed':1989,'nominal_fixed':1976} or roots!=50:
        raise RuntimeError(f'previous result mismatch: roots={roots}, shots={shots}, totals={totals}')
    return {'manifest_files_verified':len(manifest['hashes_sha256']),'evaluation_roots':roots,'shots':shots,'counts':totals,'all_nine_predictions_independently_redecoded':True,
        'evaluated_before_this_phase':True,'not_used_as_phase2a_untouched_test':True}

# First: verify the already-audited source and raw evidence without changing it.
prior_audit=verify_prior()
from decoder_bank import build_bank
models=build_bank(distance=3,rounds=5)
assert len(models)==9 and tuple(GRID)==tuple((a,b) for a in (.001,.003,.006) for b in (.001,.003,.006))

# Recompute development selection from calibration raw arrays, not stored summaries.
cal=np.load(PREV/'data/calibration_evidence.npz',allow_pickle=False)
cal_errors=np.zeros((3,9),dtype=np.int64)
for r in range(3):
    d=cal['detectors'][r]; y=cal['observables'][r]; pred=decode_grid(models,d)
    assert np.array_equal(pred^y[None,:],cal['errors'][r])
    cal_errors[r]=np.count_nonzero(pred^y[None,:],axis=1)
cal_ler=cal_errors/cal['observables'].shape[1]
best_global=int(np.argmin(cal_ler.mean(axis=0))); best_regime=np.argmin(cal_ler,axis=1).astype(int)
assert best_global==1 and best_regime.tolist()==[1,1,1]
selection={'calibration_shots_per_regime':20000,'calibration_errors':cal_errors.tolist(),'calibration_ler':cal_ler.tolist(),
    'best_global_index':best_global,'best_per_regime_indices':best_regime.tolist(),'tie_break':'lowest index via numpy argmin','selection_recomputed_from_raw':True}
(P/'SELECTION.json').write_text(json.dumps(selection,indent=2)+'\n',encoding='utf-8')

# Screen the complete fresh seed list against recoverable text artifacts before freezing.
seed_list=[99500001+1000*r+s for r in range(3) for s in range(20)]
assert len(seed_list)==len(set(seed_list))
rx=re.compile(r'(?<!\d)(?:'+ '|'.join(map(str,seed_list)) +r')(?!\d)')
searched=[]; collisions=[]
for f in ROOT.rglob('*'):
    if not f.is_file() or P.name in f.parts or '.git' in f.parts or '__pycache__' in f.parts: continue
    if f.suffix.lower() not in {'.json','.md','.py','.csv','.txt','.log','.yaml','.yml'}: continue
    searched.append(str(f.relative_to(ROOT)))
    try: txt=f.read_text(encoding='utf-8',errors='ignore')
    except OSError: continue
    collisions += [{'file':str(f.relative_to(ROOT)),'seed':int(m.group(0))} for m in rx.finditer(txt)]
if collisions: raise RuntimeError(f'Phase 2A seed collision(s): {collisions[:10]}')
(P/'SEED_SCREENING.json').write_text(json.dumps({'fresh_seeds':seed_list,'count':len(seed_list),'unique':True,'text_files_screened':searched,'text_file_count':len(searched),'collisions':collisions,'coverage_limit':'This exact-text scan cannot expose RNG use missing from records or unavailable binary-only artifacts.'},indent=2)+'\n',encoding='utf-8')

grid_records=[]; topo=[]
for i,(params) in enumerate(GRID):
    c=stim.Circuit.generated('surface_code:rotated_memory_z',distance=3,rounds=5,after_clifford_depolarization=params[0],before_measure_flip_probability=params[1])
    assert c.num_detectors==40 and c.num_observables==1
    m,rec=graph_record(i,params,c);grid_records.append(rec)
    if i==0: topo.append(rec['graph_topology_sha256'])
assert len({x['graph_topology_sha256'] for x in grid_records})==1
assert len({x['weighted_fault_graph_sha256'] for x in grid_records})==9
bank_audit={'grid_order':[[float(a),float(b)] for a,b in GRID],'models':grid_records,
    'unique_topologies':len({x['graph_topology_sha256'] for x in grid_records}),
    'unique_weighted_fault_graphs':len({x['weighted_fault_graph_sha256'] for x in grid_records}),
    'physical_correction_chains_available_in_saved_arrays':False,
    'interpretation':'The nine models share graph topology but differ in weights. Distinct edge weights do not by themselves establish distinct optimal logical predictions or physical correction chains.'}
(P/'DECODER_BANK_AUDIT.json').write_text(json.dumps(bank_audit,indent=2)+'\n',encoding='utf-8')
(P/'PRIOR_DATA_AUDIT.json').write_text(json.dumps(prior_audit,indent=2)+'\n',encoding='utf-8')

# Save the exact pre-sampling freeze before any fresh evaluation sample is drawn.
input_files=[PREV/'config.json',PREV/'MANIFEST.json',PREV/'AUDITED_RESULTS.json',PREV/'data/calibration_evidence.npz',
    ROOT/'outputs/phase4c_strong_baselines/adaptive/decoder_bank.py',ROOT/'outputs/phase4c_strong_baselines/STAGE1_FREEZE.json',
    P/'config.json',P/'PHASE2A_PROTOCOL.md',P/'run_phase2a.py',P/'analyze_phase2a.py',P/'test_phase2a.py',
    P/'SELECTION.json',P/'SEED_SCREENING.json',P/'DECODER_BANK_AUDIT.json',P/'PRIOR_DATA_AUDIT.json']
freeze={'protocol_frozen_before_fresh_evaluation':True,'pretest_seed_scan_pass':True,'selection':selection,
    'fresh_evaluation_seeds':seed_list,'shots_per_seed':10000,'input_sha256':{str(f.relative_to(ROOT)):sha(f) for f in input_files},
    'environment':{'python':platform.python_version(),'stim':stim.__version__,'pymatching':pymatching.__version__,'numpy':np.__version__}}
(P/'FREEZE.json').write_text(json.dumps(freeze,indent=2)+'\n',encoding='utf-8')
# Generate the fresh held-out development evaluation only after FREEZE.json exists.
rows=[]; started=time.perf_counter(); data=P/'data'; data.mkdir(exist_ok=True)
with (P/'SEED_MANIFEST.csv').open('w',newline='',encoding='utf-8') as sf:
    sw=csv.writer(sf);sw.writerow(['regime_index','regime','root_index','seed','shots','file'])
    for r,name in enumerate(REGIME_NAMES):
        gate,meas=CFG['regimes'][r]['gate_probability'],CFG['regimes'][r]['measurement_probability']
        circuit=stim.Circuit.generated(CFG['circuit'],distance=CFG['distance'],rounds=CFG['rounds'],after_clifford_depolarization=gate,before_measure_flip_probability=meas)
        for root in range(20):
            seed=99500001+1000*r+root
            detectors,obs=circuit.compile_detector_sampler(seed=seed).sample(shots=10000,separate_observables=True)
            detectors=np.asarray(detectors,dtype=np.uint8); obs=np.asarray(obs[:,0],dtype=np.uint8)
            pred=decode_grid(models,detectors).astype(np.uint8)
            namefile=f'eval_{r}_{name}_root{root:02d}.npz'
            np.savez_compressed(data/namefile,detectors=detectors,observable=obs,predictions=pred,
                regime_id=np.asarray(r,dtype=np.uint8),root_index=np.asarray(root,dtype=np.uint8),seed=np.asarray(seed,dtype=np.uint32))
            sw.writerow([r,name,root,seed,len(obs),f'data/{namefile}'])
            rows.append((name,root,seed,int(len(obs))))
            if root%5==0: print(f'{name}: finished root {root}/19',flush=True)
(P/'RUN_METADATA.json').write_text(json.dumps({'fresh_roots':len(rows),'shots_per_root':10000,'total_shots':sum(x[3] for x in rows),
    'runtime_seconds':time.perf_counter()-started,'seed_manifest':'SEED_MANIFEST.csv','protocol_frozen_before_sampling':True},indent=2)+'\n',encoding='utf-8')
print(f"Phase 2A raw sampling complete: {len(rows)} roots; {sum(x[3] for x in rows):,} fresh paired shots")
