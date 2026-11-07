"""Development-only matched-shot Q-SHIFT demonstration experiment."""
from __future__ import annotations
import hashlib, json, sys, time
from pathlib import Path
import numpy as np
import stim

ROOT = Path(__file__).resolve().parents[2]
ADAPTIVE = ROOT / "outputs/phase4c_strong_baselines/adaptive"
sys.path.insert(0, str(ADAPTIVE))
from decoder_bank import GRID, build_bank  # reuse the existing frozen nine-model construction

REGIMES = {
    "data_heavy": (0.006, 0.001),
    "nominal": (0.003, 0.003),
    "measurement_heavy": (0.001, 0.006),
}
REGIME_NAMES = tuple(REGIMES)
REGIME_ID = {name: i for i, name in enumerate(REGIME_NAMES)}
REGIME_DECODER = {"data_heavy": 6, "nominal": 4, "measurement_heavy": 2}
POLICIES = ("identity_no_decode", "pooled_fixed", "nominal_fixed", "adaptive", "regime_informed_diagnostic")

def make_circuit(regime: str) -> stim.Circuit:
    gate, meas = REGIMES[regime]
    return stim.Circuit.generated("surface_code:rotated_memory_z", distance=3, rounds=5,
        after_clifford_depolarization=gate, before_measure_flip_probability=meas)

def sample(regime: str, seed: int, shots: int):
    det, obs = make_circuit(regime).compile_detector_sampler(seed=int(seed)).sample(
        shots=int(shots), separate_observables=True)
    return np.asarray(det, dtype=np.uint8), np.asarray(obs[:, 0], dtype=np.uint8)

def decode_grid(models, detectors):
    return np.stack([np.asarray(m.decode_batch(detectors), dtype=np.uint8)[:, 0] for m in models])

class RegimeEstimator:
    """Three-regime detector-only product-Bernoulli estimator; no label input."""
    def __init__(self, profiles):
        self.profiles = np.clip(np.asarray(profiles, dtype=np.float64), 1e-5, 1-1e-5)
        if self.profiles.ndim != 2 or self.profiles.shape[0] != 3:
            raise ValueError("expected one detector-marginal profile per generating regime")
    def posterior(self, detectors):
        x = np.asarray(detectors, dtype=np.uint8)
        if x.ndim != 2 or x.shape[1] != self.profiles.shape[1] or len(x) == 0:
            raise ValueError("detector block has invalid shape or is empty")
        k = x.sum(axis=0, dtype=np.float64)
        n = len(x)
        ll = (k[None, :] * np.log(self.profiles) + (n-k)[None, :] * np.log1p(-self.profiles)).sum(axis=1)
        ll -= ll.max()
        p = np.exp(ll); p /= p.sum()
        return p

class AdaptivePolicy:
    """Utility-aware selection using only the preceding completed detector block."""
    def __init__(self, estimator, utility_rates, paired_se, fallback=1, confidence=.60,
                 hysteresis=2, dwell=2, penalty=.0005, z=1.96):
        self.estimator=estimator; self.utility=np.asarray(utility_rates,float); self.paired_se=np.asarray(paired_se,float)
        if self.utility.shape != (3,9) or self.paired_se.shape != (3,9,9):
            raise ValueError("calibration utility/uncertainty arrays have wrong shape")
        self.current=int(fallback); self.confidence=confidence; self.hysteresis=hysteresis; self.dwell=dwell
        self.penalty=penalty; self.z=z; self.age=0; self.pending=None; self.streak=0
        self.last_posterior=None; self.last_estimate=None
    def select_for_next_block(self, previous_completed_detectors):
        if previous_completed_detectors is None:
            return self.current, None
        posterior=self.estimator.posterior(previous_completed_detectors)
        estimate=int(np.argmax(posterior)); conf=float(posterior[estimate]); self.last_posterior=posterior
        self.last_estimate=estimate; self.age += 1
        if conf < self.confidence:
            self.pending=None; self.streak=0
            return self.current, posterior
        risks=posterior @ self.utility
        candidate=int(np.argmin(risks))
        if candidate == self.current:
            self.pending=None; self.streak=0
            return self.current, posterior
        # Approximate uncertainty of expected paired error improvement, using the
        # independent calibration samples and regime posterior as fixed weights.
        var=0.0
        for r in range(3): var += posterior[r]**2 * self.paired_se[r,self.current,candidate]**2
        gain=float(risks[self.current]-risks[candidate])
        if gain <= max(self.penalty, self.z*np.sqrt(var)):
            self.pending=None; self.streak=0
            return self.current, posterior
        if candidate == self.pending: self.streak += 1
        else: self.pending=candidate; self.streak=1
        if self.streak >= self.hysteresis and self.age >= self.dwell:
            self.current=candidate; self.pending=None; self.streak=0; self.age=0
        return self.current, posterior

