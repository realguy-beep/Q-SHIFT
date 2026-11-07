"""Q-SHIFT research harness: repeated paired tests, generalization, and adaptation.

No simulator metadata enters the mixed detector-only decoder. Python integers
encode arbitrary-width detector strings without dropping high bits. Exact lookup
tables are sparse dictionaries keyed only by observed patterns.
"""
from __future__ import annotations
import argparse, json, math, platform, time, sys
from pathlib import Path
import numpy as np
import stim, pymatching

TRAIN_LEVELS = (0.001, 0.003, 0.006)
DEFAULT_TEST_LEVELS = (0.001, 0.002, 0.003, 0.0045, 0.006, 0.008)


def detector_keys(detectors):
    """Arbitrary detector width to Python-int keys, preserving every bit."""
    d = np.asarray(detectors, dtype=np.uint8)
    packed=np.packbits(d,axis=1,bitorder="little")
    return [int.from_bytes(row.tobytes(),byteorder="little",signed=False) for row in packed]


def sample(circuit, shots, seed):
    d,o=circuit.compile_detector_sampler(seed=seed).sample(shots=shots,separate_observables=True)
    return detector_keys(d),d.astype(np.uint8),o[:,0].astype(np.uint8)


def wilson(k,n):
    z=1.959963984540054; p=k/n; den=1+z*z/n
    c=(p+z*z/(2*n))/den; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [c-h,c+h]


def paired_ci(a,b,n):
    # Paired score difference; CI based on discordant Bernoulli pairs.
    d=(a-b)/n
    se=math.sqrt(max(0,a+b-(a-b)**2/n))/n
    return [d-1.96*se,d+1.96*se]


def exact_mcnemar(a,b):
    """Two-sided exact binomial test on discordant paired outcomes."""
    n=a+b
    if n==0: return 1.0
    k=min(a,b)
    tail=sum(math.comb(n,j) for j in range(k+1))/(2**n)
    return min(1.0,2*tail)


def fit_lookup(keys, labels, alpha=1.0):
    counts={}; errs={}; pattern_counts={}
    for key,y in zip(keys,labels):
        counts[key]=counts.get(key,0)+1
        errs[key]=errs.get(key,0)+int(y)
        pattern_counts[key]=pattern_counts.get(key,0)+1
    return {"p_error":{k:(errs[k]+alpha)/(counts[k]+2*alpha) for k in counts},
            "counts":pattern_counts,"total":len(keys)}


def scores(table, keys, default=0.5):
    return np.fromiter((table["p_error"].get(k,default) for k in keys),dtype=float,count=len(keys))


def estimate_regime_windows(keys, tables, window):
    """Infer regime from detector-pattern frequencies over a stationary window."""
    selected=[]; counts={}
    for start in range(0,len(keys),window):
        chunk=keys[start:start+window]
        loglikes=[]
        for regime,table in tables.items():
            loglikes.append(sum(math.log((table["counts"].get(k,0)+1)/(table["total"]+256)) for k in chunk))
        regime=list(tables)[int(np.argmax(loglikes))]
        selected.extend([regime]*len(chunk)); counts[regime]=counts.get(regime,0)+len(chunk)
    return selected,counts


def threshold_on_validation(table,vkeys,vy):
    s=scores(table,vkeys)
    candidates=np.r_[-np.inf,np.unique(s),np.inf]
    return min(((float(np.mean(vy^(s>=t))),float(t)) for t in candidates),key=lambda z:(z[0],z[1]))


def circuit(noise,distance=3,rounds=3,noise_kind="depolarizing"):
    kwargs={"distance":distance,"rounds":rounds}
    if noise_kind=="depolarizing": kwargs["after_clifford_depolarization"]=noise
    elif noise_kind=="measurement": kwargs["before_measure_flip_probability"]=noise
    elif noise_kind in ("bit_flip","phase_flip"):
        # Independent Pauli faults after each two-qubit Clifford; keeps the
        # circuit's detector/observable annotations while changing channel.
        noisy=stim.Circuit.generated("repetition_code:memory",**kwargs,after_clifford_depolarization=noise)
        c=stim.Circuit()
        pauli="X_ERROR" if noise_kind=="bit_flip" else "Z_ERROR"
        for instruction in noisy:
            if isinstance(instruction,stim.CircuitRepeatBlock):
                body=stim.Circuit()
                for inner in instruction.body_copy():
                    if inner.name=="DEPOLARIZE2":
                        body.append(pauli,[t.value for t in inner.targets_copy()],[noise])
                    else: body.append(inner)
                c.append(stim.CircuitRepeatBlock(instruction.repeat_count,body))
            elif instruction.name=="DEPOLARIZE2":
                c.append(pauli,[t.value for t in instruction.targets_copy()],[noise])
            else: c.append(instruction)
        return c
    else: raise ValueError(noise_kind)
    return stim.Circuit.generated("repetition_code:memory",**kwargs)


