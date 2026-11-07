"""Controlled Stim noise-composition study with detector-only causal adaptation."""
from __future__ import annotations
import json, math, platform, sys, time
from pathlib import Path
import numpy as np
import stim, pymatching

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results"
RAW=ROOT/"raw"
OUT.mkdir(exist_ok=True); RAW.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT.parent))

DISTANCE=3; ROUNDS=3; P_DATA=.01; P_MEAS=.01
TRAINED=("x_dominant","z_dominant","depolarizing","measurement_only")
CONDITIONS=("x_dominant","z_dominant","depolarizing","measurement_only","mixed_xz_heldout","data_plus_measurement_heldout")
PAX={"x_dominant":(.8,.1,.1),"z_dominant":(.1,.1,.8),"depolarizing":(1/3,1/3,1/3),"mixed_xz_heldout":(.5,0,.5)}
SEED_BASE=20271215; N_SEEDS=10; N_TRAIN=30_000; N_VAL=10_000; N_TEST=20_000
WINDOW=500; CONFIRM=2; DWELL=2; POSTERIOR=.90; LOG_MARGIN=math.log(10)
SCHEDULE=("x_dominant","x_dominant","z_dominant","z_dominant","depolarizing","depolarizing","x_dominant","x_dominant","measurement_only","measurement_only","z_dominant","z_dominant")
STREAM_BLOCK=4_000


def make_circuit(condition:str)->stim.Circuit:
    """Same ideal code skeleton; only explicit local channels vary."""
    base=stim.Circuit.generated("repetition_code:memory",distance=DISTANCE,rounds=ROUNDS)
    if condition not in CONDITIONS: raise ValueError(condition)
    if condition=="measurement_only": pauli=(0.,0.,0.); pm=P_MEAS
    elif condition=="data_plus_measurement_heldout": pauli=tuple(P_DATA*x for x in PAX["depolarizing"]); pm=P_MEAS
    else: pauli=tuple(P_DATA*x for x in PAX[condition]); pm=0.
    out=stim.Circuit()
    for inst in base:
        if isinstance(inst,stim.CircuitRepeatBlock):
            body=inject_noise(inst.body_copy(),pauli,pm)
            out.append(stim.CircuitRepeatBlock(inst.repeat_count,body))
        else:
            append_noisy_instruction(out,inst,pauli,pm)
    return out


def append_noisy_instruction(out,inst,pauli,pm):
    if inst.name in ("M","MR") and pm:
        out.append("X_ERROR",[t.value for t in inst.targets_copy()],[pm])
    out.append(inst)
    if inst.name=="CX" and sum(pauli)>0:
        out.append("PAULI_CHANNEL_1",[t.value for t in inst.targets_copy()],list(pauli))


def inject_noise(body,pauli,pm):
    out=stim.Circuit()
    for inst in body:
        if isinstance(inst,stim.CircuitRepeatBlock):
            out.append(stim.CircuitRepeatBlock(inst.repeat_count,inject_noise(inst.body_copy(),pauli,pm)))
        else: append_noisy_instruction(out,inst,pauli,pm)
    return out


def sample(circuit,n,seed):
    d,o=circuit.compile_detector_sampler(seed=seed).sample(shots=n,separate_observables=True)
    keys=[int.from_bytes(row.tobytes(),"little") for row in np.packbits(d.astype(np.uint8),axis=1,bitorder="little")]
    return keys,d.astype(np.uint8),o[:,0].astype(np.uint8)


def fit_table(keys,y,alpha=1.):
    n={}; e={};
    for k,label in zip(keys,y): n[k]=n.get(k,0)+1; e[k]=e.get(k,0)+int(label)
    prior=(int(np.sum(y))+alpha)/(len(y)+2*alpha)
    return {"error":{k:(e[k]+alpha)/(n[k]+2*alpha) for k in n},"counts":n,"total":len(keys),"prior":prior}


