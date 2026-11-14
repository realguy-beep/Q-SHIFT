"""Distribution-free Freedman screen for linear burst ramps plus endpoint dwell."""
from __future__ import annotations
import json
from decimal import Decimal,localcontext
from fractions import Fraction
from pathlib import Path
HERE=Path(__file__).resolve().parent
BAND_FILE=HERE/'EFACTOR_INTERMEDIATE_BAND_DELAY_BOUNDS.json'
BASE_FILE=HERE/'EFACTOR_FREEDMAN_MEAN_RANGE_BOUNDS.json'
OUT=HERE/'EFACTOR_LINEAR_RAMP_DELAY_SCREEN.json'
RAMPS=(10000,100000,1000000)
OFFSETS=(0,100000)
ALPHA=Fraction(1,20);DELTA=Fraction(1,10)

def log_fraction(x):
    with localcontext() as c:c.prec=70;return (Decimal(x.numerator)/Decimal(x.denominator)).ln()
def upper_bound(total_mu,total_v,max_c,start):
    A=log_fraction(Fraction(start*(start+1),1)/ALPHA)
    x=total_mu-A
    if x<=0:return Decimal(1)
    return (-(x*x)/(2*(total_v+max_c*x/Decimal(3)))).exp()
def calc(segments,start,q=0,plateau=None):
    mu=sum((Decimal(n)*s[0] for n,s in segments),Decimal(0))
    v=sum((Decimal(n)*s[1] for n,s in segments),Decimal(0))
    c=max(s[2] for n,s in segments)
    if q and plateau:
        mu+=Decimal(q)*plateau[0];v+=Decimal(q)*plateau[1];c=max(c,plateau[2])
    return mu,v,c,upper_bound(mu,v,c,start)
def min_dwell(segments,start,plateau):
    lo=0;hi=1
    while calc(segments,start,hi,plateau)[3]>Decimal(DELTA.numerator)/DELTA.denominator:hi*=2
    while lo<hi:
        mid=(lo+hi)//2
        if calc(segments,start,mid,plateau)[3]<=Decimal(DELTA.numerator)/DELTA.denominator:hi=mid
        else:lo=mid+1
    q=lo;cur=calc(segments,start,q,plateau);prev=calc(segments,start,q-1,plateau) if q else None
    if cur[3]>Decimal(DELTA.numerator)/DELTA.denominator or (q and prev[3]<=Decimal(DELTA.numerator)/DELTA.denominator):raise AssertionError('dwell minimality')
    return q,cur,prev

def triplet(row):
    mu=row.get('mu_log_lower',row.get('alternative_mean_lower_log_mu'))
    v=row.get('variance_upper_v',row.get('conditional_variance_upper_v'))
    c=row.get('centered_increment_bound_c',row.get('centered_increment_absolute_bound_c'))
    return (Decimal(mu),Decimal(v),Decimal(c))
def main():
    band=json.loads(BAND_FILE.read_text(encoding='utf-8-sig'));base=json.loads(BASE_FILE.read_text(encoding='utf-8-sig'))
    bandarms={a['direction']:a['rows'] for a in band['rows_by_direction']};basearms={a['direction']:triplet(a) for a in base['arms']};rows=[]
    upbands=[next(r for r in bandarms['upward'] if r['burst_interval']==v) for v in ([.006,.008],[.008,.01])]
    downband=next(r for r in bandarms['downward_on_complement'] if r['burst_interval']==[.002,.004])
    for offset in OFFSETS:
      for R in RAMPS:
        assert R%4==0
        # Midpoint parameterization gives exactly R/4 observations in each equal-width band.
        up_segments=[(R//4,triplet(upbands[0])),(R//4,triplet(upbands[1]))]
        up_start=offset+R//2+1
        q,vals,prev=min_dwell(up_segments,up_start,basearms['upward'])
        rows.append({'direction':'upward','ramp_p_b_from_.002_to_.010':R,'ramp_global_start_shot':offset+1,'component_start_shot_at_.006':up_start,'positive_band_shots':R//2,'endpoint_high_plateau_dwell_needed':q,'total_shots_from_ramp_start_to_bound':R+q,'alpha':.05,'miss_delta':.10,'conditional_expected_log_sum_lower':str(vals[0]),'conditional_variance_sum_upper':str(vals[1]),'centered_increment_bound':str(vals[2]),'freedman_bound_at_end':str(vals[3]),'bound_if_dwell_one_shot_short':None if q==0 else str(prev[3])})
        down_segments=[(R//4,triplet(downband))]
        down_start=offset+3*R//4+1
        q,vals,prev=min_dwell(down_segments,down_start,basearms['downward_on_complement'])
        rows.append({'direction':'downward_on_complement','ramp_p_b_from_.010_to_.002':R,'ramp_global_start_shot':offset+1,'component_start_shot_at_.004':down_start,'positive_band_shots':R//4,'endpoint_low_plateau_dwell_needed':q,'total_shots_from_ramp_start_to_bound':R+q,'alpha':.05,'miss_delta':.10,'conditional_expected_log_sum_lower':str(vals[0]),'conditional_variance_sum_upper':str(vals[1]),'centered_increment_bound':str(vals[2]),'freedman_bound_at_end':str(vals[3]),'bound_if_dwell_one_shot_short':None if q==0 else str(prev[3])})
    result={'classification':'ANALYTIC_LINEAR_DRIFT_PLATEAU_DWELL_SCREEN_NOT_SIMULATED','ramp_model':'Per-shot burst parameter moves linearly between endpoints over R shots using midpoint indexing; then it holds at endpoint until the mixture component crosses. Measurement and gate parameters may vary predictably shot-to-shot anywhere in their declared rectangles.','component_strategy':'Use the one-change prior component starting at first shot entering a continuously sign-certified positive-drift band; ignore earlier ramp observations for this lower-bound argument.','concentration':'For variable per-shot bands, sum the certified conditional log-mean lower bounds and conditional variance upper bounds; use the maximum centered-increment bound in Freedman.','start_prior':'w_s=1/[s(s+1)] with exact global candidate start s.','rows':rows,'limitations':['This checks specified deterministic ramp trajectories and endpoint holds; it does not certify arbitrary monotone/smooth paths.','The resulting n is a sufficient probability bound, not a realized detection time or expected delay.','No graph action, estimator, logical label, sampling, or decoder result is included.']}
    OUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for row in rows:print(row['direction'],row.get('ramp_p_b_from_.002_to_.010',row.get('ramp_p_b_from_.010_to_.002')),row['ramp_global_start_shot'],row['component_start_shot_at_.006'] if 'component_start_shot_at_.006' in row else row['component_start_shot_at_.004'],row.get('endpoint_high_plateau_dwell_needed',row.get('endpoint_low_plateau_dwell_needed')),row['total_shots_from_ramp_start_to_bound'])
if __name__=='__main__':main()
