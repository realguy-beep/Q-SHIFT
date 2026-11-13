"""Fail-closed run state, immutable selection freeze, and root transactions."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import time
import uuid
from fractions import Fraction
from typing import Any, Iterator, Mapping

from qshift_ns4a_v2_deterministic.checkpoint import (
    CheckpointError, atomic_write_json, root_commit_marker,
    validate_checkpoint_payload, validate_resume_state,
)
from qshift_ns4a_v2_deterministic.audit_saved_arrays import audit_saved_arrays
from qshift_ns4a_v2_deterministic.protocol import CANDIDATE_IDS, CONDITIONS, make_root_id, shots_for_root

from .archive_store import archive_path, read_and_verify_commit


class RunStateError(RuntimeError):
    """Run state cannot be advanced or recovered without ambiguity."""


class RunDirectoryLock:
    """Exclusive lock; stale ownership is never auto-stolen."""

    def __init__(self, run_directory: str | Path):
        self.run_directory = Path(run_directory)
        self.path = self.run_directory / ".ns4a-v2-run.lock"
        self.token = f"{os.getpid()}:{uuid.uuid4().hex}"
        self.held = False

    def acquire(self) -> None:
        self.run_directory.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise RunStateError("run lock exists; fail closed without stale-lock takeover.") from exc
        with os.fdopen(fd, "w", encoding="ascii", newline="\n") as stream:
            stream.write(self.token)
            stream.flush()
            os.fsync(stream.fileno())
        self.held = True

    def release(self) -> None:
        if not self.held:
            return
        try:
            actual = self.path.read_text(encoding="ascii")
        except FileNotFoundError as exc:
            self.held = False
            raise RunStateError("owned run lock disappeared; ownership is ambiguous.") from exc
        if actual != self.token:
            self.held = False
            raise RunStateError("run lock ownership token changed; refusing to unlink another process lock.")
        self.path.unlink()
        self.held = False

    def __enter__(self) -> "RunDirectoryLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


class RunStateStore:
    def __init__(self, run_directory: str | Path, *, protocol_sha256: str, source_manifest_sha256: str,
                 fixture_mode: bool = False,
                 execution_manifest_sha256: str | None = None,
                 seed_inventory_sha256: str | None = None,
                 wall_clock_seconds: float = 1_800.0,
                 epoch_clock=time.time):
        self.root = Path(run_directory)
        self.root.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path = self.root / "checkpoint.json"
        self.selection_path = self.root / "selection_winner.json"
        self.protocol_sha256 = protocol_sha256
        self.source_manifest_sha256 = source_manifest_sha256
        self.fixture_mode = fixture_mode
        self.execution_manifest_sha256 = execution_manifest_sha256
        self.seed_inventory_sha256 = seed_inventory_sha256
        self.wall_clock_seconds = float(wall_clock_seconds)
        self.epoch_clock = epoch_clock
        self._last_hash: str | None = None
        self._verified_selection_sha256: str | None = None

    @staticmethod
    def _digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def initialize(self) -> None:
        if self.checkpoint_path.exists():
            raise RunStateError("run checkpoint already exists; refusing initialization overwrite.")
        now = float(self.epoch_clock())
        if not self.fixture_mode and (not self.execution_manifest_sha256 or not self.seed_inventory_sha256):
            raise RunStateError("production checkpoint must bind execution-manifest and seed-inventory hashes.")
        payload = {
            "schema": "qshift-ns4a-v2-checkpoint-v1",
            "state": "in_progress",
            "protocol_sha256": self.protocol_sha256,
            "source_manifest_sha256": self.source_manifest_sha256,
            "committed_roots": [],
            "in_flight_root": None,
            "selection_frozen": False,
            "selected_candidate": None,
            "selection_freeze_sha256": None,
            "independent_audit_verified": False,
            "independent_audit_sha256": None,
            "execution_manifest_sha256": self.execution_manifest_sha256 or self.protocol_sha256,
            "seed_inventory_sha256": self.seed_inventory_sha256 or self.source_manifest_sha256,
            "run_started_epoch_utc": now,
            "run_deadline_epoch_utc": now + self.wall_clock_seconds,
            "fixture_mode": self.fixture_mode,
        }
        self._validate_payload(payload)
        self._last_hash = atomic_write_json(self.checkpoint_path, payload)

    def read(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RunStateError("checkpoint is missing or malformed.") from exc
        self._validate_payload(payload)
        if (payload.get("protocol_sha256") != self.protocol_sha256
                or payload.get("source_manifest_sha256") != self.source_manifest_sha256
                or payload.get("execution_manifest_sha256") != (self.execution_manifest_sha256 or self.protocol_sha256)
                or payload.get("seed_inventory_sha256") != (self.seed_inventory_sha256 or self.source_manifest_sha256)):
            raise RunStateError("checkpoint protocol/source/manifest/seed identity differs from the current run binding.")
        actual = self._digest(self.checkpoint_path)
        if self._last_hash is not None and self._last_hash != actual:
            raise RunStateError("checkpoint changed outside the active run-state writer.")
        self._last_hash = actual
        return payload

    def _validate_payload(self, payload: Mapping[str, Any]) -> None:
        try:
            validate_checkpoint_payload(payload)
        except Exception as exc:
            raise RunStateError(f"checkpoint schema validation failed: {exc}") from exc
        if not isinstance(payload.get("fixture_mode"), bool):
            raise RunStateError("checkpoint fixture_mode must be an explicit boolean.")
        for field in ("execution_manifest_sha256", "seed_inventory_sha256"):
            value = payload.get(field)
            if (not isinstance(value, str) or len(value) != 64
                    or any(ch not in "0123456789abcdef" for ch in value)):
                raise RunStateError(f"checkpoint {field} is missing or malformed.")
        started, deadline = payload.get("run_started_epoch_utc"), payload.get("run_deadline_epoch_utc")
        if (isinstance(started, bool) or not isinstance(started, (int, float))
                or isinstance(deadline, bool) or not isinstance(deadline, (int, float))
                or not started < deadline):
            raise RunStateError("checkpoint persisted deadline is missing or malformed.")

        frozen = payload.get("selection_frozen")
        selected = payload.get("selected_candidate")
        selection_hash = payload.get("selection_freeze_sha256")
        if type(frozen) is not bool:
            raise RunStateError("checkpoint selection_frozen must be an explicit boolean.")
        if frozen:
            if selected not in CANDIDATE_IDS or not self._valid_sha256(selection_hash):
                raise RunStateError("frozen selection must name a frozen-grid candidate and file digest.")
        elif selected is not None or selection_hash is not None:
            raise RunStateError("unfrozen selection cannot contain a selected candidate or freeze digest.")

        audit_verified = payload.get("independent_audit_verified")
        audit_hash = payload.get("independent_audit_sha256")
        if type(audit_verified) is not bool:
            raise RunStateError("checkpoint independent_audit_verified must be an explicit boolean.")
        if audit_verified != (audit_hash is not None) or (audit_hash is not None and not self._valid_sha256(audit_hash)):
            raise RunStateError("checkpoint independent-audit flag and digest disagree.")

        committed = payload.get("committed_roots", [])
        numeric_seeds: set[int] = set()
        root_seed_refs: set[str] = set()
        for row in committed:
            seed = row.get("seed")
            if seed is None:
                if not payload["fixture_mode"]:
                    raise RunStateError("production committed roots must retain their exact numeric seed.")
            elif type(seed) is not int or seed < 0 or seed > 2**63 - 1 or seed in numeric_seeds:
                raise RunStateError("committed root seed is invalid or duplicated.")
            else:
                numeric_seeds.add(seed)
            seed_ref = row.get("root_seed_ref")
            if not isinstance(seed_ref, str) or not seed_ref or seed_ref in root_seed_refs:
                raise RunStateError("committed root seed reference is missing or duplicated.")
            root_seed_refs.add(seed_ref)

        inflight = payload.get("in_flight_root")
        if inflight is not None:
            if payload.get("state") != "in_progress" or not isinstance(inflight, Mapping):
                raise RunStateError("in-flight root is only valid in an in-progress checkpoint.")
            try:
                root_id = make_root_id(inflight.get("partition"), inflight.get("condition_id"), int(inflight.get("root_id", "")[-2:]))
                expected_shots = shots_for_root(inflight["partition"], inflight["condition_id"], int(root_id[-2:]))
            except Exception as exc:
                raise RunStateError("in-flight root identity is malformed.") from exc
            if (inflight.get("root_id") != root_id or inflight.get("shots") != expected_shots
                    or not isinstance(inflight.get("root_seed_ref"), str) or not inflight["root_seed_ref"]):
                raise RunStateError("in-flight root does not match the frozen root/shot identity.")
            seed = inflight.get("seed")
            if ((seed is None and not payload["fixture_mode"])
                    or (seed is not None and (type(seed) is not int or seed < 0 or seed > 2**63 - 1))
                    or seed in numeric_seeds or inflight["root_seed_ref"] in root_seed_refs):
                raise RunStateError("in-flight seed or seed reference is invalid or already committed.")

    @staticmethod
    def _valid_sha256(value: Any) -> bool:
        return (isinstance(value, str) and len(value) == 64
                and all(ch in "0123456789abcdef" for ch in value))

    def remaining_wall_clock_seconds(self) -> float:
        payload = self.read()
        started = payload.get("run_started_epoch_utc")
        deadline = payload.get("run_deadline_epoch_utc")
        if (isinstance(started, bool) or not isinstance(started, (int, float))
                or isinstance(deadline, bool) or not isinstance(deadline, (int, float))
                or not started < deadline):
            raise RunStateError("persisted wall-clock deadline is absent or malformed.")
        now = float(self.epoch_clock())
        if now < started:
            raise RunStateError("system clock moved before the persisted run start; deadline check is ambiguous.")
        remaining = float(deadline - now)
        if remaining <= 0:
            raise RunStateError("persisted wall-clock execution deadline has expired.")
        return remaining

    def _write(self, payload: Mapping[str, Any]) -> None:
        self._validate_payload(payload)
        previous = self._last_hash
        try:
            digest = atomic_write_json(self.checkpoint_path, payload, expected_previous_sha256=previous)
        except CheckpointError as exc:
            raise RunStateError(f"checkpoint compare-and-swap failed: {exc}") from exc
        self._last_hash = digest

    def begin_root(self, *, partition: str, condition_id: str, root_index: int,
                   shots: int, seed: int | None, root_seed_ref: str) -> dict[str, Any]:
        payload = self.read()
        if payload["state"] not in {"in_progress", "paused"} or payload.get("in_flight_root") is not None:
            raise RunStateError("run is not at a safe root boundary.")
        root_id = make_root_id(partition, condition_id, root_index)
        if shots != shots_for_root(partition, condition_id, root_index):
            raise RunStateError("root shot allocation differs from the frozen schedule.")
        if ((seed is None and not self.fixture_mode)
                or (seed is not None and (type(seed) is not int or seed < 0)) or not root_seed_ref):
            raise RunStateError("root requires an exact nonnegative seed and its inventory reference.")
        key = (partition, condition_id, root_id)
        if any((r["partition"], r["condition_id"], r["root_id"]) == key for r in payload["committed_roots"]):
            raise RunStateError("root is already committed; duplicate sampling is prohibited.")
        if any(r["root_seed_ref"] == root_seed_ref for r in payload["committed_roots"]):
            raise RunStateError("root seed reference was already consumed.")
        if seed is not None and any(r.get("seed") == seed for r in payload["committed_roots"]):
            raise RunStateError("numeric seed was already consumed by another root.")
        payload["state"] = "in_progress"
        payload["in_flight_root"] = {
            "partition": partition, "condition_id": condition_id, "root_id": root_id,
            "shots": shots, "seed": seed, "root_seed_ref": root_seed_ref,
        }
        self._write(payload)
        return dict(payload["in_flight_root"])

    def commit_root(self, row: Mapping[str, Any], *, seed: int | None) -> None:
        payload = self.read()
        inflight = payload.get("in_flight_root")
        if not isinstance(inflight, Mapping):
            raise RunStateError("no in-flight root is recorded for this commit.")
        if (row.get("partition"), row.get("condition_id"), row.get("root_id"), row.get("shots"), row.get("root_seed_ref")) != (
            inflight.get("partition"), inflight.get("condition_id"), inflight.get("root_id"),
            inflight.get("shots"), inflight.get("root_seed_ref"),
        ) or seed != inflight.get("seed"):
            raise RunStateError("commit root does not match the exact in-flight root and seed.")
        if root_commit_marker(row) != row.get("commit_marker_sha256"):
            raise RunStateError("root commit marker digest failed verification.")
        payload["committed_roots"].append(dict(row, seed=seed))
        payload["in_flight_root"] = None
        payload["state"] = "in_progress"
        self._write(payload)

    def freeze_selection(self, winner: Mapping[str, Any]) -> str:
        payload = self.read()
        expected = {("selection", c, make_root_id("selection", c, r)) for c in CONDITIONS for r in range(8)}
        committed = {(r["partition"], r["condition_id"], r["root_id"]) for r in payload["committed_roots"]}
        if payload.get("in_flight_root") is not None or committed != expected or len(payload["committed_roots"]) != 48:
            raise RunStateError("exactly all 48 selection roots, and no evaluation roots, must be committed before freezing the winner.")
        candidate = winner.get("selected_candidate")
        if candidate not in CANDIDATE_IDS:
            raise RunStateError("selection result does not name a candidate in the frozen 12-model grid.")
        self._verify_committed_directory(payload)
        self._verify_selection_winner_against_saved_arrays(winner)
        if self.selection_path.exists() or payload.get("selection_frozen"):
            raise RunStateError("selection winner already frozen; selection cannot be changed.")
        serialized = dict(winner)
        serialized["selection_state"] = "committed_before_evaluation"
        digest = atomic_write_json(self.selection_path, serialized)
        payload["selection_frozen"] = True
        payload["selected_candidate"] = candidate
        payload["selection_freeze_sha256"] = digest
        self._write(payload)
        return digest

    def require_frozen_selection(self) -> tuple[str, dict[str, Any]]:
        payload = self.read()
        if (payload.get("selection_frozen") is not True or not self.selection_path.is_file()
                or self._digest(self.selection_path) != payload.get("selection_freeze_sha256")):
            raise RunStateError("evaluation is prohibited until the immutable selection winner is committed.")
        winner = json.loads(self.selection_path.read_text(encoding="utf-8"))
        if winner.get("selected_candidate") != payload.get("selected_candidate"):
            raise RunStateError("selection winner/checkpoint identity mismatch.")
        current_hash = self._digest(self.selection_path)
        if self._verified_selection_sha256 != current_hash:
            self._verify_committed_directory(payload)
            self._verify_selection_winner_against_saved_arrays(winner)
            self._verified_selection_sha256 = current_hash
        return str(payload["selected_candidate"]), winner

    def _verify_selection_winner_against_saved_arrays(self, winner: Mapping[str, Any]) -> None:
        paths = [
            archive_path(self.root, "selection", condition, make_root_id("selection", condition, root_index))
            for condition in CONDITIONS for root_index in range(8)
        ]
        try:
            audit = audit_saved_arrays(paths, partition="selection")
        except Exception as exc:
            raise RunStateError(f"independent selection archive recomputation failed: {exc}") from exc
        result = audit.get("selection", {})
        archive_hashes = {path.name: self._digest(path) for path in paths}
        expected_ties = result.get("exact_tie_set")
        expected_scores = result.get("score_by_candidate_fraction")
        expected_float_scores = {
            candidate: float(Fraction(value)) for candidate, value in (expected_scores or {}).items()
        }
        tie_set = winner.get("exact_tie_set")
        candidate_order = winner.get("candidate_order")
        selection_conditions = winner.get("selection_conditions")
        if (audit.get("audit") != "PASS" or result.get("selected_candidate") not in CANDIDATE_IDS
                or winner.get("selected_candidate") != result.get("selected_candidate")
                or not isinstance(tie_set, (list, tuple)) or list(tie_set) != expected_ties
                or winner.get("score_fraction_by_candidate") != expected_scores
                or winner.get("score_by_candidate") != expected_float_scores
                or not isinstance(candidate_order, (list, tuple)) or list(candidate_order) != list(CANDIDATE_IDS)
                or not isinstance(selection_conditions, (list, tuple)) or list(selection_conditions) != list(CONDITIONS)
                or winner.get("selection_archive_sha256") != archive_hashes):
            raise RunStateError("selection winner or its archive hashes disagree with independent saved-array recomputation.")

    def pause_at_boundary(self) -> None:
        payload = self.read()
        if payload.get("in_flight_root") is not None:
            raise RunStateError("cannot safely pause while a sampler/root transaction is in flight.")
        if payload.get("state") != "in_progress":
            raise RunStateError("only an in-progress run can be paused.")
        self._verify_committed_directory(payload)
        payload["state"] = "paused"
        self._write(payload)

    def _verify_committed_directory(self, payload: Mapping[str, Any]) -> None:
        roots_dir = self.root / "roots"
        expected_archives: set[Path] = set()
        expected_markers: set[Path] = set()
        for row in payload.get("committed_roots", []):
            path = archive_path(self.root, row["partition"], row["condition_id"], row["root_id"]).resolve()
            marker = path.with_suffix(".commit.json").resolve()
            try:
                committed = read_and_verify_commit(path, marker)
            except Exception as exc:
                raise RunStateError(f"committed archive/marker verification failed: {exc}") from exc
            for field in ("archive_sha256", "sample_ids_sha256", "commit_marker_sha256", "root_seed_ref", "shots"):
                if committed.get(field) != row.get(field):
                    raise RunStateError(f"checkpoint/commit-marker mismatch at safe boundary ({field}).")
            expected_archives.add(path)
            expected_markers.add(marker)
        actual_archives = {p.resolve() for p in roots_dir.glob("*.npz")} if roots_dir.exists() else set()
        actual_markers = {p.resolve() for p in roots_dir.glob("*.commit.json")} if roots_dir.exists() else set()
        partial = list(roots_dir.glob("*.partial-*")) if roots_dir.exists() else []
        if actual_archives != expected_archives or actual_markers != expected_markers or partial:
            raise RunStateError("safe-boundary pause found uncommitted, partial, or unexpected root files.")

    def mark_completed(self) -> None:
        payload = self.read()
        if (payload.get("in_flight_root") is not None or payload.get("selection_frozen") is not True
                or payload.get("independent_audit_verified") is not True):
            raise RunStateError("cannot complete with an in-flight root, unfrozen selection, or missing independent audit.")
        expected = {
            (partition, condition, make_root_id(partition, condition, index))
            for partition, count in (("selection", 8), ("evaluation", 10))
            for condition in CONDITIONS for index in range(count)
        }
        actual = {
            (row.get("partition"), row.get("condition_id"), row.get("root_id"))
            for row in payload.get("committed_roots", [])
        }
        if actual != expected or len(payload.get("committed_roots", [])) != len(expected):
            raise RunStateError("cannot complete before all 48 selection and 60 evaluation roots are committed exactly once.")
        self._verify_committed_directory(payload)
        audit_path = self.root / "INDEPENDENT_AUDIT.json"
        if (not audit_path.is_file()
                or self._digest(audit_path) != payload.get("independent_audit_sha256")):
            raise RunStateError("cannot complete without the hash-verified independent audit artifact.")
        result_name = "SYNTHETIC_FIXTURE_ANALYSIS.json" if self.fixture_mode else "STATISTICAL_SUMMARY.json"
        if not (self.root / result_name).is_file():
            raise RunStateError("cannot complete without the final analysis artifact.")
        payload["state"] = "completed"
        validate_checkpoint_payload(payload)
        self._write(payload)

    def mark_failed(self, error_type: str, message: str) -> None:
        payload = self.read()
        if not isinstance(error_type, str) or not error_type or not isinstance(message, str):
            raise RunStateError("failure record needs an error type and message.")
        payload["state"] = "failed"
        payload["failure"] = {"type": error_type, "message": message[:1000]}
        self._write(payload)

    def record_independent_audit(self, audit_sha256: str) -> None:
        payload = self.read()
        if payload.get("in_flight_root") is not None:
            raise RunStateError("independent audit cannot finalize while a root is in flight.")
        if (not isinstance(audit_sha256, str) or len(audit_sha256) != 64
                or any(ch not in "0123456789abcdef" for ch in audit_sha256)):
            raise RunStateError("independent audit requires a SHA-256 digest.")
        if payload.get("independent_audit_verified") is True:
            if payload.get("independent_audit_sha256") != audit_sha256:
                raise RunStateError("a different independent audit is already committed.")
            return
        payload["independent_audit_verified"] = True
        payload["independent_audit_sha256"] = audit_sha256
        self._write(payload)

    def recover_committed_inflight(self) -> None:
        """Reconcile only a fully verified archive+marker for the exact in-flight root."""
        payload = self.read()
        inflight = payload.get("in_flight_root")
        if inflight is None:
            return
        path = archive_path(self.root, inflight["partition"], inflight["condition_id"], inflight["root_id"])
        marker = path.with_suffix(".commit.json")
        if not path.exists() and not marker.exists():
            raise RunStateError("in-flight sampler root has no committed bytes; resampling is ambiguous and forbidden.")
        if not path.exists() or not marker.exists():
            raise RunStateError("archive/marker pair is incomplete; manual recovery required, no resampling.")
        row = read_and_verify_commit(path, marker)
        if (row["partition"], row["condition_id"], row["root_id"], row["shots"], row["root_seed_ref"]) != (
            inflight["partition"], inflight["condition_id"], inflight["root_id"],
            inflight["shots"], inflight["root_seed_ref"],
        ):
            raise RunStateError("committed transaction does not match the exact in-flight root.")
        if any((r["partition"], r["condition_id"], r["root_id"]) ==
               (row["partition"], row["condition_id"], row["root_id"])
               or r["root_seed_ref"] == row["root_seed_ref"]
               or (inflight.get("seed") is not None and r.get("seed") == inflight["seed"])
               for r in payload["committed_roots"]):
            raise RunStateError("recovered transaction duplicates an already committed root or seed.")
        payload["committed_roots"].append(dict(row, seed=inflight["seed"]))
        payload["in_flight_root"] = None
        payload["state"] = "paused"
        self._write(payload)

    def validate_resume(self, *, protocol_sha256: str, source_manifest_sha256: str) -> dict[str, int]:
        payload = self.read()
        self._verify_committed_directory(payload)
        archives: dict[str, Path] = {}
        for row in payload["committed_roots"]:
            path = archive_path(self.root, row["partition"], row["condition_id"], row["root_id"])
            key = "|".join((row["partition"], row["condition_id"], row["root_id"]))
            try:
                marker_row = read_and_verify_commit(path)
            except Exception as exc:
                raise RunStateError(f"committed root archive/marker verification failed: {exc}") from exc
            for field in ("archive_sha256", "sample_ids_sha256", "commit_marker_sha256", "root_seed_ref"):
                if marker_row.get(field) != row.get(field):
                    raise RunStateError(f"checkpoint/commit-marker mismatch in {field}.")
            archives[key] = path
        partials = list((self.root / "roots").glob("*.partial-*")) if (self.root / "roots").exists() else []
        uncommitted = []
        committed_paths = set(archives.values())
        for path in (self.root / "roots").glob("*.npz") if (self.root / "roots").exists() else ():
            if path not in committed_paths:
                uncommitted.append(path)
        uncommitted.extend(partials)
        try:
            return validate_resume_state(
                payload,
                expected_protocol_sha256=protocol_sha256,
                expected_source_manifest_sha256=source_manifest_sha256,
                archive_paths_by_key=archives,
                uncommitted_files=uncommitted,
            )
        except CheckpointError as exc:
            raise RunStateError(str(exc)) from exc