def predict(table,keys,threshold): return np.fromiter((table["error"].get(k,table["prior"])>=threshold for k in keys),dtype=np.uint8,count=len(keys))


def tune_threshold(table,keys,y):
    s=np.fromiter((table["error"].get(k,table["prior"]) for k in keys),dtype=float,count=len(keys))
    thresholds=np.r_[-np.inf,np.unique(s),np.inf]
    return min(((float(np.mean(y^(s>=t))),float(t)) for t in thresholds),key=lambda x:(x[0],x[1]))


def likelihood_profiles(tables):
    return {name:{k:(n+1)/(table["total"]+256) for k,n in table["counts"].items()} for name,table in tables.items()}


def estimate_window(keys,profiles):
    # The profile entries are smoothed counts. Missing patterns share a common,
    # regime-specific small-probability fallback using its normalized total.
    # Recompute normalized maps explicitly for transparent posterior scoring.
    ll={}
    for name,profile in profiles.items():
        total=sum(profile.values())
        fallback=max(1e-15,(1-total)/(256-len(profile)) if len(profile)<256 else 1e-15)
        ll[name]=sum(math.log(profile.get(k,fallback)) for k in keys)
    names=list(ll); top=max(names,key=ll.get)
    mx=max(ll.values()); ex={name:math.exp(v-mx) for name,v in ll.items()}; z=sum(ex.values())
    posterior={name:v/z for name,v in ex.items()}
    return top,posterior,ll


def decide_switch(state, challenger, target, posterior, ll, pending, pending_n, dwell):
    """Two-window hysteresis and minimum dwell; inference receives no noise label."""
    if dwell<DWELL: return state,None,0,dwell+1,False
    others=[v for k,v in ll.items() if k!=challenger]
    confident=posterior[challenger]>=POSTERIOR and (not others or ll[challenger]-max(others)>=LOG_MARGIN)
    if not confident or target==state:
        return state,None,0,dwell+1,False
    if pending==target: pending_n+=1
    else: pending=target; pending_n=1
    if pending_n>=CONFIRM:
        return target,None,0,0,True
    return state,pending,pending_n,dwell+1,False


def wilson(k,n):
    z=1.959963984540054; p=k/n; den=1+z*z/n
    mid=(p+z*z/(2*n))/den; half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [mid-half,mid+half]


def paired_stats(candidate,fixed):
    a=int(np.sum((candidate!=0)&(fixed==0))); b=int(np.sum((candidate==0)&(fixed!=0))); n=len(fixed)
    return paired_from_counts(a,b,n)


def paired_from_counts(a,b,n):
    d=(a-b)/n; se=math.sqrt(max(0,a+b-(a-b)**2/n))/n
    disc=a+b; p=1. if not disc else min(1.,2*sum(math.comb(disc,j) for j in range(min(a,b)+1))/(2**disc))
    return {"candidate_only_wrong":a,"fixed_only_wrong":b,"difference_errors":a-b,
            "paired_rate_difference_ci95_approx":[d-1.96*se,d+1.96*se],"mcnemar_exact_two_sided_p":p}


def seed_bootstrap(values,seed=47,nboot=5000):
    a=np.asarray(values,dtype=float); rng=np.random.default_rng(seed)
    means=np.mean(a[rng.integers(0,len(a),size=(nboot,len(a)))],axis=1)
    return [float(np.quantile(means,.025)),float(np.quantile(means,.975))]


