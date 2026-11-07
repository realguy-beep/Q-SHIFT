# Stage 2 Pre-sampling Freeze Supersession and Count Reconciliation

This is an implementation-stage record created before any Stage 2 sample generation. It does not amend the scientific conditions, partitions, optimizer, thresholds, endpoints, or resource limits in `CNN_STAGE2_FROZEN_PROTOCOL.md`.

## Original committed freeze

- Commit: `ed52ca3d36ff64eb800d4adc7652b127eb594ad6`.
- Original file: `FREEZE.json` (preserved unchanged).
- Original `FREEZE.json` SHA-256: `045213b7906a06c0e4499f20cc6c5c74a8aa27f4abac1a3e5f9bb572e62dedd6`.
- Original protocol ID: `bbb9667a0920771a7bc6b910da42e9de00e5397b00e442927f85037b1581eead`.
- It records 95 reserved unique seeds, 260,000 planned shots, zero generated shots, no training, and no independent-test access.
- Its `superseded_freeze_sha256s` contains **four** pre-sampling draft hashes:
  - `bda4ce95585b2d9e745867a440c814194289af789709328e01a22e3a2fdcb501`
  - `e785217ea74d04acbd75bafa012d8fa4d07c7f28258f181d07cf1b55c7c42418`
  - `c63f169126d5659f62222f39cfb8804ebb4f78f3cf6019124f1104595f91b200`
  - `22ea99d88f06c99c82eeba715829435a80e728fa5844e5c357a0a77ef72deda9`

The earlier progress message reported three because it described the preceding pre-sampling snapshot. One additional freeze refresh was written after the exact per-split shot totals and freeze-builder validation were finalized. The committed file is authoritative: it has four draft hashes. Every such snapshot records zero shots and no training/test access; the difference is metadata finalization only, not a change in experimental allocation.

## Implementation freeze

The original `FREEZE.json` and `build_freeze.py` are not edited. A separate `FREEZE_IMPLEMENTATION_V2.json` will hash the new runner, independent auditor, regression tests, implementation-readiness record, this supersession record, and all original frozen inputs. Its chain will contain the four original draft hashes plus the SHA-256 of the committed original `FREEZE.json` (five superseded pre-sampling hashes total). The new freeze must be created and independently verified before the permitted 256-shot training-stream prefix is sampled.

If any frozen scientific parameter or seed changes, this is no longer a source-only supersession and execution must stop for a formal protocol amendment. After the first Stage 2 sample is generated, neither freeze may be changed.
