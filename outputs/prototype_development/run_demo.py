from __future__ import annotations
import hashlib, json, platform, time
from pathlib import Path
import numpy as np
import stim, pymatching
import matplotlib.pyplot as plt
from experiment import (REGIMES, REGIME_NAMES, REGIME_DECODER, POLICIES, GRID,
    build_bank, make_circuit, calibrate, run_replicate, analyze)

P=Path(__file__).resolve().parent; cfg=json.loads((P/'config.json').read_text()); data=P/'data'; data.mkdir(exist_ok=True)
whole_start=time.perf_counter()
assert cfg['confirmatory'] is False
models=build_bank(distance=cfg['distance'],rounds=cfg['rounds'])
# Circuit, DEM and noiseless checks are done before any study samples.
c0=stim.Circuit.generated(cfg['circuit'],distance=3,rounds=5)
assert c0.num_detectors==40 and c0.num_observables==1
nd,ny=c0.compile_detector_sampler(seed=cfg['rng']['diagnostic_seed']).sample(shots=64,separate_observables=True)
assert not nd.any() and not ny.any()
for i,(g,m) in enumerate(GRID):
    c=stim.Circuit.generated(cfg['circuit'],distance=3,rounds=5,after_clifford_depolarization=g,before_measure_flip_probability=m)
    assert c.num_detectors==40 and c.num_observables==1
    circuit_text=str(c)
    assert f'DEPOLARIZE1({g})' in circuit_text and f'DEPOLARIZE2({g})' in circuit_text
    assert f'X_ERROR({m})' in circuit_text  # Z-memory readout bit-flip channel before MR
    dem=c.detector_error_model(decompose_errors=True)
    assert dem.num_detectors==40 and dem.num_observables==1
    assert models[i].num_detectors==40

seeds=list(cfg['rng']['calibration_seeds'])
eval_seeds=[cfg['rng']['evaluation_seed_start']+((si*cfg['evaluation']['replicates_per_schedule']+ri)*cfg['evaluation']['blocks_per_replicate']+bi)
    for si in range(len(cfg['evaluation']['schedules'])) for ri in range(cfg['evaluation']['replicates_per_schedule']) for bi in range(cfg['evaluation']['blocks_per_replicate'])]
all_seeds=seeds+[cfg['rng']['diagnostic_seed'],cfg['rng']['bootstrap_seed']]+eval_seeds
assert len(all_seeds)==len(set(all_seeds))
cal=calibrate(models,cfg['calibration_shots_per_regime'],cfg['rng']['calibration_seeds'])
np.savez_compressed(data/'calibration_evidence.npz',profiles=cal['profiles'],utility_rates=cal['utility_rates'],paired_se=cal['paired_se'],
    errors=cal['calibration_errors'],detectors=np.stack(cal['detectors']),observables=np.stack(cal['observables']),calibration_best=cal['calibration_best'])
results={}
for si,kind in enumerate(cfg['evaluation']['schedules']):
    results[kind]=[]
    for ri in range(cfg['evaluation']['replicates_per_schedule']):
        rep=run_replicate(kind,ri,models,cal,shots=cfg['evaluation']['shots_per_block'],seed_start=cfg['rng']['evaluation_seed_start'],
            schedule_index=si,replicates=cfg['evaluation']['replicates_per_schedule'],blocks=cfg['evaluation']['blocks_per_replicate'])
        arrays=rep.pop('arrays')
        fn=f"eval_{si:02d}_{kind}_rep{ri:02d}.npz"
        np.savez_compressed(data/fn,**arrays)
        rep['evidence_file']=f'data/{fn}'
        results[kind].append(rep)
        print(kind,ri,rep['errors'], 'switches',rep['switch_count'], flush=True)
analysis=analyze(results,cfg['rng']['bootstrap_seed'],10000)
payload={"study":cfg['study'],"confirmatory":False,"config":cfg,"software":{"python":platform.python_version(),"stim":stim.__version__,"pymatching":pymatching.__version__,"numpy":np.__version__},
    "circuit_validation":{"detectors":40,"observables":1,"noiseless_all_zero":True,"dems_validated":9,"grid":[[float(a),float(b)] for a,b in GRID],"regime_specialist_indices":REGIME_DECODER},
    "calibration":{"shots_per_regime":cfg['calibration_shots_per_regime'],"profiles":cal['profiles'].tolist(),"utility_ler":cal['utility_rates'].tolist(),"calibration_best_decoder_indices":cal['calibration_best'].tolist(),"raw_file":"data/calibration_evidence.npz"},
    "analysis":analysis,"schedule_replicates":{s:[{k:v for k,v in r.items() if k!='blocks'} for r in reps] for s,reps in results.items()},
    "seed_audit":{"diagnostic_seed":cfg['rng']['diagnostic_seed'],"calibration_seeds":seeds,"evaluation_seed_start":cfg['rng']['evaluation_seed_start'],"evaluation_seed_count":len(eval_seeds),"evaluation_seed_last":max(eval_seeds),"bootstrap_seed":cfg['rng']['bootstrap_seed'],"unique":True,"historical_namespace_search":"Exact proposed seed values were absent from repository text search; see REPRODUCIBILITY.md for limits."},
    "runtime_seconds":time.perf_counter()-whole_start}
