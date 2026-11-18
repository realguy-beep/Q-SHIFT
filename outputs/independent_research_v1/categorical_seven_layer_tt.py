"""Exact singular-spectrum audit of seven-layer syndrome P/Z arrays."""
from __future__ import annotations
import hashlib,json,sys,time
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from categorical_seven_layer_parity import kernels,propagate

def rank_for_error(singular_values,tolerance):
    energy=np.square(singular_values)
    total=float(energy.sum())
    tail=np.r_[np.cumsum(energy[::-1])[::-1],0.0]
    candidates=np.flatnonzero(np.sqrt(tail/total)<=tolerance)
    return int(candidates[0]) if len(candidates) else len(singular_values)

def inspect(values,detector_count,name):
    # Array index bit j corresponds to compact detector j; reverse C-order axes.
    tensor=values.reshape((2,)*detector_count).transpose(tuple(reversed(range(detector_count))))
    results=[]
    for cut in range(1,detector_count):
        matrix=np.ascontiguousarray(tensor.reshape(1<<cut,1<<(detector_count-cut)))
        s=np.linalg.svd(matrix,compute_uv=False)
        norm=float(np.linalg.norm(s))
        item={'cut_after_detector_bits':cut,'matrix_shape':list(matrix.shape),
              'machine_rank':int(np.count_nonzero(s>np.finfo(np.float64).eps*max(matrix.shape)*s[0])),
              'rank_rel_frob_1e-6':rank_for_error(s,1e-6),
              'rank_rel_frob_1e-10':rank_for_error(s,1e-10),
              'largest_singular_value':float(s[0]),'frobenius_norm':norm}
        results.append(item)
    return {'array':name,'cuts':results,
            'max_rank_1e-6':max(x['rank_rel_frob_1e-6'] for x in results),
            'max_rank_1e-10':max(x['rank_rel_frob_1e-10'] for x in results),
            'max_machine_rank':max(x['machine_rank'] for x in results)}

def main():
    started=time.perf_counter()
    pre=json.loads((HERE/'categorical_seven_layer_preflight.json').read_text())
    blob=json.dumps(pre['events'],sort_keys=True,separators=(',',':'))
    digest=hashlib.sha256(blob.encode()).hexdigest()
    if digest!=pre['compact_event_signatures_sha256']:
        raise RuntimeError('seven-layer signature map hash mismatch')
    m=int(pre['compact_detector_count']);states=1<<m
    if states>1_048_576:raise RuntimeError('state cap exceeded')
    p,z=propagate(kernels(pre['events'])[0],states)
    if abs(float(p.sum())-1)>1e-12 or np.max(np.abs(z)-p)>1e-12:
        raise RuntimeError('exact P/Z invariant failed')
    p_result=inspect(p,m,'P_syndrome_mass')
    z_result=inspect(z,m,'Z_signed_logical_mass')
    elapsed=time.perf_counter()-started
    output={'status':'exact_seven_layer_tt_rank_audit',
            'source':'same d3 five-round X-biased ratio10 42-location tail as exact parity analysis',
            'compact_detector_order':pre['touched_detector_ids'],'detector_count':m,
            'states':states,'signature_map_sha256':digest,
            'P':p_result,'Z':z_result,'elapsed_seconds':elapsed,
            'stochastic_samples_generated':0,
            'scope':'deterministic tensor-train compressibility diagnostic on an isolated exact posterior, not an MPS decoder result'}
    path=HERE/'categorical_seven_layer_tt_results.json'
    path.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'status':output['status'],'P_max_rank_1e-10':p_result['max_rank_1e-10'],
                      'Z_max_rank_1e-10':z_result['max_rank_1e-10'],
                      'P_max_rank_1e-6':p_result['max_rank_1e-6'],
                      'Z_max_rank_1e-6':z_result['max_rank_1e-6'],
                      'elapsed_seconds':elapsed,'output':str(path)},indent=2))

if __name__=='__main__':main()
