"""Test a single detector-only pattern decoder trained across all noise regimes."""
import json
import argparse
from pathlib import Path
import numpy as np
import pymatching
import stim

LEVELS = (0.001, 0.003, 0.006)
SEED = 20261107
TRAIN_EACH = 2_000_000
VALIDATION_EACH = 300_000
TEST_EACH = 2_000_000
OUT = Path(__file__).with_name("qshift_mixed_regime_results.json")


def take(c, n, seed):
    d, o = c.compile_detector_sampler(seed=seed).sample(shots=n, separate_observables=True)
    x = np.packbits(d.astype(np.uint8), axis=1, bitorder="little")[:, 0].astype(np.uint8)
    return x, d.astype(np.uint8), o[:, 0].astype(np.uint8)


def ci(k, n):
    z = 1.959963984540054
    p = k/n; den = 1+z*z/n
    m = (p+z*z/(2*n))/den
    h = z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [float(m-h),float(m+h)]


def main():
    global SEED, TRAIN_EACH, VALIDATION_EACH, TEST_EACH
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed",type=int,default=SEED)
    parser.add_argument("--train-each",type=int,default=TRAIN_EACH)
    parser.add_argument("--validation-each",type=int,default=VALIDATION_EACH)
    parser.add_argument("--test-each",type=int,default=TEST_EACH)
    parser.add_argument("--output",type=Path,default=OUT)
    args=parser.parse_args()
    if min(args.train_each,args.validation_each,args.test_each)<=0:
        parser.error("shot counts must be positive")
    SEED=args.seed
    TRAIN_EACH=args.train_each; VALIDATION_EACH=args.validation_each; TEST_EACH=args.test_each
    trains=[]; train_y=[]; vals=[]; val_y=[]; tests={}
    circuits={}
    for i, noise in enumerate(LEVELS):
        c=stim.Circuit.generated("repetition_code:memory",distance=3,rounds=3,after_clifford_depolarization=noise)
        circuits[noise]=c
        x,_,y=take(c,TRAIN_EACH,SEED+100*i); trains.append(x); train_y.append(y)
        x,_,y=take(c,VALIDATION_EACH,SEED+100*i+1); vals.append(x); val_y.append(y)
        tests[noise]=take(c,TEST_EACH,SEED+100*i+2)
    x=np.concatenate(trains); y=np.concatenate(train_y)
    vx=np.concatenate(vals); vy=np.concatenate(val_y)
    counts=np.bincount(x,minlength=256).astype(float)
    errors=np.bincount(x,weights=y,minlength=256)
    probability=(errors+1)/(counts+2)
    score=probability[vx]
    candidates=np.r_[-np.inf,np.unique(score),np.inf]
    val_rate,threshold=min(((float(np.mean(vy^(score>=t))),float(t)) for t in candidates),key=lambda t:(t[0],t[1]))
    result={"protocol":"one pattern table and one validation-selected threshold trained on all 3 regimes; detector bits only; per-regime independent tests with same samples as matched PyMatching","seed":SEED,"shots":{"training_total":len(y),"validation_total":len(vy),"test_per_regime":TEST_EACH},"threshold":threshold,"validation_residual_rate":val_rate,"levels":{}}
    for noise,(keys,d,actual) in tests.items():
        pred=(probability[keys]>=threshold).astype(np.uint8)
        rml=actual^pred
        match=pymatching.Matching.from_detector_error_model(circuits[noise].detector_error_model(decompose_errors=True))
        rmatch=actual^np.asarray(match.decode_batch(d),dtype=np.uint8).reshape(-1)
        a=int(rml.sum()); b=int(rmatch.sum())
        only_a=int(np.sum((rml!=0)&(rmatch==0))); only_b=int(np.sum((rml==0)&(rmatch!=0)))
        result["levels"][str(noise)]={"pattern_errors":a,"pattern_rate":float(rml.mean()),"pattern_wilson_95":ci(a,TEST_EACH),"matching_errors":b,"matching_rate":float(rmatch.mean()),"matching_wilson_95":ci(b,TEST_EACH),"paired_pattern_minus_matching":{"pattern_only_wrong":only_a,"matching_only_wrong":only_b,"net_error_difference":a-b,"discordant_counts":only_a+only_b}}
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    print(f"Saved {args.output}")

if __name__=="__main__": main()
