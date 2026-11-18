"""Fresh d9 2x2 CSS/XZZX and logical-memory-basis challenge."""
from __future__ import annotations
import json,time
from pathlib import Path
from xzzx_basis_factorial import make_circuit,full_resources,one,rr
HERE=Path(__file__).resolve().parent
CONDITIONS=(('css','x'),('css','z'),('xzzx','x'),('xzzx','z'))
PREFLIGHT_SEEDS=(2026114501,2026114502,2026114503,2026114504)
MAIN_SEEDS=(2026114511,2026114512,2026114513,2026114514)
PREFLIGHT_SHOTS=10000;MAIN_SHOTS=500000;MAX_SECONDS=300
KEYS=('qubits','detectors','observables','two_qubit_interactions','one_qubit_noise_targets','ticks','measurement_flip_targets')

def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');args=ap.parse_args()
 shots=PREFLIGHT_SHOTS if args.preflight else MAIN_SHOTS
 seeds=PREFLIGHT_SEEDS if args.preflight else MAIN_SEEDS
 circuits=[make_circuit(code,basis,9,17) for code,basis in CONDITIONS]
 resources=[full_resources(c) for c in circuits]
 if any(any(resources[0][k]!=r[k] for k in KEYS) for r in resources[1:]):
  raise RuntimeError(f'resource mismatch: {resources}')
 if any(r['pauli_channel_2_probability_vectors']!=resources[0]['pauli_channel_2_probability_vectors'] for r in resources[1:]):
  raise RuntimeError('PAULI_CHANNEL_2 probability vectors differ')
 begin=time.perf_counter()
 rows=[one(code,basis,seed,shots,args.preflight,9,17) for (code,basis),seed in zip(CONDITIONS,seeds,strict=True)]
 elapsed=time.perf_counter()-begin
 projection=sum((r['sample_seconds']+r['decode_seconds'])*MAIN_SHOTS/shots for r in rows) if args.preflight else None
 passed=projection is None or projection<=MAX_SECONDS
 comparisons={}
 if not args.preflight:
  sub={(r['code'],r['basis']):r for r in rows}
  css=sub[('css','x')]['failures']+sub[('css','z')]['failures']
  xzzx=sub[('xzzx','x')]['failures']+sub[('xzzx','z')]['failures']
  comparisons={'equal_weight_separate_basis_mix_xzzx_over_css':rr(xzzx,2*shots,css,2*shots),
   'xzzx_x_over_css_x':rr(sub[('xzzx','x')]['failures'],shots,sub[('css','x')]['failures'],shots),
   'xzzx_z_over_css_z':rr(sub[('xzzx','z')]['failures'],shots,sub[('css','z')]['failures'],shots),
   'raw_counts':{f'{c}_{b}':sub[(c,b)]['failures'] for c,b in CONDITIONS}}
 out={'status':('xzzx_basis_d9_preflight_passed' if passed else 'xzzx_basis_d9_preflight_stopped') if args.preflight else 'development_xzzx_basis_d9',
  'distance':9,'rounds':17,'conditions':rows,'resources_equal':True,'equal_resource_fields':list(KEYS),
  'shots_per_condition':shots,'projected_main_seconds':projection,'max_main_seconds':MAX_SECONDS,
  'elapsed_seconds':elapsed,'new_source_equivalent_samples':shots*len(rows),'comparisons':comparisons,
  'scope':'d9 development challenge of the finite-size balanced-memory basis tradeoff; not confirmatory, arbitrary-state, or threshold evidence',
  'hardware_assumption':'native CX/XCX/CZ duration and PAULI_CHANNEL_2 distributions equal; unverified'}
 target=HERE/('xzzx_basis_factorial_d9_preflight.json' if args.preflight else 'xzzx_basis_factorial_d9_results.json')
 target.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'status':out['status'],'projected_main_seconds':projection,'elapsed_seconds':elapsed,'comparisons':comparisons,'output':str(target)},indent=2))
 return int(args.preflight and not passed)
if __name__=='__main__':raise SystemExit(main())