def calibrate(models, shots=20000, seeds=(99100001,99100002,99100003)):
    profiles=[]; err_arrays=[]; det_arrays=[]; obs_arrays=[]
    for ri,name in enumerate(REGIME_NAMES):
        d,y=sample(name,seeds[ri],shots); pred=decode_grid(models,d)
        profiles.append(d.mean(axis=0)); err_arrays.append(pred ^ y[None,:]); det_arrays.append(d); obs_arrays.append(y)
    errors=np.stack(err_arrays) # regimes x decoders x shots
    rates=errors.mean(axis=2)
    paired_se=np.zeros((3,9,9),dtype=float)
    for r in range(3):
        for a in range(9):
            for b in range(9):
                diff=errors[r,a].astype(float)-errors[r,b].astype(float)
                paired_se[r,a,b]=diff.std(ddof=1)/np.sqrt(shots)
    return {"profiles":np.asarray(profiles),"utility_rates":rates,"paired_se":paired_se,
        "calibration_errors":errors,"detectors":det_arrays,"observables":obs_arrays,
        "calibration_best":rates.argmin(axis=1).astype(int)}

def schedule_states(kind, blocks=12):
    if kind == "stationary": return ["nominal"]*blocks
    if kind == "data_to_measurement": return ["data_heavy"]*(blocks//2)+["measurement_heavy"]*(blocks-blocks//2)
    if kind == "measurement_to_data": return ["measurement_heavy"]*(blocks//2)+["data_heavy"]*(blocks-blocks//2)
    if kind == "nominal_measurement_nominal":
        a=blocks//3; b=blocks//3; return ["nominal"]*a+["measurement_heavy"]*b+["nominal"]*(blocks-a-b)
    if kind == "rapid_cycle": return [REGIME_NAMES[i%3] for i in range(blocks)]
    raise ValueError(kind)

def run_replicate(kind, replicate, models, cal, shots=512, seed_start=99200001,
                  schedule_index=0, replicates=10, blocks=12):
    states=schedule_states(kind,blocks); selector=AdaptivePolicy(RegimeEstimator(cal["profiles"]),cal["utility_rates"],cal["paired_se"])
    previous=None; outputs=[]; policy_seconds=0.; decode_seconds=0.; single_decoder_seconds=0.; adaptive_decoder_seconds=0.; all_d=[]; all_y=[]; all_preds=[]; all_adaptive=[]; all_est=[]; all_choices=[]; all_post=[]
    for bi,state in enumerate(states):
        t0=time.perf_counter(); choice,post=selector.select_for_next_block(previous); policy_seconds += time.perf_counter()-t0
        seed=seed_start+((schedule_index*replicates+replicate)*blocks+bi)
        d,y=sample(state,seed,shots)
        t0=time.perf_counter(); preds=decode_grid(models,d); decode_seconds+=time.perf_counter()-t0
        adaptive_pred=preds[choice]
        t0=time.perf_counter(); models[1].decode_batch(d); single_decoder_seconds+=time.perf_counter()-t0
        t0=time.perf_counter(); adaptive_live=np.asarray(models[choice].decode_batch(d),dtype=np.uint8)[:,0]; adaptive_decoder_seconds+=time.perf_counter()-t0
        assert np.array_equal(adaptive_live,adaptive_pred)
        regime_best=int(cal["calibration_best"][REGIME_ID[state]])
        picks={"identity_no_decode":np.zeros(shots,dtype=np.uint8),"pooled_fixed":preds[1],"nominal_fixed":preds[4],
               "adaptive":adaptive_pred,"regime_informed_diagnostic":preds[regime_best]}
        err={p:int(np.count_nonzero(pr ^ y)) for p,pr in picks.items()}
        paired={p:{"adaptive_wrong_fixed_correct":int(np.count_nonzero((adaptive_pred^y)&~(preds[1]^y))),
                   "adaptive_correct_fixed_wrong":int(np.count_nonzero(~(adaptive_pred^y)&(preds[1]^y)))} for p in ("adaptive",)}
        outputs.append({"block":bi,"regime":state,"seed":int(seed),"shots":shots,"decoder_index":choice,
            "estimate_regime":selector.last_estimate,"posterior":None if post is None else post.tolist(),"errors":err,
            "adaptive_vs_pooled_discordance":paired["adaptive"],"detector_sha256":hashlib.sha256(d.tobytes()).hexdigest(),
            "observable_sha256":hashlib.sha256(y.tobytes()).hexdigest(),"paired_input_hash":hashlib.sha256(d.tobytes()+y.tobytes()).hexdigest()})
        all_d.append(d);all_y.append(y);all_preds.append(preds);all_adaptive.append(adaptive_pred);all_est.append(-1 if selector.last_estimate is None else selector.last_estimate);all_choices.append(choice);all_post.append(np.zeros(3) if post is None else post)
        previous=d
    # Separate controller switches from regime changes and score harmfulness only as an
    # explicitly retrospective diagnostic against independent calibration utilities.
    switches=[]; harmful=0
    for i in range(1,len(all_choices)):
        if all_choices[i]!=all_choices[i-1]:
            r=REGIME_ID[states[i]]; switches.append(i)
            harmful += int(cal["utility_rates"][r,all_choices[i]] >= cal["utility_rates"][r,all_choices[i-1]])
    transitions=[i for i in range(1,len(states)) if states[i]!=states[i-1]]
    delays=[]
    est_arr=np.asarray(all_est)
    for tr in transitions:
        target=REGIME_ID[states[tr]]
        end=next((i for i in transitions if i>tr),len(states))
        hit=next((i-tr for i in range(tr+1,end) if est_arr[i]==target),None)
        delays.append(hit)
    arrays={"detectors":np.concatenate(all_d),"observables":np.concatenate(all_y),"grid_predictions":np.concatenate(all_preds,axis=1),
        "adaptive_predictions":np.concatenate(all_adaptive),"state_ids":np.repeat([REGIME_ID[s] for s in states],shots).astype(np.uint8),
        "choice_by_block":np.asarray(all_choices,dtype=np.uint8),"estimate_by_block":np.asarray(all_est,dtype=np.int8),"posterior_by_block":np.asarray(all_post,dtype=np.float32)}
    metrics={p:sum(b["errors"][p] for b in outputs) for p in POLICIES}
    return {"schedule":kind,"replicate":replicate,"states":states,"shots":shots*blocks,"blocks":outputs,"errors":metrics,
        "switch_blocks":switches,"switch_count":len(switches),"calibration_utility_harmful_switches":harmful,
        "regime_estimate_accuracy":sum(int(all_est[i]==REGIME_ID[states[i]]) for i in range(1,blocks))/(blocks-1),
        "transition_estimator_delays_blocks":delays,"censored_transition_count":sum(x is None for x in delays),
        "decode_seconds_all_nine":decode_seconds,"policy_selection_seconds":policy_seconds,
        "single_fixed_decode_seconds":single_decoder_seconds,"adaptive_selected_decode_seconds":adaptive_decoder_seconds,
        "policy_overhead_fraction_of_single_fixed_decode":policy_seconds/max(single_decoder_seconds,1e-12),
        "paired_inputs_identical":True,"arrays":arrays}

def analyze(replicates, bootstrap_seed=99300001, bootstrap_draws=10000):
    schedule_names=list(replicates); policies=list(POLICIES); summary={}; rng=np.random.default_rng(bootstrap_seed)
    for p in policies:
        errors=sum(rep["errors"][p] for rows in replicates.values() for rep in rows)
        shots=sum(rep["shots"] for rows in replicates.values() for rep in rows)
        summary[p]={"errors":int(errors),"shots":int(shots),"logical_error_rate":errors/shots,"success_rate":1-errors/shots}
    # Equal weight to schedule families, resampling independent replicates within each family.
    diffs={s:np.asarray([(r["errors"]["adaptive"]-r["errors"]["pooled_fixed"])/r["shots"] for r in replicates[s]]) for s in schedule_names}
    boot=np.empty(bootstrap_draws)
    for j in range(bootstrap_draws):
        means=[]
        for s in schedule_names:
            x=diffs[s]; means.append(np.mean(x[rng.integers(0,len(x),size=len(x))]))
        boot[j]=np.mean(means)
    point=float(np.mean([x.mean() for x in diffs.values()]))
    return {"overall":summary,"adaptive_minus_pooled_equal_schedule_mean":point,
        "adaptive_minus_pooled_seed_cluster_bootstrap_95ci":[float(x) for x in np.quantile(boot,[.025,.975])],
        "bootstrap_draws":bootstrap_draws,"bootstrap_seed":bootstrap_seed,
        "schedule_results":{s:{p:{"errors":int(sum(r["errors"][p] for r in rows)),"shots":int(sum(r["shots"] for r in rows)),
            "logical_error_rate":sum(r["errors"][p] for r in rows)/sum(r["shots"] for r in rows)} for p in policies}
            | {"adaptive_minus_pooled_seed_differences":[float(x) for x in diffs[s]],"mean_adaptive_minus_pooled":float(diffs[s].mean()),
               "switch_count":int(sum(r["switch_count"] for r in rows)),"harmful_switches_calibration_diagnostic":int(sum(r["calibration_utility_harmful_switches"] for r in rows)),
               "mean_regime_estimate_accuracy":float(np.mean([r["regime_estimate_accuracy"] for r in rows])),
               "transition_delays_blocks":[x for r in rows for x in r["transition_estimator_delays_blocks"]],
               "censored_transitions":int(sum(r["censored_transition_count"] for r in rows)),
               "mean_policy_overhead_fraction_of_single_fixed_decode":float(np.mean([r["policy_overhead_fraction_of_single_fixed_decode"] for r in rows])),
               "mean_adaptive_compute_overhead_fraction_vs_fixed":float(np.mean([(r["policy_selection_seconds"]+r["adaptive_selected_decode_seconds"]-r["single_fixed_decode_seconds"])/max(r["single_fixed_decode_seconds"],1e-12) for r in rows]))} for s,rows in replicates.items()}}