def main():
    global N_SEEDS,N_TRAIN,N_VAL,N_TEST
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds",type=int,default=N_SEEDS); ap.add_argument("--train",type=int,default=N_TRAIN)
    ap.add_argument("--validation",type=int,default=N_VAL); ap.add_argument("--test",type=int,default=N_TEST)
    ap.add_argument("--output",type=Path,default=OUT/"composition_results.json")
    a=ap.parse_args(); N_SEEDS=a.seeds;N_TRAIN=a.train;N_VAL=a.validation;N_TEST=a.test
    for x in (N_SEEDS,N_TRAIN,N_VAL,N_TEST):
        if x<1: ap.error("all counts must be positive")
    # Explicit circuit audit guard: all compositions must have identical detector schema.
    circuits={c:make_circuit(c) for c in CONDITIONS}
    schema={(c.num_detectors,c.num_observables,c.num_qubits) for c in circuits.values()}
    if schema!={(8,1,5)}: raise RuntimeError(f"unexpected detector/observable schema: {schema}")
    rows=[]; pooled_raw={name:[] for name in CONDITIONS}; stream_results=[]
    agg={name:{d:0 for d in ("fixed_matching","oracle_matching","pooled_lookup","adaptive_schedule","oracle_schedule","per_regime_lookup")} for name in CONDITIONS}
    agg_raw={name:0 for name in CONDITIONS}; agg_pair={name:[] for name in CONDITIONS}
    agg_discord={name:{dn:[0,0] for dn in ("oracle_matching","pooled_lookup","per_regime_lookup")} for name in CONDITIONS}
    class_conf={name:{r:0 for r in TRAINED} for name in CONDITIONS}
    runtime_rows=[]; memory_rows=[]
    fixed_dem=pymatching.Matching.from_detector_error_model(circuits["depolarizing"].detector_error_model(decompose_errors=True,approximate_disjoint_errors=True))
    fixed_model_bytes=sys.getsizeof(fixed_dem)
    oracle_models={name:pymatching.Matching.from_detector_error_model(c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=True)) for name,c in circuits.items()}
    for rep in range(N_SEEDS):
        seed=SEED_BASE+rep*100_000
        raw_payload={"meta_seed":np.asarray(seed)}
        train_tables={}; thresholds={}; val_select={}; train_keys_by={}; train_y_by={};
        val_records={}; val_evidence={}
        # Four permitted training regimes; distinct train and validation batches.
        for j,name in enumerate(TRAINED):
            x,d,y=sample(circuits[name],N_TRAIN,seed+j*10+1); train_keys_by[name]=x;train_y_by[name]=y
            vx,vd,vy=sample(circuits[name],N_VAL,seed+j*10+2); val_records[name]=(vx,vd,vy)
            train_tables[name]=fit_table(x,y)
            raw_payload[f"train_{name}_detectors"]=d;raw_payload[f"train_{name}_observable"]=y
            raw_payload[f"validation_{name}_detectors"]=vd;raw_payload[f"validation_{name}_observable"]=vy
        # Fixed pooled-noise lookup: equal shots per training composition; one validation-selected threshold.
        pooled_keys=sum((train_keys_by[n] for n in TRAINED),[])
        pooled_y=np.concatenate([train_y_by[n] for n in TRAINED])
        pooled_table=fit_table(pooled_keys,pooled_y)
        split_index=N_VAL//2
        vkeys=sum((val_records[n][0][:split_index] for n in TRAINED),[])
        vy=np.concatenate([val_records[n][2][:split_index] for n in TRAINED])
        pooled_val,pooled_threshold=tune_threshold(pooled_table,vkeys,vy)
        # Each regime table selects a strategy only using its own held-out validation shots.
        for name in TRAINED:
            vx,vd,vy_one=val_records[name]
            val_rate,t=tune_threshold(train_tables[name],vx[:split_index],vy_one[:split_index]); thresholds[name]=t
            policy_x=vx[split_index:]; policy_d=vd[split_index:]; policy_y=vy_one[split_index:]
            val_fixed=np.asarray(fixed_dem.decode_batch(policy_d),dtype=np.uint8).reshape(-1)
            val_lookup=predict(train_tables[name],policy_x,t)
            evidence=paired_stats(policy_y^val_lookup,policy_y^val_fixed)
            val_select[name]="lookup" if evidence["difference_errors"]<0 and evidence["mcnemar_exact_two_sided_p"]<.0125 else "fixed_matching"
            val_evidence[name]={"threshold_validation_shots":split_index,"policy_selection_shots":len(policy_y),"threshold_validation_residual_rate":val_rate,"paired_policy_evidence":evidence,"gate":"lookup only if lower residual count and exact McNemar p<0.0125; otherwise fixed matching","selected":val_select[name]}
        profiles=likelihood_profiles(train_tables)
        rep_row={"seed":seed,"static":{},"schedule":{}}
        perseed_test={}
        # Static held-out evaluation; condition names are not given to decoders.
        for ci,name in enumerate(CONDITIONS):
            pilot_keys,pilot_d,pilot_y=sample(circuits[name],WINDOW,seed+900+ci)
            pilot_regime,_,_=estimate_window(pilot_keys,profiles)
            raw_payload[f"pilot_{name}_detectors"]=pilot_d
            keys,d,y=sample(circuits[name],N_TEST,seed+1000+ci)
            raw_payload[f"test_{name}_detectors"]=d;raw_payload[f"test_{name}_observable"]=y
            raw_payload[f"test_{name}_condition"]=np.full(N_TEST,ci,dtype=np.uint8)
            start=time.perf_counter(); pred_fixed=np.asarray(fixed_dem.decode_batch(d),dtype=np.uint8).reshape(-1); rt_fixed=time.perf_counter()-start
            oracle_dem=oracle_models[name]
            start=time.perf_counter(); pred_oracle=np.asarray(oracle_dem.decode_batch(d),dtype=np.uint8).reshape(-1); rt_oracle=time.perf_counter()-start
            start=time.perf_counter(); pred_pool=predict(pooled_table,keys,pooled_threshold); rt_pool=time.perf_counter()-start
            # Static detector-only policy uses a separate preceding pilot window.
            top=pilot_regime
            for r in TRAINED: class_conf[name][r]+=int(top==r)
            # Informed per-regime comparator uses the held-out condition label only
            # for the trained regimes; held-out mixtures use the preceding detector pilot.
            reg_for_table=name if name in TRAINED else top
            start=time.perf_counter();pred_reg=predict(train_tables[reg_for_table],keys,thresholds[reg_for_table]);rt_reg=time.perf_counter()-start
            dec={"fixed_matching":pred_fixed,"oracle_matching":pred_oracle,"pooled_lookup":pred_pool,"per_regime_lookup":pred_reg}
            metrics={"raw_errors":int(y.sum()),"raw_rate":float(y.mean()),"preceding_detector_pilot_regime_estimate":top,"per_regime_lookup_selection":"oracle condition label" if name in TRAINED else "detector-only preceding pilot","decoders":{}}
            residuals={}
            for dn,pred in dec.items():
                residual=y^pred; residuals[dn]=residual; err=int(residual.sum())
                agg[name][dn]+=err
                metrics["decoders"][dn]={"errors":err,"rate":float(residual.mean()),"wilson95":wilson(err,N_TEST)}
            metrics["paired_vs_fixed"]={dn:paired_stats(residuals[dn],residuals["fixed_matching"]) for dn in dec if dn!="fixed_matching"}
            for dn in agg_discord[name]:
                agg_discord[name][dn][0]+=metrics["paired_vs_fixed"][dn]["candidate_only_wrong"]
                agg_discord[name][dn][1]+=metrics["paired_vs_fixed"][dn]["fixed_only_wrong"]
            metrics["runtime_seconds_per_shot"]={"fixed_matching":rt_fixed/N_TEST,"oracle_matching":rt_oracle/N_TEST,"pooled_lookup":rt_pool/N_TEST,"per_regime_lookup":rt_reg/N_TEST}
            metrics["memory_bytes_approx"]={"fixed_matching_python_wrapper":fixed_model_bytes,
                "pooled_lookup_python_objects":sum(sys.getsizeof(k)+sys.getsizeof(v) for k,v in pooled_table["error"].items()),
                "all_specialized_lookup_python_objects":sum(sys.getsizeof(k)+sys.getsizeof(v) for tab in train_tables.values() for k,v in tab["error"].items())}
            agg_raw[name]+=int(y.sum()); agg_pair[name].append(int(residuals["pooled_lookup"].sum())-int(residuals["fixed_matching"].sum()))
            metrics["validation_selected_strategy_by_regime"]=val_select
            metrics["validation_policy_evidence"]=val_evidence
            rep_row["static"][name]=metrics
            # Store shot-level decoder residuals for direct analysis without regenerating.
            raw_payload[f"test_{name}_fixed_residual"]=residuals["fixed_matching"]
            raw_payload[f"test_{name}_pooled_residual"]=residuals["pooled_lookup"]
            raw_payload[f"test_{name}_oracle_residual"]=residuals["oracle_matching"]
            perseed_test[name]=(keys,d,y)
        # Causal stream: no condition labels enter adapt_step or decoder selection.
        state="fixed_matching";pending=None;pending_n=0;dwell=DWELL;switches=[];events=[];stream_raw=[];stream_total=0;stream_fixed_res=[];stream_adapt_res=[];stream_oracle_res=[];adapt_times=[]
        schedule_regime_correct=[];delay_shots=[];current_event=None
        seed_err={k:0 for k in ("fixed_matching","adaptive_schedule","oracle_schedule")}
        stream_runtime={"fixed_decode_seconds":0.,"adaptive_decode_seconds":0.,"oracle_decode_seconds":0.,"adaptation_estimator_seconds":0.}
        for bi,name in enumerate(SCHEDULE):
            keys,d,y=sample(circuits[name],STREAM_BLOCK,seed+5000+bi)
            stream_raw.append((d,y,np.full(STREAM_BLOCK,TRAINED.index(name),dtype=np.uint8)))
            event_start=len(events)
            for wi,start in enumerate(range(0,STREAM_BLOCK,WINDOW)):
                stop=min(STREAM_BLOCK,start+WINDOW); wk=keys[start:stop]; wd=d[start:stop]; wy=y[start:stop]
                # Compare every strategy on the same current window.
                td=time.perf_counter();pf=np.asarray(fixed_dem.decode_batch(wd),dtype=np.uint8).reshape(-1);stream_runtime["fixed_decode_seconds"]+=time.perf_counter()-td
                td=time.perf_counter();state_pred=pf if state=="fixed_matching" else predict(train_tables[state],wk,thresholds[state]);stream_runtime["adaptive_decode_seconds"]+=time.perf_counter()-td
                td=time.perf_counter();po=np.asarray(oracle_models[name].decode_batch(wd),dtype=np.uint8).reshape(-1);stream_runtime["oracle_decode_seconds"]+=time.perf_counter()-td
                seed_err["fixed_matching"]+=int((wy^pf).sum()); seed_err["adaptive_schedule"]+=int((wy^state_pred).sum()); seed_err["oracle_schedule"]+=int((wy^po).sum())
                stream_total+=len(wy)
                # Training-regime estimate from current detectors; affects subsequent windows only.
                ta=time.perf_counter();top,posterior,ll=estimate_window(wk,profiles)
                schedule_regime_correct.append(top==name)
                previous=state
                target=top if val_select[top]=="lookup" else "fixed_matching"
                state,pending,pending_n,dwell,switched=decide_switch(state,top,target,posterior,ll,pending,pending_n,dwell)
                if switched:
                    switches.append({"after_block_index":bi,"after_window_index":wi,"shots_seen":bi*STREAM_BLOCK+stop,"from":previous,"to":state,"posterior_for_trigger_regime":posterior[top]})
                adapt_times.append(time.perf_counter()-ta)
                stream_runtime["adaptation_estimator_seconds"]+=adapt_times[-1]
                events.append({"block":bi,"window":wi,"estimated_regime":top,"posterior":posterior,"decoder_for_this_window":previous,"decoder_for_next_window":state,"switch":switched})
                stream_fixed_res.extend((wy^pf).tolist());stream_adapt_res.extend((wy^state_pred).tolist());stream_oracle_res.extend((wy^po).tolist())
            if name!=current_event:
                current_event=name
                # Evaluation-only event marker; adaptation never receives this marker.
                if bi>0:
                    target=name if val_select[name]=="lookup" else "fixed_matching"
                    state_at_boundary=events[event_start-1]["decoder_for_next_window"] if event_start else "fixed_matching"
                    matching_windows=[e["window"] for e in events[event_start:] if e["decoder_for_next_window"]==target]
                    delay=0 if state_at_boundary==target else ((min(matching_windows)+1)*WINDOW if matching_windows else None)
                    delay_shots.append({"block":bi,"new_condition_for_evaluation_only":name,"target_strategy_by_validation":target,"decoder_state_at_boundary":state_at_boundary,"delay_shots_to_target_strategy":delay})
        stream_d=np.concatenate([v[0] for v in stream_raw]);stream_y=np.concatenate([v[1] for v in stream_raw]);stream_labels=np.concatenate([v[2] for v in stream_raw])
        raw_payload["stream_detectors"]=stream_d;raw_payload["stream_observable"]=stream_y;raw_payload["stream_condition_for_audit_only"]=stream_labels
        raw_payload["stream_fixed_residual"]=np.asarray(stream_fixed_res,dtype=np.uint8);raw_payload["stream_adaptive_residual"]=np.asarray(stream_adapt_res,dtype=np.uint8);raw_payload["stream_oracle_residual"]=np.asarray(stream_oracle_res,dtype=np.uint8)
        schedule_pairs={"adaptive_schedule":paired_stats(np.asarray(stream_adapt_res,dtype=np.uint8),np.asarray(stream_fixed_res,dtype=np.uint8)),
                        "oracle_schedule":paired_stats(np.asarray(stream_oracle_res,dtype=np.uint8),np.asarray(stream_fixed_res,dtype=np.uint8))}
        rep_row["schedule"]={"schedule_labels_for_evaluation_only":list(SCHEDULE),"block_shots":STREAM_BLOCK,"window_shots":WINDOW,
          "errors":seed_err,"rates":{k:v/stream_total for k,v in seed_err.items()},"paired_vs_fixed":schedule_pairs,"switches":switches,"events":events,
          "regime_estimation_accuracy":float(np.mean(schedule_regime_correct)),"transition_boundaries_for_evaluation_only":delay_shots,
          "adaptation_delay_definition":"shots after schedule boundary until selected strategy equals validation-selected strategy for the new condition; schedule labels are evaluation-only","switch_count":len(switches),"mean_adaptation_estimator_seconds_per_window":float(np.mean(adapt_times)),"adaptation_estimator_seconds_total":float(np.sum(adapt_times)),
          "runtime_seconds_per_shot":{"fixed_decode":stream_runtime["fixed_decode_seconds"]/stream_total,"adaptive_decode":stream_runtime["adaptive_decode_seconds"]/stream_total,"oracle_decode":stream_runtime["oracle_decode_seconds"]/stream_total,"adaptive_estimator_and_switching_overhead":stream_runtime["adaptation_estimator_seconds"]/stream_total}}
        rows.append(rep_row)
        np.savez_compressed(RAW/f"v4_seed_{rep:02d}_tr{N_TRAIN}_va{N_VAL}_te{N_TEST}.npz",**raw_payload)
        stream_results.append({"seed":seed,"errors":seed_err,"switches":len(switches),"regime_accuracy":float(np.mean(schedule_regime_correct))})
        print(f"seed {rep+1}/{N_SEEDS} complete; raw checkpoint saved",flush=True)
    # Shot-pooled estimates and paired seed-bootstrap intervals.
    total_results={"schema":{"qubits":5,"detectors":8,"observables":1},"noise_conditions":list(CONDITIONS),"trained_regimes":list(TRAINED),"static":{},"schedule":{}}
    for name in CONDITIONS:
        total=N_SEEDS*N_TEST
        entry={"raw_errors":agg_raw[name],"raw_rate":agg_raw[name]/total,"shots":total,"decoders":{}}
        for dec in ("fixed_matching","oracle_matching","pooled_lookup","per_regime_lookup"):
            errors=agg[name][dec];entry["decoders"][dec]={"errors":errors,"rate":errors/total,"wilson95":wilson(errors,total)}
        entry["paired_vs_fixed"]={}
        for dn in ("oracle_matching","pooled_lookup","per_regime_lookup"):
            a_dis,b_dis=agg_discord[name][dn]
            shot_stats=paired_from_counts(a_dis,b_dis,total)
            seed_diffs=[r["static"][name]["paired_vs_fixed"][dn]["difference_errors"] for r in rows]
            entry["paired_vs_fixed"][dn]={**shot_stats,"bonferroni_p_over_six_conditions":min(1.,shot_stats["mcnemar_exact_two_sided_p"]*6),
                "per_seed_error_differences":seed_diffs,"seed_bootstrap_rate_difference_ci95":seed_bootstrap([v/N_TEST for v in seed_diffs],SEED_BASE+CONDITIONS.index(name))}
        entry["regime_estimator_top_label_counts"]={r:class_conf[name][r] for r in TRAINED}
        total_results["static"][name]=entry
    for dec in ("fixed_matching","adaptive_schedule","oracle_schedule"):
        errs=[r["schedule"]["errors"][dec] for r in rows]; shots=N_SEEDS*len(SCHEDULE)*STREAM_BLOCK
        total_results["schedule"][dec]={"errors":sum(errs),"shots":shots,"rate":sum(errs)/shots,"per_seed_errors":errs,"seed_bootstrap_rate_ci95":seed_bootstrap([x/ (len(SCHEDULE)*STREAM_BLOCK) for x in errs],SEED_BASE+99)}
    for candidate in ("adaptive_schedule","oracle_schedule"):
        discord_candidate=sum(r["schedule"]["paired_vs_fixed"][candidate]["candidate_only_wrong"] for r in rows)
        discord_fixed=sum(r["schedule"]["paired_vs_fixed"][candidate]["fixed_only_wrong"] for r in rows)
        differences=[r["schedule"]["paired_vs_fixed"][candidate]["difference_errors"] for r in rows]
        shot_stats=paired_from_counts(discord_candidate,discord_fixed,N_SEEDS*len(SCHEDULE)*STREAM_BLOCK)
        total_results["schedule"].setdefault("paired_vs_fixed",{})[candidate]={**shot_stats,"per_seed_error_differences":differences,"seed_bootstrap_rate_difference_ci95":seed_bootstrap([x/(len(SCHEDULE)*STREAM_BLOCK) for x in differences],SEED_BASE+202)}
    all_delays=[item["delay_shots_to_target_strategy"] for r in rows for item in r["schedule"]["transition_boundaries_for_evaluation_only"] if item["delay_shots_to_target_strategy"] is not None]
    total_results["schedule"].update({"per_seed_switches":[r["schedule"]["switch_count"] for r in rows],"per_seed_regime_estimation_accuracy":[r["schedule"]["regime_estimation_accuracy"] for r in rows],"switches_total":sum(r["schedule"]["switch_count"] for r in rows),"mean_detection_accuracy":float(np.mean([r["schedule"]["regime_estimation_accuracy"] for r in rows])),"adaptation_delay_shots_observed":all_delays,"mean_adaptation_delay_shots":float(np.mean(all_delays)) if all_delays else None,"mean_runtime_seconds_per_shot":{key:float(np.mean([r["schedule"]["runtime_seconds_per_shot"][key] for r in rows])) for key in rows[0]["schedule"]["runtime_seconds_per_shot"]},"mean_switch_estimator_overhead_seconds_per_window":float(np.mean([r["schedule"]["mean_adaptation_estimator_seconds_per_window"] for r in rows]))})
    result={"protocol":"same ideal Stim circuit skeleton; explicit Pauli-channel insertions after CX and X measurement flips before Z-basis M/MR; train/validation/test disjoint seeds; inference receives detector windows only; PyMatching DEM uses Stim approximate_disjoint_errors=True for mutually exclusive Pauli-channel components; schedule oracle receives true current composition with zero estimation delay","software":{"python":platform.python_version(),"stim":stim.__version__,"pymatching":pymatching.__version__,"numpy":np.__version__},"config":{"distance":DISTANCE,"rounds":ROUNDS,"p_data":P_DATA,"p_measure":P_MEAS,"train_shots_per_regime_seed":N_TRAIN,"validation_shots_per_regime_seed":N_VAL,"test_shots_per_condition_seed":N_TEST,"seeds":N_SEEDS,"window":WINDOW,"schedule":list(SCHEDULE),"stream_block_shots":STREAM_BLOCK,"trained_compositions":{"x_dominant":[.8,.1,.1],"z_dominant":[.1,.1,.8],"depolarizing":[1/3,1/3,1/3],"measurement_only":"data p=0; measurement flip p=.01"},"held_out_compositions":{"mixed_xz_heldout":[.5,0,.5],"data_plus_measurement_heldout":"depolarizing data p=.01 plus measurement p=.01"}},"validation_strategy_choices_by_seed":[r["static"]["x_dominant"]["validation_selected_strategy_by_regime"] for r in rows],"replicates":rows,"aggregate":total_results}
    result["config"].update({"seed_base":SEED_BASE,"validation_shots_split":"first half selects correction threshold; independent second half selects lookup vs matching","switch_safeguard":"two confident detector windows, posterior>=0.90, log-likelihood margin>=ln(10), minimum dwell of two windows","validation_strategy_gate":"lookup selected only when held-out policy half has fewer paired residuals and exact McNemar p<0.0125 (Bonferroni over four trained regimes)"})
    a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(f"Saved {a.output}")
    try: make_plots(total_results,a.output.stem)
    except Exception as e: print(f"Plot generation unavailable: {e}")


