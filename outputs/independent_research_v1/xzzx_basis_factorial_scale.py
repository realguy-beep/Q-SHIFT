"""Fresh d3/d7 2x2 CSS/XZZX basis screens for distance robustness."""
from __future__ import annotations
import json,time
from pathlib import Path
from xzzx_basis_factorial import make_circuit,full_resources,one,rr
HERE=Path(__file__).resolve().parent
DISTS=(3,7);CODES=('css','xzzx');BASES=('x','z')
CONDITIONS=tuple((d,c,b) for d in DISTS for c in CODES for b in BASES)
PREFLIGHT_SEEDS=tuple(range(2026114301,2026114309))
MAIN_SEEDS=tuple(range(2026114311,2026114319))
PREFLIGHT_SHOTS=10000;MAIN_SHOTS=500000;MAX_SECONDS=300
RESOURCE_KEYS=('qubits','detectors','observables','two_qubit_interactions','one_qubit_noise_targets','ticks','measurement_flip_targets')

def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');args=ap.parse_args()
 shots=PREFLIGHT_SHOTS if args.preflight else MAIN_SHOTS
 seeds=PREFLIGHT_SEEDS if args.preflight else MAIN_SEEDS
 all_resources={}
 for d in DISTS:
  subset=[(c,b) for dd,c,b in CONDITIONS if dd==d]
  rows=[full_resources(make_circuit(c,b,d,2*d-1)) for c,b in subset]
  if any(any(rows[0][k]!=r[k] for k in RESOURCE_KEYS) for r in rows[1:]):
   raise RuntimeError(f'd{d} resource mismatch: {rows}')
  if any(r['pauli_channel_2_probability_vectors']!=rows[0]['pauli_channel_2_probability_vectors'] for r in rows[1:]):
   raise RuntimeError(f'd{d} PAULI_CHANNEL_2 probability mismatch')
  all_resources[str(d)]={'equal':True,'fields':list(RESOURCE_KEYS),'resources':rows[0]}
 begin=time.perf_counter();results=[]
 for (d,code,basis),seed in zip(CONDITIONS,seeds,strict=True):
  row=one(code,basis,seed,shots,args.preflight,d,2*d-1);row['distance']=d;row['rounds']=2*d-1;results.append(row)
 elapsed=time.perf_counter()-begin
 projection=sum((x['sample_seconds']+x['decode_seconds'])*MAIN_SHOTS/shots for x in results) if args.preflight else None
 passed=projection is None or projection<=MAX_SECONDS
 comparisons={}
 if not args.preflight:
  for d in DISTS:
   sub={(r['code'],r['basis']):r for r in results if r['distance']==d}
   n=shots
   css_total=sub[('css','x')]['failures']+sub[('css','z')]['failures']
   xzzx_total=sub[('xzzx','x')]['failures']+sub[('xzzx','z')]['failures']
   comparisons[str(d)]={'equal_weight_separate_basis_mix_xzzx_over_css':rr(xzzx_total,2*n,css_total,2*n),
     'xzzx_x_over_css_x':rr(sub[('xzzx','x')]['failures'],n,sub[('css','x')]['failures'],n),
     'xzzx_z_over_css_z':rr(sub[('xzzx','z')]['failures'],n,sub[('css','z')]['failures'],n),
     'raw_counts':{f'{code}_{basis}':sub[(code,basis)]['failures'] for code in CODES for basis in BASES}}
 output={'status':('xzzx_basis_scale_preflight_passed' if passed else 'xzzx_basis_scale_preflight_stopped') if args.preflight else 'development_xzzx_basis_scale',
   'distances':list(DISTS),'shots_per_condition':shots,'conditions':results,'resource_audit':all_resources,
   'projected_main_seconds':projection,'max_main_seconds':MAX_SECONDS,'elapsed_seconds':elapsed,
   'new_source_equivalent_samples':shots*len(results),'comparisons':comparisons,
   'scope':'fresh d3/d7 extension of a replicated d5 code/memory-basis tradeoff; development-only; equal-weight separate memory workloads are not arbitrary-state performance',
   'hardware_assumption':'native CX/XCX/CZ duration and PAULI_CHANNEL_2 distributions equal; not calibrated'}
 target=HERE/('xzzx_basis_factorial_scale_preflight.json' if args.preflight else 'xzzx_basis_factorial_scale_results.json')
 target.write_text(json.dumps(output,indent=2)+'\n')
 print(json.dumps({'status':output['status'],'projected_main_seconds':projection,'elapsed_seconds':elapsed,'comparisons':comparisons,'output':str(target)},indent=2))
 return int(args.preflight and not passed)
if __name__=='__main__':raise SystemExit(main())
