"""Continuous expected-log sign bounds through the burst indifference band."""
from __future__ import annotations
import json,sys
from fractions import Fraction
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for q in (ROOT,ROOT/'outputs'/'phase3a_correlated_noise_preflight',ROOT/'outputs'/'stage4_noise_adaptive_feasibility_v1'):
    if str(q) not in sys.path:sys.path.insert(0,str(q))
import exact_three_parameter_efactor_envelope as model
OUT=HERE/'EF ACTOR_INTERMEDIATE_BAND_EXPECTED_LOG_BOUNDS.json'
CERT=HERE/'EXACT_THREE_PARAMETER_EFACTOR_ENVELOPE.json'
BANDS=[(Fraction(2,1000),Fraction(4,1000)),(Fraction(4,1000),Fraction(6,1000)),(Fraction(6,1000),Fraction(8,1000)),(Fraction(8,1000),Fraction(10,1000))]
PM=(Fraction(1,1000),Fraction(5,1000));PG=(Fraction(2,1000),Fraction(4,1000))

def readfrac(row):return Fraction(int(row['numerator']),int(row['denominator']))
def endpoint_log_bounds(m0,lam):
    f0=1+lam*(Fraction(0)/m0-1);f1=1+lam*(Fraction(1)/m0-1)
    return model.logtools.log_rational_interval(f0,terms=24),model.logtools.log_rational_interval(f1,terms=24)
def expected_log_bounds(zlo,zhi,m0,lam):
    (a_lo,a_hi),(b_lo,b_hi)=endpoint_log_bounds(m0,lam)
    low=(1-zlo)*a_lo+zlo*b_lo
    fhi=1+lam*(zhi/m0-1)
    upper=model.logtools.log_rational_interval(fhi,terms=24)[1]
    return low,upper

def main():
    cert=json.loads(CERT.read_text(encoding='utf-8-sig'));nom=model.circuit((.010,.003,.003));mapped,meta=model.features.categorical_sites(nom)
    chars,*_=model.build_character_polynomials(nom,mapped)
    rob=cert['robust_mean_e_factor_population_analysis'];opt=rob['endpoint_chord_optimum']
    arms=[]
    for direction in ('upward','downward_on_complement'):
        lam=readfrac(opt[direction]['exact_optimal_lambda'])
        m0=readfrac(rob['upward']['exact_null_mean_upper'] if direction=='upward' else rob['downward_on_complement_1_minus_X']['exact_null_mean_upper'])
        rows=[]
        for plo,phi in BANDS:
            box={'burst_p':(plo,phi),'measurement_p':PM,'gate_p':PG}
            moment=model.tensor_bernstein(chars,box)
            if direction=='upward':zlo,zhi=moment['min'],moment['max']
            else:zlo,zhi=1-moment['max'],1-moment['min']
            loglo,loghi=expected_log_bounds(zlo,zhi,m0,lam)
            rows.append({'burst_interval':[float(plo),float(phi)],'X_mean_continuous_bounds':[float(moment['min']),float(moment['max'])],'X_mean_exact_bounds':[model.fraction_record(moment['min'],compact=True),model.fraction_record(moment['max'],compact=True)],'trigger_statistic_mean_bounds':[float(zlo),float(zhi)],'trigger_statistic_mean_exact_bounds':[model.fraction_record(zlo,compact=True),model.fraction_record(zhi,compact=True)],'expected_log_lower_bound':float(loglo),'expected_log_lower_exact':model.fraction_record(loglo,compact=True),'expected_log_upper_bound':float(loghi),'expected_log_upper_exact':model.fraction_record(loghi,compact=True),'sign_classification':'uniform_positive' if loglo>0 else ('uniform_nonpositive' if loghi<=0 else 'sign_not_certified')})
            print(direction,rows[-1],flush=True)
        arms.append({'direction':direction,'lambda':float(lam),'lambda_exact':model.fraction_record(lam),'m0':float(m0),'m0_exact':model.fraction_record(m0,compact=True),'fixed_gate_rectangle':list(map(float,PG)),'measurement_rectangle':list(map(float,PM)),'bands':rows})
    out={'classification':'EXACT_CATEGORICAL_CONTINUOUS_BURST_BAND_EXPECTED_LOG_BOUNDS','model':'Balanced categorical distance-3, five-round circuit; continuous Bernstein mean bounds over measurement p [.001,.005] and gate p [.002,.004].','construction':'For Z in [0,1], concavity gives E log L >= the endpoint chord at a lower bound for E Z; Jensen gives E log L <= log L at an upper bound for E Z.','burst_bands':[[float(a),float(b)] for a,b in BANDS],'arms':arms,'limitations':['These are continuous population expected-log sign bounds, not finite-history detection delay or alarm probability.','Expected-log signs do not establish decoder choice or LER benefit.','No sequential path, sampling, decoder, or protected data was used.']}
    OUT.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print('WROTE',OUT.name)
if __name__=='__main__':main()
