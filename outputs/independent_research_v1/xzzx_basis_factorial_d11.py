"""d11 runtime/resource preflight and bounded XZZX/CSS basis screen."""
from __future__ import annotations
import json,time
from pathlib import Path
from xzzx_basis_factorial import make_circuit,full_resources,one,rr
HERE=Path(__file__).resolve().parent
CONDITIONS=(('css','x'),('css','z'),('xzzx','x'),('xzzx','z'))
PREFLIGHT_SEEDS=(2026114601,2026114602,2026114603,2026114604)
MAIN_SEEDS=(2026114611,2026114612,2026114613,2026114614)
PREFLIGHT_SHOTS=10000;MAIN_SHOTS=500000;MAX_SECONDS=300
KEYS=('qubits','detectors','observables','two_qubit_interactions','one_qubit_noise_targets','ticks','measurement_flip_targets')

def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');args=ap.parse_args()
 shots=PREFLIGHT_SHOTS if args.preflight else MAIN_SHOTS
 seeds=PREFLIGHT_SEEDS if args.preflight else MAIN_SEEDS
 circuits=[make_circuit(code,basis,11,21) for code,basis in CONDITIONS]
 resources=[full_resources(c) for c in circuits]
 if any(any(resources[0][k]!=r[k] for k in KEYS) for r in resources[1:]):raise RuntimeError(f'resource mismatch: {resources}')
 if any(r['pauli_channel_2_probability_vectors']!=resources[0]['pauli_channel_2_probability_vectors'] for r in resources[1:]):raise RuntimeError('two-qubit channel probability vectors differ')
 start=time.perf_counter()
 rows=[one(code,basis,seed,shots,args.preflight,11,21) for (code,basis),seed in zip(CONDITIONS,seeds,strict=True)]
 elapsed=time.perf_counter()-start
 projected=sum((x['sample_seconds']+x['decode_seconds'])*MAIN_SHOTS/shots for x in rows) if args.preflight else None
 passed=projected is None or projected<=MAX_SECONDS
 comparisons={}
 if not args.preflight:
  sub={(r['code'],r['basis']):r for r in rows};n=shots
  css=sub[('css','x')]['failures']+sub[('css','z')]['failures']
  xzzx=sub[('xzzx','x')]['failures']+sub[('xzzx','z')]['failures']
  comparisons={'equal_weight_separate_basis_mix_xzzx_over_css':rr(xzzx,2*n,css,2*n),
   'xzzx_x_over_css_x':rr(sub[('xzzx','x')]['failures'],n,sub[('css','x')]['failures'],n),
   'xzzx_z_over_css_z':rr(sub[('xzzx','z')]['failures'],n,sub[('css','z')]['failures'],n),
   'raw_counts':{f'{c}_{b}':sub[(c,b)]['failures'] for c,b in CONDITIONS}}
 out={'status':('xzzx_basis_d11_preflight_passed' if passed else 'xzzx_basis_d11_preflight_stopped') if args.preflight else 'development_xzzx_basis_d11',
  'distance':11,'rounds':21,'conditions':rows,'resources_equal':True,'equal_resource_fields':list(KEYS),
  'shots_per_condition':shots,'projected_main_seconds':projected,'max_main_seconds':MAX_SECONDS,
  'elapsed_seconds':elapsed,'new_source_equivalent_samples':shots*len(rows),'comparisons':comparisons,
  'scope':'d11 bounded challenge of the balanced-memory XZZX/CSS tradeoff; development-only, not confirmatory or threshold evidence',
  'hardware_assumption':'native CX/XCX/CZ duration and PAULI_CHANNEL_2 distributions equal; unverified'}
 target=HERE/('xzzx_basis_factorial_d11_preflight.json' if args.preflight else 'xzzx_basis_factorial_d11_results.json')
 target.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'status':out['status'],'projected_main_seconds':projected,'elapsed_seconds':elapsed,'output':str(target)},indent=2))
 return int(args.preflight and not passed)
if __name__=='__main__':raise SystemExit(main())
