"""Freeze Pilot 2 configuration/seed allocation without sampling any shots."""
from __future__ import annotations
import argparse, hashlib, itertools, json
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
SEED0 = 880_000_000
PGRID = [i / 500 for i in range(11)]
SCENARIOS = [
    "stationary_p0", "stationary_p008", "stationary_p016", "step_up", "step_down", "smooth", "transient", "measurement_mismatch"
]


def hashfile(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def segments(scenario, scored, warmup=200, tuning=False):
    """Return contiguous sampler segments (burst p, measurement p, shot count)."""
    if scenario == "stationary_p0": schedule=lambda t: 0.0
    elif scenario == "stationary_p008": schedule=lambda t: .008
    elif scenario == "stationary_p016": schedule=lambda t: .016
    elif scenario == "step_up": schedule=lambda t: .002 if t < scored//2 else .018
    elif scenario == "step_down": schedule=lambda t: .018 if t < scored//2 else .002
    elif scenario == "smooth": schedule=lambda t: .01 + .008*np.sin(2*np.pi*t/scored)
    elif scenario == "transient":
        start=max(50, scored//2-50); schedule=lambda t: .016 if start <= t < start+100 else .002
    elif scenario == "measurement_mismatch": schedule=lambda t: .008
    else: raise ValueError(scenario)
    meas=.006 if scenario == "measurement_mismatch" else .003
    parts=[]
    first=float(schedule(-1))
    parts.append((round(first,8),meas,warmup))
    for lo in range(0,scored,50):
        hi=min(scored,lo+50)
        if scenario=="smooth":
            p=float(.01+.008*np.sin(2*np.pi*((lo+hi)/2)/scored))
        else: p=float(schedule(lo))
        p=round(float(np.clip(p,0,.02)),8)
        if parts and parts[-1][:2]==(p,meas):
            a=parts.pop(); parts.append((p,meas,a[2]+hi-lo))
        else: parts.append((p,meas,hi-lo))
    return parts


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--freeze',action='store_true'); args=ap.parse_args()
    if not args.freeze: ap.error('pass --freeze to write the pre-sampling configuration and inventory')
    # Fixed 24-candidate tuning budget drawn reproducibly from a prespecified finite design space.
    space=list(itertools.product([4.,8.,12.,16.],[2,4,8],[2,4],[0.,.002],[100,200],["all5","first3","any5"]))
    rng=np.random.default_rng(9400285)
    chosen=sorted(rng.choice(len(space),size=24,replace=False).tolist())
    candidates=[]
    for cid,i in enumerate(chosen):
        h,w,d,hy,pw,pair=space[i]
        candidates.append(dict(candidate_id=f'C{cid:02d}', threshold=h, history_blocks=w, min_dwell_blocks=d,
                               hysteresis=hy, profile_window=pw, pair_summary=pair))
    cfg={
      "protocol_id":"qshift-v2-pilot2-v1","status":"frozen_before_sampling",
      "allocation":{"evaluation_scenarios":SCENARIOS,"evaluation_replicates":20,"warmup_shots_per_evaluation_stream":200,
        "scored_shots_per_evaluation_stream":1300,"block_size":50,"stationary_calibration_replicates_per_p":12,
        "stationary_calibration_warmup":200,"stationary_calibration_scored":800,"tuning_replicates_per_schedule":6,
        "tuning_warmup":200,"tuning_scored":300,"profile_shots_per_p":1000,"static_selection_shots_per_p":500,
        "unique_shot_budget":300000,"planned_unique_shots":298500},
      "profile_probabilities":[0,.005,.01,.015,.02],"static_candidates":PGRID,
      "adaptive_graph_grid":PGRID,"policies":["fixed_p0","static_dev","batch_profile","trailing_200","ewma_08","periodic_200","event_glr","oracle_true_p"],
      "decoder_modes":[False,True],"dem":{"decompose_errors":True,"approximate_disjoint_errors":True},
      "pymatching":{"construction_enable_correlations":"same as mode","decode_batch_enable_correlations":"same as mode"},
      "profile_training_seed_root":SEED0,"seed_algorithm":"pre-enumerated unique Stim sampler seeds, contiguous from seed_start",
      "seed_start":SEED0,"tuning_seed":9400285,"tuning_candidate_budget":24,
      "false_alarm_target_per_1000_stationary_scored_shots":1.0,"false_alarm_p_values":[0,.008,.016],
      "detection_tuning_scenarios":["step_up","step_down","smooth","transient"],
      "candidate_space":{"threshold":[4,8,12,16],"history_blocks":[2,4,8],"minimum_dwell_blocks":[2,4],
        "hysteresis":[0,.002],"profile_window":[100,200],"pair_summary":["all5","first3","any5"]},
      "candidates":candidates,
      "statistical":{"cluster_unit":"independent stream","bootstrap_replicates":20000,"interval":"two-sided percentile 95% stratified within scenario",
        "scenarios_equal_weight":True,"bootstrap_seed":8820261108,"primary_comparators":["static_dev","ewma_08"],"primary_success":"upper 95% interval < 0 for both comparisons in at least one decoder mode",
        "noninferiority_margin_event_vs_ewma_pp":.10,"cost_tradeoff_cpu_savings_fraction":.20,"switch_reduction_fraction":.20},
      "stop":{"unique_shots":300000,"cpu_hours":8,"rss_gib":8},
      "forbidden":{"stage5_access":False,"sealed_data_access":False,"full_study":False,"logical_labels_in_online_policy":False,"true_p_in_online_policy":False}}
    # Sampling plan entries specify each compiled sampler seed; this is a seed-only preflight.
    samples=[]
    def add(key,parts):
        for seg,(p,mp,n) in enumerate(parts): samples.append({"sample_key":key,"segment":seg,"burst_p":p,"measurement_p":mp,"shots":n})
    for i,p in enumerate(cfg['profile_probabilities']): add(f'profile_p{p:.3f}',[(p,.003,1000)])
    for i,p in enumerate(PGRID): add(f'static_p{p:.3f}',[(p,.003,500)])
    for p in [0,.008,.016]:
        for r in range(12): add(f'cal_p{p:.3f}_r{r:02d}',[(p,.003,200),(p,.003,800)])
    for sc in cfg['detection_tuning_scenarios']:
        for r in range(6): add(f'tune_{sc}_r{r:02d}',segments(sc,300,200,True))
    for sc in SCENARIOS:
        for r in range(20): add(f'eval_{sc}_r{r:02d}',segments(sc,1300,200))
    for i,s in enumerate(samples): s['seed']=SEED0+i
    # Explicitly safe historical Q-SHIFT development inventories only. Stage 5 is excluded by path.
    hist_paths=[
      ROOT/'outputs/stage4_noise_adaptive_feasibility_v1/seed_inventory.json',
      ROOT/'outputs/stage4_noise_adaptive_development_v1/seed_inventory.json',
      ROOT/'outputs/stage4_noise_adaptive_feasibility_v1/SEED_INVENTORY_INITIAL.json',
      ROOT/'outputs/stage4_noise_adaptive_feasibility_v1/STAGE4_PROPOSED_SEED_PLAN.json',
      ROOT/'outputs/stage4_noise_adaptive_feasibility_v1/seed_audit.json',
      ROOT/'outputs/stage4_noise_adaptive_development_v1/seed_audit.json',
      ROOT/'outputs/stage4_noise_adaptive_development_v1/additional_development_seed_audit.json',
      ROOT/'outputs/qshift_v2_dev_v1/pilot_config.json',
      ROOT/'outputs/phase4c_strong_baselines/stage2/STAGE2_SEED_INVENTORY.json',
      ROOT/'outputs/phase4c_strong_baselines/stage2/STAGE2_SEED_INVENTORY_AMENDED.json'
    ]
    available=[]; hist=[]
    for path in hist_paths:
        if not path.exists(): continue
        raw=path.read_bytes(); obj=json.loads(raw)
        nums=set()
        def walk(x,k=''):
            if isinstance(x,dict):
                for kk,v in x.items(): walk(v,kk.lower())
            elif isinstance(x,list):
                for v in x: walk(v,k)
            elif isinstance(x,(int,float)) and int(x)>0 and (k in {'seed','root','seed_root','root_seed','rng_seed','seed_start','seed_end'} or k.endswith('_seeds') or k=='seeds' or k=='recoverable_historical_development_seed_values_union') and 'count' not in k: nums.add(int(x))
        walk(obj)
        # Pilot 1 runner derived seeds from this documented root; conservatively reserve the used namespace.
        if path.name=='pilot_config.json':
            root=int(obj['seed_root']); nums.update(range(root,root+5000))
        available.append({"path":str(path.relative_to(ROOT)).replace('\\','/'),"sha256":hashlib.sha256(raw).hexdigest(),"seed_count":len(nums)})
        hist.extend(nums)
    used={int(x['seed']) for x in samples}
    collisions=sorted(used.intersection(hist))
    if collisions: raise SystemExit(f'seed collisions: {collisions[:10]}')
    inv={"protocol_id":cfg['protocol_id'],"status":"frozen_pre_sampling","seed_start":SEED0,
         "sampler_seed_count":len(samples),"seed_end":samples[-1]['seed'],"unique_seeds":len(used),
         "historical_inventories_checked":available,"historical_unique_seed_values_checked":len(set(hist)),
         "collisions":collisions,"samples":samples}
    (OUT/'PILOT2_CONFIG.json').write_text(json.dumps(cfg,indent=2),encoding='utf-8')
    (OUT/'PILOT2_SEED_INVENTORY.json').write_text(json.dumps(inv,indent=2),encoding='utf-8')
    print(json.dumps({"config_sha256":hashfile(OUT/'PILOT2_CONFIG.json'),"inventory_sha256":hashfile(OUT/'PILOT2_SEED_INVENTORY.json'),
                      "sampler_seeds":len(samples),"seed_range":[samples[0]['seed'],samples[-1]['seed']],
                      "historical_seed_values":len(set(hist)),"collisions":collisions,
                      "planned_unique_shots":cfg['allocation']['planned_unique_shots']},indent=2))
if __name__=='__main__': main()
