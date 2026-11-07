"""Restartable, bounded local development controller for Q-SHIFT.

The full experiment is opt-in and requires --full-run --confirm-full-autonomous.
There is intentionally no test split, seed stream, or test-sampling function.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Set before importing torch through experiment.py.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import psutil
import torch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RUN_DIR = HERE / "run"
DRY_DIR = HERE / "dry_run_v4"
sys.path.insert(0, str(REPO / "dashboard"))
sys.path.insert(0, str(HERE))

from experiment import atomic_json, fit_job, save_npz_atomic  # noqa: E402
from simulator import decode_matching, prepare, sample  # noqa: E402

CONFIG_PATH = HERE / "config.json"
INVENTORY_PATH = HERE / "SEED_INVENTORY.json"
FREEZE_PATH = HERE / "FREEZE_FINAL_V3.json"
DRY_PROOF_PATH = HERE / "DRY_RUN_RESUME_VERIFICATION_V4.json"
ALLOWED_SPLITS = ("train", "monitor", "calibration", "threshold_selection",
                  "final_development_evaluation")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_json(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def log_event(run_dir: Path, event: dict) -> None:
    event = {"utc": datetime.now(timezone.utc).isoformat(), **event}
    path = run_dir / "progress.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, allow_nan=False, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())


def quarantine_file(path: Path, run_dir: Path, reason: str) -> None:
    if not path.exists():
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = path.with_name(f"{path.stem}.quarantine.{stamp}{path.suffix}")
    os.replace(path, target)
    log_event(run_dir, {"type": "artifact_quarantined", "source": str(path),
                        "quarantine": str(target), "reason": reason})


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def validate_binary(name: str, values: np.ndarray) -> None:
    if not np.isfinite(values).all():
        raise ValueError(f"{name} contains NaN or infinity")
    if np.any((values != 0) & (values != 1)):
        raise ValueError(f"{name} contains non-binary values")


def assert_allowed_split(split: str) -> None:
    if split not in ALLOWED_SPLITS:
        raise RuntimeError(f"Split {split!r} is prohibited; no independent test data are allocated.")


class SafePause(Exception):
    """Raised only at a reproducible sample boundary before a root archive is committed."""


def verify_freeze() -> tuple[dict, dict, dict]:
    if not FREEZE_PATH.is_file() or not INVENTORY_PATH.is_file():
        raise RuntimeError("Pre-sampling freeze or seed inventory is missing. Run --prepare-freeze first.")
    freeze = read_json(FREEZE_PATH)
    config = read_json(CONFIG_PATH)
    inventory = read_json(INVENTORY_PATH)
    if not inventory.get("passed"):
        raise RuntimeError(f"Seed inventory did not pass: {inventory.get('collisions')}")
    if freeze.get("config_sha256") != sha256(CONFIG_PATH):
        raise RuntimeError("Frozen config SHA-256 mismatch.")
    if freeze.get("seed_inventory_sha256") != sha256(INVENTORY_PATH):
        raise RuntimeError("Frozen seed-inventory SHA-256 mismatch.")
    for rel, digest in freeze.get("source_sha256", {}).items():
        path = (HERE / rel) if rel in {"controller.py", "experiment.py", "prepare_freeze.py",
                                       "config.json", "SEED_INVENTORY.json",
                                       "PROTOCOL.md", "ANALYSIS_PLAN.json",
                                       "tests/test_controller.py"} else (REPO / rel)
        if not path.is_file() or sha256(path) != digest:
            raise RuntimeError(f"Frozen source hash mismatch or missing file: {rel}")
    for package, version in freeze.get("packages", {}).items():
        if importlib.metadata.version(package) != version:
            raise RuntimeError(f"Frozen package version changed for {package}: expected {version}")
    if os.path.normcase(os.path.realpath(sys.executable)) != os.path.normcase(os.path.realpath(freeze.get("python_executable", ""))):
        raise RuntimeError("Python executable differs from the pre-sampling freeze; use the frozen environment.")
    if not torch.cuda.is_available() or torch.cuda.get_device_name(0) != freeze.get("cuda_device_name_at_freeze"):
        raise RuntimeError("CUDA availability/device differs from the pre-sampling freeze.")
    seeds = []
    for stream in inventory["streams"]:
        assert_allowed_split(stream["split"])
        seeds.extend(int(s) for s in stream["seeds"])
    for stream in inventory["dry_run_streams"]:
        assert_allowed_split(stream["split"])
        seeds.append(int(stream["seed"]))
    seeds += [int(v) for row in inventory["model_streams"]
              for v in (row["torch_seed"], row["sampling_seed"], row["shuffle_seed"])]
    seeds += [int(v) for v in inventory["dry_run_model_rng_seeds"]]
    seeds += [int(v) for v in inventory["circuit_diagnostic_seeds"]]
    seeds += [int(v) for v in inventory["dry_run_circuit_diagnostic_seeds"]]
    if len(seeds) != len(set(seeds)) or len(seeds) != inventory["proposed_derived_seed_count"]:
        raise RuntimeError("Frozen inventory contains duplicate or unaccounted seeds.")
    if "test" in json.dumps(inventory).lower() and inventory.get("test_stream", "").lower().find("no test stream") < 0:
        # Only the explicit statement that no test stream exists is permitted.
        raise RuntimeError("Unexpected test-stream metadata in seed inventory.")
    return freeze, config, inventory


def configure_determinism(seed: int) -> None:
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)


class CheckpointStore:
    """Two-slot atomic checkpoints with hash verification and fallback."""
    def __init__(self, directory: Path):
        self.directory = directory / "checkpoints"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.events = directory

    def _paths(self, job_id: str, slot: str):
        stem = f"{job_id}.{slot}"
        return self.directory / f"{stem}.pt", self.directory / f"{stem}.json"

    def load(self, job_id: str):
        valid, present = [], False
        for slot in ("A", "B"):
            data_path, meta_path = self._paths(job_id, slot)
            present |= data_path.exists() or meta_path.exists()
            if not data_path.exists() or not meta_path.exists():
                continue
            try:
                meta = read_json(meta_path)
                actual = sha256(data_path)
                if actual != meta.get("sha256"):
                    raise RuntimeError("checkpoint SHA-256 mismatch")
                wrapper = torch.load(data_path, map_location="cpu", weights_only=False)
                if int(wrapper.get("sequence", -1)) != int(meta["sequence"]):
                    raise RuntimeError("checkpoint sequence metadata mismatch")
                valid.append((int(meta["sequence"]), wrapper["payload"], slot))
            except Exception as exc:
                log_event(self.events, {"type": "checkpoint_rejected", "job_id": job_id,
                                        "slot": slot, "reason": str(exc)})
        if not valid:
            if present:
                raise RuntimeError(f"Both checkpoint slots for {job_id} are corrupt or unverifiable.")
            return None
        valid.sort(key=lambda x: x[0])
        if len(valid) == 1:
            return valid[0][1]
        return valid[-1][1]

    def save(self, job_id: str, payload: dict) -> None:
        slots = []
        for slot in ("A", "B"):
            data_path, meta_path = self._paths(job_id, slot)
            if data_path.exists() and meta_path.exists():
                try:
                    meta = read_json(meta_path)
                    if sha256(data_path) == meta.get("sha256"):
                        slots.append((int(meta["sequence"]), slot))
                except Exception:
                    pass
        seq = max((s for s, _ in slots), default=0) + 1
        current_slot = max(slots)[1] if slots else "B"
        target = "B" if current_slot == "A" else "A"
        data_path, meta_path = self._paths(job_id, target)
        tmp = data_path.with_suffix(data_path.suffix + ".tmp")
        with tmp.open("wb") as f:
            torch.save({"sequence": seq, "payload": payload}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, data_path)
        atomic_json({"sequence": seq, "sha256": sha256(data_path)}, meta_path)


class RunLock:
    def __init__(self, run_dir: Path):
        self.path = run_dir / "controller.lock"
        self.created = False

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                info = read_json(self.path)
                proc = psutil.Process(int(info["pid"]))
                same = abs(proc.create_time() - float(info["process_created"])) < 2.0
                if proc.is_running() and same:
                    raise RuntimeError(f"Controller is already active (PID {proc.pid}).")
            except psutil.NoSuchProcess:
                pass
            except (KeyError, ValueError, json.JSONDecodeError):
                raise RuntimeError("Lock file is malformed; inspect it and remove only if no controller is running.")
            self.path.unlink(missing_ok=True)
        proc = psutil.Process()
        atomic_json({"pid": os.getpid(), "process_created": proc.create_time(),
                     "started_utc": datetime.now(timezone.utc).isoformat()}, self.path)
        self.created = True

    def release(self):
        if self.created:
            self.path.unlink(missing_ok=True)


def resource_state(run_dir: Path, device: torch.device, limits: dict) -> dict:
    rss = psutil.Process().memory_info().rss / (1024 ** 3)
    free_disk = shutil.disk_usage(run_dir).free / (1024 ** 3)
    allocated = torch.cuda.memory_allocated(device) / (1024 ** 3) if device.type == "cuda" else 0.0
    return {"rss_gib": rss, "free_disk_gib": free_disk, "gpu_allocated_gib": allocated,
            "ok": (rss <= float(limits["maximum_process_rss_gib"])
                   and free_disk >= float(limits["minimum_free_disk_gib"])
                   and allocated <= float(limits["maximum_gpu_allocated_gib"]))}


def sample_stream(circuit, matching, stream: dict, run_dir: Path, *, batch_size: int = 1024, guard=None):
    assert_allowed_split(stream["split"])
    n = int(stream["shots"])
    d_parts, y_parts, p_parts = [], [], []
    remaining = n
    expected_seeds = list(map(int, stream["seeds"]))
    n_batches = math.ceil(n / batch_size)
    if len(expected_seeds) < n_batches:
        raise RuntimeError(f"Seed allocation too short for {stream['split']} {stream['regime']}.")
    for batch_i in range(n_batches):
        if guard is not None:
            guard()
        count = min(batch_size, remaining)
        d, y = sample(circuit, expected_seeds[batch_i], count)
        p = decode_matching(matching, d)
        validate_binary("detectors", d); validate_binary("observable", y); validate_binary("pymatching", p)
        d_parts.append(d); y_parts.append(y); p_parts.append(p)
        remaining -= count
    out = {"detectors": np.concatenate(d_parts), "observable": np.concatenate(y_parts),
           "pymatching": np.concatenate(p_parts)}
    if out["detectors"].shape != (n, 40) or out["observable"].shape != (n,) or out["pymatching"].shape != (n,):
        raise RuntimeError("Sample stream produced unexpected array dimensions.")
    return out


def generate_root(root_i: int, inventory: dict, envs: dict, run_dir: Path, config: dict,
                  resource_guard) -> tuple[dict, dict]:
    root_path = run_dir / "data" / f"root_{root_i:02d}.npz"
    meta_path = run_dir / "data" / f"root_{root_i:02d}.json"
    records = [s for s in inventory["streams"] if int(s["root_id"]) == root_i
               and s["split"] != "final_development_evaluation"]
    if root_path.exists() and meta_path.exists():
        try:
            meta = read_json(meta_path)
            if int(meta.get("root_id", -1)) != root_i or sha256(root_path) != meta.get("sha256"):
                raise RuntimeError("root identity/hash mismatch")
            data = load_root_data(root_path)
            validate_root_coverage(data, records)
            return data, meta
        except Exception as exc:
            quarantine_file(root_path, run_dir, f"root archive verification failed: {exc}")
            quarantine_file(meta_path, run_dir, f"root metadata verification failed: {exc}")
    elif root_path.exists() or meta_path.exists():
        quarantine_file(root_path, run_dir, "orphaned root archive; metadata pair missing")
        quarantine_file(meta_path, run_dir, "orphaned root metadata; archive pair missing")
    arrays, splits = {}, {}
    for stream in records:
        resource_guard()
        split, regime = stream["split"], stream["regime"]
        arrays_for_stream = sample_stream(envs[regime]["circuit"], envs[regime]["matching"],
                                          stream, run_dir, guard=resource_guard)
        for name, arr in arrays_for_stream.items():
            arrays[f"{split}__{regime}__{name}"] = arr
        splits[f"{split}__{regime}"] = {"shots": int(stream["shots"]), "seeds": stream["seeds"]}
    save_npz_atomic(root_path, arrays)
    meta = {"root_id": root_i, "sha256": sha256(root_path), "splits": splits,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "test_samples_generated_or_accessed": 0}
    atomic_json(meta, meta_path)
    data = unpack_root_arrays(arrays)
    validate_root_coverage(data, records)
    return data, meta


def ensure_final_evaluation(root_i: int, inventory: dict, envs: dict, run_dir: Path,
                            config: dict, resource_guard, *, dry=False) -> Path:
    path = run_dir / "data" / ("dry_final_root_00.npz" if dry else f"final_root_{root_i:02d}.npz")
    meta_path = path.with_suffix(".json")
    if path.exists() and meta_path.exists():
        try:
            meta = read_json(meta_path)
            if sha256(path) != meta.get("sha256") or int(meta.get("root_id", -1)) != root_i:
                raise RuntimeError("final-development archive identity/hash mismatch")
            load_final_evaluation(path, config["regimes"], config["dry_run"]["final_eval_shots"] if dry else 10000)
            return path
        except Exception as exc:
            quarantine_file(path, run_dir, f"final-development archive verification failed: {exc}")
            quarantine_file(meta_path, run_dir, f"final-development metadata verification failed: {exc}")
    elif path.exists() or meta_path.exists():
        quarantine_file(path, run_dir, "orphaned final-development archive; metadata pair missing")
        quarantine_file(meta_path, run_dir, "orphaned final-development metadata; archive pair missing")
    arrays, split_records = {}, {}
    if dry:
        records = [s for s in inventory["dry_run_streams"]
                   if s["split"] == "final_development_evaluation"]
    else:
        records = [s for s in inventory["streams"] if int(s["root_id"]) == root_i
                   and s["split"] == "final_development_evaluation"]
    if {s["regime"] for s in records} != set(config["regimes"]):
        raise RuntimeError(f"Missing final-development seed streams for root {root_i}.")
    for record in records:
        resource_guard()
        regime = record["regime"]
        shots = int(config["dry_run"]["final_eval_shots"]) if dry else int(record["shots"])
        seeds = [int(record["seed"])] if dry else list(map(int, record["seeds"]))
        stream = {"split": "final_development_evaluation", "regime": regime,
                  "shots": shots, "seeds": seeds}
        block = sample_stream(envs[regime]["circuit"], envs[regime]["matching"], stream,
                              run_dir, guard=resource_guard)
        for name, arr in block.items():
            arrays[f"final__{regime}__{name}"] = arr
        split_records[regime] = {"shots": shots, "seeds": seeds}
    save_npz_atomic(path, arrays)
    atomic_json({"root_id": root_i, "sha256": sha256(path), "regimes": split_records,
                 "generated_after_selection": True, "independent_test_access": 0}, meta_path)
    return path


def load_final_evaluation(path: Path, regimes: list[str] | tuple[str, ...], shots: int) -> dict:
    out = {}
    with np.load(path, allow_pickle=False) as z:
        if any("test" in key.lower() for key in z.files):
            raise RuntimeError("Prohibited test evidence found in final-development archive.")
        for key in z.files:
            parts = key.split("__")
            if len(parts) != 3 or parts[0] != "final":
                raise RuntimeError(f"Unexpected final-development field {key}.")
            _, regime, name = parts
            out.setdefault(regime, {})[name] = z[key]
    if set(out) != set(regimes):
        raise RuntimeError("Final-development archive has an unexpected regime set.")
    for regime, data in out.items():
        if set(data) != {"detectors", "observable", "pymatching"}:
            raise RuntimeError(f"Final-development bundle incomplete for {regime}.")
        if data["detectors"].shape != (int(shots), 40) or data["observable"].shape != (int(shots),) or data["pymatching"].shape != (int(shots),):
            raise RuntimeError(f"Final-development array dimensions invalid for {regime}.")
        for name, value in data.items():
            validate_binary(f"final/{regime}/{name}", value)
    return out


def validate_root_coverage(data: dict, records: list[dict]) -> None:
    for stream in records:
        split, regime, n = stream["split"], stream["regime"], int(stream["shots"])
        assert_allowed_split(split)
        block = data[split].get(regime)
        if block is None:
            raise RuntimeError(f"Saved root lacks {split}/{regime} data.")
        if block["detectors"].shape != (n, 40) or block["observable"].shape != (n,) or block["pymatching"].shape != (n,):
            raise RuntimeError(f"Saved root has invalid paired dimensions for {split}/{regime}.")


def unpack_root_arrays(arrays: dict) -> dict:
    result = {s: {} for s in ALLOWED_SPLITS}
    for key, value in arrays.items():
        parts = key.split("__")
        if len(parts) != 3:
            raise RuntimeError(f"Unexpected data archive field: {key}")
        split, regime, name = parts
        assert_allowed_split(split)
        if name not in {"detectors", "observable", "pymatching"}:
            raise RuntimeError(f"Unexpected sample field: {name}")
        result[split].setdefault(regime, {})[name] = np.asarray(value)
    for split in ALLOWED_SPLITS:
        for regime, block in result[split].items():
            if set(block) != {"detectors", "observable", "pymatching"}:
                raise RuntimeError(f"Incomplete {split}/{regime} sample bundle.")
            validate_binary(f"{split}/{regime}/observable", block["observable"])
            validate_binary(f"{split}/{regime}/pymatching", block["pymatching"])
            validate_binary(f"{split}/{regime}/detectors", block["detectors"])
    return result


def load_root_data(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        if any("test" in key.lower() for key in z.files):
            raise RuntimeError("Prohibited test field found in saved development archive.")
        arrays = {key: z[key] for key in z.files}
    return unpack_root_arrays(arrays)


def jobs_for_root(root_i: int, inventory: dict, config: dict, config_digest: str, dry=False):
    rows = inventory["model_streams"]
    selected = [row for row in rows if (int(row["root_id"]) == root_i)]
    jobs = []
    for row in selected:
        model = row["model"]
        name = model
        job_id = f"root{root_i:02d}_{name}_{int(row['train_size_per_regime'])}"
        jobs.append({**row, "model": model, "job_id": job_id, "config_sha256": config_digest,
                     "max_epochs": int(config["training"]["max_epochs"]),
                     "batch_size": int(config["training"]["batch_size"]), "dry": False})
    if not dry:
        return jobs
    seed = int(inventory["dry_run_model_rng_seeds"][0])
    return [{"root_id": root_i, "model": "position_flat_cnn", "train_size_per_regime": int(config["dry_run"]["train_shots"]),
             "torch_seed": seed, "sampling_seed": seed + 1, "shuffle_seed": seed + 2,
             "job_id": f"dry_root{root_i:02d}_position_flat_cnn", "config_sha256": config_digest,
             "max_epochs": int(config["dry_run"]["max_epochs"]),
             "batch_size": int(config["dry_run"]["batch_size"]), "dry": True}]


def aggregate_report(run_dir: Path, config: dict, status: str, detail: str = ""):
    results = []
    for path in sorted((run_dir / "job_results").glob("*.json")) if (run_dir / "job_results").exists() else []:
        row = read_json(path)
        if row.get("status") == "completed":
            results.append(row)
    groups = {}
    for row in results:
        key = (row["model"], int(row["train_size_per_regime"]))
        groups.setdefault(key, []).append(row)
    def t_summary(values):
        values = np.asarray(values, dtype=float)
        n = len(values)
        if n < 2:
            return float(np.mean(values)) if n else float("nan"), None, None, None
        critical = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776}.get(n, 1.96)
        mean = float(values.mean()); se = float(values.std(ddof=1) / math.sqrt(n))
        return mean, mean - critical * se, mean + critical * se, float(values.std(ddof=1))
    lines = ["# Q-SHIFT Autonomous Development Morning Report", "",
             f"**Status:** {status}", "",
             "Development-only experiment. No independent test stream was allocated, generated, or accessed.", "",
             "## Completed job summary", "",
             "| Model | Train shots/regime | Roots | Mean LER | LER 95% root-t interval | Mean PM LER | Mean paired difference | Paired-difference 95% root-t interval | Candidate-only / PM-only |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for (model, size), rows in sorted(groups.items()):
        lers = [r["equal_regime_ler"] for r in rows]
        pms = [r["equal_regime_pymatching_ler"] for r in rows]
        diffs = [r["paired_ler_difference"] for r in rows]
        mean, lo, hi, sd = t_summary(lers)
        ci = "not estimable (<2 roots)" if lo is None else f"[{lo:.5%}, {hi:.5%}]"
        dmean, dlo, dhi, _ = t_summary(diffs)
        dci = "not estimable (<2 roots)" if dlo is None else f"[{dlo:+.5%}, {dhi:+.5%}]"
        lines.append(f"| {model} | {size:,} | {len(rows)} | {mean:.5%} | {ci} | {np.mean(pms):.5%} | {dmean:+.5%} | {dci} | {sum(r['candidate_only'] for r in rows)} / {sum(r['pymatching_only'] for r in rows)} |")
    lines += ["", "## Root-level results", "", "| Root | Model | Train shots/regime | Equal-regime LER | PyMatching LER | Paired difference | Candidate-only / PM-only |", "|---:|---|---:|---:|---:|---:|---:|"]
    for row in results:
        lines.append(f"| {row.get('root_id')} | {row['model']} | {row['train_size_per_regime']:,} | {row['equal_regime_ler']:.5%} | {row['equal_regime_pymatching_ler']:.5%} | {row['paired_ler_difference']:+.5%} | {row['candidate_only']} / {row['pymatching_only']} |")
    lines += ["", "## By generating regime", "", "| Model | Size/regime | Regime | Roots | Mean neural LER | Mean PyMatching LER | Paired difference and 95% root-t interval | Positive recall |", "|---|---:|---|---:|---:|---:|---:|---:|"]
    regime_groups = {}
    for row in results:
        for regime, metrics in row["per_regime"].items():
            regime_groups.setdefault((row["model"], int(row["train_size_per_regime"]), regime), []).append(metrics)
    for (model, size, regime), vals in sorted(regime_groups.items()):
        diff_vals = [v["ler"] - v["pymatching_ler"] for v in vals]
        m, lo, hi, _ = t_summary(diff_vals)
        ci = "not estimable (<2 roots)" if lo is None else f"[{lo:+.5%}, {hi:+.5%}]"
        recall = [v["positive_recall"] for v in vals if v["positive_recall"] is not None]
        lines.append(f"| {model} | {size:,} | {regime} | {len(vals)} | {np.mean([v['ler'] for v in vals]):.5%} | {np.mean([v['pymatching_ler'] for v in vals]):.5%} | {m:+.5%} ({ci}) | mean recall {np.mean(recall):.3%} |")
    lines += ["", "## Interpretation and gate", "",
              "These are development estimates. Thresholds were frozen using separate threshold-selection streams before final-development evaluation; they are not independent confirmatory results.",
              "A GO decision for a larger supervised study requires a reproducible, practically meaningful paired benefit across independent roots. This report does not authorize opening or generating an independent test set.", ""]
    if detail:
        lines += ["## Stop or failure detail", "", detail, ""]
    atomic_text(run_dir / "FINAL_MORNING_REPORT.md", "\n".join(lines))
    atomic_json({"status": status, "completed_jobs": len(results), "results": results,
                 "independent_test_access": 0}, run_dir / "FINAL_MORNING_REPORT.json")


def write_manifest(run_dir: Path, status: str):
    files = {}
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path.name not in {"RUN_MANIFEST.json", "controller.lock", "STOP_REQUESTED"} and not path.name.endswith(".tmp"):
            files[str(path.relative_to(run_dir))] = sha256(path)
    atomic_json({"status": status, "file_sha256": files,
                 "independent_test_access": 0}, run_dir / "RUN_MANIFEST.json")


def run_experiment(run_dir: Path, *, dry: bool, resume: bool, force_dry_pause: bool | None = None):
    freeze, config, inventory = verify_freeze()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; frozen experiment requires the verified CUDA environment.")
    device = torch.device("cuda:0")
    torch.cuda.set_device(device)
    configure_determinism(int(inventory["dry_run_model_rng_seeds"][0]))
    limits = config["runtime_limits"]
    progress_path = run_dir / "progress.json"
    prior = read_json(progress_path, {}) if resume else {}
    if not resume and progress_path.exists():
        raise RuntimeError("Progress exists; use --resume rather than overwriting run evidence.")
    run_dir.mkdir(parents=True, exist_ok=True)
    if resume and (run_dir / "STOP_REQUESTED").exists():
        (run_dir / "STOP_REQUESTED").unlink()
        log_event(run_dir, {"type": "resume_acknowledged_stop_marker_removed"})
    state = {"status": "running", "active_wall_seconds": float(prior.get("active_wall_seconds", 0)),
             "started_utc": prior.get("started_utc", datetime.now(timezone.utc).isoformat()),
             "sampled_roots": list(prior.get("sampled_roots", [])),
             "completed_jobs": list(prior.get("completed_jobs", [])), "dry_run": bool(dry),
             "independent_test_access": 0, "freeze_sha256": sha256(FREEZE_PATH)}
    atomic_json(state, progress_path)
    store = CheckpointStore(run_dir)
    started = time.perf_counter()
    completed_gpu_previous = 0.0
    for result_file in (run_dir / "job_results").glob("*.json") if (run_dir / "job_results").exists() else []:
        saved = read_json(result_file, {})
        completed_gpu_previous += float(saved.get("gpu_training_seconds", 0))
    current_gpu = [0.0]
    current_root = 0
    envs, coords, fingerprints = prepare_regimes_for_controller(config, inventory, dry=dry)
    atomic_json({"circuits": fingerprints, "detectors": 40, "observables": 1,
                 "noiseless_checks_passed": True, "test_access": 0}, run_dir / "CIRCUIT_VALIDATION.json")

    def resource_guard(*, check_deadline=False):
        snapshot = resource_state(run_dir, device, limits)
        if not snapshot["ok"]:
            raise RuntimeError(f"Resource safety limit crossed: {snapshot}")
        if check_deadline:
            elapsed = float(prior.get("active_wall_seconds", 0)) + time.perf_counter() - started
            if (run_dir / "STOP_REQUESTED").exists() or elapsed >= float(limits["autonomous_wall_seconds"]):
                raise SafePause("Safe stop or wall-time cap reached during deterministic data generation.")
        return snapshot

    for root_i in ([0] if dry else range(int(config["independent_roots"]))):
        current_root = root_i
        resource_guard()
        sample_guard = lambda: resource_guard(check_deadline=True)
        try:
            root_data, root_meta = generate_root(root_i, inventory, envs, run_dir, config, sample_guard) if not dry else generate_dry_root(inventory, envs, run_dir, config, sample_guard)
        except SafePause as exc:
            state["status"] = "paused"
            state["pause_reason"] = str(exc)
            state["active_wall_seconds"] = float(prior.get("active_wall_seconds", 0)) + time.perf_counter() - started
            state["current_root"] = root_i
            atomic_json(state, progress_path)
            aggregate_report(run_dir, config, "PAUSED", str(exc))
            write_manifest(run_dir, "paused")
            return state
        if not dry and root_i not in state["sampled_roots"]:
            state["sampled_roots"].append(root_i)
        atomic_json(state, progress_path)
        digest = sha256(CONFIG_PATH)
        jobs = jobs_for_root(root_i, inventory, config, digest, dry=dry)
        for job in jobs:
            result_path = run_dir / "job_results" / f"{job['job_id']}.json"
            pred_path = run_dir / "predictions" / f"{job['job_id']}.npz"
            selection_path = run_dir / "selections" / f"{job['job_id']}.json"
            if result_path.exists():
                saved = read_json(result_path)
                if saved.get("status") == "completed" and pred_path.exists() and sha256(pred_path) == saved.get("predictions_sha256"):
                    if job["job_id"] not in state["completed_jobs"]:
                        state["completed_jobs"].append(job["job_id"])
                        atomic_json(state, progress_path)
                    continue
                raise RuntimeError(f"Completed result/evidence is inconsistent: {job['job_id']}")
            job["root_id"] = root_i
            job["config_sha256"] = digest
            current_gpu[0] = 0.0
            current_gpu_step = [0]
            last_progress_step = [0]
            invocation_started = time.perf_counter()

            def stop_check():
                state["active_wall_seconds"] = float(prior.get("active_wall_seconds", 0)) + time.perf_counter() - started
                total_gpu = completed_gpu_previous + current_gpu[0]
                state["current_job"] = job["job_id"]
                state["current_root"] = root_i
                state["gpu_training_seconds"] = total_gpu
                snapshot = resource_guard()
                state["resources"] = snapshot
                stop_file = run_dir / "STOP_REQUESTED"
                wall_hit = state["active_wall_seconds"] >= float(limits["autonomous_wall_seconds"])
                gpu_hit = total_gpu >= float(limits["gpu_training_seconds"])
                if stop_file.exists() or wall_hit or gpu_hit:
                    state["status"] = "paused"
                    state["pause_reason"] = ("safe stop requested" if stop_file.exists() else
                                              "wall limit reached" if wall_hit else "GPU-time limit reached")
                    atomic_json(state, progress_path)
                    return True
                if current_gpu_step[0] >= last_progress_step[0] + 10:
                    last_progress_step[0] = current_gpu_step[0]
                    state["last_progress_step"] = current_gpu_step[0]
                    atomic_json(state, progress_path)
                return False

            def on_step(info):
                current_gpu[0] = float(info["gpu_seconds"])
                current_gpu_step[0] = int(info["steps"])
                if info.get("phase") or current_gpu_step[0] % 10 == 0:
                    log_event(run_dir, {"type": "batch_or_eval", "root": root_i, **info,
                                        "gpu_training_seconds_total": completed_gpu_previous + current_gpu[0]})

            train_root_data = {k: v for k, v in root_data.items() if k != "final_development_evaluation"}
            def final_loader(root=root_i, job_selection=selection_path):
                if not job_selection.is_file():
                    raise RuntimeError("Final-development evaluation requested before model/threshold selection was frozen.")
                final_path = ensure_final_evaluation(root, inventory, envs, run_dir, config,
                                                     sample_guard, dry=dry)
                expected = int(config["dry_run"]["final_eval_shots"]) if dry else 10000
                return load_final_evaluation(final_path, config["regimes"], expected)

            def load_checkpoint(jid):
                return store.load(jid)
            def save_checkpoint(jid, payload):
                store.save(jid, payload)

            if force_dry_pause is None:
                pause_after = int(config["dry_run"]["forced_pause_after_batches"]) if dry and not resume else None
            else:
                pause_after = int(config["dry_run"]["forced_pause_after_batches"]) if dry and force_dry_pause else None
            result = fit_job(job, train_root_data, coords, config, device, load_checkpoint,
                             save_checkpoint, stop_check, selection_path, pred_path, final_loader,
                             dry_pause_after=pause_after,
                             progress_callback=on_step)
            if result["status"] == "paused":
                state["status"] = "paused"
                state["pause_reason"] = state.get("pause_reason", "dry-run forced pause" if dry else "fit paused")
                state["active_wall_seconds"] = float(prior.get("active_wall_seconds", 0)) + time.perf_counter() - started
                atomic_json(state, progress_path)
                aggregate_report(run_dir, config, "PAUSED", state["pause_reason"])
                write_manifest(run_dir, "paused")
                return {"status": "paused", "job_id": job["job_id"], "steps": result["steps"]}
            result.update({"job_id": job["job_id"], "model": job["model"],
                           "root_id": root_i, "train_size_per_regime": job["train_size_per_regime"],
                           "predictions_sha256": sha256(pred_path),
                           "elapsed_wall_seconds": time.perf_counter() - invocation_started,
                           "device": str(device), "cuda_device_name": torch.cuda.get_device_name(device)})
            atomic_json(result, result_path)
            state["completed_jobs"].append(job["job_id"])
            completed_gpu_previous += float(result.get("gpu_training_seconds", 0))
            atomic_json(state, progress_path)
            log_event(run_dir, {"type": "job_completed", "job_id": job["job_id"],
                                "gpu_training_seconds": result.get("gpu_training_seconds"),
                                "paired_ler_difference": result.get("paired_ler_difference")})
            resource_guard()
        if dry:
            break
    state["status"] = "completed" if not dry else "dry_run_completed"
    state["active_wall_seconds"] = float(prior.get("active_wall_seconds", 0)) + time.perf_counter() - started
    state["gpu_training_seconds"] = completed_gpu_previous
    atomic_json(state, progress_path)
    aggregate_report(run_dir, config, state["status"])
    write_manifest(run_dir, state["status"])
    return state


def prepare_regimes_for_controller(config: dict, inventory: dict, *, dry=False):
    from structured_training import prepare_regimes
    base_config = {"memory_basis": config["memory_basis"], "distance": config["distance"],
                   "rounds": config["rounds"], "gate_p": config["gate_p"],
                   "measurement_p": config["measurement_p"], "bias_ratio": config["bias_ratio"]}
    # Match the frozen regime order; the shared Phase 2B generator maps each name to categorical Pauli channels.
    from noise_model import REGIMES
    if tuple(REGIMES) != tuple(config["regimes"]):
        raise RuntimeError(f"Frozen regime order {config['regimes']} differs from generator {REGIMES}.")
    # prepare_regimes expects the same fixed distance-3, five-round z-memory pilot configuration.
    seeds = inventory["dry_run_circuit_diagnostic_seeds"] if dry else inventory["circuit_diagnostic_seeds"]
    return prepare_regimes({**base_config, "device": "cuda"}, seeds)


def load_split_from_npz(path: Path, split: str) -> dict:
    assert_allowed_split(split)
    with np.load(path, allow_pickle=False) as z:
        if any("test" in key.lower() for key in z.files):
            raise RuntimeError("Prohibited test evidence found in NPZ archive.")
        out = {}
        prefix = split + "__"
        for key in z.files:
            if key.startswith(prefix):
                _, regime, name = key.split("__")
                out.setdefault(regime, {})[name] = z[key]
    if not out:
        raise RuntimeError(f"Missing saved split {split} in {path}")
    return out


def generate_dry_root(inventory: dict, envs: dict, run_dir: Path, config: dict, resource_guard):
    path = run_dir / "data" / "dry_root_00.npz"
    meta_path = run_dir / "data" / "dry_root_00.json"
    if path.exists() and meta_path.exists():
        try:
            meta = read_json(meta_path)
            if sha256(path) != meta.get("sha256"):
                raise RuntimeError("Dry-run sample archive hash mismatch.")
            data = load_root_data(path)
            for regime in config["regimes"]:
                for split, count in (("train", config["dry_run"]["train_shots"]),
                                     ("monitor", config["dry_run"]["monitor_shots"]),
                                     ("calibration", config["dry_run"]["calibration_shots"]),
                                     ("threshold_selection", config["dry_run"]["threshold_shots"])):
                    if data[split][regime]["detectors"].shape != (int(count), 40):
                        raise RuntimeError(f"Invalid dry-run dimensions for {split}/{regime}.")
            return data, meta
        except Exception as exc:
            quarantine_file(path, run_dir, f"dry root verification failed: {exc}")
            quarantine_file(meta_path, run_dir, f"dry root metadata verification failed: {exc}")
    elif path.exists() or meta_path.exists():
        quarantine_file(path, run_dir, "orphaned dry-run archive; metadata pair missing")
        quarantine_file(meta_path, run_dir, "orphaned dry-run metadata; archive pair missing")
    arrays, meta_splits = {}, {}
    dry_streams = inventory["dry_run_streams"]
    # The small reproducibility run uses all three generating regimes to exercise equal-regime training and evaluation.
    dry_counts = {"train": config["dry_run"]["train_shots"], "monitor": config["dry_run"]["monitor_shots"],
                  "calibration": config["dry_run"]["calibration_shots"],
                  "threshold_selection": config["dry_run"]["threshold_shots"]}
    split_streams = {(s["split"], s["regime"]): s for s in dry_streams}
    for ri, regime in enumerate(config["regimes"]):
        for split in ("train", "monitor", "calibration", "threshold_selection"):
            resource_guard()
            template = split_streams[(split, regime)]
            seed = int(template["seed"])
            stream = {"split": split, "regime": regime, "shots": int(dry_counts[split]),
                      "seeds": list(range(seed, seed + math.ceil(int(dry_counts[split]) / 1024)))}
            block = sample_stream(envs[regime]["circuit"], envs[regime]["matching"], stream, run_dir)
            for name, arr in block.items(): arrays[f"{split}__{regime}__{name}"] = arr
            meta_splits[f"{split}__{regime}"] = {"shots": stream["shots"], "seeds": stream["seeds"]}
    save_npz_atomic(path, arrays)
    meta = {"root_id": 0, "sha256": sha256(path), "splits": meta_splits,
            "dry_run": True, "test_samples_generated_or_accessed": 0}
    atomic_json(meta, meta_path)
    return unpack_root_arrays(arrays), meta


def dry_resume_verification() -> dict:
    """Force-pause and resume one job, then compare with uninterrupted replay."""
    result = run_experiment(DRY_DIR, dry=True, resume=False, force_dry_pause=True)
    if result.get("status") != "paused":
        raise RuntimeError(f"Dry run did not pause at the frozen point: {result}")
    paused_progress = read_json(DRY_DIR / "progress.json")
    if paused_progress.get("status") != "paused":
        raise RuntimeError("Forced pause was not durably recorded.")
    # First invocation deliberately pauses after the frozen two-batch point.
    resumed = run_experiment(DRY_DIR, dry=True, resume=True)
    if resumed.get("status") != "dry_run_completed":
        raise RuntimeError(f"Dry run did not finish after resume: {resumed}")
    job_id = "dry_root00_position_flat_cnn"
    resumed_result = read_json(DRY_DIR / "job_results" / f"{job_id}.json")
    selection = read_json(DRY_DIR / "selections" / f"{job_id}.json")
    predictions_path = DRY_DIR / "predictions" / f"{job_id}.npz"
    # Independently rerun the exact frozen dry job in an isolated reference folder.
    ref_dir = HERE / "dry_run_reference_v4"
    if ref_dir.exists(): shutil.rmtree(ref_dir)
    reference = run_experiment(ref_dir, dry=True, resume=False, force_dry_pause=False)
    if reference.get("status") != "dry_run_completed":
        raise RuntimeError(f"Uninterrupted dry reference failed: {reference}")
    ref_result_path = ref_dir / "job_results" / f"{job_id}.json"
    ref_result = read_json(ref_result_path)
    ref_selection = read_json(ref_dir / "selections" / f"{job_id}.json")
    ref_predictions = ref_dir / "predictions" / f"{job_id}.npz"
    sample_checks = []
    for name in ("dry_root_00.npz", "dry_final_root_00.npz"):
        with np.load(DRY_DIR / "data" / name, allow_pickle=False) as a, \
             np.load(ref_dir / "data" / name, allow_pickle=False) as b:
            sample_checks.append(a.files == b.files and all(np.array_equal(a[k], b[k]) for k in a.files))
    samples_exact = all(sample_checks)
    with np.load(predictions_path, allow_pickle=False) as a, np.load(ref_predictions, allow_pickle=False) as b:
        exact = a.files == b.files and all(np.array_equal(a[k], b[k]) for k in a.files)
    if not samples_exact or not exact or selection["selected_model_state_sha256"] != ref_selection["selected_model_state_sha256"]:
        raise RuntimeError("Resume equivalence failed: checkpoint restore changed selected weights or predictions.")
    # preserve a compact reference hash record; scratch reference arrays are not part of full-run evidence.
    proof = {"status": "PASS", "forced_pause_after_batches": 2, "resume_status": resumed["status"],
             "resumed_steps": resumed_result["steps"], "selection_state_hash_equal": True,
             "sample_arrays_exactly_equal": samples_exact, "prediction_arrays_exactly_equal": exact,
             "resumed_predictions_sha256": sha256(predictions_path),
             "reference_predictions_sha256": sha256(ref_predictions),
             "independent_test_access": 0}
    atomic_json(proof, DRY_PROOF_PATH)
    aggregate_report(DRY_DIR, read_json(CONFIG_PATH), "DRY_RUN_PASS")
    write_manifest(DRY_DIR, "dry_run_pass")
    shutil.rmtree(ref_dir)
    return proof


def request_stop(run_dir: Path):
    run_dir.mkdir(parents=True, exist_ok=True)
    atomic_text(run_dir / "STOP_REQUESTED", "Stop requested by user/controller command.\n")
    print(f"Safe stop requested: {run_dir / 'STOP_REQUESTED'}")


def status(run_dir: Path):
    print(json.dumps({"full_run": read_json(run_dir / "progress.json", {"status": "not started"}),
                      "dry_run": read_json(DRY_DIR / "progress.json", {"status": "not started"})}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare-freeze", action="store_true")
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--full-run", action="store_true")
    group.add_argument("--resume", action="store_true")
    group.add_argument("--stop", action="store_true")
    group.add_argument("--status", action="store_true")
    parser.add_argument("--confirm-full-autonomous", action="store_true")
    args = parser.parse_args()
    if args.prepare_freeze:
        from prepare_freeze import main as freeze_main
        freeze_main()
        return
    if args.stop:
        request_stop(RUN_DIR); request_stop(DRY_DIR); return
    if args.status:
        status(RUN_DIR); return
    if args.full_run or args.resume:
        if not args.confirm_full_autonomous:
            raise SystemExit("Full development execution requires --confirm-full-autonomous. No experiment was started.")
        proof = read_json(DRY_PROOF_PATH, {})
        if proof.get("status") != "PASS" or proof.get("prediction_arrays_exactly_equal") is not True:
            raise SystemExit("A passing dry-run pause/resume equivalence proof is required before any full run.")
    run_dir = DRY_DIR if args.dry_run else RUN_DIR
    if args.resume and not (run_dir / "progress.json").is_file():
        raise SystemExit("No resumable run exists.")
    lock = RunLock(run_dir)
    lock.acquire()
    try:
        if args.dry_run:
            print(json.dumps(dry_resume_verification(), indent=2))
        else:
            outcome = run_experiment(run_dir, dry=False, resume=args.resume)
            print(json.dumps(outcome, indent=2))
    except KeyboardInterrupt:
        state = read_json(run_dir / "progress.json", {})
        state["status"] = "interrupted_at_safe_boundary"
        atomic_json(state, run_dir / "progress.json")
        aggregate_report(run_dir, read_json(CONFIG_PATH), "INTERRUPTED", "Keyboard interrupt received; resume with the frozen command.")
        print("Interrupted at a safe training checkpoint; use --resume --confirm-full-autonomous.")
    except Exception as exc:
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        log_event(run_dir, {"type": "failure", "error": str(exc), "traceback": detail})
        state = read_json(run_dir / "progress.json", {})
        state.update({"status": "failed", "failure": str(exc), "traceback": detail})
        atomic_json(state, run_dir / "progress.json")
        aggregate_report(run_dir, read_json(CONFIG_PATH), "FAILED", detail)
        try:
            write_manifest(run_dir, "failed")
        except Exception:
            pass
        raise
    finally:
        lock.release()


if __name__ == "__main__":
    main()
