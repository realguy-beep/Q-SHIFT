"""Fixed-chi averaged row/column MPS mode ablation under X bias."""
from __future__ import annotations
import argparse,json,resource,time
from pathlib import Path
import numpy as np
import qecsim
import qecsim.paulitools as pt
from scipy.stats import binomtest,t
from qecsim.models.generic import BiasedDepolarizingErrorModel
from qecsim.models.planar import PlanarCode,PlanarMPSDecoder,PlanarMWPMDecoder

HERE=Path(__file__).resolve().parent
P=.05;BIAS=5.;CHI=16
PRE={3:2026113401,5:2026113402};MAIN={3:2026113411,5:2026113412}

def interval(delta,discord,shots):
    var=max(0.,(discord-shots*delta*delta)/(shots-1))
    se=(var/shots)**.5;critical=float(t.ppf(.975,shots-1))
    return [delta-critical*se,delta+critical*se]

def run(d,shots,seed):
    code=PlanarCode(d,d);noise=BiasedDepolarizingErrorModel(bias=BIAS,axis='X')
    decoders={'mwpm':PlanarMWPMDecoder(),
              'mps_c':PlanarMPSDecoder(chi=CHI,mode='c'),
              'mps_a':PlanarMPSDecoder(chi=CHI,mode='a')}
    rng=np.random.default_rng(seed);fails={k:0 for k in decoders};invalid={k:0 for k in decoders}
    only={pair:{'left':0,'right':0} for pair in (('mps_a','mps_c'),('mps_a','mwpm'),('mps_c','mwpm'))}
    seconds={k:0. for k in decoders}
    for shot in range(shots):
        error=noise.generate(code,P,rng);syndrome=pt.bsp(error,code.stabilizers.T);bad={}
        for name,decoder in decoders.items():
            start=time.perf_counter()
            recovery=decoder.decode(code,syndrome,error_model=noise,error_probability=P)
            seconds[name]+=time.perf_counter()-start
            recovered=np.bitwise_xor(error,recovery)
            if np.any(pt.bsp(recovered,code.stabilizers.T)):invalid[name]+=1
            bad[name]=bool(np.any(pt.bsp(recovered,code.logicals.T)))
            fails[name]+=bad[name]
        for left,right in only:
            only[(left,right)]['left']+=int(bad[left] and not bad[right])
            only[(left,right)]['right']+=int(bad[right] and not bad[left])
    comparisons={}
    for left,right in only:
        lo=only[(left,right)]['left'];ro=only[(left,right)]['right'];n=lo+ro
        delta=(fails[left]-fails[right])/shots
        comparisons[f'{left}_minus_{right}']={'paired_delta':delta,
            'paired_normal_95':interval(delta,n,shots),
            'left_only_failures':lo,'right_only_failures':ro,'discordant':n,
            'mcnemar_exact_two_sided':float(binomtest(lo,n,.5).pvalue) if n else 1.}
    return {'distance':d,'shots':shots,'seed':seed,'failures':fails,
            'ler':{k:v/shots for k,v in fails.items()},'invalid_recoveries':invalid,
            'comparisons':comparisons,'decode_seconds':seconds,
            'seconds_per_decode':{k:v/shots for k,v in seconds.items()},
            'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');a=ap.parse_args()
    n=100 if a.preflight else 5000;seeds=PRE if a.preflight else MAIN
    start=time.perf_counter();rows=[run(d,n,seeds[d]) for d in (3,5)];elapsed=time.perf_counter()-start
    valid=all(not any(r['invalid_recoveries'].values()) for r in rows)
    projected=elapsed*50 if a.preflight else None
    gate=valid and all(r['failures']['mps_a']<r['failures']['mps_c'] for r in rows)
    out={'status':'preflight' if a.preflight else 'biased_mps_averaged_mode_ablation',
         'qecsim_version':qecsim.__version__,'p':P,'bias':BIAS,'axis':'X',
         'chi':CHI,'modes':['c','a'],'shots_per_distance':n,'distance_results':rows,
         'all_recoveries_valid':valid,'mode_a_advancement_gate_passed':gate,
         'projected_main_seconds':projected,'elapsed_seconds':elapsed,
         'stochastic_qshift_circuit_shots':0,
         'scope':'perfect-syndrome code-capacity mode ablation; no repeated-measurement circuit claim'}
    path=HERE/('tensor_mps_biased_mode_preflight.json' if a.preflight else 'tensor_mps_biased_mode_results.json')
    path.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'status':out['status'],'elapsed':elapsed,'projection':projected,'gate':gate,
                      'distances':[{'d':r['distance'],'failures':r['failures'],
                                    'seconds':r['seconds_per_decode']} for r in rows]},indent=2))
    return int(a.preflight and (not valid or projected>300))
if __name__=='__main__':raise SystemExit(main())
