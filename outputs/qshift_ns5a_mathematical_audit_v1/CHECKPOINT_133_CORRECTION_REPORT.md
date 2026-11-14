# Checkpoint 133 correction report

## Scope and preservation

This is a versioned correction package. The research package at `outputs/qshift_method_landscape_research_v1/` was not edited. In particular, the original checkpoint-133 source, `EFACTOR_FIXEDPOINT_MIXTURE_AUDIT_PRE_THRESHOLD_FIX.json`, `EFACTOR_FIXEDPOINT_MIXTURE_AUDIT.json`, `RESEARCH_LOG.md`, and their recorded hashes remain historical evidence. This report corrects the interpretation and supplies an independent deterministic implementation; it does not rewrite the historical record.

## Defect

For a nonnegative e-process and target false-alarm probability `alpha`, Ville's threshold is `1/alpha`. At `alpha=1/20`, the alarm threshold is 20. The historical code instead used

```text
e_low * alpha.denominator >= SCALE * alpha.numerator
```

which is equivalent to `e_low/SCALE >= alpha`, i.e. `E >= 0.05`. It is not the `E >= 20` alarm predicate. The same mistake appears in the implication guard, so the saved assertion established implication for the wrong, much weaker threshold. Consequently the checkpoint-133 reported crossing count of 5,184 comparisons per direction is unsupported as an alarm-crossing result.

## Correct comparison

Write `alpha=a/b`, `Q=SCALE`, and `E_lower=e/Q`. Then

```text
E_lower >= 1/alpha
<=> e/Q >= b/a
<=> e*a >= Q*b.
```

The corrected implementation is `lower_integer * alpha.numerator >= scale * alpha.denominator`. The exact-rational reference compares `E >= 1/alpha` directly. Tests cover 19, 20, and 21 at alpha 0.05, plus an alpha 0.2 cross-check.

## Corrected exhaustive result

The independent audit reads only exact rational model-envelope values from `EXACT_THREE_PARAMETER_EFACTOR_ENVELOPE.json`; it reconstructs the two six-factor tables and checks every abstract category prefix of lengths 1–4. Per direction this is 1,554 distinct prefixes, with an exact recurrence/direct-mixture equality check and a fixed-point lower-bound check on each prefix. It also reproduces the historical loop shape: 1,296 length-four sequences, each evaluated at four prefixes (5,184 comparisons, including suffix duplicates).

| Direction | Distinct prefixes crossing at E ≥ 20 | Historical-loop prefix hits after correction | Length-4 sequences with any crossing |
|---|---:|---:|---:|
| Upward | 239 | 244 | 238 / 1,296 |
| Downward on `1-X` | 0 | 0 | 0 / 1,296 |

Exact-mixture and fixed-point-lower-bound crossing counts agree in this finite enumeration; every tested lower value is at most the exact value. The prior 5,184 count is therefore replaced by the values above for this abstract fixture. These are combinatorial properties of a bounded list of category-factor sequences—not probabilities, observed detector histories, alarm rates, power, or delay evidence.

## Integer and rounding audit

The prototype uses `Q=2^96`, floors each nonnegative factor, start weight and remaining prior tail, and floors each recurrence product divided by Q. By induction, each stored scaled component and their sum are lower bounds; they cannot create a threshold crossing that the exact mixture lacks. Down-rounding may suppress a real crossing. Python integers are arbitrary precision, so this audit does not establish overflow safety for a C/C++/embedded port. The largest intermediate product in this bounded enumeration uses 199 bits upward and 192 bits downward; a 128-bit multiply is already insufficient for the tested upward fixture. Saved checkpoint 137 separately reports that the quantized start weight first becomes zero at `s=281,474,976,710,656`; a zero-weight start has no delay guarantee. Fixed-width multiplication, time counter limits, persistence, and a deployed numerical implementation remain unverified.

## Differences from checkpoint 133

1. Threshold is corrected from alpha to `1/alpha`.
2. An independent exact `Fraction` implementation computes the one-change mixture by direct component sum and by recurrence.
3. Exact below/equal/above threshold cases and a non-default alpha are tested.
4. All distinct prefixes through length four are counted separately from the repeated-prefix historical loop.
5. Crossing counts are recomputed without assuming a crossing exists; downward has zero at this horizon.
6. The interpretation is restricted to abstract factor arithmetic; no detector sequence or stochastic evidence is introduced.
