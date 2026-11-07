# Archived manifest verification

Scanned 30 JSON manifest files under `outputs/`. The check is read-only. A file is PASS only when both its recorded SHA-256 and (if present) byte size match.

| Manifest | Status | Entries | Pass | Mismatch | Missing |
|---|---:|---:|---:|---:|---:|
| `outputs/categorical_decoder_feasibility/MANIFEST.json` | PASS | 20 | 20 | 0 | 0 |
| `outputs/categorical_inference_investigation/MANIFEST.json` | PASS | 59 | 59 | 0 | 0 |
| `outputs/competition_pivot/MANIFEST.json` | PASS | 15 | 15 | 0 | 0 |
| `outputs/conditional_go_resolution/MANIFEST.json` | PASS | 21 | 21 | 0 | 0 |
| `outputs/correlation_mechanism_audit/MANIFEST.json` | PASS | 115 | 115 | 0 | 0 |
| `outputs/correlation_pilot/MANIFEST.json` | PASS | 106 | 106 | 0 | 0 |
| `outputs/dem_feasibility_gate/MANIFEST.json` | PASS | 142 | 142 | 0 | 0 |
| `outputs/final_research_decision/MANIFEST.json` | PASS | 13 | 13 | 0 | 0 |
| `outputs/headroom_feasibility/MANIFEST.json` | PASS | 623 | 623 | 0 | 0 |
| `outputs/matching_representation_investigation/MANIFEST.json` | PASS | 27 | 27 | 0 | 0 |
| `outputs/noise_composition_phase/raw/manifest_guarded_v4.json` | PASS | 10 | 10 | 0 | 0 |
| `outputs/noise_composition_phase/raw/manifest_v4.json` | PASS | 11 | 11 | 0 | 0 |
| `outputs/phase2_specialist_decoder/raw/manifest_smoke.json` | PASS | 1 | 1 | 0 | 0 |
| `outputs/phase2_specialist_decoder/raw/manifest_smoke_calfit.json` | PASS | 1 | 1 | 0 | 0 |
| `outputs/phase2_specialist_decoder/raw/manifest_smoke_v2.json` | PASS | 1 | 1 | 0 | 0 |
| `outputs/phase2_specialist_decoder/raw/manifest_specialist_results_v1.json` | PASS | 10 | 10 | 0 | 0 |
| `outputs/phase2a_decoder_specialization/PHASE2A_MANIFEST.json` | PASS | 89 | 89 | 0 | 0 |
| `outputs/phase2b_pauli_bias/SHA256_MANIFEST.json` | PASS | 182 | 182 | 0 | 0 |
| `outputs/phase2c_decoder_fidelity/MANIFEST.json` | PASS | 88 | 88 | 0 | 0 |
| `outputs/phase3_geometry_investigation/raw/manifest_phase3a_surface_pilot_v1.json` | PASS | 3 | 3 | 0 | 0 |
| `outputs/phase3_geometry_investigation/raw/manifest_phase3a_surface_pilot_v2.json` | PASS | 3 | 3 | 0 | 0 |
| `outputs/phase3_geometry_investigation/raw/manifest_phase3a_surface_pilot_v3.json` | PASS | 3 | 3 | 0 | 0 |
| `outputs/phase3_geometry_investigation/raw/manifest_phase3a_surface_pilot_v4.json` | PASS | 3 | 3 | 0 | 0 |
| `outputs/phase3b_independent_replication/SHA256_MANIFEST.json` | PASS | 30 | 30 | 0 | 0 |
| `outputs/phase4a_model_adequacy/MANIFEST.json` | MISMATCH | 223 | 220 | 3 | 0 |
| `outputs/phase4a_model_adequacy/MANIFEST_FINAL.json` | PASS | 226 | 226 | 0 | 0 |
| `outputs/phase4b_replication/MANIFEST.json` | PASS | 102 | 102 | 0 | 0 |
| `outputs/phase4c_strong_baselines/adaptive/ADAPTIVE_MANIFEST.json` | MISMATCH | 13 | 7 | 6 | 0 |
| `outputs/phase4c_strong_baselines/stage2/STAGE2_RECOVERY_MANIFEST.json` | PASS | 21 | 21 | 0 | 0 |
| `outputs/prototype_development/MANIFEST.json` | PASS | 72 | 72 | 0 | 0 |