def matching_decoder(c):
    return pymatching.Matching.from_detector_error_model(c.detector_error_model(decompose_errors=True))


def run(args):
    rng_seed=args.seed
    result={"title":"Q-SHIFT paired research benchmark","seed":rng_seed,
      "environment":{"python":platform.python_version(),"stim":stim.__version__,"pymatching":pymatching.__version__,"numpy":np.__version__},
      "protocol":"independent train/validation/test simulation batches; paired held-out shots across decoders; no threshold or policy selection on test data",
      "training_noise_levels":list(TRAIN_LEVELS),"shot_counts":{"train_per_regime":args.train,"validation_per_regime":args.validation,"test_per_condition_per_seed":args.test},"runs":[]}
    # Keep independent seed runs; test comparisons are paired within each run.
    for rep in range(args.repeats):
      base=rng_seed+rep*1_000_000
      train_k=[];train_y=[];val_k=[];val_y=[]
      for j,p in enumerate(TRAIN_LEVELS):
        c=circuit(p,args.distance,args.rounds,args.noise_kind)
        x,_,y=sample(c,args.train,base+10*j);train_k.extend(x);train_y.extend(y)
        x,_,y=sample(c,args.validation,base+10*j+1);val_k.extend(x);val_y.extend(y)
      mixed=fit_lookup(train_k,train_y,args.alpha)
      val_rate,mixed_t=threshold_on_validation(mixed,val_k,np.asarray(val_y,dtype=np.uint8))
      per_regime={}; validation_policy={}
      for j,p in enumerate(TRAIN_LEVELS):
        # Regime-specific table and threshold trained/tuned only on that regime's batches.
        c=circuit(p,args.distance,args.rounds,args.noise_kind)
        x,_,y=sample(c,args.train,base+100+10*j); v,vd,vy=sample(c,args.validation,base+100+10*j+1)
        tab=fit_lookup(x,y,args.alpha); vr,t=threshold_on_validation(tab,v,vy)
        per_regime[p]=(tab,t)
        # Choose lookup or nominal matching from independent validation shots.
        fixed_val=matching_decoder(circuit(0.003,args.distance,args.rounds,args.noise_kind))
        fixed_prediction=np.asarray(fixed_val.decode_batch(vd),dtype=np.uint8).reshape(-1)
        lookup_prediction=(scores(tab,v)>=t).astype(np.uint8)
        validation_policy[p]="lookup" if np.mean(vy^lookup_prediction)<=np.mean(vy^fixed_prediction) else "matching"
      runrow={"replicate":rep,"seed":base,"mixed_validation_rate":val_rate,"mixed_threshold":mixed_t,"conditions":{}}
      for ci,p in enumerate(args.test_levels):
        c=circuit(p,args.distance,args.rounds,args.noise_kind)
        keys,d,y=sample(c,args.test,base+500+ci)
        dem_true=matching_decoder(c)
        dem_fixed=matching_decoder(circuit(0.003,args.distance,args.rounds,args.noise_kind))
        t0=time.perf_counter(); pred_fixed=np.asarray(dem_fixed.decode_batch(d),dtype=np.uint8).reshape(-1); fixed_sec=time.perf_counter()-t0
        t0=time.perf_counter(); pred_true=np.asarray(dem_true.decode_batch(d),dtype=np.uint8).reshape(-1); true_sec=time.perf_counter()-t0
        t0=time.perf_counter(); pred_mixed=(scores(mixed,keys)>=mixed_t).astype(np.uint8); mixed_sec=time.perf_counter()-t0
        # Adaptive policy: infer the regime over windows, then use a validation-selected decoder.
        t0=time.perf_counter(); selected_regimes,regime_counts=estimate_regime_windows(keys,{q:per_regime[q][0] for q in TRAIN_LEVELS},args.window)
        pred_adaptive=np.empty(len(y),dtype=np.uint8)
        for start in range(0,len(y),args.window):
          stop=min(len(y),start+args.window); q=selected_regimes[start]
          if validation_policy[q]=="matching": pred_adaptive[start:stop]=pred_fixed[start:stop]
          else:
            tab,t=per_regime[q]
            pred_adaptive[start:stop]=(scores(tab,keys[start:stop])>=t).astype(np.uint8)
        adaptive_choice="windowed detector-frequency estimate + validation-selected lookup/matching"
        # Per-regime decoder with true regime is explicitly oracle/informed reference.
        nearest=min(TRAIN_LEVELS,key=lambda q:abs(q-p))
        tab,t=per_regime[nearest]
        pred_special=(scores(tab,keys)>=t).astype(np.uint8)
        adaptive_sec=time.perf_counter()-t0
        dec={"fixed_pymatching_0.003":pred_fixed,"noise_specific_pymatching_oracle":pred_true,
             "mixed_lookup":pred_mixed,"nearest_regime_lookup_oracle":pred_special,"adaptive_validation_choice":pred_adaptive}
        table_bytes=sum(sys.getsizeof(k)+sys.getsizeof(v) for tab,_ in per_regime.values() for k,v in tab["p_error"].items())+sum(sys.getsizeof(k)+sys.getsizeof(v) for k,v in mixed["p_error"].items())
        cond={"raw_errors":int(y.sum()),"raw_rate":float(y.mean()),"detector_count":int(d.shape[1]),"unseen_from_training":p not in TRAIN_LEVELS,"adaptive_policy":adaptive_choice,"estimated_regime_shot_counts":{str(k):v for k,v in regime_counts.items()},"validation_decoder_choice_by_regime":{str(k):v for k,v in validation_policy.items()},"runtime_seconds_per_test_shot":{"fixed_pymatching":fixed_sec/args.test,"noise_specific_pymatching":true_sec/args.test,"mixed_lookup":mixed_sec/args.test,"adaptive_regime_estimation_overhead":adaptive_sec/args.test},"lookup_table_python_object_bytes_approx":table_bytes,"decoders":{}}
        residuals={}
        for name,pred in dec.items():
          r=y^pred;residuals[name]=r;k=int(r.sum())
          cond["decoders"][name]={"errors":k,"rate":float(r.mean()),"wilson_95":wilson(k,args.test)}
        cond["paired_vs_fixed"]={}
        for name,r in residuals.items():
          if name=="fixed_pymatching_0.003":continue
          a=int(np.sum((r!=0)&(residuals["fixed_pymatching_0.003"]==0)))
          b=int(np.sum((r==0)&(residuals["fixed_pymatching_0.003"]!=0)))
          cond["paired_vs_fixed"][name]={"decoder_only_wrong":a,"fixed_only_wrong":b,"error_difference":int(r.sum())-int(residuals["fixed_pymatching_0.003"].sum()),"risk_difference_ci_95_approx":paired_ci(a,b,args.test),"exact_mcnemar_two_sided_p":exact_mcnemar(a,b)}
        runrow["conditions"][str(p)]=cond
      result["runs"].append(runrow)
      print(f"completed replicate {rep+1}/{args.repeats}",flush=True)
    # Aggregate per condition/decoder across independent replicates (shot-weighted pooled errors).
    aggregate={}
    for p in args.test_levels:
      aggregate[str(p)]={}
      names=result["runs"][0]["conditions"][str(p)]["decoders"].keys()
      for name in names:
        ks=[r["conditions"][str(p)]["decoders"][name]["errors"] for r in result["runs"]]
        n=args.test*args.repeats;k=sum(ks)
        aggregate[str(p)][name]={"errors":k,"shots":n,"rate":k/n,"wilson_95":wilson(k,n),"per_seed_errors":ks}
      for name in result["runs"][0]["conditions"][str(p)]["paired_vs_fixed"]:
        a=sum(r["conditions"][str(p)]["paired_vs_fixed"][name]["decoder_only_wrong"] for r in result["runs"])
        b=sum(r["conditions"][str(p)]["paired_vs_fixed"][name]["fixed_only_wrong"] for r in result["runs"])
        aggregate[str(p)].setdefault("paired_vs_fixed",{})[name]={"decoder_only_wrong":a,"fixed_only_wrong":b,"error_difference":a-b,"risk_difference_ci_95_approx":paired_ci(a,b,args.test*args.repeats),"exact_mcnemar_two_sided_p":exact_mcnemar(a,b)}
    result["aggregate"]=aggregate
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(f"Saved {args.output}")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repeats",type=int,default=10);p.add_argument("--seed",type=int,default=20261201)
    p.add_argument("--train",type=int,default=100_000);p.add_argument("--validation",type=int,default=30_000);p.add_argument("--test",type=int,default=100_000)
    p.add_argument("--alpha",type=float,default=1.0);p.add_argument("--distance",type=int,default=3);p.add_argument("--rounds",type=int,default=3)
    p.add_argument("--noise-kind",choices=["depolarizing","bit_flip","phase_flip","measurement"],default="depolarizing")
    p.add_argument("--window",type=int,default=1000)
    p.add_argument("--test-levels",type=float,nargs="+",default=list(DEFAULT_TEST_LEVELS));p.add_argument("--output",type=Path,default=Path(__file__).with_name("qshift_research_results.json"))
    a=p.parse_args()
    if min(a.repeats,a.train,a.validation,a.test,a.distance,a.rounds,a.window)<=0 or a.alpha<=0:p.error("all counts and alpha must be positive")
    a.test_levels=tuple(a.test_levels)
    run(a)

if __name__=="__main__":main()
