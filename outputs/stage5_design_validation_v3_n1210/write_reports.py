"""Render concise reports from the independently audited design-MC outputs."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
a=json.loads((HERE/'DESIGN_MC_RESULTS.json').read_text(encoding='utf-8'))
audit=json.loads((HERE/'INDEPENDENT_AUDIT.json').read_text(encoding='utf-8'))
h=json.loads((HERE/'secondary_holm/SECONDARY_HOLM_RESULTS_REPAIR_V1.json').read_text(encoding='utf-8'))
ha=json.loads((HERE/'secondary_holm/SECONDARY_HOLM_AUDIT_REPAIR_V2.json').read_text(encoding='utf-8'))

def pct(x): return f'{100*x:.3f}%'
def row_table(headers,rows):
 out=['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']
 out += ['| '+' | '.join(str(x) for x in row)+' |' for row in rows]
 return '\n'.join(out)

nullrows=[]
for r in a['primary_null_validation']:
 ok=(r['type1_wilson95'][1]<=.052 and r['upper_bound_coverage_wilson95'][0]>=.94 and r['central_interval_coverage_wilson95'][0]>=.94)
 nullrows.append([r['scenario'],pct(r['type1']),pct(r['type1_wilson95'][1]),pct(r['upper_bound_coverage_wilson95'][0]),pct(r['central_interval_coverage_wilson95'][0]),'PASS' if ok else 'FAIL'])
powerrows=[]
for r in a['primary_power']:
 gate='Formal' if r['formal_gate'] and r['true_delta']==-.0003 else 'Sensitivity'
 powerrows.append([r['scenario'],f'{r["true_delta"]:.4f}',pct(r['power']),f'{pct(r["power_wilson95"][0])}–{pct(r["power_wilson95"][1])}',gate])
p0null=[]
for r in a['p0_null_validation']:
 ok=r['type1_wilson95'][1]<=.052 and r['upper_bound_coverage_wilson95'][0]>=.94
 p0null.append([r['scenario'],pct(r['type1']),pct(r['type1_wilson95'][1]),pct(r['upper_bound_coverage_wilson95'][0]),'PASS' if ok else 'FAIL'])
holmrows=[]
for r in h['complete_null_holm_fwer']:
 holmrows.append([r['scenario'],f'{r["holm_family_rejections"]:,}/200,000',pct(r['holm_familywise_rate']),pct(r['simultaneous_wilson_upper']),pct(.052),'PASS' if r['pass'] else 'FAIL'])
summary={
 'allocation_roots_per_condition':1210,'projected_stage5_shots_if_later_authorized':27225000,
 'stage5_shots_generated':0,'sealed_test_accessed':False,
 'primary_critical_values':a['primary_critical_values'],
 'primary_gate_decision':a['decision'],
 'primary_null_max_wilson_upper':max(r['type1_wilson95'][1] for r in a['primary_null_validation']),
 'primary_min_one_sided_coverage_lower':min(r['upper_bound_coverage_wilson95'][0] for r in a['primary_null_validation']),
 'primary_min_central_coverage_lower':min(r['central_interval_coverage_wilson95'][0] for r in a['primary_null_validation']),
 'power_at_minus_0_0003_min_1_5x':min((r for r in a['primary_power'] if r['true_delta']==-.0003 and r['sd_multiplier']==1.5),key=lambda r:r['power_wilson95'][0]),
 'power_at_minus_0_0003_min_2x':min((r for r in a['primary_power'] if r['true_delta']==-.0003 and r['sd_multiplier']==2.),key=lambda r:r['power_wilson95'][0]),
 'secondary_holm_validation_pass':h['overall_secondary_validation_pass'],
 'secondary_holm_audit':ha['gates'],
 'overall_readiness':'NO-GO: secondary Holm procedure fails finite-envelope Type-I/FWER checks under skewed and tied root effects',
 'production_design_mc_seconds':a['run_seconds'],'primary_independent_audit_seconds':audit['audit_runtime_seconds'],
 'holm_mc_seconds':h['runtime_seconds'],'holm_independent_audit_seconds':ha['runtime_seconds']}
(HERE/'DESIGN_VALIDATION_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')

report=f'''# Stage 5 n=1,210 allocation: statistical design validation

## Decision

**NO-GO for Stage 5 sampling readiness.** The primary Endpoint B procedure and allocation pass their prespecified finite-envelope size, coverage, and formal power gates. The required condition-level Welch/Holm family fails under right-skew and tied/asymmetric nulls. No Stage 5 runner or sampling inventory was prepared; the Stage 5 sampling command was not run.

This is design simulation only. The proposed 1,210-root allocation projects to **27,225,000** Stage 5 calibration/evaluation shots if separately authorized. This validation generated **zero** Stim/Stage 5 shots and did not access sealed test outcomes.

## Frozen primary design

The estimand is the equal-weight average of four nonzero-condition, root-level paired adaptive-minus-fixed LER differences. Practical boundary: −0.0002. Planning alternative: −0.0003. Root-level distributions use the historical provisional condition SDs (derived from seven roots) scaled by 1.5× or 2×. The calibrated studentized-mean method and Wilson-bound criteria were not changed. Eleven primary null scenarios were used for separate critical-value calibration and independent validation; 20 power cells cover five 1.5× and five 2× families at effects −0.0003 and −0.0004. The missing 2× zero-inflated power family was included.

Primary calibration criticals at n=1,210: one-sided **{a['primary_critical_values']['one_sided_critical']:.6f}**; central lower **{a['primary_critical_values']['central_lower_critical']:.6f}**; central upper **{a['primary_critical_values']['central_upper_critical']:.6f}**. Each null and power cell has 100,000 replicates.

### Primary boundary-null size and coverage

Pass requirements per null scenario: Wilson 95% upper bound for type-I ≤5.2%; one-sided upper-bound coverage Wilson lower bound ≥94%; central interval coverage Wilson lower bound ≥94%.

{row_table(['Null scenario','Type-I','Type-I Wilson upper','One-sided coverage Wilson lower','Central coverage Wilson lower','Gate'],nullrows)}

All 11 primary null cells passed. Worst type-I Wilson upper: **{pct(summary['primary_null_max_wilson_upper'])}**. Lowest one-sided coverage lower bound: **{pct(summary['primary_min_one_sided_coverage_lower'])}**. Lowest central coverage lower bound: **{pct(summary['primary_min_central_coverage_lower'])}**.

### Primary power

The formal gate from the prior protocol is the 95% Wilson lower bound ≥80% at −0.0003 in all five 1.5× scenarios. The prior protocol labels 2× cases as sensitivity, so this report does not relabel them as a new formal gate; all were nevertheless simulated. `zero_inflated65_q2` is explicitly present.

{row_table(['Root-effect scenario','True effect','Power','95% Wilson interval','Status'],powerrows)}

The formal 1.5× power gate passed in all five cells. The lowest power Wilson lower bound was **{pct(summary['power_at_minus_0_0003_min_1_5x']['power_wilson95'][0])}** for `{summary['power_at_minus_0_0003_min_1_5x']['scenario']}`. At 2×, all five −0.0003 sensitivity lower bounds also exceeded 80%; the lowest was **{pct(summary['power_at_minus_0_0003_min_2x']['power_wilson95'][0])}** for `{summary['power_at_minus_0_0003_min_2x']['scenario']}`. These are operating characteristics under the simulated root-effect families, not forecasts guaranteed for real Stage 5 roots.

### p=0 no-harm endpoint

{row_table(['p=0 null scenario','Type-I','Wilson upper','Upper-bound coverage Wilson lower','Gate'],p0null)}

The separate p=0 calibration critical was **{a['p0_calibration']['one_sided_critical']:.6f}**. All four null size/coverage cells passed. All eight p=0 safety-pass simulations (four distributions × true effects 0 and +0.0001; 100,000 each) had 100,000/100,000 passes, with Wilson lower bound 99.996%.

## Required secondary Holm family — failure

The Stage 5 candidate’s saved implementation uses one-sided Student-t/Welch-reference p-values for four condition-level differences and Holm adjustment at .05. This exact procedure was evaluated at 200,000 complete-null family replicates per scenario. Each family contains four independent condition-root vectors with the frozen unequal SDs. The ten scenarios cover the five root-effect families at 1.5× and 2×. Marginal p-values were also checked at each Holm step threshold with simultaneous one-sided Wilson bounds across 160 marginal checks.

{row_table(['Complete-null family','Holm rejections','FWER','Simultaneous Wilson upper','Required upper ≤5.2%','Gate'],holmrows)}

Right-skew lognormal FWER was **9.3815%** at 1.5× (18,763/200,000; simultaneous Wilson upper 9.551%) and **9.3350%** at 2× (18,670/200,000; upper 9.504%). Tied/asymmetric FWER was **6.8360%** at 1.5× and **6.9295%** at 2×. Therefore the Holm family fails its 5.2% operating bound. At the .05 marginal threshold, the right-skew 1.5× example had 13,985/200,000 rejections (6.9925%; simultaneous upper **7.1901%**, allowed upper 5.2%).

Independent replay reproduced all 160 marginal rejection counts and all 10 familywise counts exactly. The audit’s Holm gates are false. This is a method failure under the prespecified skewed/tied finite envelope, not a serialization artifact. Earlier serialization and audit-schema failures and their repaired versions are retained alongside the successful evidence.

## Independent audit and resource record

- Primary design simulation: 58 cells × 100,000 replicates; 612.57 seconds; final process RSS 102,903,808 bytes (this is a completion-time RSS reading, not a sampled peak).
- Primary independent audit: full seeded replay of 11 critical-value calibration cells, 11 primary null cells, 20 power cells, and 16 p=0 cells; exact counts and cutoffs matched; 568.48 seconds.
- Secondary Holm simulation: 10 families × 200,000; 245.24 seconds.
- Secondary independent audit: 160 marginal checks and 10 familywise cells replayed with exact counts; 247.17 seconds.
- Design-only primary seed inventory: 65 unique streams, zero collisions against 11,370 distinct large integers found in the explicit nonsealed metadata allowlist.
- Secondary inventory: 10 unique streams, zero collisions against 11,436 distinct large integers, including the parent design streams/results.
- Historical Stage 5 v2, Stage 4C, Stage 5 design v2, and the prior final decision memo hashes were verified and preserved by the freezes/audits.

## Limits

These simulations assess only the stated finite envelope. The SD values come from seven roots and remain uncertain; operating-characteristic validation cannot fix that. The root-effects are synthetic summary differences, not Stim-generated shots. Passing primary power does not establish a real decoder benefit. The secondary-test failure blocks the complete Stage 5 statistical package under the current protocol. No acceptance threshold or effect was changed, and the allocation was not increased.
'''
(HERE/'STATISTICAL_VALIDATION_REPORT.md').write_text(report,encoding='utf-8')

holmdoc=f'''# Secondary condition-level Welch/Holm validation

## Result: FAIL

The Stage 5 candidate’s existing one-sided Student-t/Welch-reference p-values followed by a four-test Holm adjustment were tested under ten complete-null synthetic root-effect families at n=1,210. Each scenario used 200,000 independent family replicates. The exact sampled seeds and family definitions are in `SECONDARY_HOLM_SEED_INVENTORY.json` and `SECONDARY_HOLM_CONFIG.json`.

{row_table(['Null family','Rejected families / 200,000','FWER','Simultaneous Wilson upper','Gate'],[[r['scenario'],f"{r['holm_family_rejections']:,}/200,000",pct(r['holm_familywise_rate']),pct(r['simultaneous_wilson_upper']),'PASS' if r['pass'] else 'FAIL'] for r in h['complete_null_holm_fwer']])}

The FWER upper-bound requirement was 5.2%. Both right-skew lognormal conditions and both tied/asymmetric conditions failed. In the right-skew 1.5× condition, FWER was 9.3815%; in the right-skew 2× condition it was 9.3350%. The tied/asymmetric rates were 6.8360% and 6.9295%. Normal, Student-t, and zero-inflated families passed the complete-null FWER check in this finite simulation.

The 160 marginal checks cover four condition variances × four Holm step thresholds × ten families. Their simultaneous Wilson bounds also fail in skew/tied cases. A concrete marginal failure is right-skew 1.5×, condition index 0, nominal step alpha .05: 13,985/200,000 (6.9925%), simultaneous one-sided upper bound 7.1901% versus the allowed 5.2%.

## Independent replay

`audit_holm_repair_v2.py` uses a separately written root-effect generator, p-value reconstruction, Holm step-down, and Wilson calculation. It matched all 160 marginal counts and all ten Holm familywise counts exactly. The audit completed 10 scenario replays and reported:

```json
{{"marginal_pvalue_validity_pass": false, "complete_null_holm_fwer_pass": false,
  "all_scenarios_replayed": true, "all_marginal_counts_replayed": true}}
```

The estimator is validated only for the finite families in this design exercise. These findings do not establish behavior on unmodeled distributions and do not justify replacing the current method post hoc. A new secondary-inference method would require a separately predeclared and validated prospective amendment before Stage 5 sampling.
'''
(HERE/'SECONDARY_HOLM_FINDINGS.md').write_text(holmdoc,encoding='utf-8')

decision=f'''# Stage 5 n=1,210 readiness decision

## NO-GO for sampling readiness

The n=1,210 primary Endpoint B design passes the previously frozen finite-envelope type-I and confidence-bound coverage requirements. The 1.5× formal power gate passes at −0.0003, and every requested 2× sensitivity family—including the previously missing zero-inflated 2× condition—was simulated at both −0.0003 and −0.0004. The separate p=0 size, coverage, and reported safety-pass conditions also pass.

The complete design does **not** pass, because the previously specified four-condition Welch/Holm family is anti-conservative for the skewed and tied/asymmetric null models. Its complete-null familywise rejection rate reaches 9.3815% (right-skew lognormal 1.5×), versus the frozen 5.2% maximum. The independent replay reproduced the rejection counts.

Because the Holm family is part of the prior multiplicity plan, the primary endpoint’s successful calibration is insufficient for overall readiness. The v2 frozen protocol and the n=666 candidate remain unchanged. No 1,210-root Stage 5 runner, Stage 5 sample seed inventory, or sampling freeze is prepared. No allocation increase or inferential-method substitution is made here.

## Scope and safety

- Statistical design simulation completed; Stage 5 evaluation shots generated: **0**.
- Sealed historical test data accessed: **No**.
- Stage 4C evidence modified: **No**.
- Website worktree modified: **No**.
- Stage 5 sampling authorization: **Not granted by this work**; a new versioned design and separate authorization remain necessary.

## Blocking issue

The frozen candidate Welch/Holm procedure fails finite-envelope Type-I control under right-skew lognormal and tied/asymmetric root effects. Do not execute Stage 5 with the current full multiplicity plan. Any replacement secondary procedure must be specified and validated prospectively, without changing Endpoint B, its −0.0002 boundary, the −0.0003 planning alternative, or the allocation solely to obtain a pass. Stage 5 remains NO-GO until the multiplicity procedure is resolved and independently reviewed.

See `STATISTICAL_VALIDATION_REPORT.md`, `SECONDARY_HOLM_FINDINGS.md`, and `INDEPENDENT_AUDIT.json` / `secondary_holm/SECONDARY_HOLM_AUDIT_REPAIR_V2.json` for the detailed evidence.
'''
(HERE/'READINESS_DECISION.md').write_text(decision,encoding='utf-8')
