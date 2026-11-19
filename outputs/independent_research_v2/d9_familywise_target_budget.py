"""Exact binomial shot budgets for a 10,000x LER claim across multiple cells."""
from __future__ import annotations
import json,math,platform,hashlib
from pathlib import Path
from scipy.stats import beta
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
base=json.loads((ROOT/'outputs'/'independent_research_v1'/'d9_relative_target_sample_budget.json').read_text())
p=float(base['candidate_target_using_baseline_lower'])
def required(k,alpha):
 if k==0:return math.ceil(math.log(alpha)/math.log1p(-p))
 lo=2;hi=1_000_000_000
 while lo<hi:
  mid=(lo+hi)//2
  if beta.ppf(1-alpha,k+1,mid-k)<=p:hi=mid
  else:lo=mid+1
 return lo
rows=[]
for claims in (1,6,12):
 candidate_alpha=.05/claims
 joint_candidate_alpha=.025/claims
 rows.append({'simultaneous_candidate_claims':claims,
  'candidate_only_95_fwer':{'per_claim_alpha':candidate_alpha,'zero_failures_shots_per_cell':required(0,candidate_alpha),'one_failure_shots_per_cell':required(1,candidate_alpha)},
  'joint_95_with_half_alpha_reserved_for_baseline':{'per_claim_candidate_alpha':joint_candidate_alpha,'zero_failures_shots_per_cell':required(0,joint_candidate_alpha),'one_failure_shots_per_cell':required(1,joint_candidate_alpha)}})
out={'baseline_source':'outputs/independent_research_v1/d9_relative_target_sample_budget.json','baseline_ler_point':base['d9_mismatched_ler_point'],'baseline_ler_exact_95_lower':base['d9_mismatched_ler_exact_95_lower'],'relative_target':base['relative_target'],'candidate_ler_target_using_baseline_lower':p,'budgets':rows,'assumptions':['IID Bernoulli logical failures within each cell','zero or one candidate failure; independent claims family-wise controlled by Bonferroni','candidate-only table conditions on the existing baseline lower endpoint','joint table reserves half of total alpha for baseline uncertainty; baseline multiplicity beyond the single d9 denominator is not modeled','excludes multiple seeds, decoder selection, code selection, drift, and correlated shot blocks'],'stochastic_samples_generated':0,'software_versions':{'python':platform.python_version()}}
(HERE/'d9_familywise_target_budget.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
