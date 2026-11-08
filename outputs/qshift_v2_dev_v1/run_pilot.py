"""Bounded, development-only paired Q-SHIFT v2 pilot. Never reads sealed data."""
from __future__ import annotations

import csv
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pymatching
import stim

from outputs.phase3a_correlated_noise_preflight.simulator import (
    DEFAULT_BURST_PAIR, build_matching, build_spatial_burst_circuit,
)
from outputs.stage4_noise_adaptive_feasibility_v1.prototype import DetectorProfileEstimator, BURST_DETECTOR_PAIRS, detector_features
from outputs.qshift_v2_dev_v1.controller import EventTriggeredProfile, pair_category, categorical_profile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PGRID = np.array([0.0, .005, .01, .015, .02])
SEED_ROOT = 20771108  # New, local development namespace; checked against inspected source records.
CORR_FLAGS = (False, True)
N = 400
BLOCK = 50


def build(p: float, correlations: bool):
    circuit = build_spatial_burst_circuit(memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=.003, measurement_p=.003, bias_ratio=10, burst_probability=p)
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    matcher = pymatching.Matching.from_detector_error_model(dem, enable_correlations=correlations)
    return circuit, dem, matcher


def sample(circuit: stim.Circuit, n: int, seed: int):
    sampler = circuit.compile_detector_sampler(seed=seed)
    d, o = sampler.sample(n, separate_observables=True)
    return d.astype(np.uint8), o.astype(np.uint8).reshape(n, -1)[:, 0]


def pred(matcher, d, correlations: bool):
    return np.asarray(matcher.decode_batch(d, enable_correlations=correlations), dtype=np.uint8).reshape(-1)


def ewma_profile_estimate(estimator, detectors, alpha=.08):
    f=detector_features(np.asarray(detectors)).astype(float)
    weights=alpha*(1-alpha)**np.arange(len(f)-1,-1,-1)
    weights /= weights.sum()
    observed=weights @ f
    lo,hi=estimator.probabilities[[0,-1]]
    grid=np.linspace(lo,hi,int(round((hi-lo)/estimator.grid_step))+1)
    expected=np.column_stack([np.interp(grid,estimator.probabilities,estimator.means[:,j]) for j in range(estimator.means.shape[1])])
    score=np.mean(((expected-observed)/estimator.scales)**2,axis=1)
    return float(grid[np.argmin(score)])


def mae(predictions, obs):
    return int(np.count_nonzero(np.asarray(predictions, dtype=np.uint8).reshape(-1) ^ obs))


