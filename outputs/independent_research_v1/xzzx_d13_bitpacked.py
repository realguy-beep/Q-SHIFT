"""d13 exact-equivalence and throughput screen for bit-packed decoding."""
from __future__ import annotations
import json,time,resource
from pathlib import Path
import numpy as np,pymatching
from xzzx_basis_factorial import make_circuit,full_resources,rr
HERE=Path(__file__).resolve().parent
CONDITIONS=(('css','x'),('css','z'),('xzzx','x'),('xzzx','z'))
PREFLIGHT_SEEDS=(2026115001,2026115002,2026115003,2026115004)
MAIN_SEEDS=(2026115011,2026115012,2026115013,2026115014)
PREFLIGHT_SHOTS=50000;MAIN_SHOTS=500000;MAX_SECONDS=300
KEYS=('qubits','detectors','observables','two_qubit_interactions','one_qubit_noise_targets','ticks','measurement_flip_targets')

def one(code,basis,seed,shots):
 c=make_circuit(code,basis,13,25)
 dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=.0018)
 m=pymatching.Matching.from_detector_error_model(dem,enable_correlations=True)
 t=time.perf_counter();d,o=c.compile_detector_sampler(seed=seed).sample(shots=shots,separate_observables=True)
 unpacked_sample=time.perf_counter()-t
 t=time.perf_counter();dp,op=c.compile_detector_sampler(seed=seed).sample(shots=shots,separate_observables=True,bit_packed=True)
 packed_sample=time.perf_counter()-t
 if not np.array_equal(np.packbits(d,axis=1,bitorder='little'),dp):raise RuntimeError(f'packed detector stream mismatch {code}/{basis}')
 if not np.array_equal(np.packbits(o,axis=1,bitorder='little'),op):raise RuntimeError(f'packed observable stream mismatch {code}/{basis}')
 t=time.perf_counter();pred=np.asarray(m.decode_batch(d,enable_correlations=True),dtype=np.uint8)
 normal_decode=time.perf_counter()-t
 t=time.perf_counter();predp=np.asarray(m.decode_batch(dp,bit_packed_shots=True,bit_packed_predictions=True,enable_correlations=True),dtype=np.uint8)
 packed_decode=time.perf_counter()-t
 expected=np.packbits(pred,axis=1,bitorder='little')
 if not np.array_equal(expected,predp):raise RuntimeError(f'bit-packed decoder prediction mismatch {code}/{basis}')
 if pred.shape!=(shots,1):raise RuntimeError(f'unexpected observable shape {pred.shape}')
 observed=np.unpackbits(op,axis=1,bitorder='little')[:,:1]
 fails=int(np.count_nonzero(pred!=observed))
 scalar=np.asarray([m.decode(d[i],enable_correlations=True) for i in range(min(100,shots))],dtype=np.uint8).reshape(min(100,shots),-1)
 if not np.array_equal(scalar,pred[:len(scalar)]):raise RuntimeError(f'scalar/batch mismatch {code}/{basis}')
 return {'code':code,'basis':basis,'seed':seed,'shots':shots,'failures':fails,'ler':fails/shots,
  'normal_sample_seconds':unpacked_sample,'packed_sample_seconds':packed_sample,
  'normal_decode_seconds':normal_decode,'packed_decode_seconds':packed_decode,
  'decoder_speedup':normal_decode/packed_decode if packed_decode else None,
  'packed_end_to_end_seconds':packed_sample+packed_decode,
  'prediction_mismatches':0,'sampler_mismatches':0,'scalar_batch_checks':min(100,shots),
  'resources':full_resources(c),'max_rss_kib':int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)}

def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');args=ap.parse_args()
 shots=PREFLIGHT_SHOTS if args.preflight else MAIN_SHOTS;seeds=PREFLIGHT_SEEDS if args.preflight else MAIN_SEEDS
 circuits=[make_circuit(c,b,13,25) for c,b in CONDITIONS];resources_list=[full_resources(c) for c in circuits]
 if any(any(resources_list[0][k]!=r[k] for k in KEYS) for r in resources_list[1:]):raise RuntimeError(f'resource mismatch: {resources_list}')
 if any(r['pauli_channel_2_probability_vectors']!=resources_list[0]['pauli_channel_2_probability_vectors'] for r in resources_list[1:]):raise RuntimeError('two-qubit channel vector mismatch')
 begin=time.perf_counter();rows=[one(c,b,s,shots) for (c,b),s in zip(CONDITIONS,seeds,strict=True)];elapsed=time.perf_counter()-begin
 projection=sum(r['packed_end_to_end_seconds']*MAIN_SHOTS/shots for r in rows) if args.preflight else None
 passed=all(r['prediction_mismatches']==r['sampler_mismatches']==0 for r in rows) and (projection is None or projection<=MAX_SECONDS)
 comparisons={}
 if not args.preflight:
  sub={(r['code'],r['basis']):r for r in rows};n=shots
  css=sub[('css','x')]['failures']+sub[('css','z')]['failures'];xz=sub[('xzzx','x')]['failures']+sub[('xzzx','z')]['failures']
  comparisons={'equal_weight_separate_basis_mix_xzzx_over_css':rr(xz,2*n,css,2*n),
   'xzzx_x_over_css_x':rr(sub[('xzzx','x')]['failures'],n,sub[('css','x')]['failures'],n),
   'xzzx_z_over_css_z':rr(sub[('xzzx','z')]['failures'],n,sub[('css','z')]['failures'],n)}
 out={'status':('xzzx_d13_bitpacked_preflight_passed' if passed else 'xzzx_d13_bitpacked_preflight_stopped') if args.preflight else 'development_xzzx_d13_bitpacked',
  'distance':13,'rounds':25,'conditions':rows,'resources_equal':True,'equal_resource_fields':list(KEYS),
  'shots_per_condition':shots,'projected_main_seconds':projection,'max_main_seconds':MAX_SECONDS,
  'elapsed_seconds':elapsed,'new_source_equivalent_samples':shots*len(rows),'comparisons':comparisons,
  'scope':'exact-equivalence and throughput ablation; same PyMatching algorithm and noise model',
  'hardware_assumption':'native CX/XCX/CZ duration and noise equality remains unverified'}
 target=HERE/('xzzx_d13_bitpacked_preflight.json' if args.preflight else 'xzzx_d13_bitpacked_results.json')
 target.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'status':out['status'],'projected_main_seconds':projection,'elapsed_seconds':elapsed,'decoder_speedups':[x['decoder_speedup'] for x in rows],'output':str(target)},indent=2))
 return int(args.preflight and not passed)
if __name__=='__main__':raise SystemExit(main())
