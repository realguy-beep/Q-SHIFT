"""Check for period-2 message oscillation under the frozen V2 schedule."""
import json, math, pathlib, sys
import numpy as np
import stim
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(HERE))
from factor_bp_v2 import FactorBPV2
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as model
OUT=HERE/'PERIOD2_DIAGNOSTICS.json'

def trace(decoder, syndrome):
    x=np.asarray(syndrome); mask=sum(int(b)<<i for i,b in enumerate(x))^decoder.fixed_detector_mask
    vc=np.asarray([decoder.prior[v] for v,_ in decoder.edges],dtype=float)
    cv=np.zeros(len(decoder.edges),dtype=float); states=[]; residuals=[]
    for _ in range(decoder.iterations):
        updated=np.zeros_like(cv)
        for c,es in enumerate(decoder.by_c):
            if not es: continue
            vals=[math.tanh(vc[e]/2) for e in es]; pre=[1.0]
            for a in vals: pre.append(pre[-1]*a)
            suf=[1.0]*(len(es)+1)
            for i in range(len(es)-1,-1,-1): suf[i]=vals[i]*suf[i+1]
            sign=-1.0 if ((mask>>c)&1) else 1.0
            for i,e in enumerate(es):
                v=sign*pre[i]*suf[i+1]
                raw=2*math.atanh(max(-1+decoder.clip,min(1-decoder.clip,v)))
                updated[e]=decoder.damping*cv[e]+(1-decoder.damping)*raw
        nxt=np.empty_like(vc)
        for v,es in enumerate(decoder.by_v):
            for e in es: nxt[e]=decoder.prior[v]+math.fsum(updated[o] for o in es if o!=e)
        residuals.append(float(np.max(np.abs(updated-cv))) if len(cv) else 0.0)
        states.append(updated.copy()); cv,vc=updated,nxt
        if residuals[-1]<decoder.tolerance: break
    reference=decoder.decode_one(syndrome)
    if len(residuals)!=reference['iterations'] or abs(residuals[-1]-reference['message_residual'])>1e-12:
        raise AssertionError('trace diverges from the frozen V2 update')
    p2=(float(np.max(np.abs(states[-1]-states[-3]))) if len(states)>=3 and len(states[-1]) else None)
    return {'converged':reference['converged'],'iterations':len(residuals),
            'final_consecutive_residual':residuals[-1],
            'last_period2_difference':p2,
            'last_10_consecutive_residuals':residuals[-10:],
            'residual_increases':sum(b>a for a,b in zip(residuals,residuals[1:]))}

def main():
    if OUT.exists(): raise FileExistsError(f'refusing to overwrite {OUT}')
    records=[]
    for q in (0.0,0.01):
        spec=model.CodeSpec(distance=3,rounds=5); support=model.burst_qubits(spec,'scaled_v1')
        circuit=model.build_candidate_circuit(spec,q,support)
        dem=circuit.detector_error_model(decompose_errors=False,approximate_disjoint_errors=True)
        bp=FactorBPV2(dem); syndromes=[np.zeros(spec.detectors,dtype=np.uint8)]
        for event in model.extract_burst_events(spec,support)[:5]:
            s=np.zeros(spec.detectors,dtype=np.uint8);s[list(event.detector_ids)]=1;syndromes.append(s)
        records.append({'case':'d3','q':q,'fixtures':[trace(bp,s) for s in syndromes]})
    dem=stim.DetectorErrorModel('error(0.1) D0 D1\nerror(0.2) D1 D2\nerror(0.3) D0 D2\ndetector D0\ndetector D1\ndetector D2\nlogical_observable L0')
    records.append({'case':'toy-three-check-cycle','q':None,'fixtures':[trace(FactorBPV2(dem),[1,1,0])]})
    OUT.write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{'case':r['case'],'q':r['q'],'fixtures':[
        {k:f[k] for k in ('converged','iterations','final_consecutive_residual','last_period2_difference','residual_increases')}
        for f in r['fixtures']]} for r in records],indent=2))
if __name__=='__main__': main()