(P/'DEVELOPMENT_RESULTS.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')

# Figure: paired test-set rates with replicate-cluster bootstrap interval for adaptive - pooled.
labels=list(results); x=np.arange(len(labels)); names=['identity_no_decode','pooled_fixed','nominal_fixed','adaptive','regime_informed_diagnostic']; colors=['#a7b0b7','#24496b','#7796ab','#008b8b','#d99b3d']
fig,ax=plt.subplots(figsize=(10.5,5.3)); width=.15
for j,(name,color) in enumerate(zip(names,colors)):
    vals=[analysis['schedule_results'][s][name]['logical_error_rate'] for s in labels]
    ax.bar(x+(j-2)*width,vals,width,label=name.replace('_',' '),color=color)
ax.set_xticks(x,labels,rotation=15,ha='right');ax.set_ylabel('Logical error rate');ax.set_title('Matched-shot decoding across changing-noise schedules (development only)');ax.legend(fontsize=8,ncol=2);ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(P/'QSHIFT_DEVELOPMENT_RESULTS.png',dpi=180);plt.close(fig)

# Build a self-contained trial viewer from real detector samples and predictions.
demo_kind='data_to_measurement'; demo_rep=results[demo_kind][0]; a=np.load(P/demo_rep['evidence_file'])
shots=cfg['evaluation']['shots_per_block']; records=[]
for i in range(len(a['observables'])):
    b=i//shots; local=i%shots; choice=int(a['choice_by_block'][b]); y=int(a['observables'][i]); adaptive=int(a['grid_predictions'][choice,i]); pooled=int(a['grid_predictions'][1,i]); nominal=int(a['grid_predictions'][4,i])
    records.append({"block":b,"shot":local,"regime":REGIME_NAMES[int(a['state_ids'][i])],"choice":choice,"detectors":a['detectors'][i].astype(int).tolist(),"observable":y,
        "adaptive":adaptive,"pooled":pooled,"nominal":nominal,"identity":0,"grid_predictions":a['grid_predictions'][:,i].astype(int).tolist()})
