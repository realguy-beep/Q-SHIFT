"""Alpha spending sensitivity for externally verified one-change episodes."""
from __future__ import annotations
import json
from decimal import Decimal,localcontext
from fractions import Fraction
from pathlib import Path
HERE=Path(__file__).resolve().parent;INPUT=HERE/'EFACTOR_FREEDMAN_MEAN_RANGE_BOUNDS.json';OUT=HERE/'EFACTOR_EXTERNAL_EPOCH_ALPHA_SPENDING.json'
ALPHA_TOTAL=Fraction(1,20);EPOCHS=(1,2,10,100);STARTS=(1,1000,1000000);DELTA=Fraction(1,10)
def lnfrac(x):
 with localcontext() as c:c.prec=70;return (Decimal(x.numerator)/Decimal(x.denominator)).ln()
def bnd(n,alpha,w,mu,v,C):
 A=lnfrac(1/(alpha*w));x=Decimal(n)*mu-A
 if x<=0:return Decimal(1)
 return (-(x*x)/(2*(Decimal(n)*v+C*x/Decimal(3)))).exp()
def first(alpha,w,mu,v,C):
 target=Decimal(DELTA.numerator)/Decimal(DELTA.denominator);lo=hi=1
 while bnd(hi,alpha,w,mu,v,C)>target:hi*=2
 while lo<hi:
  mid=(lo+hi)//2
  if bnd(mid,alpha,w,mu,v,C)<=target:hi=mid
  else:lo=mid+1
 if bnd(lo,alpha,w,mu,v,C)>target or bnd(lo-1,alpha,w,mu,v,C)<=target:raise AssertionError('minimal n')
 return lo
def main():
 src=json.loads(INPUT.read_text(encoding='utf-8-sig'));arms=[]
 for arm in src['arms']:
  mu=Decimal(arm['alternative_mean_lower_log_mu']);v=Decimal(arm['conditional_variance_upper_v']);C=Decimal(arm['centered_increment_absolute_bound_c']);rows=[]
  for j in EPOCHS:
   alpha=ALPHA_TOTAL/Fraction(j*(j+1))
   for s in STARTS:
    w=Fraction(1,s*(s+1));n=first(alpha,w,mu,v,C);rows.append({'epoch_index_j':j,'alpha_j_exact':f'{alpha.numerator}/{alpha.denominator}','candidate_start_s':s,'start_weight_exact':f'{w.numerator}/{w.denominator}','delta':.1,'sufficient_postchange_shots':n,'freedman_bound_at_n':str(bnd(n,alpha,w,mu,v,C)),'bound_at_n_minus_1':str(bnd(n-1,alpha,w,mu,v,C))})
  arms.append({'direction':arm['direction'],'rows':rows})
 partial=sum((ALPHA_TOTAL/Fraction(j*(j+1)) for j in range(1,1001)),Fraction(0));assert partial==ALPHA_TOTAL*Fraction(1000,1001)
 out={'classification':'ANALYTIC_ALPHA_SPENDING_FOR_EXTERNALLY_VERIFIED_EPOCHS','global_false_switch_budget_total':str(ALPHA_TOTAL),'episode_allocation':'alpha_j=alpha_total/[j(j+1)], j=1,2,...; exact total is alpha_total by telescoping.','validity_requirements':['At each episode start, the baseline regime and corresponding directional null are trusted independently of the prior e-alarm.','Each episode uses one fixed direction and at most one change mixture; after an alarm, freeze/hold pending external re-baselining.','Conditional e-process null validity holds within each episode.','Union bound requires no independence across episodes.'],'partial_sum_first_1000':str(partial),'delta':float(DELTA),'arms':arms,'limitations':['An alarm does not prove the new regime and cannot authorize an automatic opposite-direction test.','If the baseline is reset from the alarm itself, the new episode null may be false and the global guarantee fails.','This is a protocol option, not a tested controller or decoder-utility result.','No sampling or histories were generated.']}
 OUT.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
 for arm in arms:
  print(arm['direction'])
  for r in arm['rows']:
   if r['candidate_start_s']==1000:print(r['epoch_index_j'],r['sufficient_postchange_shots'])
if __name__=='__main__':main()
