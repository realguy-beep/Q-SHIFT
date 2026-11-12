# Fair baseline matrix for a later authorized study

This is a design recommendation only. **No arm below was sampled or run.** The HAMLD arm is blocked by the deterministic preflight and must not be activated until the exact pinned implementation and an adapter pass compatibility tests.

## Arms and information parity

| Arm | Decoder/input model | Information | Role |
|---|---|---|---|
| PM nominal | PyMatching on existing Q-SHIFT DEM at `p_burst=0`; ordinary decode and explicit-correlation variant separated | Public frozen circuit/noise assumptions | Mandatory fixed incumbent |
| PM static tuned | PyMatching on candidate fixed burst-aware DEM selected using detector-only features on independent tuning roots | Same development detector availability and tuning allocation as other deployable arms | Strong static primary comparator; selection rule must be frozen before evaluation |
| PM correlation ablation | Same burst-profile DEM/weights as above; construct matching with `enable_correlations=True`, then explicitly decode with `enable_correlations=True`; pair against both ordinary graph/ordinary decode and exact mode pairings | Same DEM and same detector rows | Correlation-mode diagnostic; not a separately tuned baseline |
| HAMLD deployable candidate | Same original Stim circuit and detector-only selected nominal/burst profile; likely `decompose_errors=False` DEM, after direct input path is validated | No true hidden p; profile selection only from permitted detector-only tuning streams | Distinct inference comparison, currently blocked |
| Privileged reference | PyMatching/HAMLD using the true generating parameter, only if separately useful | Receives true hidden noise parameter | Oracle diagnostic only; never included among deployable comparisons |

Keep `enable_correlations` configuration explicit at both PyMatching graph construction and `decode`/`decode_batch`. PyMatching's flag is designed for decomposable error mechanisms; do not infer that it models arbitrary categorical or higher-order circuit correlations exactly. The DEM's Stim `approximate_disjoint_errors=True` choice must be held constant across PM correlation arms and disclosed.

## Matching tuning rule to freeze

Before any evaluation outcomes are generated, specify: (1) exact candidate `p_burst` grid; (2) exact condition mixture and per-condition detector-only calibration allocation; (3) exact 45-feature discrepancy and scaling; (4) deterministic tie-break; (5) whether one shared p or stratum-specific profiles are allowed; (6) number/identity policy for fresh tuning roots; (7) graph-cache budget and construction time; (8) one frozen selected profile. No evaluation labels or evaluation detector histories enter selection. If a label-selected static decoder is shown, mark it privileged/secondary.

The HAMLD arm must receive the same detector-only selected profile/noise parameters as the static PM baseline. Its native undecomposed DEM and PyMatching's decomposed matching DEM are not literally the same approximation; record both conversions, their Stim flags and mechanism counts, and do not attribute any effect solely to inference until this representation difference is understood. Do not give HAMLD the true burst rate while comparing it to an estimated-PM arm. A separately privileged true-p pair can bound model-oracle potential but is not an algorithm comparison.

## Chronology, pairing and estimand

Every decoder receives the identical held-out development detector matrix in shot order; all are scored on the identical observable array. Use fresh independent root IDs and report root-level paired logical-error difference `candidate − tuned PM` by condition plus the prespecified equal-condition average. Keep tuning roots disjoint from evaluation roots. Confidence intervals and tests cluster at roots; shot discordance is descriptive/variance input, not an independent sample size. Distinguish the development decoder comparison from later independent confirmation. If a decoder makes identical predictions to another, record identity; do not count it as a separate effective method.

## Stop/go gates

First require deterministic parsing/semantics tests: DEM instruction and separator preservation; probability-weight transformation; duplicate mechanism aggregation; detector and L0 mapping; all-zero, one-hot/single-fault, boundary and logical-fault convention; exact prediction output dimensions; parity consistency; and reproducible clean build. For HAMLD source reviewed here, these gates fail. Only after repair and review should a development authorization be considered. No result from these arms is authorized by this protocol document.
