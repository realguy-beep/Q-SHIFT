import json,csv,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;d=json.loads((P/'STAGE2_RECOVERED_RESULTS.json').read_text());rows=d['per_root'];order=['calibrated','pooled_fixed','nominal_fixed','minimax_fixed','condition_specific']
assert len(rows)==60 and sum(x['shots'] for x in rows)==1800000
for c,v in d['per_regime'].items():
 rr=[x for x in rows if x['condition']==c];assert sum(x['errors'][0] for x in rr)==v['errors']['calibrated'];assert sum(x['errors'][1] for x in rr)==v['errors']['pooled_fixed']
with (P/'STAGE2_RECOVERED_PER_ROOT.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (P/'STAGE2_RECOVERED_PER_REGIME.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['regime','shots','raw_errors']+order)
 for c,v in d['per_regime'].items():w.writerow([c,v['shots'],sum(x['raw_errors'] for x in rows if x['condition']==c)]+[v['errors'][k] for k in order])
(P/'STAGE2_RECOVERED_STATISTICS.md').write_text('# Recovered Stage 2 statistics\n\nEqual-regime calibrated minus pooled fixed = %.8f. Regime-stratified bootstrap 95%% CI %s. Frozen sign-flip p=%.8f. The primary evidence does not support calibrated superiority over pooled fixed.\n\n| Regime | Calibrated | Pooled fixed | Difference | Relative reduction |\n|---|---:|---:|---:|---:|\n'% (d['primary']['equal_regime_difference'],d['primary']['bootstrap_ci95'],d['primary']['sign_flip_p_two_sided'])+''.join(f"| {c} | {v['errors']['calibrated']} | {v['errors']['pooled_fixed']} | {v['primary_difference']:.8f} | {v['relative_reduction']:.4%} |\n" for c,v in d['per_regime'].items())+'\nSecondary tests and Holm values: '+json.dumps(d['secondary'],indent=2)+'\n')
(P/'STAGE2_RECOVERED_LIMITATIONS.md').write_text('# Limitations\n\nAll 60 saved test prediction bundles independently re-decoded; raw test shots were 1.8m. Calibration detector arrays and scoring traces were not saved, so calibration choices cannot be independently refit. Numerical prediction verification is not full calibration provenance. Data are distance 3/five rounds and only three stationary on-grid regimes.\n')
(P/'STAGE2_RECOVERY_AUDIT.md').write_text((P/'STAGE2_RECOVERY_AUDIT.md').read_text()+'\nAggregate checks against every per-root row passed; recovered reporting CSVs were generated directly from the verified JSON.\n')
files=[{'file':x.name,'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} for x in P.iterdir() if x.is_file() and x.name!='STAGE2_RECOVERY_MANIFEST.json'];(P/'STAGE2_RECOVERY_MANIFEST.json').write_text(json.dumps(files,indent=2))
print('verified roots',len(rows),'shots',sum(x['shots'] for x in rows))
