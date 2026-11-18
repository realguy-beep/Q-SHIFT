# Failure and blocker analysis

## Exact DEM conversion gate

The proposed mechanism follow-up in the existing Q-SHIFT research-direction materials assumes an alternate non-approximated DEM family. Direct testing on all six Phase 2B circuit conditions shows Stim refuses to analyze the `PAULI_CHANNEL_2` operations unless `approximate_disjoint_errors=True`. The failure happens at circuit conversion, before any sampling. Repeating the call or increasing resources cannot resolve this semantic/API constraint.

A DEM represents independent mechanisms. Mutually exclusive categorical Pauli-pair outcomes are not equivalent to independent fault mechanisms in general. Enabling the approximation changes that representation. Reusing the same approximate DEM with correlation on/off validly isolates the decoder option conditional on that DEM, as the existing pilot did, but cannot attribute any observed interaction to information loss in the conversion.

The existing exact categorical decoder study provides an exhaustive toy reference, but its scalability report estimates 2^609 full-circuit assignments. It has no exact structured inference cost result for the d=3 circuit. Therefore neither unrestricted enumeration nor a direct exact-DEM substitute is presently justified for the full circuit.

## Prior correlation pilot

The prior development pilot showed a favorable aggregate point estimate but failed its prespecified practical gate and contained adverse strata. Selecting a post-hoc same-name regime rule or training a per-syndrome selector on its sparse disagreements would reuse outcomes already inspected. That would be hypothesis generation, not an independent validation. The raw bundles are not present in this worktree, so no secondary reanalysis was attempted.

## External-source access

An attempt to query the arXiv API returned an egress tunnel `403 Forbidden`. The official Stim source documentation on `raw.githubusercontent.com` was reachable. DOI resolution through `doi.org` also returned `403`. The repository contains a prior focused literature comparison with detailed citations, but this expedition has not independently fetched every primary paper or revalidated each 2024–2026 source. Literature claims that depend on unavailable sources remain provisional.

## Categorical sum-product prototype

The first implementation estimated logical parity from the product of individual location beliefs. It achieved LER 0.084708 on the one-qubit exact toy. That calculation incorrectly treated beliefs conditioned on shared detector checks as independent for logical parity. The revised prototype added a global logical-parity factor and compared two Bethe partition estimates. It reduced toy risk to 0.057354 but remained far above exact MAP risk 0.002646, agreeing on only two of four syndromes. On the two-qubit fixture it matched exact MAP, which shows that a single positive toy is not a validation of this method.

Likely issue: the global logical parity factor creates loops in the factor graph, and the Bethe approximation is not accurate enough for the one-qubit fixture. This explanation is consistent with the topology dependence but is not yet proven by an exact Bethe/free-energy derivation or a tree-topology control. The candidate is stopped before circuit evaluation. A follow-up must separate coding errors from approximation error with hand-computable trees and exact toy posterior checks, and should only proceed if all fixtures meet a prespecified risk/decision agreement gate.

## Thresholded DEM sensitivity route

The official Stim CLI permits a maximum probability threshold for approximating disjoint errors. A fixed threshold of 0.001 cannot convert any of the biased conditions because one two-qubit Pauli-pair event has probability 0.00178571. Thresholds 0.0018, 0.003, and 1.0 all convert, but produce identical DEM and matching graph hashes within every condition. This threshold family therefore provides no alternate matching model at the tested probabilities. Changing the gate probabilities or threshold after observing decoder outcomes would be a different study and is not supported by this static check.

## BP+LSD fixed-configuration screen

LDPC 2.4.1 BP+LSD was applied to a binary fault-variable matrix formed from each flattened approximate DEM. This is a representable model for the chosen DEM, and every returned estimate matched its input detector syndrome. However, the three tested LSD method labels all yielded 321 logical failures on 30,000 original-circuit samples, versus 138 for correlation-enabled PyMatching; each lost in all six conditions.

The negative result could reflect low-order BP on loopy checks, a poor binary posterior under the DEM approximation, the chosen min-sum/iteration settings, or differences in how the library's LSD fallback selects among valid fault explanations. The data do not distinguish these causes. Because the output syndromes were valid and the baseline was built from the same approximate model, the comparison is useful as a method feasibility result. It does not test other LSD configurations, larger distances, or a native categorical decoder. No post-hoc tuning was done.

## Importance-sampling scope limitation

The likelihood-ratio estimator is exact for the Bernoulli mechanisms represented in the flattened DEM. The source circuit contains categorical two-qubit channels whose exact non-approximated DEM conversion is blocked. Applying the exact DEM weight ratio therefore estimates risk under the chosen approximate surrogate, not under the source circuit's categorical distribution. The lower variance and replication stability cannot remove that model discrepancy. A future circuit-level rare-event method must expose and reweight mutually exclusive local Pauli outcomes directly, then reproduce direct-sampling rates in an overlap region before extrapolation.
