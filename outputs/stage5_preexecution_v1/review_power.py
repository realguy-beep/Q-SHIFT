"""Recompute historical Stage 4 root SDs and Stage 5 normal-theory planning values."""
from __future__ import annotations
import csv, json, math
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=(.004,.008,.012,.016)

def mean_sd(xs):
 n=len(xs); m=sum(xs)/n
 return m, math.sqrt(sum((x-m)**2 for x in xs)/(n-1))

def power_review():
 sources={}
 # Stage 4 development profile-minus-fixed root paired LERs.
 path=ROOT/'outputs/stage4_noise_adaptive_development_v1/PAIRED_COMPARISONS.csv'
 groups=defaultdict(list)
 with path.open(newline='',encoding='utf-8') as handle:
  for r in csv.DictReader(handle):
   p=float(r['probability'])
   if p in P: groups[p].append(float(r['estimated_minus_fixed']))
 sources['stage4_development']={p:mean_sd(groups[p]) for p in groups}
 counts_development={p:len(groups[p]) for p in groups}
 # Stage 4C profile-minus-fixed root paired LERs, recomputed from error counts.
 path=ROOT/'outputs/stage4c_cnn_noise_estimation_v1/STAGE4C_PER_ROOT.csv'
 groups=defaultdict(list)
 with path.open(newline='',encoding='utf-8') as handle:
  for r in csv.DictReader(handle):
   p=float(r['probability'])
   if p in P: groups[p].append(float(r['stage4b_profile_ler'])-float(r['fixed_nominal_ler']))
 sources['stage4c']={p:mean_sd(groups[p]) for p in groups}
 counts_stage4c={p:len(groups[p]) for p in groups}
 rows=[]; conservative=[]
 for p in P:
  if counts_development[p]!=7 or counts_stage4c[p]!=7: raise ValueError(f'incomplete historical root summary at p={p}')
  a=sources['stage4_development'][p][1]; b=sources['stage4c'][p][1]; s=max(a,b); conservative.append(s)
  rows.append({'p':p,'stage4_development_n':counts_development[p],'stage4_development_sd':a,
               'stage4c_n':counts_stage4c[p],'stage4c_sd':b,'used_sd':s})
 se=math.sqrt(sum(s*s for s in conservative)/(4*4*100))
 def cdf(x): return .5*(1+math.erf(x/math.sqrt(2)))
 delta=.0002
 z=delta/se
 null_reject=cdf(z-1.96)+(1-cdf(z+1.96))
 point_boundary=.5
 individual=[cdf(delta/(s/math.sqrt(100))) for s in conservative]
 return {'status':'recomputed_from_saved_development_root_summaries_only','per_condition':rows,
   'equal_stratum_mean_se':se,'power_two_sided_reject_zero_at_true_delta_minus_0.0002_normal_approx':null_reject,
   'probability_primary_point_estimate_at_or_below_minus_0.0002_at_boundary':point_boundary,
   'probability_each_condition_point_mean_favorable_if_all_true_deltas_minus_0.0002':individual,
   'probability_all_four_condition_point_means_favorable_independence_approx':math.prod(individual),
   'full_gate_power_at_boundary_upper_bound':point_boundary,
   'point_gate_probability_at_true_delta_minus_0.0005':cdf((.0005-.0002)/se),
   'scope':'normal-theory approximation; not a simulation experiment or guarantee; seven roots/cell make variance inputs uncertain'}

if __name__=='__main__': print(json.dumps(power_review(),indent=2))
