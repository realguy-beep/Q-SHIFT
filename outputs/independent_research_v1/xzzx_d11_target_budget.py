"""Optimistic IID evidence budget for the d11 1e-4 relative-rate target."""
from __future__ import annotations
import json,math
from pathlib import Path
from scipy.optimize import brentq
from scipy.stats import poisson
HERE=Path(__file__).resolve().parent

def main():
 r=json.loads((HERE/'xzzx_basis_factorial_d11_results.json').read_text())
 css={x['basis']:x for x in r['conditions'] if x['code']=='css'}
 xzzx={x['basis']:x for x in r['conditions'] if x['code']=='xzzx'}
 baseline=(css['x']['failures']+css['z']['failures'])/(css['x']['shots']+css['z']['shots'])
 candidate=(xzzx['x']['failures']+xzzx['z']['failures'])/(xzzx['x']['shots']+xzzx['z']['shots'])
 target=baseline*1e-4;alpha=.05
 rows=[]
 for observed in (0,1,3):
  lam=brentq(lambda z:poisson.cdf(observed,z)-alpha,1e-12,50.)
  rows.append({'observed_candidate_failures':observed,
               'iid_candidate_shots_to_bound_at_target':int(math.ceil(lam/target)),
               'poisson_count_cutoff_at_boundary':lam,
               'assumption':'one-sided 95% upper-rate criterion; rare-event Poisson approximation'})
 out={'status':'analytical_development_feasibility_note','distance':11,
  'equal_weight_separate_memory_css_failures':css['x']['failures']+css['z']['failures'],
  'equal_weight_separate_memory_css_shots':css['x']['shots']+css['z']['shots'],
  'baseline_point_ler':baseline,'relative_target':1e-4,'candidate_target_ler':target,
  'equal_weight_xzzx_failures':xzzx['x']['failures']+xzzx['z']['failures'],
  'equal_weight_xzzx_shots':xzzx['x']['shots']+xzzx['z']['shots'],
  'candidate_point_ler':candidate,'candidate_over_target_point':candidate/target,
  'observed_equal_weight_rate_ratio':candidate/baseline,
  'observed_rate_ratio_95_ci':r['comparisons']['equal_weight_separate_basis_mix_xzzx_over_css']['conditional_exact_95_ci'],
  'optimistic_iid_shot_budgets':rows,
  'limitations':['Uses the observed baseline point as known; baseline uncertainty increases evidence needs.',
                 'Ignores root clustering, multiple conditions, model selection, and code-family selection.',
                 'The current d11 XZZX point rate is above the target; more shots at the same true rate cannot make it meet the target.',
                 'Equal-weight separate basis tasks are not arbitrary-state logical channel trials.']}
 (HERE/'xzzx_d11_target_budget.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'baseline':baseline,'target':target,'candidate':candidate,'candidate_over_target':candidate/target,'budgets':rows},indent=2))
if __name__=='__main__':main()
