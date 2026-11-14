"""Representability horizon and weight penalty for Q=2^96 prior rounding."""
from __future__ import annotations
import json,math
from decimal import Decimal,localcontext
from fractions import Fraction
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE/'EFACTOR_FIXEDPOINT_PRIOR_HORIZON.json';Q_BITS=96;Q=1<<Q_BITS
SAMPLES=(1,1000,10**6,10**9,10**12,2**40)
def main():
    smax=(math.isqrt(1+4*Q)-1)//2
    while (smax+1)*(smax+2)<=Q:smax+=1
    while smax*(smax+1)>Q:smax-=1
    rows=[]
    for s in (*SAMPLES,smax,smax+1):
        exact=Fraction(1,s*(s+1));integer=Q//(s*(s+1))
        if integer:
            represented=Fraction(integer,Q);loss=1-represented/exact
            with localcontext() as ctx:
                ctx.prec=70
                logpen=(Decimal(Q)/Decimal(integer*s*(s+1))).ln()
        else:loss=None;logpen=None
        rows.append({'start_s':s,'exact_prior_weight':f'{exact.numerator}/{exact.denominator}','rounded_weight_integer':integer,'rounded_weight_over_Q':str(Fraction(integer,Q)) if integer else '0','relative_weight_loss':float(loss) if loss is not None else None,'additional_log_threshold_nats':str(logpen) if logpen is not None else None,'candidate_component_available':integer>0})
    assert smax*(smax+1)<=Q and (smax+1)*(smax+2)>Q
    assert Q//(smax*(smax+1))==1 and Q//((smax+1)*(smax+2))==0
    result={'classification':'DETERMINISTIC_FIXEDPOINT_PRIOR_WEIGHT_REPRESENTABILITY_AUDIT','q_bits':Q_BITS,'scale_exact':str(Q),'max_start_with_nonzero_floor_weight':smax,'first_start_with_zero_floor_weight':smax+1,'max_start_approximately':float(smax),'rows':rows,'interpretation':'Downward-rounded weights preserve false-alarm conservatism by pointwise domination, but a zero-rounded candidate weight supplies no detection-delay guarantee for that change start. For nonzero weights the extra threshold is log(exact_weight/rounded_weight).','limitations':['Python arbitrary integers only; no fixed-width counter or state overflow validation.','No streams or decoder behavior evaluated.']}
    OUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'q_bits':Q_BITS,'max_start':smax,'rows':rows},indent=2))
if __name__=='__main__':main()
