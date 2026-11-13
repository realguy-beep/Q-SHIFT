# Seed allocation and collision-screening procedure

Status: preparation only. No numeric production or benchmark seeds were allocated and no historical seed metadata was opened during this milestone.

## Production partitions

The eventual V2 inventory must allocate disjoint numeric seeds for the 48 selection roots and 60 evaluation roots across the six frozen conditions, plus separate analysis streams for selection-rank bootstrap, primary bootstrap, and each of the three secondary sign-flip contrasts. The five analysis streams are not Stim seeds and must remain domain-separated from sampler seeds. Sample identifiers continue to derive from partition, condition, root, and row offset; they do not replace seed-uniqueness checks.

Before any values are issued, an owner-approved allowlist must identify the exact historical seed-metadata files and permitted fields. Only those seed fields may be read. Normalize each Stim seed to its exact signed integer representation, reject duplicates within the proposed inventory, then compare every proposed sampler seed against the allowed historical set and all other proposed partitions. Record allowlist path/digest, parsed field names, count, collision result, and inventory digest. Do not inspect result arrays or outcomes as part of collision screening.

The separate benchmark namespace is `qshift-ns4a-v2-execution-readiness-benchmark-v1`; its inventory template deliberately contains six null entries. After separate benchmark authorization, allocate exactly one disposable seed per condition and run the same duplicate/collision screen. The benchmark namespace must never be used to fill a missing production seed. No historical seed metadata allowlist was supplied here, so collision screening cannot be completed and seed allocation is deferred.

## Fail-closed conditions

Reject incomplete or extra inventory keys, non-integer or out-of-range values, duplicate numeric seeds, a seed collision with the explicitly allowlisted historical set, or a hash change after freeze. Do not derive replacement seeds after a collision; prepare a new versioned inventory and obtain review. Production runner activation additionally requires a matching immutable execution manifest and a separate owner authorization record.
