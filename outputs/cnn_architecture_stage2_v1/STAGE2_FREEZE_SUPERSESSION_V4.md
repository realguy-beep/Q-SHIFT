# Stage 2 Implementation Freeze V4 — Pre-sampling Supersession

V4 supersedes the V3 implementation freeze before any Stage 2 samples. It changes no scientific configuration, seeds, training budget, allocation, selection rule, analysis endpoint, or resource limit.

## V3 preflight issue

V3 correctly recorded zero samples and zero training, but its first verification call exposed a verifier field-semantics bug: the runner compared the original FREEZE.json hash to supersedes_freeze_file_sha256. In V3, that field correctly refers to the immediately superseded V2 implementation freeze; the original historical hash is separately stored as historical_original_freeze_sha256. Verification stopped before any sampler was constructed.

The runner and independent auditor now check these two chain links separately: original FREEZE.json against historical_original_freeze_sha256, and FREEZE_IMPLEMENTATION_V3.json against supersedes_freeze_file_sha256. The V2 and V3 freeze files remain unchanged historical pre-sampling records. At V3 stop, run_v1/ did not exist and no Stage 2 sample had been generated.

## Freeze-chain reconciliation

The original committed FREEZE.json contains four superseded drafts. V2 added the original freeze (five total); V3 added V2 (six total); V4 adds V3 (seven total). V4 itself is not superseded. The chain is metadata/provenance and implementation-validation history only.

## V4 scope

V4 hashes the original frozen science/configuration inputs, all prior freeze records and their explanatory notes, the corrected runner/verifier, current tests, and this readiness/supersession record. Its state is FROZEN_IMPLEMENTATION_V4_NOT_EXECUTED with zero shots, no training, no final-development access, and no independent-test allocation/access. Any further source change before sampling requires another documented superseding freeze.
