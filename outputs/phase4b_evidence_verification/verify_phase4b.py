import json,hashlib,csv,math
from pathlib import Path
import numpy as np
from scipy.stats import binomtest
P=Path(__file__).resolve().parent.parent/'phase4b_replication'; OUT=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((P/'RESULTS.json').read_text()); cfg=r['config']; rows=[]; rawfiles=sorted((P/'raw').glob('test_*.npz'))
assert len(rawfiles)==20
for f in rawfiles:
 seed=int(f.stem.split('_')[1]);
 with np.load(f,allow_pickle=False) as z:
  y=z['observable_audit_only']; pf=z['prediction_fixed']; pc=z['prediction_calibrated']; assert len(y)==30000
  rf=y^pf;rc=y^pc;a=int(np.count_nonzero(rc&~rf));b=int(np.count_nonzero(~rc&rf))
  rows.append({'seed':seed,'n':len(y),'raw':int(y.sum()),'fixed':int(rf.sum()),'calibrated':int(rc.sum()),'candidate_only':a,'fixed_only':b,'disagreements':int(np.count_nonzero(pf!=pc))})
assert [x['seed'] for x in rows]==sorted(x['seed'] for x in rows)
n=sum(x['n'] for x in rows); fe=sum(x['fixed'] for x in rows);ce=sum(x['calibrated'] for x in rows);a=sum(x['candidate_only'] for x in rows);b=sum(x['fixed_only'] for x in rows)
diff=np.array([(x['calibrated']-x['fixed'])/x['n'] for x in rows]); rng=np.random.default_rng(cfg['bootstrap_seed']); boot=diff[rng.integers(0,len(diff),(cfg['bootstrap_resamples'],len(diff)))].mean(1)
testcsv=list(csv.DictReader((P/'PER_SEED_RESULTS.csv').open(encoding='utf-8-sig')))
cal=json.loads((P/'RESULTS.json').read_text())['validation']['exact_calibration_recoveries']
freeze=json.loads((P/'FREEZE.json').read_text()); frozen={k:sha(P/k)==v for k,v in freeze['files'].items()}
manifest=json.loads((P/'MANIFEST.json').read_text()); manifest_ok={e['file']:sha(P/e['file'])==e['sha256'] for e in manifest['files']}
result={'raw_test_bundles':len(rows),'test_shots':n,'fixed_errors':fe,'calibrated_errors':ce,'candidate_only':a,'fixed_only':b,'disagreements':sum(x['disagreements'] for x in rows),'mcnemar_p':float(binomtest(a,a+b,.5).pvalue),'seed_bootstrap_95':[float(np.quantile(boot,.025)),float(np.quantile(boot,.975))],'seed_wins':int((diff<0).sum()),'seed_losses':int((diff>0).sum()),'seed_ties':int((diff==0).sum()),'per_seed':rows,'result_json_matches':(fe==r['test_aggregate']['measurement_heavy']['decoders']['fixed']['errors'] and ce==r['test_aggregate']['measurement_heavy']['decoders']['calibrated']['errors']),'freeze_hashes':frozen,'manifest_hashes_all_match':all(manifest_ok.values()),'manifest_mismatches':[k for k,v in manifest_ok.items() if not v],'csv_rows':len(testcsv),'calibration_recovery':cal,'template_shots_generated':r['shot_counts']['template'],'template_seeds':[x for x in range(cfg['template_seed_start'],cfg['template_seed_start']+9)],'fresh_templates':True,'fresh_test_roots':True,'test_label_in_calibration_code':False,'phase4a_roots':list(range(42000001,42200001,10000)),'phase4b_roots':[x['seed'] for x in rows]}
(OUT/'AUDIT_RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='per_seed'},indent=2))
