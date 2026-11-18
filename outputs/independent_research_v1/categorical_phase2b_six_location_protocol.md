# Exact six-location native-categorical Phase 2B layer

## Authorized bounded expansion

The separate structural preflight on all six target pairs in the final d=3, five-round Z-memory/X-biased-10:1 `PAULI_CHANNEL_2` layer passed the fixed 1,000,000-entry cap: 10 touched detectors, induced width 4, predicted max factor 131,072. This permits one deterministic exact-inference screen on the full six-pair layer.

## Validation

- Retain all 16 categorical outcomes and the exact source probability vector at each of the six target pairs; identity is the remaining channel mass.
- Derive local detector/logical signatures by forced deterministic Pauli insertion and raw-record parity relative to a shared noiseless source circuit.
- Cross-check combined signatures on 512 deterministic assignments.
- Build a separate exact XOR-convolution reference over all 16^6 configurations, aggregating equal (syndrome, logical) states at each step. This reference is independent of factor elimination and does not materialize all assignments.
- Compare VE with the reference on every reachable syndrome and both logical classes; report posterior normalization, aggregate MAP risk, width, and maximum dense-factor entries.
- Stop at the 1,000,000-entry cap. Do not add circuit layers or other noise classes in this screen.

## Scope

This is the full six-pair channel layer only, with all other circuit noise set to identity. It is not full-circuit Q-SHIFT decoding, a matched decoder comparison, or a stochastic LER estimate. No stochastic circuit shots are generated.
