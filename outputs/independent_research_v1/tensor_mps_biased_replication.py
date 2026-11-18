"""Independent-seed replication of the biased code-capacity MPS screen."""
from __future__ import annotations
import argparse,json,resource,time
from pathlib import Path
import qecsim
from tensor_mps_biased import run_distance

HERE=Path(__file__).resolve().parent
PRE={3:2026113321,5:2026113322}
MAIN={3:2026113331,5:2026113332}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');a=ap.parse_args()
    shots=100 if a.preflight else 5000;seeds=PRE if a.preflight else MAIN
    start=time.perf_counter();rows=[run_distance(d,shots,seeds[d]) for d in (3,5)]
    elapsed=time.perf_counter()-start
    valid=all(not any(r['invalid_recoveries'].values()) for r in rows)
    projected=elapsed*50 if a.preflight else None
    output={'status':'preflight' if a.preflight else 'biased_mps_independent_development_replication',
            'qecsim_version':qecsim.__version__,'shots_per_distance':shots,
            'distance_results':rows,'all_recoveries_valid':valid,
            'projected_main_seconds':projected,'elapsed_seconds':elapsed,
            'stochastic_qshift_circuit_shots':0,
            'scope':'independent seed development replication; perfect-syndrome code-capacity only'}
    path=HERE/('tensor_mps_biased_replication_preflight.json' if a.preflight
               else 'tensor_mps_biased_replication_results.json')
    path.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'status':output['status'],'elapsed':elapsed,'projection':projected,
                      'valid':valid,'distances':[{'d':r['distance'],'mps':r['failures']['mps_chi16'],
                                                'mwpm':r['failures']['mwpm']} for r in rows]},indent=2))
    return int(a.preflight and (not valid or projected>300))

if __name__=='__main__':raise SystemExit(main())