## Non-passing entries

- `outputs/phase4a_model_adequacy/MANIFEST.json` — `IMPLEMENTATION_LOG.md` (MISMATCH); record at `$.files[4]`; expected SHA-256 `5842b291e0e29e37bb1f04c18e915048b1e727c9093c3b525f2cbb07ea1ba139`, actual `bc2a6069b6d1110a408c9b8a6aa4dff62f9d786731f7abeaa21fe044419d9994`.
- `outputs/phase4a_model_adequacy/MANIFEST.json` — `PHASE4A_INTERPRETATION.md` (MISMATCH); record at `$.files[24]`; expected SHA-256 `164f48e809a09d2c7276f6cdbc4694262f083777ad55dabb447537bd3f1bec25`, actual `16abf291df414415b50df781d6aa115c91ba661fba8f4d6de2783aaca464fbb7`.
- `outputs/phase4a_model_adequacy/MANIFEST.json` — `PHASE4A_RESULTS.md` (MISMATCH); record at `$.files[27]`; expected SHA-256 `0abec8c61d5c7bc238069eee041e7f4c824740331f912056ee7fd5b2983d126f`, actual `97f0280092a57c5f8432b0d52b1eda1a69aa09a47758440eac562738da521ff3`.
- `outputs/phase4c_strong_baselines/adaptive/ADAPTIVE_MANIFEST.json` — `ADAPTIVE_PROGRESS.md` (MISMATCH); record at `$[0]`; expected SHA-256 `a5f1fab0083bd49e1fe6a5156ad7925e877cb7bcf5da12f6e3d4a1fac688c4d6`, actual `a22da8e54cce7e8cee049c1b9aa304e1a78a13e091417decb292ca7b18536df6`.
- `outputs/phase4c_strong_baselines/adaptive/ADAPTIVE_MANIFEST.json` — `core.py` (MISMATCH); record at `$[2]`; expected SHA-256 `407507e72325c56476e4038d87f683b9a1c7a92f73c44d8be1cd91279109d8f9`, actual `c7e24c3e5de2127fa5e2a1a1fa235c5b43143a764246878b704192cf31027211`.
- `outputs/phase4c_strong_baselines/adaptive/ADAPTIVE_MANIFEST.json` — `evaluation.py` (MISMATCH); record at `$[5]`; expected SHA-256 `8750b3a560eb627eb26b1fa5b8f6491ec927316937e3b40770624bafbf3eb162`, actual `92f5cf3b357a98bbe1d1989168346a7c4d23cc6c1bf5ceecfd3f11aa8ffc2f19`.
- `outputs/phase4c_strong_baselines/adaptive/ADAPTIVE_MANIFEST.json` — `run_development.py` (MISMATCH); record at `$[9]`; expected SHA-256 `ce3bd054e89fffa3bc007a94675c6d47b9d28b71e9b33093afc269b042f12176`, actual `c9c076dbb8205f523e419e2979d5b1dc58f38049005bcf284f5c8b16e256f239`.
- `outputs/phase4c_strong_baselines/adaptive/ADAPTIVE_MANIFEST.json` — `schedules.py` (MISMATCH); record at `$[10]`; expected SHA-256 `908163c872a9025ad60d5bb6e4599f04f6a5d9f9187754c1b5d17a091f5f3b91`, actual `49b43711f1f37e591cc1b9742ce6e22bd3925abd1528d16993f41facb1649da8`.
- `outputs/phase4c_strong_baselines/adaptive/ADAPTIVE_MANIFEST.json` — `test_core.py` (MISMATCH); record at `$[12]`; expected SHA-256 `7426672cc021056ea99ca397641dac1412306a782a5aae283bff563994d7c231`, actual `8a95b0610c9e62d21fe5923625b172deac74ad985ff6a4f1d1dec91a6fa645eb`.
