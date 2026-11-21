# Q-SHIFT response-gap review

**The first useful target is next-block switching for a plausible, prebuilt decoder.** Replace AD3's “alarm, then recall if not rejected” rule with directional change diagnosis, a separate margin for identifying the new state, and a switch only when the new key has a development-calibrated logical-risk advantage. Keep a strong pooled static key available when the observations are ambiguous. Test the approach with AD3 and strong static on exactly the same rows. [Recommended approach](RECOMMENDED_APPROACH.md)

AD3's weak intermittent schedule is the most informative case. Within that run, AD's 2,279 errors fell to 1,751 with AD3, versus 178 with the privileged current-state reference. AD3 halved the historical median from four to two blocks, yet 523 of the 528 avoided errors came from the repeat ON segment. First ON stayed at three to five blocks. In the 24 larger or combined-change transitions, the alarm index equalled the change index every time, but median action recovery stayed at four to five blocks under AD3's six-block requirement. The current analysis recount also corrects S2 alarm attribution to **14/24 same index, 17/24 by the next index, seven unmatched before the next change**. The frozen prose and decisions are preserved. [Root-cause audit](RESPONSE_GAP_ROOT_CAUSE.md)

Under the current interface, the first changed block is usable only after it is observed. **One block is the reactive minimum and an observed outcome in some events.** Reliably achieving it for a novel support is unproven. In S2's model, even an ideal test at 1% false and 90% correct needs at least 46 fresh rows for ON and 90 for OFF, a loose limit derived from the probability that zero burst faults occurred. Actual syndrome overlap can require more. Sub-block control would need ordered calibration prefixes, labels available in time where used, and evaluation on later shots. A system with no predictive side information cannot reliably react at onset. [Mathematical feasibility](MATHEMATICAL_FEASIBILITY.md)

The proposed decision experiment randomizes timings while fixing the policy and action-cost tradeoff before independent held-out development. It tests paired unconditional LER against AD3 and pooled static, the timely recurrent-ON fraction, and stationary harm and false switches. It reports first ON, return, OFF, unseen-support and transient performance separately. A quicker alarm alone cannot pass. The initial development screen can end the project early if the state score cannot reliably separate weak ON/OFF from alternatives or if prospective switches fail to change logical predictions usefully. [Validation design](PREREGISTERED_VALIDATION_PLAN.md)

| Decision | Candidate |
|---|---|
| Primary | Directional decoder-bank selection with explicit abstention and separate risk gate |
| Conservative alternative | Pooled robust static during uncertainty, with a validated last-good hold only where it helps |
| Ambitious direction | Ordered prefix control using jointly calibrated evidence and a separate false-switch validation |

## Reports and verification

- [Root cause and causal timeline](RESPONSE_GAP_ROOT_CAUSE.md)
- [Literature review](LITERATURE_REVIEW.md)
- [Mathematical feasibility](MATHEMATICAL_FEASIBILITY.md)
- [Candidate decision matrix](CANDIDATE_METHOD_MATRIX.md)
- [Recommended approach](RECOMMENDED_APPROACH.md)
- [Proposed preregistration](PREREGISTERED_VALIDATION_PLAN.md)
- [Pinned evidence and primary references](REFERENCES.md)

**21 November 2026 checkpoint.** Base `8c3ac5ee4ec3eb98d408b4053cbd81e3f73efb17`. All eight reports under `outputs/qshift_response_gap_research_v1/`. Historical research worktrees were accessed through committed Git content. This sprint generated zero shots, opened no sealed outcome material, and executed no project experiment, replay or test. Arithmetic checks used the public committed episode ledger, pinned Git blobs and formula substitution. Historical recount documents report reanalysis and selected replays. Direct fresh-checkout byte verification has the AD3 line-ending exception documented in the root-cause report.

- ☑ Scope and publication base verified against origin.
- ☑ Historical source and results reviewed, with arithmetic totals and event matching checked on all 60 public episode records.
- ☑ Primary literature, mathematical limits and candidate ranking documented.
- ☑ Decision protocol and publication checks prepared. Future validation needs a separate execution decision.

Further uncertainty comes from six historical roots per schedule, finite and selected public footprints, conditional simulation labels, and a specific circuit and decoder engine. The numerical recap diagnoses where delay cost errors. It does not quantify how many of those errors an untested controller will avoid.
