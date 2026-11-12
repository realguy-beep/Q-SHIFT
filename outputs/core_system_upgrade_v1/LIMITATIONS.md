# Limitations and Non-Claims — Core System Upgrade v1

1. This is software infrastructure, not a new decoder or a decoding-performance experiment. It does not establish improvements in logical error rate.
2. PyMatching's adapter records the configured correlation flag. For an already-constructed legacy model, the caller must verify and state its constructor setting; PyMatching does not expose a universal construction-mode introspection API. The dashboard wrapper is backed by the inspected Phase 2B build_bank call site.
3. NoiseEstimate.source="detector_only" and causal block indices are contracts checked at the API boundary, not cryptographic proof of how the upstream estimator was trained. Future integrations still require source/evidence audit.
4. The generic evaluator intentionally refuses protected-test data. It also does not provide statistical inference beyond paired counts/rates; root-clustered uncertainty and hypothesis tests belong in a frozen study analysis.
5. The evaluator hashes the paired arrays, which includes observables for evidence identity, but only passes detector copies to decoders. The hash is not an independent provenance attestation.
6. The dashboard circuit remains its existing distance-3/five-round pilot. The adapter can describe dimensions, but adding distances, families or noise models requires separate circuit validation.
7. The historical adaptive controller and evaluation scripts remain untouched. Existing development evidence is exploratory and includes known limitations; the new controller is not evidence that adaptation helps.
8. The Stim categorical-to-DEM approximation documented by Phase 2B remains unchanged.
9. No browser end-to-end test was performed. No physical device, actual qubit, or hardware correction was tested.
10. Full existing dashboard tests were not run because a number of them sample circuits/train models; selected non-sampling regression classes and focused new deterministic tests passed.
11. The interface change is a semantics note within the existing training dashboard. A spatial per-shot detector-event visualization and an individual-shot known-fault versus inferred-prediction view are still absent; adding them should use clearly sourced run evidence or a separately labeled deterministic fixture, not fabricated metrics.
12. The starting repository's V2.4 freeze lists 17 hashes, of which 13 do not match the files already in base commit `0ff77c70e38a7e6c2ff547958aee00b0ae5c1fe5`; the other four match, with `.gitignore` differing from the Git blob only by Windows newline conversion. The 13 source discrepancies are pre-existing historical provenance issues, not successful freeze verification. V2.4 remains HOLD. See `FROZEN_V2_4_HASH_AUDIT.md` for the full comparison.