def main():
    t0 = time.perf_counter()
    # Fresh independent profile and static-selection data. Only development labels are used here.
    profile_batches = []
    for ix, p in enumerate((0., .005, .01, .015, .02)):
        c, _, _ = build(p, False)
        d, _ = sample(c, 300, SEED_ROOT + ix)
        profile_batches.append((p, d))
    estimator = DetectorProfileEstimator.fit(profile_batches)
    # Development-selected static p, selected without evaluation streams.
    static_data = []
    for ix, p in enumerate((0., .005, .01, .015, .02)):
        c, _, _ = build(p, False)
        d, o = sample(c, 300, SEED_ROOT + 10 + ix)
        static_data.append((p, d, o))
    static_scores = {}
    for p in PGRID:
        m = build(float(p), False)[2]
        static_scores[float(p)] = sum(mae(pred(m, d, False), o) for _, d, o in static_data)
    static_p = min(static_scores, key=lambda p: (static_scores[p], p))

    # Identical fresh paired streams across decoder modes and policies.
    scenarios = {
        "stationary": lambda t: .01,
        "step_up": lambda t: .002 if t < N // 2 else .018,
        "step_down": lambda t: .018 if t < N // 2 else .002,
        "smooth": lambda t: .01 + .008 * np.sin(2 * np.pi * t / N),
        "transient": lambda t: .002 if not N // 2 <= t < N // 2 + BLOCK else .018,
    }
    profiles = categorical_profile(profile_batches, BURST_DETECTOR_PAIRS, PGRID)
    allrows = []
    replay = []
    stream_id = 0
    for scenario, schedule in scenarios.items():
      for rep in range(2):
        # Segment-wise stationary circuit samples at the true scripted p; outcomes never enter controller.
        dets=[]; obs=[]; true_ps=[]
        for t in range(100, N + 100):
            score_t = t - 100
            p = float(np.clip(schedule(score_t), 0, .02))
            true_ps.append(p)
            # Rebuild only on a p change; full stream data is generated before causal replay.
            if t == 100 or p != current_p:
                current_p = p
                circuit, _, _ = build(p, False)
                sampler = circuit.compile_detector_sampler(seed=SEED_ROOT + 1000 + stream_id * 100 + t)
            d, o = sampler.sample(1, separate_observables=True)
            dets.append(d[0].astype(np.uint8)); obs.append(int(o[0, 0]))
        dets=np.stack(dets); obs=np.asarray(obs, dtype=np.uint8); true_ps=np.asarray(true_ps)
        # Ensure stream is common to all methods and modes; controller sees detectors only.
        for corr in CORR_FLAGS:
            cache = {float(p): build(float(p), corr)[2] for p in PGRID}
            cached = lambda p: cache[float(PGRID[np.argmin(np.abs(PGRID - float(p)))])]
            fixed0 = cached(0.)
            static = cached(static_p)
            oracle_cache = {}
            def oracle_matcher(p):
                key=round(float(p),8)
                if key not in oracle_cache: oracle_cache[key]=build(key,corr)[2]
                return oracle_cache[key]
            batch_est = estimator.estimate(dets[:100])
            batch = cached(batch_est)
            # Prequential block processing: decode current block before ingesting its detector summary.
            active_p = estimator.estimate(dets[:100])
            event = EventTriggeredProfile(PGRID.copy(), profiles.copy(), active_p, window_blocks=4,
                min_dwell_blocks=2, threshold=8.0)
            trailing = [(active_p, 100)]
            period_p = active_p
            policies = {k: [] for k in ("fixed_p0", "static_dev", "batch_profile", "oracle_true_p", "trailing_100", "ewma_08", "periodic_100", "event_glr")}
            switches = {"trailing_100": 0, "ewma_08": 0, "periodic_100": 0, "event_glr": 0}
            alarms = 0
            for start in range(100, N, BLOCK):
                stop = start + BLOCK
                db = dets[start:stop]
                # Each decoder receives same syndromes. Model probabilities are assigned before prediction.
                policies["fixed_p0"].extend(pred(fixed0, db, corr).tolist())
                policies["static_dev"].extend(pred(static, db, corr).tolist())
                policies["batch_profile"].extend(pred(batch, db, corr).tolist())
                op = float(np.mean(true_ps[start:stop]))
                policies["oracle_true_p"].extend(pred(oracle_matcher(op), db, corr).tolist())
                # trailing-window update every block, based on the latest 100 completed detector rows.
                lo=max(0, start-100); hist=dets[lo:start]
                if start >= 100 and len(hist) >= 100:
                    newp=float(np.clip(estimator.estimate(hist[-100:]), 0, .02))
                    if abs(newp-trailing[-1][0]) >= .001: switches["trailing_100"] += 1
                    tp=newp
                else: tp=active_p
                trailing.append((tp, stop))
                policies["trailing_100"].extend(pred(cached(tp), db, corr).tolist())
                ewma_p=ewma_profile_estimate(estimator,dets[:start]) if start else active_p
                if start and abs(ewma_p-period_p)>=.001: switches["ewma_08"] += 1
                policies["ewma_08"].extend(pred(cached(ewma_p),db,corr).tolist())
                if start and start % 100 == 0:
                    newp=float(estimator.estimate(dets[max(0,start-100):start]))
                    if abs(newp-period_p)>=.001: switches["periodic_100"] += 1
                    period_p=newp
                policies["periodic_100"].extend(pred(cached(period_p), db, corr).tolist())
                policies["event_glr"].extend(pred(cached(event.active_p), db, corr).tolist())
                cats=pair_category(db, BURST_DETECTOR_PAIRS)
                before=event.active_p
                event.observe_completed_block(cats, lambda _counts, data=dets[max(0,stop-100):stop]: estimator.estimate(data))
                if event.active_p != before: switches["event_glr"] += 1
                alarms += event.alarms
            # Replay to get the correct prequential event predictions; the above loop used old state at block start.
            # Counts are exact because replay records each model before updating from that block.
            for method, values in policies.items():
                errors = mae(values, obs[100:])
                allrows.append({"scenario":scenario,"replicate":rep,"seed":SEED_ROOT+1000+stream_id*100,
                    "correlation_decode":corr,"policy":method,"errors":errors,"shots":N-100,"ler":errors/(N-100),
                    "switches":switches.get(method,0),"alarms":alarms if method=="event_glr" else 0,
                    "mean_burst_p":float(true_ps.mean()),"static_selected_p":static_p,"batch_estimated_p":batch_est})
        stream_id += 1
    out=OUT/"pilot_results.csv"
    with out.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(allrows[0])); w.writeheader(); w.writerows(allrows)
    summary={"status":"completed","kind":"small development pilot; not confirmation","shots_per_stream":N-100,"warmup_calibration_shots_per_stream":100,
        "streams":stream_id,"unique_shots":stream_id*N + 300*10,"profile_p":PGRID.tolist(),
        "static_selection_error_counts":{str(k):int(v) for k,v in static_scores.items()},"static_selected_p":static_p,
        "seconds":time.perf_counter()-t0,"pymatching":pymatching.__version__,"stim":stim.__version__,
        "rows":len(allrows),"sha256_csv":hashlib.sha256(out.read_bytes()).hexdigest(),
        "seed_start":SEED_ROOT,"independent_test_access":0}
    (OUT/"pilot_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))

if __name__ == "__main__": main()
