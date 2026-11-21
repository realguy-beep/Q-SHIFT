# What delayed AD2 and AD3?

## Evidence and scope

AD2 and AD3 are separate development studies at distance 5, five rounds and 120 detectors. The public weight-three X-burst supports A–D affect 10, 20, 25 and 30 detectors respectively in the recorded footprints. A burst is enabled at q = 0.01 after each of five measurement/reset boundaries. Background gate and measurement probability is 0.003 except S3, where both step from 0.0025 to 0.0035. Each study used six independent episode roots per schedule, 30 blocks per episode, and 1,000 shared evaluation rows per scored block, blocks 6–29. Each arm thus has 144,000 scored rows per schedule. Within AD3, AD is the AD2 policy run on the fresh AD3 rows. AD2 versus AD3 across separate runs is descriptive. See [Q1–Q6](REFERENCES.md#q-shift-evidence).

The response gap has two observable parts. The action gap is time from the noise transition to a useful decoder choice. The loss gap is logical errors with a deployable controller minus the same decoder engine's errors when given true current noise and burst support. The privileged reference is a benchmark for model information in BP+OSD. It is neither a deployable baseline nor a theorem about the optimal decoder.

## What the controller knew

| When | Information and action |
|---|---|
| Before choosing for block t | The policy may use 2,000 unlabelled detector rows and 250 separate detector/observable calibration rows from each completed prior block. Both loops generate the current calibration streams early, but their estimator slices exclude t. Evaluation detector rows are passed to the selected decoder after the model choice. Paired evaluation observable labels score the predictions. |
| AD2 chooses | The six previous blocks feed the background fit and detector-parity support-class learner. The separate calibration labels resolve the observable flip within the detector-equivalent class. E1T can reject the fit and send the main AD arm to the nominal model. AD_LG instead retains the last accepted model on flags. |
| AD3 observes and chooses | At the start of iteration t ≥ 2, AD3 scores u = t−1 against up to six earlier blocks in the current segment. A summed marginal binomial statistic G above 163.13055 resets the segment at u. The earliest affected decode is t = u+1. With M=6, the short segment estimator cannot run. The short route is recall of a previously accepted class/flip entry if its G is below the cutoff. Otherwise AD3 uses AD. |
| Truth and runtime | True support passes through the estimator API for correctness annotation. In the inspected learner the truth comparison follows class/flip selection. True current noise enters the simulation schedule and separately the oracle arm. Runtime caches decoder/model keys, but delay reports count blocks and do not identify wall-clock cost of model activation. |

Source chain: `ad2.py` `episode_job`, `advance`, `latencies`, `ad3.py` `g_stat`, `recall`, `episode_job`, `ad1.py` `estimate_window`, `brt.py` `learn` and `estimate4.py`/`estimate5.py` guards [Q1, Q2, Q5, Q6](REFERENCES.md#q-shift-evidence). “Detector-only” applies to the change statistic and class evidence. Relearning the entire model here uses labelled calibration for the flip. Hardware availability of analogous labels is a separate research question.

## Measured delay and logical loss

Historical acquisition is the first scored block b > c (c is true change block) with accepted exact class and flip, evaluated against the most recent history block. OFF credits either a flag or no learned class. AD2's median encodes missing as 99. The legacy search can scan beyond the next transition, and it records neither sustained recovery nor the first decoder key change. The observed acquisition/release records in the table stayed inside their actual segments. The separate alarm-delay matcher does cross transitions. See [Q3–Q6](REFERENCES.md#q-shift-evidence).

| Schedule | AD2 historical median, blocks | AD → AD3 on AD3 rows, blocks | AD2 AD / oracle errors | AD3 AD / AD3 / oracle errors |
|---|---:|---:|---:|---:|
| C0 A stationary | — | — | 270 / 273 | 346 / 346 / 253 |
| S1 A→B | 4 | 4 → 4 | 354 / 157 | 397 / 397 / 156 |
| S2 OFF→A→OFF→A→OFF | 3.5 | 4 → 2 | 2,048 / 187 | 2,279 / 1,751 / 178 |
| S3 A→C and background step | 5.5 | 5 → 5 | 323 / 188 | 312 / 312 / 194 |
| S4 B→C→D | 4 | 4 → 4 | 258 / 116 | 234 / 234 / 98 |

AD2 beat ONCE and PERIODIC across four changing schedules under its historical rule. AD3 passed F1–F4, and met the ≤2-block F5 target only on S2. S1/S3/S4 had 24/24 same-index alarms, yet their per-block error counts agreed with AD. Different represented decoder keys did occur on 4, 6 and 1 scored blocks respectively. Equal error counts alone cannot establish equal predictions. On S2, the paired decrease of 528/144,000 is 0.3667 percentage points (23.17% of AD errors). The historical episode bootstrap interval was −0.5431 to −0.1847 points. It has six roots and is specific to this comparison. AD3 removed 25.13% of AD's excess over the oracle and retained 1.0924 points of excess (1,573 errors). [Q3, Q4](REFERENCES.md#q-shift-evidence)

### S2 events recounted from 24 transition instances

Each row aggregates six independent episodes and 36,000 evaluation rows. Alarm matching takes the first alarm u with c ≤ u < next change, or end of available checks. “Next index” counts u=c+1 only. Each alarm can be credited at most once.

| Transition | Same index | Next index | Unmatched in segment | AD errors | AD3 errors | Oracle errors |
|---|---:|---:|---:|---:|---:|---:|
| Block 6, first ON | 2 | 1 | 3 | 1,195 | 1,195 | 66 |
| Block 12, first OFF | 4 | 0 | 2 | 34 | 32 | 27 |
| Block 18, recurrent ON | 5 | 1 | 0 | 1,023 | 500 | 69 |
| Block 24, second OFF | 3 | 1 | 2 | 27 | 24 | 16 |
| Total | 14 | 3 | 7 | 2,279 | 1,751 | 178 |

The published AD3 prose says 15/24 same-index, 18/24 within two observed blocks and two undetected. The committed delay list has 14 zeros, three ones, four sixes, one twelve and two nulls. The five long matches are alarms in later S2 segments. Corrected counts are **14/24 same-index, 17/24 by the next index and seven unmatched within their segment**. The historical verdict is left as recorded. C0 had two alarms across 168 comparisons in six episodes (two episodes with an alarm). Comparisons within an episode share reference rows and reset state. [Q4, Q6](REFERENCES.md#q-shift-evidence)

The repeat ON accounted for 523 of the 528 avoided S2 errors. On that recurrence, before AD3 first accepted the target (10 episode-blocks), AD3 and AD each made 449 errors versus 18 for oracle. At and after first acceptance (26 episode-blocks, through the segment end), AD3 made 51 versus AD's 574 and oracle's 51. First ON stayed at 3–5 blocks with both policies, with 1,180 AD3 errors before first acceptance versus 51 oracle, then 15 versus 15. For settled blocks under the six-block history rule, AD/AD3 and oracle made 138/138 (S1), 151/153 (S3) and 54/53 (S4) on AD3 rows. S2 has no such blocks by construction. These subdivisions condition on realized calibration and are descriptive. At the four S2 change indices themselves, AD3 made 562 errors against 36 oracle errors. The 526 difference describes that policy, including the unchanged-action blocks. It is no bound on a different first-block fallback. [Q3, Q4, Q6](REFERENCES.md#q-shift-evidence)

## Mechanisms and uncertainty

- **Novel state after a clear alarm.** AD3 often detected enough evidence for “different” at the first opportunity without having a short-window decoder model it could accept. Its screen gave exact-and-unflagged recovery of 1/80, 20/80 and 48/80 for one, two and three burst-ON blocks, with flags 55/80, 54/80 and 29/80. Among unflagged windows, exact recovery was 1/25, 20/26 and 48/51. Those are pooled screen results at static states, with separate OFF cases. Three-block A was 20/20, B 17/20, C 5/20 and D 6/20. The screen does not show which flagged models would have been correct before rejection. A small-window fit and the acceptance rule both need diagnosis. AD2's three-block descriptive arm was dropped by preflight after the S1 rehearsal exposed flags and cost. The main AD2 study did not test it. [Q1, Q2, Q7](REFERENCES.md#q-shift-evidence)
- **Weak intermittent state.** The 10-detector A shift had change-index G ranges 147–172, 156–235, 144–206 and 139–200 for the four events, against τ≈163. The six-block rolling window blends regimes for most of a short segment. Detection and model availability both mattered. Nothing here separates irreducible syndrome overlap from loss of information in the marginal score or the fitting rule. S3 combined background and burst changes in one condition, which precludes attributing its delay to either component in isolation. [Q3, Q4, Q7](REFERENCES.md#q-shift-evidence)
- **Recall and fallback.** AD3's recall cutoff reuses the alarm threshold even though recall uses a variable short segment and a selected library entry. Non-rejection is weak evidence of a match. As an illustration of fallback cost, AD and AD3 each made 346 C0 errors against ONCE's 250. Two flagged blocks in one root account for the 96 difference. F3 compared AD3 with AD, so its pass did not establish protection against a strong static method. AD_LG helped transition loss in S1 by the AD2 criterion and was close overall, but it also retains the old support after real changes. [Q3, Q4, Q6](REFERENCES.md#q-shift-evidence)
- **Compute.** In the archived AD3 episode timings, median estimated workload totals divided by 24 scored blocks are about 57 s for C0 and 47 s for S2, with the historical worker concurrency. That timing includes the shared slow fit and excludes the separately timed decoding and the alarm at loop start. It cannot measure alarm-to-activation or per-shot production latency. Decoder prebuilding addresses that wall-clock question while preserving the block-level causal floor. [Q2, Q4, Q6](REFERENCES.md#q-shift-evidence)

## Reproducibility notes

Read the pinned plans, protocols, implementations, freeze metadata, preflights, screen, run status, timeline summaries, aggregate results and recount reports. A fresh arithmetic recount summed the per-block arm integers in 30 public episode records per study and matched every schedule total. Grouped blocks by the transition indices above, excluding the next change. Each committed historical recount reports identical reanalysis and five episode-0 decoded-bit replays. This review used committed summaries and did no replay or sampling.

Eight selected AD2 freeze entries and nine of ten selected AD3 entries match SHA-256 over the original committed blobs. The tenth AD3 entry, `ad3.py`, has LF Git blob SHA-256 `febfd05518fe610030a62b6074fe23af66410ef87cf5bae8c8bc00e697fcb368`. Re-encoding its 480 LF endings as CRLF reproduces the manifest SHA-256 `98f5a62bc0b691c49a978278cea0bd19b15ae9d0c06ace614c224ff1b9520b4b` exactly. The original guard checks working-tree bytes, while `.gitattributes` declares LF for Python. This identifies a line-ending portability issue for a strict clean checkout. It leaves the historical execution environment unverified here. The two `RUN_STATUS.json` artifacts name the expected freeze commits and 30 jobs each. No historical hashes were edited. See [Q1–Q4, Q8](REFERENCES.md#q-shift-evidence).
