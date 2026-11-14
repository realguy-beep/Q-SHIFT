"""Fixed-point downward-rounded mixture recurrence audit (exact arithmetic only)."""
from __future__ import annotations
import itertools,json
from fractions import Fraction
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=HERE/'EXACT_THREE_PARAMETER_EFACTOR_ENVELOPE.json'
OUTPUT=HERE/'EFACTOR_FIXEDPOINT_MIXTURE_AUDIT.json'
Q_BITS=96
SCALE=1<<Q_BITS

def frac(record):return Fraction(int(record['numerator']),int(record['denominator']))
def floor_scaled(x):return (x.numerator*SCALE)//x.denominator

def factor_table(cert,direction):
    opt=cert['robust_mean_e_factor_population_analysis']['endpoint_chord_optimum'][direction]
    lam=frac(opt['exact_optimal_lambda'])
    if direction=='upward':m0=frac(cert['robust_mean_e_factor_population_analysis']['upward']['exact_null_mean_upper'])
    else:m0=frac(cert['robust_mean_e_factor_population_analysis']['downward_on_complement_1_minus_X']['exact_null_mean_upper'])
    return [1+lam*(Fraction(k,5)/m0-1) if direction=='upward' else 1+lam*(Fraction(5-k,5)/m0-1) for k in range(6)]

def audit_direction(cert,direction,length=4):
    factors=factor_table(cert,direction)
    low_factors=[floor_scaled(x) for x in factors]
    max_rel=Fraction(0);checked=0;threshold_implications=0;direct_sum_checks=0
    for seq in itertools.product(range(6),repeat=length):
        a_exact=Fraction(0);a_low=0
        for t,k in enumerate(seq,start=1):
            w=Fraction(1,t*(t+1));r=Fraction(1,t+1)
            a_exact=factors[k]*(a_exact+w)
            w_low=(SCALE*w.numerator)//w.denominator
            r_low=(SCALE*r.numerator)//r.denominator
            a_low=(low_factors[k]*(a_low+w_low))//SCALE
            e_low=a_low+r_low
            e_exact=a_exact+r
            direct=Fraction(1,t+1)
            for s in range(1,t+1):
                component=Fraction(1)
                for i in range(s-1,t):component*=factors[seq[i]]
                direct+=Fraction(1,s*(s+1))*component
            if direct!=e_exact:raise AssertionError('exact recurrence differs from direct mixture expansion')
            direct_sum_checks+=1
            if Fraction(e_low,SCALE)>e_exact:raise AssertionError('rounded mixture exceeded exact mixture')
            alpha=Fraction(1,20)
            if e_low*alpha.denominator >= SCALE*alpha.numerator:
                threshold_implications+=1
                if e_exact*alpha.denominator < alpha.numerator:raise AssertionError('lower-bound crossing did not imply exact crossing')
            approx=Fraction(low_factors[k],SCALE)
            max_rel=max(max_rel,(factors[k]-approx)/factors[k])
        checked+=1
    return {'direction':direction,'q_bits':Q_BITS,'factor_exact_rationals':[f'{x.numerator}/{x.denominator}' for x in factors],'factor_lower_fixedpoint_integers':low_factors,'max_relative_factor_shortfall':float(max_rel),'abstract_factor_sequences_exhaustively_checked':checked,'sequence_length':length,'exact_recurrence_vs_direct_mixture_comparisons':direct_sum_checks,'lower_process_crossings_checked_at_alpha_0_05':threshold_implications,'pointwise_dominance_verified':True}

def main():
    cert=json.loads(SOURCE.read_text(encoding='utf-8-sig'))
    arms=[audit_direction(cert,d) for d in ('upward','downward_on_complement')]
    result={'classification':'DETERMINISTIC_FIXEDPOINT_LOWER_BOUND_ARITHMETIC_AUDIT_NOT_DECODER_OR_STREAM_TEST','scale':'2^96','rounding':'Every nonnegative rational factor, start weight, and remaining prior mass is rounded downward using integer floor. The fixed-point update is a lower bound on the exact rational mixture component sum.','exact_recurrence':'A_t=L_t*(A_(t-1)+w_t), E_t=A_t+1/(t+1).','fixedpoint_recurrence':'a_t=floor(l_t*(a_(t-1)+floor(2^q*w_t))/2^q); e_t=a_t+floor(2^q/(t+1)); with each l_t=floor(2^q*L_t).','safety_argument':'By induction all stored integers divided by 2^q are no larger than their corresponding exact nonnegative rational values. Therefore a threshold crossing by the computed lower bound implies a crossing by the exact mixture, so downward rounding can lose power but cannot inflate the Ville false-alarm probability.','arms':arms,'limitations':['This is an arithmetic prototype; platform/compiler integer semantics and production integration have not been validated.','It does not resolve the physical model assumptions, graph action, repeated transitions, or decoder utility.','The abstract factor sequences exhaustively test recurrence arithmetic, not detector histories or stochastic output.']}
    OUTPUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(arms,indent=2))
if __name__=='__main__':main()
