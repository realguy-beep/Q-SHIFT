# Independent replication: selective BP+LSD escalation efficacy

## Purpose

The initial fixed hybrid showed a large macro LER reduction but failed its runtime limit. Verify the accuracy signal on fresh simulator streams before considering any separate faster escalator design. This replication does not reconsider the current BP+LSD runtime rejection.

## Frozen replication

- Repeat the exact six d3 conditions, channel model, DEM threshold, correlated/ordinary matching models, and syndrome-only disagreement flag from `selective_bplsd_escalation_protocol.md`.
- Route flagged syndromes to the same fixed `LSD_CS` settings; retain correlation-enabled matching otherwise.
- 100,000 main shots/condition. Preflight seeds 2026114301–4306, main seeds 2026114311–4316, in the same condition order.
- Efficacy replication requires equal-weight macro relative LER reduction >=10%, every cell no worse by more than 5%, and zero invalid escalated syndromes. Report full end-to-end runtime including both matching passes and escalations. The runtime threshold remains known to fail from the first screen; the replication is not an advancement decision.

## Stop rule

Stop before main if circuit/noiseless/decoder checks fail or projected sample-plus-decode time exceeds 300 seconds. Do not tune the flag, decoder settings, or conditions after results.
