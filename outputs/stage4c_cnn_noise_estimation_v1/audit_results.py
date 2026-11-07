"""Independent Stage 4C re-estimation, re-decoding, and aggregate audit."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch

from outputs.stage4_noise_adaptive_feasibility_v1.prototype import (
    DetectorProfileEstimator, build_decoder, decode_prediction,
)
from .models import (BurstProbabilityCNN, RidgeBurstRegressor, batch_feature_vector,
                     detector_coordinate_map, encode_calibration_batch, encode_training_batches, parameter_count)
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUN = HERE / "run"
PROBS = (0.0, 0.004, 0.008, 0.012, 0.016)
METHOD_TO_KEY = {"fixed_nominal": "pred_fixed", "stage4b_profile": "pred_profile",
                 "ridge": "pred_ridge", "cnn": "pred_cnn", "privileged_true_p": "pred_privileged"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_freeze() -> dict:
    freeze = json.loads((HERE / "FREEZE.json").read_text(encoding="utf-8"))
    if freeze.get("status") != "FROZEN_BEFORE_SAMPLING":
        raise RuntimeError("invalid freeze state")
    for rel, expected in freeze["files_sha256"].items():
        path = REPO / rel
        if not path.is_file() or sha(path) != expected:
            raise RuntimeError(f"frozen file mismatch: {rel}")
    return freeze


def independent_ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    mu = x.mean(axis=0)
    sd = x.std(axis=0)
    sd[sd <= 1e-9] = 1.0
    z = (x - mu) / sd
    design = np.concatenate([np.ones((len(z), 1)), z], axis=1)
    penalty = np.eye(design.shape[1]) * alpha
    penalty[0, 0] = 0
    beta = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    return mu, sd, beta


def independent_ridge_predict(params, x):
    mu, sd, beta = params
    z = (np.asarray(x, dtype=np.float64) - mu) / sd
    return np.clip(np.concatenate([np.ones((len(z), 1)), z], axis=1) @ beta, 0, 0.02)


def train_cnn_independently(train_d, train_p, valid_d, valid_p, coord_map, inventory):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(int(inventory["analysis_rngs"]["torch_initialization"]))
    model = BurstProbabilityCNN().cpu()
    opt = torch.optim.AdamW(model.parameters(), lr=0.003, weight_decay=0.0001)
    loss_fn = torch.nn.MSELoss()
    xt = torch.from_numpy(encode_training_batches(train_d, coord_map))
    yt = torch.from_numpy((train_p / 0.02).astype(np.float32))
    xv = torch.from_numpy(encode_training_batches(valid_d, coord_map))
    yv = torch.from_numpy(valid_p.astype(np.float32))
    generator = torch.Generator(device="cpu").manual_seed(int(inventory["analysis_rngs"]["torch_batch_order"]))
    best, best_epoch, best_val, stale = None, 0, float("inf"), 0
    for epoch in range(1, 401):
        model.train()
        order = torch.randperm(len(xt), generator=generator)
        for start in range(0, len(xt), 32):
            ix = order[start:start + 32]
            opt.zero_grad(set_to_none=True)
            loss = loss_fn(model(xt[ix]), yt[ix])
            if not torch.isfinite(loss):
                raise FloatingPointError("non-finite independently recomputed loss")
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            val = float(torch.mean(torch.abs(model(xv) * 0.02 - yv)))
        if val < best_val - 1e-12:
            best, best_epoch, best_val, stale = {k: v.detach().clone() for k, v in model.state_dict().items()}, epoch, val, 0
        else:
            stale += 1
        if stale >= 30:
            break
    if best is None:
        raise RuntimeError("independent training did not select a checkpoint")
    model.load_state_dict(best)
    return model.eval(), best_epoch, best_val


def load_archives(inventory: dict):
    with np.load(RUN / "training_batches.npz", allow_pickle=False) as z:
        td, tp, ts = z["detectors"], z["probabilities"], z["seeds"]
    with np.load(RUN / "validation_batches.npz", allow_pickle=False) as z:
        vd, vp, vs = z["detectors"], z["probabilities"], z["seeds"]
    expected_train = np.asarray([x["seed"] for x in inventory["streams"] if x["kind"] == "training_detector_batch"], dtype=np.uint64)
    expected_val = np.asarray([x["seed"] for x in inventory["streams"] if x["kind"] == "validation_detector_batch"], dtype=np.uint64)
    if td.shape != (360, 250, 40) or tp.shape != (360,) or not np.array_equal(ts, expected_train):
        raise RuntimeError("training data inventory/shape mismatch")
    if vd.shape != (120, 250, 40) or vp.shape != (120,) or not np.array_equal(vs, expected_val):
        raise RuntimeError("validation data inventory/shape mismatch")
    if not np.isin(td, (0, 1)).all() or not np.isin(vd, (0, 1)).all():
        raise RuntimeError("non-binary detector values in training or validation arrays")
    if not np.array_equal(tp, np.repeat((0.0, 0.01, 0.02), 120)):
        raise RuntimeError("training probability labels differ from frozen schedule")
    if not np.array_equal(vp, np.repeat((0.005, 0.015), 60)):
        raise RuntimeError("validation probability labels differ from frozen schedule")
    return td, tp, ts, vd, vp, vs


def main() -> None:
    start_time = time.perf_counter()
    freeze = verify_freeze()
    config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    inventory = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    seed_audit = json.loads((HERE / "seed_audit.json").read_text(encoding="utf-8"))
    if seed_audit.get("stage4c_historical_collisions") != [] or seed_audit.get("stage4c_seed_count") != 554:
        raise RuntimeError("seed audit failed")
    status = json.loads((RUN / "status.json").read_text(encoding="utf-8"))
    if status.get("status") != "completed" or status.get("completed_jobs") != 35 or status.get("completed_shots") != 277500:
        raise RuntimeError("runner status/counts do not claim complete Stage 4C allocation")
    if status.get("independent_test_accessed") != 0:
        raise RuntimeError("independent-test access flag is not zero")
    td, tp, ts, vd, vp, vs = load_archives(inventory)
    profile = DetectorProfileEstimator.fit([(float(p), d) for p, d in zip(tp, td)])
    tx = np.stack([batch_feature_vector(d) for d in td])
    vx = np.stack([batch_feature_vector(d) for d in vd])
    ridge_candidates = []
    for alpha in (0.01, 0.1, 1.0, 10.0):
        params = independent_ridge_fit(tx, tp, alpha)
        mae = float(np.mean(np.abs(independent_ridge_predict(params, vx) - vp)))
        ridge_candidates.append((mae, alpha, params))
    selected = min(ridge_candidates, key=lambda t: (t[0], t[1]))
    ridge_mae, ridge_alpha, ridge_params = selected
    recorded_ridge = json.loads((RUN / "ridge_model.json").read_text(encoding="utf-8"))
    if float(recorded_ridge["alpha"]) != float(ridge_alpha):
        raise RuntimeError("Ridge alpha does not reproduce from validation data")
    for a, b in zip(ridge_params, (np.asarray(recorded_ridge["mean"]), np.asarray(recorded_ridge["scale"]), np.asarray(recorded_ridge["coef"]))):
        if not np.allclose(a, b, rtol=1e-10, atol=1e-12):
            raise RuntimeError("saved Ridge weights differ from independent least-squares refit")

    coord_map = detector_coordinate_map(build_spatial_burst_circuit(burst_probability=0.0).get_detector_coordinates())
    cnn, best_epoch, val_mae = train_cnn_independently(td, tp, vd, vp, coord_map, inventory)
    ckpt = torch.load(RUN / "cnn_checkpoint.pt", map_location="cpu", weights_only=True)
    if int(ckpt["best_epoch"]) != best_epoch or not np.isclose(float(ckpt["validation_mae"]), val_mae, rtol=0, atol=1e-10):
        raise RuntimeError("independent CNN training did not reproduce selected checkpoint metadata")
    for key, tensor in cnn.state_dict().items():
        if not torch.allclose(tensor, ckpt["state_dict"][key], rtol=0, atol=1e-7):
            raise RuntimeError(f"independently retrained CNN weights differ: {key}")

    fixed_models = {"fixed_nominal": build_decoder(0.0)[2]}
    rows, errors = [], {name: 0 for name in METHOD_TO_KEY}
    condition_counts = {str(p): {name: 0 for name in METHOD_TO_KEY} for p in PROBS}
    condition_shots = {str(p): 0 for p in PROBS}
    root_seen = set()
    expected_streams = {(x["kind"], float(x["probability"]), int(x["root"])): int(x["seed"])
                        for x in inventory["streams"] if x["kind"] in ("evaluation_calibration_detectors", "paired_evaluation_detectors_observables")}
    for pi, p in enumerate(PROBS):
        for root in range(7):
            name = f"p{int(round(p*1000)):03d}_root{root:02d}.npz"
            path = RUN / "roots" / name
            if not path.is_file():
                raise FileNotFoundError(f"missing evaluation evidence {name}")
            with np.load(path, allow_pickle=False) as z:
                cal, det, obs = z["calibration_detectors"], z["evaluation_detectors"], z["observables"]
                stored = {key: z[key].astype(np.uint8) for key in METHOD_TO_KEY.values()}
                meta = json.loads(str(z["metadata_json"].item()))
            if cal.shape != (2000,40) or det.shape != (2500,40) or obs.shape != (2500,):
                raise RuntimeError(f"shape mismatch in {name}")
            if any(not np.isin(arr,(0,1)).all() for arr in (cal,det,obs,*stored.values())):
                raise RuntimeError(f"nonbinary values in {name}")
            pair = (p,root)
            if pair in root_seen:
                raise RuntimeError("duplicate evaluation root")
            root_seen.add(pair)
            expected_cal = expected_streams[("evaluation_calibration_detectors", p, root)]
            expected_eval = expected_streams[("paired_evaluation_detectors_observables", p, root)]
            if meta["seeds"] != {"calibration": expected_cal, "evaluation": expected_eval}:
                raise RuntimeError(f"seed provenance mismatch in {name}")
            p_profile = profile.estimate(cal)
            chunks = cal.reshape(8,250,40)
            p_ridge = float(np.mean([independent_ridge_predict(ridge_params, batch_feature_vector(x)[None])[0] for x in chunks]))
            cnn_values=[]
            with torch.no_grad():
                for x in chunks:
                    enc = encode_calibration_batch(x,coord_map)
                    cnn_values.append(float(cnn(torch.from_numpy(enc[None])).item()*0.02))
            p_cnn=float(np.clip(np.mean(cnn_values),0,0.02))
            estimates={"profile":p_profile,"ridge":p_ridge,"cnn":p_cnn,"privileged":p}
            recorded=meta["p_estimates"]
            for n,k in (("profile","profile"),("ridge","ridge"),("cnn","cnn")):
                if not np.isclose(float(recorded[k]),estimates[n],rtol=0,atol=1e-12):
                    raise RuntimeError(f"{n} p estimate does not reproduce in {name}")
            expected_predictions={"fixed_nominal":decode_prediction(fixed_models["fixed_nominal"],det)}
            for method, estimator_name in (("stage4b_profile","profile"),("ridge","ridge"),("cnn","cnn"),("privileged_true_p","privileged")):
                _, dem, matcher=build_decoder(estimates[estimator_name])
                if (dem.num_detectors,dem.num_observables,matcher.num_detectors,matcher.num_fault_ids)!=(40,1,40,1):
                    raise RuntimeError(f"invalid rebuilt graph for {method} in {name}")
                expected_predictions[method]=decode_prediction(matcher,det)
            for method in METHOD_TO_KEY:
                if not np.array_equal(expected_predictions[method],stored[METHOD_TO_KEY[method]]):
                    raise RuntimeError(f"saved {method} predictions fail independent re-decode in {name}")
                err=int(np.sum(expected_predictions[method]^obs))
                errors[method]+=err
                condition_counts[str(p)][method]+=err
            condition_shots[str(p)]+=len(obs)
            rows.append({"file":name,"probability":p,"root":root,"shots":len(obs),"estimates_recomputed":True,"all_predictions_redecoded":True})
    if len(root_seen)!=35 or sum(condition_shots.values())!=87500:
        raise RuntimeError("evaluation root/shot coverage mismatch")
    recorded_results=json.loads((HERE/"STAGE4C_RESULTS.json").read_text(encoding="utf-8"))
    for method,count in errors.items():
        if recorded_results["methods"][method]["total_errors"]!=count:
            raise RuntimeError(f"independently recomputed aggregate differs for {method}")
    for p in PROBS:
        for method,count in condition_counts[str(p)].items():
            expected=recorded_results["methods"][method]["per_condition_errors"][str(p)]
            if expected!=count:
                raise RuntimeError(f"per-condition count mismatch for p={p} method={method}")
    run_manifest={"training_batches_sha256":sha(RUN/"training_batches.npz"),
        "validation_batches_sha256":sha(RUN/"validation_batches.npz"),
        "cnn_checkpoint_sha256":sha(RUN/"cnn_checkpoint.pt"),
        "root_archives":{r["file"]:sha(RUN/"roots"/r["file"]) for r in rows}}
    audit={"status":"PASS","freeze_verified":True,"frozen_file_count":len(freeze["files_sha256"]),
        "stage4c_seed_count":inventory["unique_seed_count"],"historical_seed_collisions":seed_audit["stage4c_historical_collisions"],
        "training_shots":90000,"validation_shots":30000,"evaluation_calibration_shots":70000,
        "paired_evaluation_shots":87500,"total_unique_shots":277500,"roots_verified":len(root_seen),
        "independent_test_accessed":False,"partitions_binary_and_shape_valid":True,
        "ridge_alpha_independently_reselected":ridge_alpha,"ridge_validation_mae":ridge_mae,
        "cnn_best_epoch_independently_reproduced":best_epoch,"cnn_validation_mae_independently_reproduced":val_mae,
        "cnn_parameter_count":parameter_count(cnn),"all_calibration_estimates_recomputed":True,
        "all_five_decoder_arms_independently_redecoded":True,"aggregate_errors_independently_recomputed":errors,
        "per_condition_errors_independently_recomputed":condition_counts,
        "root_files":rows,"local_evidence_sha256":run_manifest,
        "auditor_runtime_seconds":time.perf_counter()-start_time,
        "limitations":["Audit replays the frozen simulator/modeling method; the burst mechanism remains synthetic.",
            "CNN weight retraining check is deterministic and conditional on one fixed training allocation and initialization.",
            "Finite historical seed coverage cannot rule out unrecorded RNG use.",
            "No independent-test data were opened or accessed."]}
    (HERE/"STAGE4C_AUDIT_RESULTS.json").write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
    lines=["# Stage 4C Independent Evidence Audit","", "**Status: PASS.**",
        "",f"- Frozen source/configuration hashes verified: {audit['frozen_file_count']}",
        f"- Unique Stage 4C seeds: {audit['stage4c_seed_count']}; recoverable historical collisions: 0",
        f"- Fresh unique samples: {audit['total_unique_shots']:,} (training 90,000; validation 30,000; calibration 70,000; paired evaluation 87,500)",
        f"- Evaluation roots independently checked: {audit['roots_verified']}/35; all five decoder predictions re-decoded exactly.",
        f"- CNN checkpoint independently retrained: best epoch {best_epoch}; validation MAE {val_mae:.7f}; {audit['cnn_parameter_count']:,} parameters.",
        "- Stage4B profile, Ridge and CNN estimates were recomputed from calibration detector arrays only.",
        "- Paired evaluation detector/observable arrays are shared across all five decoder arms.",
        "- Independent-test access: **none**.","", "Per-method aggregate errors independently reconstructed:",""]
    lines += [f"- {k}: {v}/87,500" for k,v in errors.items()]
    lines += ["", "Raw local arrays remain in the ignored `run/` directory. SHA-256 values are in `STAGE4C_AUDIT_RESULTS.json` and `EVIDENCE_MANIFEST.json.",
        "Finite recoverable seed records do not establish the absence of unrecorded historical RNG use. This audit verifies saved development evidence, not hardware behavior or independent confirmation."]
    (HERE/"STAGE4C_INDEPENDENT_AUDIT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","roots":len(root_seen),"shots":sum(condition_shots.values()),"errors":errors,"audit_seconds":audit["auditor_runtime_seconds"]},indent=2))


if __name__ == "__main__":
    main()
