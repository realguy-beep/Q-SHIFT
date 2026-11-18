"""d7 2x2 XZZX/CSS memory screen at an existing 5:1 X-bias point."""
from __future__ import annotations
import json,time
from pathlib import Path
from xzzx_basis_factorial import make_circuit,full_resources,one,rr
HERE=Path(__file__).resolve().parent
CONDITIONS=(('css','x'),('css','z'),('xzzx','x'),('xzzx','z'))
PREFLIGHT_SEEDS=(2026114801,2026114802,2026114803,2026114804)
MAIN_SEEDS=(2026114811,2026114812,2026114813,2026114814)
PREFLIGHT_SHOTS=10000;MAIN_SHOTS=500000;MAX_SECONDS=300
KEYS=('qubits','detectors','observables','two_qubit_interactions','one_qubit_noise_targets','ticks','measurement_flip_targets')

def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');args=ap.parse_args()
 shots=PREFLIGHT_SHOTS if args.preflight else MAIN_SHOTS
 seeds=PREFLIGHT_SEEDS if args.preflight else MAIN_SEEDS
 circuits=[make_circuit(c,b,7,13,bias_ratio=5.) for c,b in CONDITIONS]
 resources=[full_resources(c) for c in circuits]
 if any(any(resources[0][k]!=r[k] for k in KEYS) for r in resources[1:]):raise RuntimeError(f'resource mismatch: {resources}')
 if any(r['pauli_channel_2_probability_vectors']!=resources[0]['pauli_channel_2_probability_vectors'] for r in resources[1:]):raise RuntimeError('two-qubit channel vectors differ')
 start=time.perf_counter();rows=[one(c,b,s,shots,args.preflight,7,13,bias_ratio=5.) for (c,b),s in zip(CONDITIONS,seeds,strict=True)];elapsed=time.perf_counter()-start
 projected=sum((x['sample_seconds']+x['decode_seconds'])*MAIN_SHOTS/shots for x in rows) if args.preflight else None
 passed=projected is None or projected<=MAX_SECONDS
 comparisons={}
 if not args.preflight:
  sub={(r['code'],r['basis']):r for r in rows};n=shots
  css=sub[('css','x')]['failures']+sub[('css','z')]['failures'];xz=sub[('xzzx','x')]['failures']+sub[('xzzx','z')]['failures']
  comparisons={'equal_weight_separate_basis_mix_xzzx_over_css':rr(xz,2*n,css,2*n),
   'xzzx_x_over_css_x':rr(sub[('xzzx','x')]['failures'],n,sub[('css','x')]['failures'],n),
   'xzzx_z_over_css_z':rr(sub[('xzzx','z')]['failures'],n,sub[('css','z')]['failures'],n),
   'raw_counts':{f'{c}_{b}':sub[(c,b)]['failures'] for c,b in CONDITIONS}}
 out={'status':('xzzx_bias5_preflight_passed' if passed else 'xzzx_bias5_preflight_stopped') if args.preflight else 'development_xzzx_bias5',
  'distance':7,'rounds':13,'bias_ratio':5.,'conditions':rows,'resources_equal':True,'equal_resource_fields':list(KEYS),
  'shots_per_condition':shots,'projected_main_seconds':projected,'max_main_seconds':MAX_SECONDS,'elapsed_seconds':elapsed,
  'new_source_equivalent_samples':shots*len(rows),'comparisons':comparisons,
  'scope':'d7 robustness comparison against known 5:1 X-bias; development-only, not arbitrary-state or hardware evidence',
  'hardware_assumption':'native CX/XCX/CZ durations and PAULI_CHANNEL_2 distributions equal; unverified'}
 target=HERE/('xzzx_bias_ratio5_preflight.json' if args.preflight else 'xzzx_bias_ratio5_results.json')
 target.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'status':out['status'],'projected_main_seconds':projected,'elapsed_seconds':elapsed,'output':str(target)},indent=2))
 return int(args.preflight and not passed)
if __name__=='__main__':raise SystemExit(main())
