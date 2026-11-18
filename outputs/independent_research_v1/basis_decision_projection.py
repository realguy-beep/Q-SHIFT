"""Recompute cross-sample static-rate projection from fixed artifacts."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
classifier=json.loads((HERE/'bias_binary_cross_strength_results.json').read_text())
rates={}
for row in json.loads((HERE/'bias_crossover_results.json').read_text())['aligned_vs_mismatched']:
    rates.setdefault(float(row['bias_ratio']),{})[row['regime']]=(row['aligned_ler'],row['mismatched_ler'])
for row in json.loads((HERE/'basis_orientation_results.json').read_text())['conditions']:
    if row['regime'] in ('x_biased','z_biased'):
        a=row['bias_aligned_basis'];m=row['bias_mismatched_basis']
        rates.setdefault(10.0,{})[row['regime']]=(row['per_basis'][a]['ler'],row['per_basis'][m]['ler'])
rows=[]
for ratio in (2.0,5.0,10.0):
  for n in (25,100,500):
    acc={r['profile']:r['accuracy'] for r in classifier['individual_cells'] if r['distance']==3 and r['bias_ratio']==ratio and r['calibration_shots']==n}
    xa,xm=rates[ratio]['x_biased'];za,zm=rates[ratio]['z_biased']
    policy_x=acc['x_biased']*xa+(1-acc['x_biased'])*xm
    policy_z=acc['z_biased']*za+(1-acc['z_biased'])*zm
    policy=(policy_x+policy_z)/2;fixed_z=(xm+za)/2;fixed_x=(xa+zm)/2;oracle=(xa+za)/2
    rows.append({'distance':3,'bias_ratio':ratio,'calibration_shots':n,'x_profile_direction_accuracy':acc['x_biased'],'z_profile_direction_accuracy':acc['z_biased'],'projected_policy_ler_equal_profile_prior':policy,'projected_fixed_z_ler':fixed_z,'projected_fixed_x_ler':fixed_x,'projected_oracle_profile_ler':oracle,'relative_reduction_vs_fixed_best':1-policy/min(fixed_z,fixed_x),'oracle_gap_fraction':(policy-oracle)/(min(fixed_z,fixed_x)-oracle) if min(fixed_z,fixed_x)>oracle else None})
out={'status':'cross_sample_projection','profile_prior':'equal X-biased/Z-biased','classifier':'fixed binary LDA trained at d3 ratio10; predictions evaluated on independent detector-only calibration windows','logical_rates':'independent existing source-circuit samples from basis_orientation_results and bias_crossover_results','caveat':'projection only: combines separate classifier accuracy and separate per-profile LER; no direct end-to-end selected-policy test; calibration execution overhead excluded','rows':rows}
(HERE/'bias_decision_projection.json').write_text(json.dumps(out,indent=2)+'\n')
for r in rows:print(r)