def make_plots(summary,stem):
    import matplotlib.pyplot as plt
    names=list(summary["static"]); decoders=("fixed_matching","oracle_matching","pooled_lookup","per_regime_lookup")
    fig,ax=plt.subplots(figsize=(10,5))
    x=np.arange(len(names));width=.19
    for i,dec in enumerate(decoders):
        rates=[summary["static"][n]["decoders"][dec]["rate"] for n in names]
        ax.bar(x+(i-1.5)*width,rates,width,label=dec)
    ax.set_yscale("log");ax.set_xticks(x,names,rotation=20,ha="right");ax.set_ylabel("Residual observable error rate");ax.legend(fontsize=8);ax.set_title("Noise-composition test (log scale)");fig.tight_layout();fig.savefig(ROOT/f"{stem}_noise_composition_residuals.png",dpi=160);plt.close(fig)
    sched=summary["schedule"];labels=["fixed_matching","adaptive_schedule","oracle_schedule"]
    fig,ax=plt.subplots(figsize=(6,4));ax.bar(labels,[sched[k]["rate"] for k in labels]);ax.set_ylabel("Residual observable error rate");ax.set_title("Time-varying schedule");fig.tight_layout();fig.savefig(ROOT/f"{stem}_time_varying_comparison.png",dpi=160);plt.close(fig)

if __name__=="__main__": main()
