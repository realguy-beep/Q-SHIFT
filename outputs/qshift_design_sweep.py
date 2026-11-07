"""Small interpretable circuit/noise-family sweep; exploratory, single-seed."""
import json, time
from pathlib import Path
import numpy as np
import pymatching
import qshift_research as qr

SEED=20261230
CASES=[(3,3,"depolarizing"),(5,5,"depolarizing"),(3,5,"depolarizing"),
       (3,3,"bit_flip"),(3,3,"phase_flip"),(3,3,"measurement")]
TRAIN=100_000; VALIDATION=30_000; TEST=100_000; NOISE=.003

def main():
    rows=[]
    for i,(distance,rounds,kind) in enumerate(CASES):
        c=qr.circuit(NOISE,distance,rounds,kind)
        tx,_,ty=qr.sample(c,TRAIN,SEED+10*i)
        vx,vd,vy=qr.sample(c,VALIDATION,SEED+10*i+1)
        qx,qd,qy=qr.sample(c,TEST,SEED+10*i+2)
        table=qr.fit_lookup(tx,ty,1.0); val_rate,threshold=qr.threshold_on_validation(table,vx,vy)
        t=time.perf_counter(); lookup=(qr.scores(table,qx)>=threshold).astype(np.uint8); lookup_seconds=time.perf_counter()-t
        decoder=pymatching.Matching.from_detector_error_model(c.detector_error_model(decompose_errors=True))
        t=time.perf_counter(); matched=np.asarray(decoder.decode_batch(qd),dtype=np.uint8).reshape(-1); match_seconds=time.perf_counter()-t
        rl=qy^lookup; rm=qy^matched
        rows.append({"distance":distance,"rounds":rounds,"noise_family":kind,"noise_parameter":NOISE,"detectors":c.num_detectors,"training_patterns_seen":len(table["p_error"]),"raw_errors":int(qy.sum()),"lookup_errors":int(rl.sum()),"matching_errors":int(rm.sum()),"validation_lookup_rate":val_rate,"lookup_runtime_seconds_per_shot":lookup_seconds/TEST,"matching_runtime_seconds_per_shot":match_seconds/TEST,"lookup_memory_approx_bytes":sum(__import__('sys').getsizeof(k)+__import__('sys').getsizeof(v) for k,v in table['p_error'].items())})
        print(rows[-1],flush=True)
    out=Path(__file__).with_name("qshift_design_sweep_results.json")
    out.write_text(json.dumps({"protocol":"exploratory single seeded run; fresh train/validation/test; lookup threshold validation-selected; no superiority claims","seed":SEED,"shots":{"train":TRAIN,"validation":VALIDATION,"test":TEST},"cases":rows},indent=2)+"\n",encoding="utf-8")
    print(f"Saved {out}")

if __name__=="__main__":main()
