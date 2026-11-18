"""Fixed-chi=16 planar MPS vs MWPM under X-biased code-capacity noise."""
from __future__ import annotations

import argparse
import json
import resource
import time
from pathlib import Path

import numpy as np
import qecsim
import qecsim.paulitools as pt
from scipy.stats import binomtest, t
from qecsim.models.generic import BiasedDepolarizingErrorModel
from qecsim.models.planar import PlanarCode, PlanarMPSDecoder, PlanarMWPMDecoder

HERE=Path(__file__).resolve().parent
P=.05
BIAS=5.0
AXIS='X'
CHI=16
PREFLIGHT_SEEDS={3:2026113301,5:2026113302}
MAIN_SEEDS={3:2026113311,5:2026113312}


def wilson(k,n):
    z=1.959963984540054;p=k/n;d=1+z*z/n
    center=(p+z*z/(2*n))/d
    half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [float(center-half),float(center+half)]


def run_distance(distance,shots,seed):
    code=PlanarCode(distance,distance)
    noise=BiasedDepolarizingErrorModel(bias=BIAS,axis=AXIS)
    rng=np.random.default_rng(seed)
    decoders={'mwpm':PlanarMWPMDecoder(),
              'mps_chi16':PlanarMPSDecoder(chi=CHI,mode='c')}
    failures={name:0 for name in decoders}
    only={name:0 for name in decoders}
    seconds={name:0.0 for name in decoders}
    invalid={name:0 for name in decoders}
    for shot in range(shots):
        error=noise.generate(code,P,rng)
        syndrome=pt.bsp(error,code.stabilizers.T)
        decoded={}
        for name,decoder in decoders.items():
            start=time.perf_counter()
            recovery=decoder.decode(code,syndrome,error_model=noise,error_probability=P)
            seconds[name]+=time.perf_counter()-start
            recovered=np.bitwise_xor(error,recovery)
            if np.any(pt.bsp(recovered,code.stabilizers.T)):
                invalid[name]+=1
            decoded[name]=bool(np.any(pt.bsp(recovered,code.logicals.T)))
            failures[name]+=decoded[name]
        only['mwpm']+=int(decoded['mwpm'] and not decoded['mps_chi16'])
        only['mps_chi16']+=int(decoded['mps_chi16'] and not decoded['mwpm'])
    discord=only['mwpm']+only['mps_chi16']
    delta=(failures['mps_chi16']-failures['mwpm'])/shots
    variance=max(0.0,(discord-shots*delta*delta)/(shots-1)) if shots>1 else 0.0
    se=float(np.sqrt(variance/shots))
    critical=float(t.ppf(.975,shots-1)) if shots>1 else 0.0
    return {'distance':distance,'code_shape':code.n_k_d,
            'error_model':f'BiasedDepolarizingErrorModel(bias={BIAS}, axis={AXIS}); p={P}; X:Y:Z ratio 10:1:1',
            'shots':shots,'seed':seed,'mps_chi':CHI,'mps_mode':'c',
            'failures':failures,'ler':{k:failures[k]/shots for k in failures},
            'wilson_95':{k:wilson(failures[k],shots) for k in failures},
            'invalid_recoveries':invalid,'paired_mps_minus_mwpm_ler':delta,
            'paired_normal_95':[delta-critical*se,delta+critical*se],
            'mwpm_only_failures':only['mwpm'],'mps_only_failures':only['mps_chi16'],
            'discordant_shots':discord,
            'mcnemar_exact_two_sided':float(binomtest(only['mwpm'],discord,.5).pvalue) if discord else 1.0,
            'decode_seconds':seconds,'seconds_per_decode':{k:seconds[k]/shots for k in seconds},
            'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preflight',action='store_true')
    parser.add_argument('--shots',type=int,default=5000);args=parser.parse_args()
    if args.shots<=0:parser.error('--shots must be positive')
    pre=args.preflight;shots=100 if pre else args.shots
    seeds=PREFLIGHT_SEEDS if pre else MAIN_SEEDS
    start=time.perf_counter()
    rows=[run_distance(d,shots,seeds[d]) for d in (3,5)]
    elapsed=time.perf_counter()-start
    valid=all(not any(r['invalid_recoveries'].values()) for r in rows)
    passed=(valid and all(r['paired_normal_95'][1]<0 and
                          r['failures']['mps_chi16']<r['failures']['mwpm'] for r in rows))
    projected=elapsed*(args.shots/shots) if pre else None
    output={'status':'preflight' if pre else 'biased_code_capacity_mps_development',
            'qecsim_version':qecsim.__version__,'p':P,'bias':BIAS,'axis':AXIS,
            'axis_to_off_axis_probability_ratio':2*BIAS,'mps_chi':CHI,'mps_mode':'c',
            'shots_per_distance':shots,'distance_results':rows,'all_recoveries_valid':valid,
            'both_distance_advancement_gate_passed':passed,
            'elapsed_seconds':elapsed,'projected_main_seconds':projected,
            'stochastic_qshift_circuit_shots':0,
            'scope':'perfect-syndrome code-capacity study; no Q-SHIFT repeated-measurement circuit inference'}
    target=HERE/('tensor_mps_biased_preflight.json' if pre else 'tensor_mps_biased_results.json')
    target.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'status':output['status'],'elapsed_seconds':elapsed,
                      'projected_main_seconds':projected,'gate':passed,
                      'distances':[{'d':r['distance'],'mwpm':r['failures']['mwpm'],
                                    'mps':r['failures']['mps_chi16'],
                                    'paired_ci':r['paired_normal_95']} for r in rows]},indent=2))
    return int(pre and projected>300)


if __name__=='__main__':raise SystemExit(main())