events=[{"block":int(i),"decoder":int(demo_rep['blocks'][i]['decoder_index'])} for i in demo_rep['switch_blocks']]
viewer={"records":records,"switches":events,"metrics":{p:demo_rep['errors'][p] for p in POLICIES},"shots":demo_rep['shots'],"schedule":demo_rep['states'],"caption":"This viewer replays one actual seeded Stim evaluation replicate. The hidden regime is shown for interpretation only and is not passed to the decoder-selection policy."}
html='''<!doctype html><html><head><meta charset="utf-8"><title>Q-SHIFT Trial Viewer</title><style>body{font:15px system-ui,sans-serif;max-width:1050px;margin:28px auto;padding:0 20px;color:#243548}h1,h2{color:#183756}.card{border:1px solid #d4e0e8;border-radius:10px;padding:14px;margin:12px 0;background:#f7fafc}label{margin-right:16px}.ok{color:#087e68;font-weight:bold}.bad{color:#b23939;font-weight:bold}.bits{font-family:monospace;word-break:break-all;line-height:1.8}.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}.cell{padding:8px;border-radius:6px;background:#e8f1f6;text-align:center}table{border-collapse:collapse;width:100%}td,th{padding:7px;border:1px solid #d4e0e8;text-align:left}input{vertical-align:middle}</style></head><body><h1>Q-SHIFT: real simulated trial viewer</h1><p id="caption"></p><div class="card"><label>Block <select id="block"></select></label><label>Trial within block <input id="shot" type="range" min="0" max="511" value="0"><span id="shotval">0</span></label></div><div id="trial"></div><h2>Switch events</h2><div id="switches"></div><h2>Replicate scorecard</h2><div id="scores"></div><script>const DATA=__DATA__;const block=document.querySelector('#block'),shot=document.querySelector('#shot');document.querySelector('#caption').textContent=DATA.caption;for(let i=0;i<DATA.schedule.length;i++){let o=document.createElement('option');o.value=i;o.text=`Block ${i} — generated condition: ${DATA.schedule[i]}`;block.appendChild(o)}function render(){let b=+block.value,s=+shot.value;document.querySelector('#shotval').textContent=s;let r=DATA.records[b*512+s];let pred=(x)=>x===r.observable;let bitHTML=r.detectors.map((v,i)=>`<span title="Detector ${i}" style="display:inline-block;margin:2px;padding:2px 4px;background:${v?'#f4d7ce':'#e1eee9'}">D${i}:${v}</span>`).join('');let rows=[['Adaptive correction (decoder '+r.choice+')',r.adaptive],['Pooled fixed correction (decoder 1)',r.pooled],['Nominal fixed correction (decoder 4)',r.nominal],['Identity / no correction',r.identity]].map(x=>`<tr><td>${x[0]}</td><td>${x[1]}</td><td class="${pred(x[1])?'ok':'bad'}">${pred(x[1])?'Correct':'Incorrect'}</td></tr>`).join('');document.querySelector('#trial').innerHTML=`<div class="card"><b>Trial ${s}, block ${b}</b> | evaluation regime: <b>${r.regime}</b> | predicted logical correction: <b>${r.adaptive}</b> | actual logical observable: <b>${r.observable}</b><p>Adaptive prediction: <span class="${pred(r.adaptive)?'ok':'bad'}">${pred(r.adaptive)?'correct':'incorrect'}</span></p><h3>40 detector signals</h3><div class="bits">${bitHTML}</div><h3>Paired predictions on this exact shot</h3><table><tr><th>Method</th><th>Predicted logical flip</th><th>Outcome</th></tr>${rows}</table></div>`}block.onchange=render;shot.oninput=render;render();document.querySelector('#switches').textContent=DATA.switches.length?DATA.switches.map(x=>`block ${x.block}: selected decoder ${x.decoder}`).join(' | '):'No decoder switches in this replicate.';document.querySelector('#scores').innerHTML='<table><tr><th>Method</th><th>Errors</th><th>LER</th></tr>'+Object.entries(DATA.metrics).map(([k,v])=>`<tr><td>${k}</td><td>${v}</td><td>${(v/DATA.shots*100).toFixed(3)}%</td></tr>`).join('')+'</table>';</script></body></html>'''.replace('__DATA__',json.dumps(viewer,separators=(',',':')))
study_rows=[]
for method,stat in analysis['overall'].items():
    k=stat['errors']; n=stat['shots']; ph=k/n; z=1.959963984540054; den=1+z*z/n; mid=(ph+z*z/(2*n))/den; half=z*np.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/den
    study_rows.append(f"<tr><td>{method}</td><td>{k:,}/{n:,}</td><td>{ph:.4%}</td><td>{(1-ph):.4%}</td><td>[{max(0,mid-half):.4%}, {min(1,mid+half):.4%}]</td></tr>")
study_table='<h2>Full development-study scorecard (all matched shots)</h2><table><tr><th>Method</th><th>Errors / shots</th><th>LER</th><th>Success</th><th>Shotwise Wilson 95% LER interval</th></tr>'+''.join(study_rows)+'</table>'
ci=analysis['adaptive_minus_pooled_seed_cluster_bootstrap_95ci']
study_table+=f"<p>Adaptive minus pooled equal-schedule LER: {analysis['adaptive_minus_pooled_equal_schedule_mean']:+.5%}; seed-cluster bootstrap 95% interval [{ci[0]:+.5%}, {ci[1]:+.5%}]. The replicate scorecard below is for the selected trial-viewer schedule.</p>"
html=html.replace('<h2>Replicate scorecard</h2>',study_table+'<h2>Selected replicate scorecard</h2>')
(P/'QSHIFT_DEMO.html').write_text(html,encoding='utf-8')

# Machine-readable audit and reports.
hashes={str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(P.rglob('*')) if f.is_file() and f.name!='MANIFEST.json'}
manifest={"study":cfg['study'],"confirmatory":False,"file_sha256":hashes,"all_evaluation_shots":sum(r['shots'] for rows in results.values() for r in rows),"evaluation_roots":sum(len(v) for v in results.values()),"runtime_seconds":payload['runtime_seconds']}
(P/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({"overall":analysis['overall'],"adaptive_minus_pooled":analysis['adaptive_minus_pooled_equal_schedule_mean'],"ci":analysis['adaptive_minus_pooled_seed_cluster_bootstrap_95ci'],"runtime_seconds":payload['runtime_seconds']},indent=2))
