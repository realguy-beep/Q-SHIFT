"""Full-roster deterministic rehearsal using formulas, never Stim sampling."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import time
from typing import Any

import numpy as np

from qshift_ns4a_v2_deterministic.protocol import (
    CANDIDATE_IDS, CONDITIONS, EVALUATION_ARMS, make_root_id,
    selection_shots,
)
from qshift_ns4a_v2_deterministic.selection import choose_global_candidate, run_and_score_selection_batch
from qshift_ns4a_v2_deterministic.paired_evaluation import run_paired_evaluation_batch
from qshift_ns4a_v2_deterministic.sample_schema import make_sample_ids
from qshift_ns4a_v2_deterministic.checkpoint import atomic_write_json

from .analysis import analyze_verified_archives
from .archive_store import build_archive_arrays, commit_root_archive, archive_path
from .audit import audit_run_directory
from .models import CONFIG_PATH, build_evaluation_bank, build_model_catalog, evaluation_decoder_views
from .protocol import validate_allocation
from .resource_guard import ResourceGuard
from .run_state import RunDirectoryLock, RunStateStore
from .runner import _CheckedDecoderView, _write_once_json


FIXTURE_DEFINITION = "uint32 modular detector pattern; parity label derived from fixed detector columns and condition index; no RNG, Stim sampler, hidden regime labels, or experimental shot source"
FIXTURE_ANALYSIS_STREAMS = {
    "selection_rank_bootstrap": 31_003,
    "primary_bootstrap": 31_019,
    "primary_sign_flip": 31_033,
    "secondary_sign_flip_bm_vs_selected_dem_ordinary_pm": 31_037,
    "secondary_sign_flip_bm_vs_selected_dem_correlation_enabled_pm": 31_043,
    "secondary_sign_flip_selected_pm_vs_nominal_ordinary_pm": 31_051,
}


def deterministic_fixture(condition_index: int, root_index: int, shots: int, *, partition: str) -> tuple[np.ndarray, np.ndarray]:
    if type(condition_index) is not int or not 0 <= condition_index < 6:
        raise ValueError("fixture condition index must be in [0,5].")
    if type(root_index) is not int or root_index < 0:
        raise ValueError("fixture root index must be nonnegative.")
    if type(shots) is not int or shots <= 0 or partition not in {"selection", "evaluation"}:
        raise ValueError("fixture shots/partition invalid.")
    row = np.arange(shots, dtype=np.uint32)[:, None] + np.uint32(root_index * 7919)
    col = np.arange(40, dtype=np.uint32)[None, :]
    modulus = np.uint32(97 + condition_index * 2)
    threshold = np.uint32(4 + (condition_index % 5))
    detector = (((row * np.uint32(7 + condition_index) + col * np.uint32(13 + root_index)
                  + np.uint32(17 * condition_index + 31 * root_index)) % modulus) < threshold).astype(np.uint8)
    labels = (detector[:, 0] ^ detector[:, 7] ^ detector[:, 21] ^ np.uint8(condition_index % 2))[:, None]
    return detector, labels


def _fixture_ref(partition: str, condition: str, root_index: int) -> str:
    return f"fixture-only:no-seed:{partition}:{condition}:r{root_index:02d}"


def run_full_deterministic_rehearsal(*, output_directory: str | Path | None = None) -> dict[str, Any]:
    """Exercise all frozen roots/arms using source-defined deterministic bytes.

    Output artifacts are disposable fixture records and must not be represented
    as samples, outcomes, or a scientific experiment. By default all files live
    in a temporary directory and are removed before return.
    """
    start = time.perf_counter()
    allocation = validate_allocation()
    owned_temp = tempfile.TemporaryDirectory(prefix="qshift-ns4a-v2-fixture-") if output_directory is None else None
    run_dir = Path(owned_temp.name) if owned_temp else Path(output_directory)
    run_dir.mkdir(parents=True, exist_ok=True)
    if any(run_dir.iterdir()):
        raise FileExistsError("deterministic rehearsal output directory must be empty.")
    catalog = build_model_catalog()
    protocol_sha = hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()
    source_sha = hashlib.sha256(b"NS4A deterministic rehearsal only; not an execution freeze").hexdigest()
    guard = ResourceGuard(run_dir)
    guard.start()
    try:
        with RunDirectoryLock(run_dir):
            state = RunStateStore(
                run_dir,
                protocol_sha256=protocol_sha,
                source_manifest_sha256=source_sha,
                fixture_mode=True,
            )
            state.initialize()
            selection_scores = []
            for condition_index, condition_id in enumerate(CONDITIONS):
                sampling = catalog.conditions[condition_id].sampling_identity
                for root_index in range(8):
                    shots = selection_shots(condition_index, root_index)
                    state.begin_root(
                        partition="selection", condition_id=condition_id, root_index=root_index,
                        shots=shots, seed=None, root_seed_ref=_fixture_ref("selection", condition_id, root_index),
                    )
                    detectors, labels = deterministic_fixture(condition_index, root_index, shots, partition="selection")
                    ids = make_sample_ids("selection", condition_id, make_root_id("selection", condition_id, root_index), shots)
                    result = run_and_score_selection_batch(
                        condition_id=condition_id, root_index=root_index,
                        root_id=make_root_id("selection", condition_id, root_index),
                        detectors=detectors, detector_sample_ids=ids,
                        labels=labels, label_sample_ids=ids, prediction_sample_ids=ids,
                        decoders=catalog.selection_decoders,
                    )
                    selection_scores.append(result.root_score)
                    predictions = np.stack([result.predictions_by_candidate[name] for name in CANDIDATE_IDS])
                    identities = catalog.selection_model_identities_by_condition[condition_id]
                    arrays = build_archive_arrays(
                        partition="selection", condition_id=condition_id, root_id=result.root_score.root_id,
                        detectors=detectors, observables=labels, predictions=predictions,
                        model_identity_sha256_by_candidate={name: identities[name].identity_sha256 for name in CANDIDATE_IDS},
                        sampling_identity_sha256=sampling.identity_sha256,
                        root_seed_ref=_fixture_ref("selection", condition_id, root_index),
                        extra_metadata={"synthetic_fixture": True, "fixture_definition": FIXTURE_DEFINITION},
                    )
                    row = commit_root_archive(
                        run_dir, arrays, root_seed_ref=_fixture_ref("selection", condition_id, root_index),
                    )
                    state.commit_root(row, seed=None)
                    guard.check("fixture_selection_root")

            winner = choose_global_candidate(selection_scores)
            winner["selection_archive_sha256"] = {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (archive_path(run_dir, "selection", c, make_root_id("selection", c, r))
                             for c in CONDITIONS for r in range(8))
            }
            winner["fixture_only"] = True
            state.freeze_selection(winner)
            selected, _ = state.require_frozen_selection()

            evaluation_rows = 0
            for condition_index, condition_id in enumerate(CONDITIONS):
                bank, bm_registration = build_evaluation_bank(catalog, condition_id, selected)
                try:
                    views = evaluation_decoder_views(bank, catalog.conditions[condition_id].circuit)
                    for root_index in range(10):
                        root_id = make_root_id("evaluation", condition_id, root_index)
                        state.begin_root(
                            partition="evaluation", condition_id=condition_id, root_index=root_index,
                            shots=4_000, seed=None,
                            root_seed_ref=_fixture_ref("evaluation", condition_id, root_index),
                        )
                        detectors, labels = deterministic_fixture(condition_index, root_index, 4_000, partition="evaluation")
                        ids = make_sample_ids("evaluation", condition_id, root_id, 4_000)
                        result = run_paired_evaluation_batch(
                            condition_id=condition_id, root_index=root_index, root_id=root_id,
                            detectors=detectors, detector_sample_ids=ids,
                            labels=labels, label_sample_ids=ids, prediction_sample_ids=ids,
                            decoders=views,
                        )
                        predictions = np.stack([result["predictions_by_arm"][arm] for arm in EVALUATION_ARMS])
                        registered_by_arm = {
                            "nominal_ordinary_pymatching": "nominal_ordinary_pymatching",
                            "nominal_correlation_enabled_pymatching": "nominal_correlation_enabled_pymatching",
                            "pooled_selected_fixed_pymatching": "pooled_selected_fixed_pymatching",
                            "matched_selected_dem_pymatching_other_mode_control": "matched_selected_dem_pymatching_other_mode_control",
                            "beliefmatching_same_selected_dem": "beliefmatching",
                        }
                        model_ids = {arm: bank.adapter(registered).model_identity.identity_sha256
                                     for arm, registered in registered_by_arm.items()}
                        arrays = build_archive_arrays(
                            partition="evaluation", condition_id=condition_id, root_id=root_id,
                            detectors=detectors, observables=labels, predictions=predictions,
                            model_identity_sha256_by_candidate=model_ids,
                            sampling_identity_sha256=catalog.conditions[condition_id].sampling_identity.identity_sha256,
                            root_seed_ref=_fixture_ref("evaluation", condition_id, root_index),
                            extra_metadata={"synthetic_fixture": True, "fixture_definition": FIXTURE_DEFINITION,
                                            "selected_candidate": selected},
                        )
                        row = commit_root_archive(
                            run_dir, arrays, root_seed_ref=_fixture_ref("evaluation", condition_id, root_index),
                        )
                        state.commit_root(row, seed=None)
                        evaluation_rows += 4_000
                        guard.check("fixture_evaluation_root")
                finally:
                    bm_registration.adapter.close()

            independent = audit_run_directory(run_dir, state.read())
            audit_bytes = json.dumps(independent, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            audit_sha = _write_once_json(run_dir / "INDEPENDENT_AUDIT.json", independent)
            state.record_independent_audit(audit_sha)
            analysis = analyze_verified_archives(
                independent, selected_candidate=selected, analysis_seeds=FIXTURE_ANALYSIS_STREAMS,
            )
            _write_once_json(run_dir / "SYNTHETIC_FIXTURE_ANALYSIS.json", analysis)
            state.mark_completed()
            final_state = state.read()

        report = {
            "schema": "qshift-ns4a-v2-deterministic-rehearsal-v1",
            "status": "PASS_SYNTHETIC_FIXTURE_ONLY",
            "scientific_sampling": False,
            "stim_sampler_calls": 0,
            "generated_experimental_events": 0,
            "fixture_rows": allocation["total"],
            "selection_fixture_rows": allocation["selection"],
            "evaluation_fixture_rows": evaluation_rows,
            "selection_roots": 48,
            "evaluation_roots": 60,
            "candidates_exercised": list(CANDIDATE_IDS),
            "evaluation_arms_exercised": list(EVALUATION_ARMS),
            "selected_candidate_on_fixture_only": selected,
            "independent_auditor": independent["audit"],
            "independently_recomputed_total_rows": independent["total_shots"],
            "fixture_analysis_status": analysis["analysis_status"],
            "epistemic_notice": "All labels and detector rows are deterministic source-defined fixtures; no LER or decoder outcome here is a scientific result.",
            "elapsed_seconds": time.perf_counter() - start,
            "resource_snapshot": guard.check("fixture_rehearsal_complete"),
            "fixture_analysis_streams": FIXTURE_ANALYSIS_STREAMS,
            "checkpoint_state": final_state["state"],
            "archive_count": 108,
            "archive_audit_sha256": audit_sha,
            "temporary_outputs_removed": owned_temp is not None,
        }
        # The audit payload hash is retained; detailed synthetic per-root
        # arrays are intentionally disposable and never added to Git.
        if output_directory is not None:
            output = Path(output_directory) / "DETERMINISTIC_REHEARSAL_SUMMARY.json"
            _write_once_json(output, report)
        return report
    finally:
        if owned_temp is not None:
            owned_temp.cleanup()
