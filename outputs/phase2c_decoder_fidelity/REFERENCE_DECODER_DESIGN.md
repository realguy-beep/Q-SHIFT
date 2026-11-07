# Reference Decoder Design

## Purpose

Phase 2B's PyMatching bank decodes Stim's DEM, not the exact mutually exclusive circuit-level categorical Pauli distribution. The Phase 2C reference is a detector-only statistical approximation to the conditional probability of the logical observable.

## Method

For each memory basis and assumed generator composition, draw a fresh 60,000-shot training sample from the actual Phase 2B Stim circuit. Fit a RandomForestClassifier with the frozen configuration in `config.json`, using 40 binary detector bits as features and the one observable bit as target. At inference the model calculates a vote fraction approximating `P(L=1 | D)` and predicts correction 1 only when this probability is strictly above 0.5. No hidden regime, physical error locations, or current observable is supplied to inference.

The training distribution is the actual categorical channel simulator, including within-gate two-qubit Pauli-pair outcomes. The posterior estimate is limited by finite training data, forest approximation, rare logical events, and imperfect probability calibration. It is therefore a more channel-faithful *empirical posterior surrogate*, not an exact decoder and not proof of optimal decoding.

## Calibration and comparators

An independent 10,000-shot calibration sample for each generating condition selects (a) one global fixed reference forest per memory basis by equal-regime mean LER and (b) one candidate separately per calibration regime. Candidate order and ties are frozen. The latter is an informed reference using regime identity, not an adaptive policy. All candidate decoders process the same held-out detector shots.

## Exact small-case validation

`exact_toy.py` enumerates products of finite categorical location outcomes, XOR-combines detector masks and logical bits, and returns exact joint/posterior likelihoods. Tests cover a known ambiguous syndrome, independent-event composition, normalization, and invalid distributions. This establishes correctness for toy examples only; it does not enumerate the full surface-code circuit.
