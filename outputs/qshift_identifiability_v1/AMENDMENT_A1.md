# IDENT1: build stop and amendment A1

**Status: approved by the project owner on 2026-11-24, as proposed in `AMENDMENT_A1_PROPOSED.md` (commit fe8325d3b).** The build stopped at the first predeclared stop rule. No moment, separation, rejection or harm value has been computed for any support. Nothing was sampled. `PROTOCOL_IDENT1.md` is unchanged.

## What happened

`python split.py` built the signature classes and the split of section 4.

- The classes reproduce `CLASSES_D5.json` exactly: 1,003 classes, all supports and observable flips.
- With the eight grid maps as drafted, the groups chain together. Weight 1-3: one group holds 995 of 1,003 classes (99%). Weight 1-4: one group holds 2,562 of 2,563.
- Section 4's limit is 20%, so the rule is to stop and amend before computing anything else.

**Cause: an error in the protocol.** An X burst triggers only the Z checks. Of the eight grid maps, only the identity and the 180° rotation map signature classes onto signature classes. The other six do not preserve the Z-check layout, so "mirror images" under them are unrelated bursts, and linking them merged almost everything. The protocol's check "every group lies in exactly one half" would not have caught this.

## Change

**Overrides: section 4 (split rule), and section 8 (the Symmetry check). Section 9's rerun rule is applied, not overridden. Every other section stands.**

1. Section 4: "the eight symmetries of the 5×5 data-qubit grid" becomes "every grid map that maps signature classes onto signature classes", which is the identity and the 180° rotation.
2. The split is computed once, on weight 1-4 classes together. The hash rule, the SEEN rule, the 20% limit and all else in section 4 are unchanged.
3. Section 8, Symmetry: additionally, each map used must send every class onto exactly one class.

## Effect, known before approval (structure only)

| | Classes | Groups | Largest group | DESIGN | HELD | SEEN |
|---|---|---|---|---|---|---|
| Weight 1-4 | 2,563 | 1,304 | 2 | 1,182 | 1,297 | 84 |

Of these, 1,003 classes contain a support of weight 1-3 and 1,560 have weight-4 supports only.

**Clarification, no rule change:** 26 supports trigger no detector (4 of weight 2, 22 of weight 4). They cannot be studied through detectors and are excluded. So 12,628 of the 12,650 four-qubit supports are covered, not all of them.

## Disclosure

- The counts above were seen before this amendment was written. They depend on labels and hashes only, and no outcome exists that they could have been chosen against.
- The 180° rotation preserves the classes. Whether it also preserves the full noise model (gate order, time structure) has not been checked. If it does not, rotated pairs sharing a half is only a precaution.
- Under the corrected rule, related but not symmetric bursts (for example neighbouring supports) can fall in different halves. HELD is therefore new supports, not an independent kind of burst.
