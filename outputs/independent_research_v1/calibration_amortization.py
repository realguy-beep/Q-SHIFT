"""Compute illustrative calibration-throughput break-even from saved policy LERs."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
x=json.loads((HERE/'adaptive_basis_end_to_end_results.json').read_text())
C=500;rows=[]
for r in x['summary']:
    p_a=r['policy_ler'];p_s=r['fixed_z_ler']
    rows.append({'bias_ratio':r['bias_ratio'],'calibration_shots':C,'policy_ler':p_a,'static_ler':p_s,'break_even_logical_shots_per_calibration':C*(1-p_s)/(p_s-p_a),'assumption':'calibration shots produce no logical output; one calibration circuit costs one logical circuit'})
out={'status':'plug_in_resource_calculation','formula':'N > C*(1-p_static)/(p_static-p_policy)','rows':rows,'scope':'illustrative only; rates are development estimates and stability over this horizon is untested'}
(HERE/'calibration_amortization.json').write_text(json.dumps(out,indent=2)+'\n')
for r in rows:print(r)
