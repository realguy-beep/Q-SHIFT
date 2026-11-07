"""Stationary-window change experiment for detector-only regime adaptation."""
import json,time
from pathlib import Path
import numpy as np
import pymatching
import qshift_research as qr

SEED=20261222
REGIMES=(0.001,0.003,0.006)
STREAM=(0.001,0.006,0.003,0.008,0.0045,0.002)
TRAIN=200_000
VALIDATION=50_000
SEGMENT=100_000
WINDOW=1000


def main():
    tables={}; thresholds={}; validation_policy={}; count_tables={}; circuits={}
    for i,p in enumerate(REGIMES):
        c=qr.circuit(p);circuits[p]=c
        x,_,y=qr.sample(c,TRAIN,SEED+i*10)
        vx,vd,vy=qr.sample(c,VALIDATION,SEED+i*10+1)
        table=qr.fit_lookup(x,y,1.0); vr,t=qr.threshold_on_validation(table,vx,vy)
        tables[p]=table;thresholds[p]=t
        fixed=pymatching.Matching.from_detector_error_model(qr.circuit(.003).detector_error_model(decompose_errors=True))
        fixed_pred=np.asarray(fixed.decode_batch(vd),dtype=np.uint8).reshape(-1)
        lookup_pred=(qr.scores(table,vx)>=t).astype(np.uint8)
        validation_policy[p]="lookup" if np.mean(vy^lookup_pred)<=np.mean(vy^fixed_pred) else "matching"
    stream_rows=[];lookup_errors=match_errors=adaptive_errors=raw_errors=regime_correct=0;total=0
    for si,p in enumerate(STREAM):
        c=qr.circuit(p);keys,d,y=qr.sample(c,SEGMENT,SEED+1000+si)
        fixed=pymatching.Matching.from_detector_error_model(qr.circuit(.003).detector_error_model(decompose_errors=True))
        t0=time.perf_counter(); fixed_pred=np.asarray(fixed.decode_batch(d),dtype=np.uint8).reshape(-1);fixed_seconds=time.perf_counter()-t0
        t0=time.perf_counter(); selected,regcounts=qr.estimate_regime_windows(keys,tables,WINDOW);estimate_seconds=time.perf_counter()-t0
        pred=np.empty(len(y),dtype=np.uint8)
        for start in range(0,len(y),WINDOW):
            q=selected[start];stop=min(len(y),start+WINDOW)
            if validation_policy[q]=="matching":pred[start:stop]=fixed_pred[start:stop]
            else:pred[start:stop]=(qr.scores(tables[q],keys[start:stop])>=thresholds[q]).astype(np.uint8)
        r= y^pred; rm=y^fixed_pred
        lk=(qr.scores(tables[min(REGIMES,key=lambda q:abs(q-p))],keys)>=thresholds[min(REGIMES,key=lambda q:abs(q-p))]).astype(np.uint8)
        lookup_errors+=int((y^lk).sum());match_errors+=int(rm.sum());adaptive_errors+=int(r.sum());raw_errors+=int(y.sum());total+=len(y)
        expected=min(REGIMES,key=lambda q:abs(q-p)); regime_correct+=sum(n for q,n in regcounts.items() if q==expected)
        stream_rows.append({"noise_segment":p,"adaptive_errors":int(r.sum()),"fixed_errors":int(rm.sum()),"estimated_regimes":{str(q):n for q,n in regcounts.items()},"true_nearest_training_regime":expected,"fixed_runtime_seconds":fixed_seconds,"regime_estimation_seconds":estimate_seconds})
    result={"protocol":"six stationary segments; adaptive regime inferred from unsupervised detector-pattern frequency windows; thresholds/policies selected on separate validation; no true noise passed to adaptive decoder","seed":SEED,"shots_per_regime_train":TRAIN,"shots_per_regime_validation":VALIDATION,"shots_per_stream_segment":SEGMENT,"window_shots":WINDOW,"validation_policy":{str(k):v for k,v in validation_policy.items()},"summary":{"raw_errors":raw_errors,"fixed_pymatching_errors":match_errors,"adaptive_errors":adaptive_errors,"nearest_oracle_lookup_errors":lookup_errors,"regime_estimation_accuracy_vs_nearest_training_regime":regime_correct/total,"total_test_shots":total},"segments":stream_rows}
    out=Path(__file__).with_name("qshift_time_varying_results.json");out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8");print(json.dumps(result,indent=2));print(f"Saved {out}")

if __name__=="__main__":main()
