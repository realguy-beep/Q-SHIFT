# Q-SHIFT Core System Upgrade v1 — Implementation Report

## Outcome

Implemented a small, versioned integration layer for conventional and future decoders, tightened dashboard input/sampling validation, preserved the current Phase 2B PyMatching behavior, and clarified observable-versus-physical-correction semantics in the existing page. This is an engineering release; it contains no new logical-error measurements.

## Concrete defects and fixes

- **Configuration coercion:** the previous validate_config called int(), float(), and bool() on request values. Invalid JSON types could be silently changed into plausible settings. It now accepts JSON-native integer/real/boolean types strictly, rejects booleans as integers, rejects NaN/infinity, and checks Stim’s seed range before allocation. Valid default and preset behavior is retained.
- **Simulator inputs and diagnostics:** sample previously cast seed and shot count before validation, then assumed (shots, 40) detectors and (shots, 1) observables. It now checks positive integer shots, integer Stim seed bounds, circuit observable count, returned dimensions and binary values. Sampler errors are re-raised with seed/shot context and the original exception chain. No fallback or noise-channel change was introduced.
- **Decoder contract:** new qshift_core_v1 defines explicit detector-only inputs, binary prediction dimensions, metadata/provenance, and runtime. Its PyMatching adapter uses the exact same explicit correlation mode at construction and decoding. The compatibility wrapper maintains the existing one-observable output shape.
- **Adaptive hooks:** a versioned registry and selector record requested/selected decoder, estimated versus configured parameters, reason and fallback. Proposals based on the current or a future block are rejected. Low confidence, missing estimates and unsupported names return to fixed PyMatching. This infrastructure is not wired to claim a deployable adaptive gain.
- **Evaluation:** the new paired record utility receives arrays supplied by a caller, passes identical detector bytes to each decoder and uses observables only for scoring after decode. It records paired failure discordances and sample hash. Protected-test scope is explicitly refused.
- **UI:** added a concise note clarifying configured noise, logical-observable prediction, and the absence of a physical correction map.

## Files changed

- qshift_core_v1/__init__.py
- qshift_core_v1/contracts.py
- qshift_core_v1/baselines.py
- qshift_core_v1/pymatching_adapter.py
- qshift_core_v1/controller.py
- qshift_core_v1/evaluation.py
- qshift_core_v1/seeds.py
- dashboard/configuration.py
- dashboard/seed_protocol.py
- dashboard/simulator.py
- dashboard/tests/test_core_system_v1.py
- dashboard/static/index.html
- dashboard/static/styles.css
- README.md
- RESEARCH_STATUS.md
- EXPERIMENT_INDEX.md
- outputs/core_system_upgrade_v1/ documentation and manifest

## Scientific interpretation

Fixed PyMatching remains the established strong baseline in the project. Existing classifier/switching and neural results have not demonstrated a reliable improvement. The adapter and selector make future integration safer and easier to audit; they do not change this evidence. The existing Phase 2B model remains a graph-based approximation of the categorical Stim channel.

## Remaining boundary

No full dashboard suite was run because several existing tests call Stim sampling or training. The targeted tests below contain no simulator sampling or training. No model training, performance benchmark, research evaluation, hardware action, Stage 5 access, or protected outcome access occurred.

The current dashboard is a training console rather than a per-shot circuit explorer. The targeted UI change does not add detector geometry rendering or a known-fault/single-shot panel; those remain future interface work and must be driven by actual persisted run evidence or an explicitly labeled deterministic fixture.

## Historical freeze integrity note

The starting repository contains a pre-existing discrepancy in the V2.4 freeze: 13 of 17 expected file hashes differ from the corresponding bytes already present at base commit `0ff77c70e38a7e6c2ff547958aee00b0ae5c1fe5`; four entries match, including `.gitignore` whose only base-blob difference is CRLF/LF checkout conversion. The current contents match the base commit after newline normalization, so this engineering work did not create those differences. This does not prove provenance before the base commit. The exact rows and impact are recorded in [FROZEN_V2_4_HASH_AUDIT.md](FROZEN_V2_4_HASH_AUDIT.md). V2.4 remains HOLD; this branch did not modify or authorize it.
