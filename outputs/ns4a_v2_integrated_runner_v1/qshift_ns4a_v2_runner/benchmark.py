"""Separately authorized, tightly bounded NS-4A runtime benchmark.

The current readiness task never creates a benchmark permit, seed inventory,
or approval record. Importing this module cannot reach a Stim sampler.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any, Mapping

import numpy as np

from qshift_ns4a_v2_deterministic.protocol import CANDIDATE_IDS, CONDITIONS, EVALUATION_ARMS
from .integrity import sha256_file, verify_source_manifest
from .models import build_evaluation_bank, build_model_catalog, evaluation_decoder_views


BENCHMARK_PROTOCOL_SCHEMA = "qshift-ns4a-v2-benchmark-protocol-v1"
BENCHMARK_NAMESPACE = "qshift-ns4a-v2-execution-readiness-benchmark-v1"
BENCHMARK_AUTHORIZATION_STATEMENT = (
    "I, realguy-beep, explicitly authorize only the bounded NS-4A V2 execution-readiness benchmark "
    "bound to its exact protocol, source manifest, and benchmark-only seed inventory."
)
_BENCHMARK_NONCE = object()
_PLAN_DIR = Path(__file__).resolve().parents[2] / "ns4a_v2_final_readiness_v1"
_BENCHMARK_OUTPUT_ROOT = _PLAN_DIR / "benchmark_runs"


class BenchmarkError(RuntimeError):
    """Bounded benchmark authorization, integrity, or resource failure."""


@dataclass(frozen=True)
class _BenchmarkPermit:
    protocol: Mapping[str, Any]
    inventory: Mapping[str, Any]
    seeds: Mapping[str, int]
    benchmark_id: str
    protocol_sha256: str
    inventory_sha256: str
    source_manifest_sha256: str
    nonce: object


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"


def _load_json(path: str | Path, label: str) -> tuple[dict[str, Any], str]:
    target = Path(path)
    try:
        raw = target.read_bytes()
        value = json.loads(raw)
    except Exception as exc:
        raise BenchmarkError(f"{label} is missing or malformed.") from exc
    if not isinstance(value, dict):
        raise BenchmarkError(f"{label} must be a JSON object.")
    return value, hashlib.sha256(raw).hexdigest()


def _validate_protocol(protocol: Mapping[str, Any]) -> None:
    caps = protocol.get("hard_limits", {})
    expected = {
        "schema": BENCHMARK_PROTOCOL_SCHEMA,
        "namespace": BENCHMARK_NAMESPACE,
        "shots_per_condition": 1_000,
        "maximum_total_shots": 6_000,
    }
    for field, value in expected.items():
        if protocol.get(field) != value:
            raise BenchmarkError(f"bounded benchmark protocol field {field!r} changed.")
    if tuple(protocol.get("conditions", ())) != CONDITIONS:
        raise BenchmarkError("benchmark condition order differs from the frozen six-condition roster.")
    if sum(protocol["shots_per_condition"] for _ in protocol["conditions"]) != protocol["maximum_total_shots"]:
        raise BenchmarkError("benchmark shot arithmetic exceeds or differs from the declared cap.")
    if caps != {
        "sampler_calls": 6,
        "maximum_sampler_shots_per_call": 1_000,
        "candidate_decoders": 12,
        "evaluation_arms": 5,
        "sampler_returns_observables": False,
        "maximum_wall_clock_seconds": 600,
        "maximum_peak_working_set_bytes": 1_073_741_824,
        "minimum_free_disk_bytes": 1_073_741_824,
        "maximum_output_bytes": 134_217_728,
    }:
        raise BenchmarkError("benchmark pipeline/cap configuration differs from the reviewed plan.")


def _parse_utc(value: Any, label: str) -> float:
    from datetime import datetime, timezone

    if not isinstance(value, str) or not value.endswith("Z"):
        raise BenchmarkError(f"{label} must be an explicit UTC timestamp ending in Z.")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc).timestamp()
    except ValueError as exc:
        raise BenchmarkError(f"{label} is not a valid UTC timestamp.") from exc


def _authorize_benchmark(
    *, protocol_path: str | Path,
    seed_inventory_path: str | Path,
    authorization_path: str | Path,
    source_manifest_path: str | Path,
    reserved_seed_values: set[int] | frozenset[int] | None,
) -> _BenchmarkPermit:
    if Path(protocol_path).resolve() != (_PLAN_DIR / "BENCHMARK_PROTOCOL.json").resolve():
        raise BenchmarkError("benchmark protocol must be the reviewed versioned protocol file.")
    if Path(source_manifest_path).resolve() != (_PLAN_DIR / "SOURCE_HASH_MANIFEST_V4.json").resolve():
        raise BenchmarkError("benchmark source manifest must be the final reviewed V4 manifest.")
    if (Path(seed_inventory_path).resolve().parent != _PLAN_DIR.resolve()
            or Path(seed_inventory_path).name != "BENCHMARK_SEED_INVENTORY_V1.json"):
        raise BenchmarkError("benchmark inventory must be a new separate V1 inventory; template values cannot authorize sampling.")
    if (Path(authorization_path).resolve().parent != _PLAN_DIR.resolve()
            or Path(authorization_path).name != "BENCHMARK_OWNER_APPROVAL_V1.json"):
        raise BenchmarkError("benchmark approval must be provided at the reviewed versioned approval path.")
    protocol, protocol_sha = _load_json(protocol_path, "benchmark protocol")
    _validate_protocol(protocol)
    inventory, inventory_sha = _load_json(seed_inventory_path, "benchmark seed inventory")
    authorization, _ = _load_json(authorization_path, "owner benchmark authorization")
    source_manifest, source_manifest_sha = _load_json(source_manifest_path, "V3 source manifest")
    source_record = verify_source_manifest(source_manifest_path, repository_root=Path(__file__).resolve().parents[3])
    if source_record["manifest_sha256"] != source_manifest_sha:
        raise BenchmarkError("source manifest changed during authorization validation.")
    source_rows = {row.get("path"): row.get("sha256") for row in source_manifest.get("files", []) if isinstance(row, dict)}
    expected_protocol_relative = "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_PROTOCOL.json"
    expected_module_relative = "outputs/ns4a_v2_integrated_runner_v1/qshift_ns4a_v2_runner/benchmark.py"
    if (source_manifest.get("schema") != "qshift-ns4a-v2-source-manifest-v1"
            or source_manifest.get("readiness_revision") != "NS-4A V2 final-readiness V4"
            or source_rows.get(expected_protocol_relative) != protocol_sha
            or source_rows.get(expected_module_relative) != sha256_file(__file__)
            or source_manifest.get("sampling_authorized") is not False):
        raise BenchmarkError("benchmark plan or executable differs from the reviewed immutable source manifest.")
    if reserved_seed_values is None:
        raise BenchmarkError("collision screen is incomplete: explicitly allowlisted reserved-seed metadata was not supplied.")
    if inventory.get("schema") != "qshift-ns4a-v2-benchmark-seed-inventory-v1":
        raise BenchmarkError("benchmark seed inventory schema is invalid.")
    if inventory.get("namespace") != BENCHMARK_NAMESPACE:
        raise BenchmarkError("benchmark seed namespace is not disjointly named.")
    if (inventory.get("scientific_seed_allocation") is not False
            or inventory.get("numeric_seeds_allocated") is not True
            or inventory.get("sampling_authorized") is not False):
        raise BenchmarkError("benchmark inventory must not contain or alias scientific seed allocation.")
    seeds = inventory.get("seed_by_condition")
    if not isinstance(seeds, dict) or set(seeds) != set(CONDITIONS):
        raise BenchmarkError("benchmark inventory must cover all six conditions exactly once.")
    if any(type(seed) is not int or not 0 <= seed <= 2**63 - 1 for seed in seeds.values()):
        raise BenchmarkError("benchmark seed inventory is unallocated or contains invalid seeds.")
    if len(set(seeds.values())) != 6 or set(seeds.values()) & set(reserved_seed_values):
        raise BenchmarkError("benchmark seeds collide with each other or the approved reserved-seed metadata.")
    if any(type(seed) is not int or not 0 <= seed <= 2**63 - 1 for seed in reserved_seed_values):
        raise BenchmarkError("approved reserved-seed metadata contains invalid or ambiguous seed values.")
    if authorization.get("schema") != "qshift-ns4a-v2-benchmark-authorization-v1":
        raise BenchmarkError("owner benchmark authorization schema is invalid.")
    if (authorization.get("owner_id") != "realguy-beep"
            or authorization.get("scope") != "bounded_benchmark_only"
            or authorization.get("approval_statement") != BENCHMARK_AUTHORIZATION_STATEMENT
            or authorization.get("sampling_authorized") is not True
            or authorization.get("protocol_sha256") != protocol_sha
            or authorization.get("seed_inventory_sha256") != inventory_sha
            or authorization.get("source_manifest_sha256") != source_manifest_sha):
        raise BenchmarkError("owner authorization does not match benchmark scope and immutable input hashes.")
    now = time.time()
    created = _parse_utc(authorization.get("created_utc"), "authorization created_utc")
    expires = _parse_utc(authorization.get("expires_utc"), "authorization expires_utc")
    if not created <= now <= expires or expires - created > 86_400:
        raise BenchmarkError("benchmark authorization is expired, future-dated, or exceeds the 24-hour validity bound.")
    benchmark_id = hashlib.sha256((protocol_sha + inventory_sha + source_manifest_sha).encode()).hexdigest()[:16]
    return _BenchmarkPermit(protocol, inventory, dict(seeds), benchmark_id, protocol_sha,
                            inventory_sha, source_manifest_sha, _BENCHMARK_NONCE)


def _peak_working_set_bytes() -> int:
    """Return OS high-water process memory; fail closed if unavailable."""
    if not hasattr(os, "name") or os.name != "nt":
        raise BenchmarkError("this bounded benchmark requires Windows process peak-working-set measurement.")
    import ctypes
    from ctypes import wintypes

    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(counters)
    process = ctypes.windll.kernel32.GetCurrentProcess()
    if not ctypes.windll.psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb):
        raise BenchmarkError("Windows process peak-working-set measurement failed.")
    return int(counters.PeakWorkingSetSize)


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    if path.exists():
        raise BenchmarkError(f"benchmark artifact already exists; refusing overwrite: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=path.name + ".partial-", delete=False) as stream:
            temp_path = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def write_detector_archive(path: str | Path, *, condition: str, detectors: np.ndarray,
                           candidate_predictions: np.ndarray, evaluation_predictions: np.ndarray,
                           benchmark_seed_ref: str,
                           sampling_identity_sha256: str, evaluation_identity_sha256_by_arm: Mapping[str, str]) -> dict[str, Any]:
    """Persist detector-only benchmark arrays; no observable labels are accepted."""
    target = Path(path)
    det = np.asarray(detectors)
    candidate = np.asarray(candidate_predictions)
    evaluation = np.asarray(evaluation_predictions)
    if (condition not in CONDITIONS or det.dtype != np.uint8 or det.ndim != 2
            or det.shape[1] != 40 or np.any(det > 1)):
        raise BenchmarkError("benchmark detector fixture violates binary [shots,40] schema.")
    shots = len(det)
    if (candidate.dtype != np.uint8 or candidate.shape != (12, shots, 1) or np.any(candidate > 1)
            or evaluation.dtype != np.uint8 or evaluation.shape != (5, shots, 1) or np.any(evaluation > 1)):
        raise BenchmarkError("benchmark decoder predictions violate frozen candidate/arm schemas.")
    if tuple(evaluation_identity_sha256_by_arm) != EVALUATION_ARMS:
        raise BenchmarkError("benchmark evaluation model identities are incomplete or out of order.")
    if (not isinstance(benchmark_seed_ref, str) or not benchmark_seed_ref
            or len(sampling_identity_sha256) != 64
            or any(len(v) != 64 for v in evaluation_identity_sha256_by_arm.values())):
        raise BenchmarkError("benchmark model/sampling identity digests are malformed.")
    sample_ids = np.asarray([f"benchmark|{condition}|{i:04d}" for i in range(shots)], dtype="U")
    metadata = {
        "schema": "qshift-ns4a-v2-benchmark-detector-archive-v1",
        "condition_id": condition,
        "shots": shots,
        "candidate_ids": list(CANDIDATE_IDS),
        "evaluation_arms": list(EVALUATION_ARMS),
        "sampling_identity_sha256": sampling_identity_sha256,
        "evaluation_identity_sha256_by_arm": dict(evaluation_identity_sha256_by_arm),
        "benchmark_seed_ref": benchmark_seed_ref,
        "labels_saved": False,
        "sample_id_sha256": hashlib.sha256("\n".join(sample_ids.tolist()).encode()).hexdigest(),
    }
    temp = target.with_name(target.name + f".partial-{os.getpid()}")
    if target.exists() or temp.exists():
        raise BenchmarkError("benchmark archive path already exists or has an interrupted partial write.")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with temp.open("xb") as stream:
            np.savez_compressed(
                stream, detectors=det, candidate_predictions=candidate,
                evaluation_predictions=evaluation, sample_ids=sample_ids,
                metadata_json=np.asarray(json.dumps(metadata, sort_keys=True, separators=(",", ":"))),
            )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()
    digest = sha256_file(target)
    marker = {"schema": "qshift-ns4a-v2-benchmark-commit-v1", "archive": target.name,
              "archive_sha256": digest, "metadata": metadata}
    marker_path = target.with_suffix(".commit.json")
    _atomic_write_bytes(marker_path, _canonical_bytes(marker))
    return {"archive_sha256": digest, "archive_path": str(target), "commit_marker_sha256": sha256_file(marker_path),
            "bytes": target.stat().st_size, "shots": shots}


def verify_detector_archive(path: str | Path) -> dict[str, Any]:
    """Recovery-time verifier for committed detector-only benchmark archives."""
    target = Path(path)
    marker_path = target.with_suffix(".commit.json")
    if not target.is_file() or not marker_path.is_file():
        raise BenchmarkError("benchmark archive/commit marker is incomplete; no automatic resampling is allowed.")
    digest = sha256_file(target)
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        with np.load(target, allow_pickle=False) as data:
            if set(data.files) != {"detectors", "candidate_predictions", "evaluation_predictions", "sample_ids", "metadata_json"}:
                raise BenchmarkError("benchmark archive keys differ from the detector-only contract.")
            det = np.asarray(data["detectors"])
            candidates = np.asarray(data["candidate_predictions"])
            evaluation = np.asarray(data["evaluation_predictions"])
            ids = np.asarray(data["sample_ids"])
            metadata = json.loads(str(np.asarray(data["metadata_json"]).item()))
    except BenchmarkError:
        raise
    except Exception as exc:
        raise BenchmarkError("benchmark archive or commit marker is unreadable.") from exc
    shots = int(metadata.get("shots", -1))
    if (marker.get("schema") != "qshift-ns4a-v2-benchmark-commit-v1"
            or marker.get("archive") != target.name or marker.get("archive_sha256") != digest
            or marker.get("metadata") != metadata or metadata.get("labels_saved") is not False
            or not isinstance(metadata.get("benchmark_seed_ref"), str) or not metadata["benchmark_seed_ref"]
            or det.dtype != np.uint8 or det.shape != (shots, 40) or np.any(det > 1)
            or candidates.dtype != np.uint8 or candidates.shape != (12, shots, 1) or np.any(candidates > 1)
            or evaluation.dtype != np.uint8 or evaluation.shape != (5, shots, 1) or np.any(evaluation > 1)
            or ids.shape != (shots,) or ids.dtype.kind != "U"
            or hashlib.sha256("\n".join(ids.tolist()).encode()).hexdigest() != metadata.get("sample_id_sha256")):
        raise BenchmarkError("benchmark archive content/identity differs from its verified marker.")
    return {"archive_sha256": digest, "shots": shots, "bytes": target.stat().st_size, "labels_saved": False}


def run_authorized_benchmark(*, repository_root: str | Path, protocol_path: str | Path,
                             seed_inventory_path: str | Path, authorization_path: str | Path,
                             source_manifest_path: str | Path,
                             reserved_seed_values: set[int] | frozenset[int] | None) -> dict[str, Any]:
    """Execute the 6,000-shot resource benchmark only with a scoped owner token.

    This function is intentionally not called by tests or the deterministic
    rehearsal. It never stores labels or computes logical-error metrics.
    """
    permit = _authorize_benchmark(
        protocol_path=protocol_path, seed_inventory_path=seed_inventory_path,
        authorization_path=authorization_path, source_manifest_path=source_manifest_path,
        reserved_seed_values=reserved_seed_values,
    )
    if permit.nonce is not _BENCHMARK_NONCE:
        raise BenchmarkError("benchmark permit is invalid.")
    root = Path(repository_root).resolve()
    output_root = _BENCHMARK_OUTPUT_ROOT.resolve()
    if root not in output_root.parents:
        raise BenchmarkError("benchmark output root is outside repository scope.")
    run_dir = output_root / permit.benchmark_id
    run_dir.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    limits = permit.protocol["hard_limits"]
    free_disk_at_start = shutil.disk_usage(run_dir).free
    if free_disk_at_start < limits["minimum_free_disk_bytes"]:
        raise BenchmarkError("benchmark stopped: required free-disk reserve is unavailable.")
    def check(phase: str) -> None:
        elapsed = time.monotonic() - start
        rss = _peak_working_set_bytes()
        free_disk = shutil.disk_usage(run_dir).free
        if elapsed > limits["maximum_wall_clock_seconds"]:
            raise BenchmarkError(f"benchmark wall-clock cap exceeded during {phase}.")
        if rss > limits["maximum_peak_working_set_bytes"]:
            raise BenchmarkError(f"benchmark peak process memory cap exceeded during {phase}: {rss}.")
        if free_disk < limits["minimum_free_disk_bytes"]:
            raise BenchmarkError(f"benchmark free-disk reserve violated during {phase}.")
        if sum(p.stat().st_size for p in run_dir.rglob("*") if p.is_file()) > limits["maximum_output_bytes"]:
            raise BenchmarkError("benchmark output-byte cap exceeded.")

    check("preflight")
    model_start = time.perf_counter()
    catalog = build_model_catalog()
    model_construction_seconds = time.perf_counter() - model_start
    check("model-construction")
    import stim

    timings: dict[str, Any] = {"stim_sampler_compile_seconds": {}, "stim_generation_seconds": {}, "candidate_decode_seconds": {},
                               "evaluation_decode_seconds": {}, "archive_write_seconds": {},
                               "archive_recovery_verify_seconds": {}}
    archive_records: list[dict[str, Any]] = []
    bank_construction_seconds: dict[str, float] = {}
    for condition in CONDITIONS:
        check(f"before-stim:{condition}")
        condition_model = catalog.conditions[condition]
        seed = permit.seeds[condition]
        tic = time.perf_counter()
        sampler = condition_model.circuit.compile_detector_sampler(seed=seed)
        timings["stim_sampler_compile_seconds"][condition] = time.perf_counter() - tic
        tic = time.perf_counter()
        detectors = np.asarray(sampler.sample(shots=1_000, separate_observables=False), dtype=np.uint8)
        timings["stim_generation_seconds"][condition] = time.perf_counter() - tic
        if detectors.shape != (1_000, 40) or np.any(detectors > 1):
            raise BenchmarkError("Stim detector-only benchmark output violates [1000,40] binary shape.")
        check(f"stim-generation:{condition}")
        candidate_predictions = np.empty((12, 1_000, 1), dtype=np.uint8)
        for index, candidate_id in enumerate(CANDIDATE_IDS):
            tic = time.perf_counter()
            prediction = catalog.selection_decoders[candidate_id].decode(detectors)
            timings["candidate_decode_seconds"].setdefault(candidate_id, 0.0)
            timings["candidate_decode_seconds"][candidate_id] += time.perf_counter() - tic
            if (not isinstance(prediction.bits, np.ndarray) or prediction.bits.dtype != np.uint8
                    or prediction.bits.shape != (1_000, 1) or np.any(prediction.bits > 1)):
                raise BenchmarkError(f"candidate {candidate_id} returned invalid benchmark predictions.")
            candidate_predictions[index] = prediction.bits
            check(f"candidate-decoding:{candidate_id}")
        bank_start = time.perf_counter()
        bank, registration = build_evaluation_bank(catalog, condition, "balanced_no_burst::ordinary_pymatching")
        bank_construction_seconds[condition] = time.perf_counter() - bank_start
        try:
            views = evaluation_decoder_views(bank, condition_model.circuit)
            evaluation_predictions = np.empty((5, 1_000, 1), dtype=np.uint8)
            for arm_index, arm in enumerate(EVALUATION_ARMS):
                tic = time.perf_counter()
                result = views[arm].decode(detectors)
                timings["evaluation_decode_seconds"].setdefault(arm, 0.0)
                timings["evaluation_decode_seconds"][arm] += time.perf_counter() - tic
                if (not isinstance(result.bits, np.ndarray) or result.bits.dtype != np.uint8
                        or result.bits.shape != (1_000, 1) or np.any(result.bits > 1)):
                    raise BenchmarkError(f"evaluation arm {arm} returned invalid benchmark predictions.")
                evaluation_predictions[arm_index] = result.bits
                check(f"evaluation-decoding:{arm}")
            from .models import evaluation_model_identity_map

            identity_map = evaluation_model_identity_map(bank)
            archive_path = run_dir / f"{condition}.npz"
            tic = time.perf_counter()
            record = write_detector_archive(
                archive_path, condition=condition, detectors=detectors,
                candidate_predictions=candidate_predictions,
                evaluation_predictions=evaluation_predictions,
                benchmark_seed_ref=f"benchmark-inventory:{sha256_file(seed_inventory_path)}:{condition}",
                sampling_identity_sha256=condition_model.sampling_identity.identity_sha256,
                evaluation_identity_sha256_by_arm=identity_map,
            )
            timings["archive_write_seconds"][condition] = time.perf_counter() - tic
            archive_records.append(record)
            check(f"archive:{condition}")
        finally:
            registration.adapter.close()

    recovery_start = time.perf_counter()
    recovery = [verify_detector_archive(run_dir / f"{condition}.npz") for condition in CONDITIONS]
    recovery_seconds = time.perf_counter() - recovery_start
    check("recovery-verification")
    for condition, record in zip(CONDITIONS, recovery):
        timings["archive_recovery_verify_seconds"][condition] = recovery_seconds / len(CONDITIONS)
        if record["archive_sha256"] != next(r["archive_sha256"] for r in archive_records if r["archive_path"].endswith(f"{condition}.npz")):
            raise BenchmarkError("recovery verification changed benchmark archive identity.")
    total_output_bytes = sum(p.stat().st_size for p in run_dir.rglob("*") if p.is_file())
    if total_output_bytes > limits["maximum_output_bytes"]:
        raise BenchmarkError("benchmark output exceeds hard output cap.")
    pipeline_wall_seconds = time.monotonic() - start
    report = {
        "schema": "qshift-ns4a-v2-benchmark-results-v1",
        "benchmark_id": permit.benchmark_id,
        "benchmark_protocol_sha256": permit.protocol_sha256,
        "benchmark_seed_inventory_sha256": permit.inventory_sha256,
        "source_manifest_sha256": permit.source_manifest_sha256,
        "sampling_authorized_scope": "bounded execution-readiness benchmark only",
        "scientific_pilot": False,
        "logical_labels_saved": False,
        "logical_error_metrics_computed": False,
        "stim_shots": 6_000,
        "stim_sampler_calls": 6,
        "model_construction_seconds": model_construction_seconds,
        "evaluation_bank_construction_seconds": bank_construction_seconds,
        "timings": timings,
        "archive_records": archive_records,
        "recovery_verified_archives": len(recovery),
        "recovery_verification_seconds_total": recovery_seconds,
        "total_wall_seconds_through_archive_audit": pipeline_wall_seconds,
        "detector_shots_per_second_including_construction_and_io": 6_000 / pipeline_wall_seconds,
        "peak_working_set_bytes": _peak_working_set_bytes(),
        "archive_and_marker_bytes_excluding_report": total_output_bytes,
        "free_disk_bytes_at_start": free_disk_at_start,
        "free_disk_bytes_after_archives": shutil.disk_usage(run_dir).free,
        "benchmark_seeds_are_development_only": True,
        "independent_test_access": False,
    }
    report_path = run_dir / "BENCHMARK_REPORT.json"
    _atomic_write_bytes(report_path, json.dumps(report, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n")
    check("final-report-write")
    return report


def validate_fixture_limits(protocol: Mapping[str, Any]) -> dict[str, int]:
    """Sampler-free validation of the same benchmark caps used at runtime."""
    _validate_protocol(protocol)
    return {"maximum_total_shots": protocol["maximum_total_shots"],
            "maximum_wall_clock_seconds": protocol["hard_limits"]["maximum_wall_clock_seconds"],
            "maximum_output_bytes": protocol["hard_limits"]["maximum_output_bytes"]}

