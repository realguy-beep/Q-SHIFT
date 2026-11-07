# Reproduction and audit trail

Run these commands from the repository root in the current Python environment:

```powershell
python outputs/unified_headroom_audit/audit_existing_headroom.py
python outputs/unified_headroom_audit/verify_archived_manifests.py
python outputs/unified_headroom_audit/reconcile_phase5e_accounting.py
python outputs/unified_headroom_audit/verify_audit_source_hashes.py
python outputs/unified_headroom_audit/build_manifest.py
python outputs/unified_headroom_audit/verify_final_manifest.py
```

The first command reads archived arrays and writes the new audit’s `RESULTS.json`, paired-complementarity tables, per-root oracle counts, calibration-selection recomputation tables, adaptive evidence summary, and `SOURCE_FILE_HASHES.json`. It generates no Stim shots and does not modify historical result directories. The second command checks all archived JSON checksum manifests under `outputs/`, excluding this audit’s own directory to avoid recursive self-verification; its full entry results are in `MANIFEST_VERIFICATION.json` and `.md`. The third reconciles Phase 5E counts from saved files without sampling. The fourth rehashes all inputs recorded by the new array audit. The last two commands build and verify this audit’s manifest after all deliverables are final.

The raw-array calculations use identical saved detector/outcome bundles across all compared decoders where prediction arrays are present. Model selection is recalculated only from archived calibration data. Test labels are used only to rescore saved predictions, calculate paired disagreement/oracle diagnostics explicitly marked hindsight, and reconcile archived totals. The Stage 2 detector-calibration fit is not rerun because its calibration samples were not saved.

## Verified audit execution

- Saved NPZ evidence bundles read for the calculations: 802.
- New simulation shots: 0.
- Current Phase 4C Stage 2 checkpoints: all 60 are included; saved prediction/observable residual counts reconcile with recovered Stage 2 totals. Independent decoder re-decoding was previously passed by the Phase 4B/Stage 2 evidence audit.
- Calibration choices independently recomputed from archived calibration arrays: all 12 multi-distance decoder banks reconcile; Phase 2A selection also reconciles.
- Archived manifest scan: 30 manifests, 2,233 checksum entries; 28 fully pass. Two historical manifests have known mismatches: original Phase 4A’s three Markdown expansions (its final manifest passes 226/226) and the superseded Phase 5 adaptive manifest’s six edited entries. Details and hashes are in `MANIFEST_VERIFICATION.json`.
- Repository Git history is unavailable; freeze files and manifest hashes are the available provenance, not a cryptographic time-stamp service.

`MANIFEST.json` contains hashes for the new report, code, and machine-readable outputs. It is written last and intentionally excludes itself.

