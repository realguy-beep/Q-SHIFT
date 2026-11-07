"""Paired Phase 2 study of composition-specialized Stim DEM/PyMatching models."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, platform, sys, time
from pathlib import Path
import numpy as np
import stim, pymatching

ROOT=Path(__file__).resolve().parent
RAW=ROOT/"raw"; RESULTS=ROOT/"results"
RAW.mkdir(exist_ok=True);RESULTS.mkdir(exist_ok=True)
PHASE1=ROOT.parent/"noise_composition_phase"/"run_composition_experiment.py"
spec=importlib.util.spec_from_file_location("phase1_noise_builder",PHASE1)
phase1=importlib.util.module_from_spec(spec);spec.loader.exec_module(phase1)

SPECIALISTS=("x_dominant","z_dominant","depolarizing","measurement_only")
CONDITIONS=("x_dominant","z_dominant","depolarizing","measurement_only","mixed_xz_heldout","data_plus_measurement_heldout")
SEED_BASE=20301215
P_GRID=(.006,.008,.010,.012,.014)


def sample(c,shots,seed):
    d,o=c.compile_detector_sampler(seed=seed).sample(shots=shots,separate_observables=True)
    return d.astype(np.uint8),o[:,0].astype(np.uint8)


def wilson(k,n):
    z=1.959963984540054;p=k/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [mid-half,mid+half]


def exact_p(a,b):
    n=a+b
    if n==0:return 1.
    return min(1.,2*sum(math.comb(n,j) for j in range(min(a,b)+1))/(2**n))


def paired(candidate_residual,fixed_residual):
    a=int(np.sum((candidate_residual!=0)&(fixed_residual==0)))
    b=int(np.sum((candidate_residual==0)&(fixed_residual!=0)))
    n=len(fixed_residual);diff=a-b
    delta=diff/n;se=math.sqrt(max(0,a+b-diff*diff/n))/n
    return {"candidate_only_wrong":a,"fixed_only_wrong":b,"difference_errors":diff,
      "paired_rate_difference_ci95_approx":[delta-1.96*se,delta+1.96*se],"mcnemar_exact_two_sided_p":exact_p(a,b)}


def seed_bootstrap(values,seed,nboot=5000):
    v=np.asarray(values,dtype=float);rng=np.random.default_rng(seed)
    means=np.mean(v[rng.integers(0,len(v),size=(nboot,len(v)))],axis=1)
    return [float(np.quantile(means,.025)),float(np.quantile(means,.975))]


def circuit_at_probability(regime,p):
    old_data,old_measure=phase1.P_DATA,phase1.P_MEAS
    try:
        phase1.P_DATA=p;phase1.P_MEAS=p
        return phase1.make_circuit(regime)
    finally:
        phase1.P_DATA=old_data;phase1.P_MEAS=old_measure


def detector_keys(d):
    return [int.from_bytes(row.tobytes(),"little") for row in np.packbits(d,axis=1,bitorder="little")]


def fit_probability_from_calibration(calibration_detectors,template_profiles):
    """Fit only p from detector-pattern likelihood; no L0 labels are read."""
    keys=detector_keys(calibration_detectors); scores={}
    for p,profile in template_profiles.items():
        total=profile["shots"];counts=profile["counts"]
        fallback=1/(total+256)
        scores[p]=sum(math.log((counts.get(k,0)+1)*fallback) for k in keys)
    best=max(P_GRID,key=lambda p:(scores[p],-abs(p-.010)))
    return best,{str(p):scores[p] for p in P_GRID}


def matching_for(c):
    dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=True)
    model=pymatching.Matching.from_detector_error_model(dem)
    return model,{"dem_text_bytes":len(str(dem).encode("utf-8")),"dem_error_terms":sum(1 for line in str(dem).splitlines() if line.startswith("error(")),
       "matching_num_detectors":int(model.num_detectors),"matching_num_edges":int(model.num_edges),"matching_python_wrapper_bytes":sys.getsizeof(model)}


def run(args):
    manifest_path=RAW/f"manifest_{args.output.stem}.json"
    plot_path=RESULTS/f"{args.output.stem}_cross_evaluation.png"
    raw_pattern=f"{args.output.stem}_seed_*_base{args.seed}_cal{args.calibration}_val{args.validation}_test{args.test}.npz"
    existing=list(RAW.glob(raw_pattern))
    if args.output.exists() or manifest_path.exists() or plot_path.exists() or existing:
        raise FileExistsError("This run name already has artifacts; choose a new --output stem to preserve all prior results.")
    conditions={name:phase1.make_circuit(name) for name in CONDITIONS}
    signatures={(c.num_qubits,c.num_detectors,c.num_observables) for c in conditions.values()}
    if signatures!={(5,8,1)}:raise RuntimeError(f"circuit schema mismatch: {signatures}")
    fixed_model,fixed_meta=matching_for(conditions["depolarizing"])
    oracle_models={name:matching_for(c)[0] for name,c in conditions.items()}
    template_profiles={}
    for ri,regime in enumerate(SPECIALISTS):
        template_profiles[regime]={}
        for pi,pvalue in enumerate(P_GRID):
            d,_=sample(circuit_at_probability(regime,pvalue),args.template,args.seed+7_000_000+ri*100+pi)
            counts={}
            for key in detector_keys(d):counts[key]=counts.get(key,0)+1
            template_profiles[regime][pvalue]={"counts":counts,"shots":len(d)}
    decoder_names=("fixed_nominal","oracle_noise_specific",*SPECIALISTS)
    candidate_names=("fixed_nominal",*SPECIALISTS)
    raw_by_seed=[];per_seed=[]
    model_counts={c:{d:0 for d in decoder_names} for c in CONDITIONS}
    raw_counts={c:0 for c in CONDITIONS}
    discord={c:{d:[0,0] for d in decoder_names if d!="fixed_nominal"} for c in CONDITIONS}
    disagreement={c:{d:0 for d in decoder_names if d!="fixed_nominal"} for c in CONDITIONS}
    oracle_counts={c:0 for c in CONDITIONS};oracle_choice_counts={c:{d:0 for d in candidate_names} for c in CONDITIONS}
    oracle_discord={c:[0,0] for c in CONDITIONS}
    runtime_sum={d:0. for d in decoder_names};runtime_calls=0
    calibration_fits=[];specialist_metadata=[]
    for rep in range(args.seeds):
        seed=args.seed+rep*100_000
        raw={"seed":np.asarray(seed,dtype=np.int64)}
        calib={};validation={};test={}
        # Calibration detector data estimates p by likelihood; observable labels are not read.
        for j,name in enumerate(SPECIALISTS):
            d,y=sample(conditions[name],args.calibration,seed+10+j)
            calib[name]=(d,y);raw[f"calibration_{name}_detectors"]=d;raw[f"calibration_{name}_observable_audit_only"]=y
        fitted_p={};fit_scores={};specialist_models={};meta_seed={}
        for name in SPECIALISTS:
            fitted_p[name],fit_scores[name]=fit_probability_from_calibration(calib[name][0],template_profiles[name])
            specialist_models[name],meta_seed[name]=matching_for(circuit_at_probability(name,fitted_p[name]))
            meta_seed[name].update({"estimated_p":fitted_p[name],"calibration_detector_log_likelihood_grid":fit_scores[name]})
        calibration_fits.append({"seed":seed,"estimated_p":fitted_p,"log_likelihood_grid":fit_scores})
        specialist_metadata.append(meta_seed)
        for j,name in enumerate(CONDITIONS):
            d,y=sample(conditions[name],args.validation,seed+100+j)
            validation[name]=(d,y);raw[f"validation_{name}_detectors"]=d;raw[f"validation_{name}_observable_audit_only"]=y
            d,y=sample(conditions[name],args.test,seed+200+j)
            test[name]=(d,y);raw[f"test_{name}_detectors"]=d;raw[f"test_{name}_observable_audit_only"]=y
        seedrow={"seed":seed,"conditions":{}}
        for condition in CONDITIONS:
            vd,vy=validation[condition]
            td,ty=test[condition]
            decoders={"fixed_nominal":fixed_model,"oracle_noise_specific":oracle_models[condition],**specialist_models}
            val_errors={};predictions={};residuals={};runtime={}
            for name,model in decoders.items():
                vp=np.asarray(model.decode_batch(vd),dtype=np.uint8).reshape(-1)
                val_errors[name]=int(np.sum(vy^vp))
                t0=time.perf_counter();pred=np.asarray(model.decode_batch(td),dtype=np.uint8).reshape(-1);runtime[name]=time.perf_counter()-t0
                predictions[name]=pred;residuals[name]=ty^pred
                model_counts[condition][name]+=int(residuals[name].sum())
                runtime_sum[name]+=runtime[name];runtime_calls+=1
            # Validation chooses one strategy per condition. Test labels do not enter this choice.
            chosen=min(candidate_names,key=lambda n:(val_errors[n],0 if n=="fixed_nominal" else 1,n))
            oracle_err=int(residuals[chosen].sum());oracle_counts[condition]+=oracle_err;oracle_choice_counts[condition][chosen]+=1
            raw_counts[condition]+=int(ty.sum())
            for name in decoders:
                if name=="fixed_nominal":continue
                pair=paired(residuals[name],residuals["fixed_nominal"])
                discord[condition][name][0]+=pair["candidate_only_wrong"]
                discord[condition][name][1]+=pair["fixed_only_wrong"]
                disagreement[condition][name]+=int(np.sum(predictions[name]!=predictions["fixed_nominal"]))
            oracle_pair=paired(residuals[chosen],residuals["fixed_nominal"])
            oracle_discord[condition][0]+=oracle_pair["candidate_only_wrong"];oracle_discord[condition][1]+=oracle_pair["fixed_only_wrong"]
            metrics={"raw_errors":int(ty.sum()),"validation_errors_by_model":val_errors,"validation_selected_oracle_model":chosen,
              "decoders":{},"paired_vs_fixed":{},"prediction_disagreement_vs_fixed":{},"runtime_seconds_per_test_shot":{}}
            for name in decoders:
                err=int(residuals[name].sum())
                metrics["decoders"][name]={"errors":err,"rate":float(residuals[name].mean()),"wilson95":wilson(err,args.test)}
                metrics["runtime_seconds_per_test_shot"][name]=runtime[name]/args.test
                if name!="fixed_nominal":
                    metrics["paired_vs_fixed"][name]=paired(residuals[name],residuals["fixed_nominal"])
                    metrics["prediction_disagreement_vs_fixed"][name]=int(np.sum(predictions[name]!=predictions["fixed_nominal"]))
            metrics["oracle_validation_selected_test_errors"]=oracle_err
            metrics["oracle_validation_selected_paired_vs_fixed"]=oracle_pair
            seedrow["conditions"][condition]=metrics
        per_seed.append(seedrow)
        raw_path=RAW/f"{args.output.stem}_seed_{rep:02d}_base{args.seed}_cal{args.calibration}_val{args.validation}_test{args.test}.npz"
        np.savez_compressed(raw_path,**raw)
        raw_by_seed.append({"name":raw_path.name,"bytes":raw_path.stat().st_size,"sha256":hashlib.sha256(raw_path.read_bytes()).hexdigest()})
        print(f"seed {rep+1}/{args.seeds} complete; raw checkpoint saved",flush=True)
    total_shots=args.seeds*args.test
    aggregate={"shots_per_condition":total_shots,"conditions":{},"usefulness_gate":{}}
    all_candidates=[(c,d) for c in CONDITIONS for d in SPECIALISTS]
    for condition in CONDITIONS:
        entry={"raw_errors":raw_counts[condition],"raw_rate":raw_counts[condition]/total_shots,"decoders":{},"paired_vs_fixed":{},"prediction_disagreement_rate_vs_fixed":{},"oracle_model_choices":oracle_choice_counts[condition]}
        for name in decoders:
            errors=model_counts[condition][name]
            entry["decoders"][name]={"errors":errors,"rate":errors/total_shots,"wilson95":wilson(errors,total_shots)}
            if name!="fixed_nominal":
                a,b=discord[condition][name];p=exact_p(a,b)
                seed_diff=[r["conditions"][condition]["decoders"][name]["errors"]-r["conditions"][condition]["decoders"]["fixed_nominal"]["errors"] for r in per_seed]
                entry["paired_vs_fixed"][name]={"candidate_only_wrong":a,"fixed_only_wrong":b,"difference_errors":a-b,
                  "paired_rate_difference_ci95_approx":[(a-b)/total_shots-1.96*math.sqrt(max(0,a+b-(a-b)**2/total_shots))/total_shots,(a-b)/total_shots+1.96*math.sqrt(max(0,a+b-(a-b)**2/total_shots))/total_shots],
                  "mcnemar_exact_two_sided_p":p,"bonferroni_p_over_24":min(1.,p*24),"per_seed_error_differences":seed_diff,
                  "seed_bootstrap_rate_difference_ci95":seed_bootstrap([x/args.test for x in seed_diff],args.seed+CONDITIONS.index(condition))}
                entry["prediction_disagreement_rate_vs_fixed"][name]=disagreement[condition][name]/total_shots
        entry["validation_oracle_selected_model"]={"test_errors":oracle_counts[condition],"rate":oracle_counts[condition]/total_shots,"model_choices":oracle_choice_counts[condition]}
        oa,ob=oracle_discord[condition];op=exact_p(oa,ob)
        entry["validation_oracle_selector_paired_vs_fixed"]={"candidate_only_wrong":oa,"fixed_only_wrong":ob,"difference_errors":oa-ob,"mcnemar_exact_two_sided_p":op,"paired_rate_difference_ci95_approx":[(oa-ob)/total_shots-1.96*math.sqrt(max(0,oa+ob-(oa-ob)**2/total_shots))/total_shots,(oa-ob)/total_shots+1.96*math.sqrt(max(0,oa+ob-(oa-ob)**2/total_shots))/total_shots]}
        aggregate["conditions"][condition]=entry
    credible=[]
    for condition in CONDITIONS:
        for name in SPECIALISTS:
            comp=aggregate["conditions"][condition]["paired_vs_fixed"][name]
            perseed_ci=comp["seed_bootstrap_rate_difference_ci95"]
            passed=(comp["difference_errors"]<0 and comp["bonferroni_p_over_24"]<.05 and perseed_ci[1]<0)
            if passed:credible.append({"condition":condition,"specialist":name})
    aggregate["usefulness_gate"]={"comparisons":len(all_candidates),"bonferroni_family_size":24,"credible_specialists":credible,
      "proceed_to_detector_selection":bool(credible),"criterion":"lower paired test errors, Bonferroni-adjusted exact McNemar p<0.05, and seed-bootstrap 95% upper bound below zero"}
    aggregate["oracle_selector"]={"validation_selected_test_errors":{c:oracle_counts[c] for c in CONDITIONS},"total_errors":sum(oracle_counts.values()),"total_shots":len(CONDITIONS)*total_shots,
      "fixed_total_errors":sum(model_counts[c]["fixed_nominal"] for c in CONDITIONS),"fixed_total_shots":len(CONDITIONS)*total_shots,
      "model_choice_counts_by_condition":oracle_choice_counts}
    agg_runtime={name:runtime_sum[name]/(args.seeds*len(CONDITIONS)*args.test) for name in decoder_names}
    oa=sum(pair[0] for pair in oracle_discord.values());ob=sum(pair[1] for pair in oracle_discord.values())
    on=args.seeds*len(CONDITIONS)*args.test;op=exact_p(oa,ob)
    result={"protocol":"independent calibration/validation/test seeds; fixed DEM weights from explicit composition-specific calibration circuits; test shots paired across fixed, all specialists, and validation-selected oracle; no adaptation if the specialist gate fails",
      "software":{"python":platform.python_version(),"stim":stim.__version__,"pymatching":pymatching.__version__,"numpy":np.__version__},
      "config":{"distance":3,"rounds":3,"detectors":8,"observables":1,"conditions":list(CONDITIONS),"specialists":list(SPECIALISTS),"seed_base":args.seed,"seeds":args.seeds,"calibration_shots_per_specialist_seed":args.calibration,"validation_shots_per_condition_seed":args.validation,"test_shots_per_condition_seed":args.test,"p_data":.01,"p_measure":.01,"probability_fit":"maximum detector-pattern likelihood over the configured grid; known composition family, no L0 labels","probability_grid":list(P_GRID),"template_shots_per_grid_point":args.template,"selector_validation":"minimum residual count among fixed and four specialists, tie favors fixed; selected separately per condition","test_tuning":"none","DEM":"Stim approximate_disjoint_errors=True for mixed Pauli channels"},
      "fixed_model_metadata":fixed_meta,"specialist_model_metadata_by_seed":specialist_metadata,"calibration_probability_fits_by_seed":calibration_fits,"aggregate_runtime_seconds_per_test_shot":agg_runtime,"aggregate":aggregate,"replicates":per_seed,"raw_files":raw_by_seed}
    aggregate["oracle_selector_vs_fixed"]={"oracle_only_wrong":oa,"fixed_only_wrong":ob,"difference_errors":oa-ob,"mcnemar_exact_two_sided_p":op,"paired_rate_difference_ci95_approx":[(oa-ob)/on-1.96*math.sqrt(max(0,oa+ob-(oa-ob)**2/on))/on,(oa-ob)/on+1.96*math.sqrt(max(0,oa+ob-(oa-ob)**2/on))/on],"test_shots":on}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.exists(): raise FileExistsError(f"Refusing to overwrite existing result: {args.output}")
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    manifest_path.write_text(json.dumps({"result_stem":args.output.stem,"files":raw_by_seed},indent=2)+"\n",encoding="utf-8")
    print("Saved",args.output)
    make_plot(aggregate,args.output.stem)


def make_plot(aggregate,stem):
    import matplotlib.pyplot as plt
    conditions=list(aggregate["conditions"]);models=("fixed_nominal","x_dominant","z_dominant","depolarizing","measurement_only")
    labels=("Fixed nominal","X specialist","Z specialist","Depolarizing specialist","Measurement specialist")
    fig,ax=plt.subplots(figsize=(11,5.5));x=np.arange(len(conditions));w=.15
    for i,(model,label) in enumerate(zip(models,labels)):
        rates=np.array([aggregate["conditions"][c]["decoders"][model]["rate"] for c in conditions])
        cis=np.array([aggregate["conditions"][c]["decoders"][model]["wilson95"] for c in conditions])
        pos=x+(i-2)*w;ax.bar(pos,rates,w,label=label)
        ax.errorbar(pos,rates,yerr=np.vstack([np.maximum(0,rates-cis[:,0]),np.maximum(0,cis[:,1]-rates)]),fmt="none",ecolor="black",capsize=2,linewidth=.7)
    ax.set_yscale("log");ax.set_xticks(x,conditions,rotation=18,ha="right");ax.set_ylabel("Residual observable error rate");ax.set_title("Specialist PyMatching cross-evaluation; Wilson 95% intervals");ax.legend(fontsize=8);fig.tight_layout()
    out=ROOT/"results"/f"{stem}_cross_evaluation.png";fig.savefig(out,dpi=180);plt.close(fig);print("Saved",out)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--seeds",type=int,default=10);p.add_argument("--calibration",type=int,default=30_000);p.add_argument("--validation",type=int,default=10_000);p.add_argument("--test",type=int,default=30_000);p.add_argument("--template",type=int,default=20_000);p.add_argument("--seed",type=int,default=SEED_BASE);p.add_argument("--output",type=Path,default=RESULTS/"specialist_results.json")
    a=p.parse_args()
    if min(a.seeds,a.calibration,a.validation,a.test,a.template)<=0:p.error("all shot counts and seeds must be positive")
    run(a)

if __name__=="__main__":main()
