"""Read saved shots/predictions and verify reported counts; no simulation or decoding."""
import json,hashlib
from pathlib import Path
import numpy as np
from scipy.stats import binomtest
P=Path(__file__).resolve().parent
r=json.loads((P/'RESULTS.json').read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
frozen=json.loads((P/'FREEZE.json').read_text())
assert all(sha(P/n)==h for n,h in frozen['files'].items())
manifest=json.loads((P/'MANIFEST.json').read_text())
assert all(sha(P/e['file'])==e['sha256'] for e in manifest['files'])
checked=0
for stage in ['validation','test']:
 for row in r[stage+'_rows']:
  with np.load(P/'raw'/f"{stage}_{row['seed_root']}_{row['condition']}.npz",allow_pickle=False) as z:
   y=z['observable_audit_only'];assert len(y)==row['shots'] and int(y.sum())==row['raw_errors']
   d=np.unpackbits(z['detectors_packed_little'],axis=1,bitorder='little')[:,:int(z['detector_count'])]
   assert d.shape==(len(y),40)
   fixed=y^z['prediction_fixed']
   for name,m in row['decoders'].items():
    residual=y^z['prediction_'+name]
    assert int(residual.sum())==m['errors']
    assert int((residual & ~fixed).sum())==m['candidate_only_wrong']
    assert int((~residual & fixed).sum())==m['fixed_only_wrong']
   checked+=1
 for name,a in r[stage+'_aggregate'].items():
  rr=[x for x in r[stage+'_rows'] if x['condition']==name]
  assert sum(x['shots'] for x in rr)==a['shots']
  for k,v in a['decoders'].items():
   assert sum(x['decoders'][k]['errors'] for x in rr)==v['errors']
   n=v['candidate_only_wrong']+v['fixed_only_wrong']
   p=binomtest(v['candidate_only_wrong'],n,.5).pvalue if n else 1.
   assert abs(p-v['mcnemar_p'])<1e-14
report={'saved_validation_test_files_checked':checked,'original_manifest_files_verified':len(manifest['files']),'frozen_source_method_config_unchanged':True,'saved_predictions_recompute_residuals':True,'aggregate_counts_and_exact_p_verified':True,'new_simulation_shots':0,'decoder_reexecution':False}
(P/'POSTRUN_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
lines=['','## Detailed independent test analysis','', 'All differences below are candidate minus fixed; negative favors the candidate. Intervals and rates use probability units unless stated otherwise.','']
for n,a in r['test_aggregate'].items():
 lines += ['### '+n,'',f"Raw observable error rate: {a['raw_errors']/a['shots']:.8f}.",'','| Decoder | Errors | Rate | Wilson 95% interval | Discordant: candidate-only / fixed-only |','|---|---:|---:|---|---|']
 for k,v in a['decoders'].items():
  lines.append(f"| {k} | {v['errors']} | {v['rate']:.8f} | {v['wilson95']} | {v['candidate_only_wrong']} / {v['fixed_only_wrong']} |")
 for k in ['calibrated','model_informed']:
  v=a['decoders'][k]
  lines+=['',f"**{k}:** paired difference {v['difference_rate']:.8f}; paired approximate 95% CI {v['paired_ci95_approx']}; seed-bootstrap mean 95% CI {v['seed_bootstrap_mean_ci95']}. Exact paired p={v['mcnemar_p']:.8g}; seed sign p={v['seed_sign_p']:.8g}. Seed wins/losses/ties={v['seed_wins']}/{v['seed_losses']}/{v['seed_ties']}. Disagreement rate={v['disagreements']/a['shots']:.8f}. Secondary Holm-adjusted paired p={v.get('mcnemar_p_holm5','primary; no secondary adjustment')}; sign p={v.get('seed_sign_p_holm5','primary diagnostic')}. Relative change vs fixed={(v['errors']/a['decoders']['fixed']['errors']-1)*100:.3f}%."]
lines+=['','## Measured overhead','']
total=r['shot_counts']['validation']+r['shot_counts']['test']
for k,t in r['timings']['decoding_seconds'].items(): lines.append(f'- {k}: {t/total*1e6:.4f} microseconds/shot, batched validation and test calls combined.')
lines += [f"- Calibration marginal scoring: {r['timings']['fit_seconds']/60*1000:.4f} ms per 20,000-shot calibration batch, excluding calibration sampling and template construction.",'- No adaptive switching was implemented; switching overhead and adaptation delay are not applicable.','- Templates and calibration are additional offline work. Decode-only timing must not be presented as the complete calibration-inclusive cost.','', '## Saved-artifact verification','',f"Recomputed residuals and discordant counts from all {checked} saved validation/test bundles; reconciled aggregates and exact paired p-values; verified {len(manifest['files'])} original artifact hashes and the frozen source/config/method hashes. This audit did not resample or rerun decoding."]
with (P/'PHASE4A_RESULTS.md').open('a',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
with (P/'PHASE4A_INTERPRETATION.md').open('a',encoding='utf-8') as f:
 f.write('\n## Scope of the observed gain\n\nMeasurement-heavy residuals fell from 1,118 to 940 on 600,000 paired final shots: 178 fewer errors, 15.92% relative reduction, or 0.02967 percentage points absolute. Nominal tied exactly. Data-heavy had 22 more errors (8,599 versus 8,577), with no statistically supported difference. The successful gate is specific to the primary measurement-heavy condition. Calibration selected the true grid pair in all 60 batches, so calibrated and model-informed predictions coincide. This does not establish performance when calibration is inaccurate.\n\nThe calibration/validation gate was inspected before final test sampling. Validation selected whether to run the frozen study, not new model parameters or a new primary endpoint. Finite shared templates and on-grid generating conditions make this an optimistic, controlled model-adequacy pilot. An independently replicated benefit against a pooled fixed competitor is needed before any broad claim.\n')
with (P/'IMPLEMENTATION_LOG.md').open('a',encoding='utf-8') as f:f.write('\nThe frozen run completed all planned shots and gates. Post-run read-only analysis verified hashes and rescored saved predictions, with zero new simulation shots. Reports were then expanded with uncertainty, discordance, overhead, and interpretation. MANIFEST_FINAL.json records the expanded deliverables; MANIFEST.json is the original end-of-run snapshot.\n')
files=[{'file':str(p.relative_to(P)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(P.rglob('*')) if p.is_file() and p.name!='MANIFEST_FINAL.json' and '__pycache__' not in p.parts]
(P/'MANIFEST_FINAL.json').write_text(json.dumps({'files':files},indent=2)+'\n')
print(json.dumps(report))
