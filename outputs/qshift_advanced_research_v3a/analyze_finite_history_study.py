"""Deterministic root-level analysis for authorized Phase 3A study outputs.

This script does not generate samples or resample roots. It computes paired
root summaries and the prespecified stratified Welch t interval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from collections import defaultdict

import numpy as np
from scipy.stats import t as student_t


def _root_errors(records:list[dict], *, split:str, scenario:str, family:str,
                 history:int, change_after:int|None, target:str)->dict[str,float]:
    grouped=defaultdict(list)
    for row in records:
        if row['split']!=split or row['scenario']!=scenario or row['template_family']!=family:
            continue
        if int(row['history_length'])!=history: continue
        if change_after is not None and int(row['history_end_exclusive'])<change_after+history:
            continue
        error=abs(float(row[target])-float(row['truth_'+target]))
        grouped[(row['root_id'],row['arm'])].append(error)
    out={}
    roots=sorted({root for root,_ in grouped})
    for root in roots:
        arms={arm:np.asarray(grouped[(root,arm)],dtype=np.float64) for arm in ('A','B')}
        if any(len(v)==0 for v in arms.values()):
            raise ValueError(f'missing paired arm for {scenario}/{root}')
        if len(arms['A'])!=len(arms['B']):
            raise ValueError(f'unpaired update counts for {scenario}/{root}')
        out[root+':A']=float(arms['A'].mean())
        out[root+':B']=float(arms['B'].mean())
    return out


def _stratum(rows:dict[str,float])->dict:
    roots=sorted({key[:-2] for key in rows})
    diffs=[]; mean_a=[]; mean_b=[]
    for root in roots:
        a=rows[root+':A']; b=rows[root+':B']
        diffs.append(b-a); mean_a.append(a); mean_b.append(b)
    if len(diffs)<2: raise ValueError('need at least two independent roots per primary stratum')
    d=np.asarray(diffs,dtype=np.float64)
    return {'root_count':len(d),'candidate_a_mean_absolute_error':float(np.mean(mean_a)),
            'candidate_b_mean_absolute_error':float(np.mean(mean_b)),
            'paired_difference_B_minus_A_mean':float(d.mean()),
            'paired_difference_sample_variance':float(d.var(ddof=1)),
            'root_level_paired_differences':d.tolist()}


def stratified_welch(primary_strata:dict[str,dict],confidence:float=.95)->dict:
    names=sorted(primary_strata)
    if len(names)!=2: raise ValueError('primary estimand requires exactly the two step strata')
    means=[]; vars_=[]; ns=[]
    for name in names:
        q=primary_strata[name]; means.append(q['paired_difference_B_minus_A_mean'])
        vars_.append(q['paired_difference_sample_variance']); ns.append(q['root_count'])
    estimate=float(np.mean(means))
    components=[vars_[i]/ns[i] for i in range(2)]
    variance=float(sum(components)/4)
    se=float(np.sqrt(variance))
    denom=sum((components[i]**2)/(ns[i]-1) for i in range(2))
    dof=float((sum(components)**2)/denom) if denom>0 else float('inf')
    alpha=1-confidence
    upper=float(estimate+student_t.ppf(confidence,dof)*se)
    q=float(student_t.ppf(1-alpha/2,dof))
    return {'strata_equal_weighted':names,'estimate_B_minus_A':estimate,
            'standard_error':se,'degrees_of_freedom':dof,
            'one_sided_upper_endpoint':upper,'two_sided_interval':[estimate-q*se,estimate+q*se],
            'confidence':confidence,'interpretation':'development-only root-level interval conditional on fixed templates'}


def analyze_payload(payload:dict,primary_split:str='heldout_development')->dict:
    records=payload.get('records',[])
    if not records: raise ValueError('results file contains no records')
    primary={}
    for scenario in ('measurement_step_up','measurement_step_down'):
        rows=_root_errors(records,split=primary_split,scenario=scenario,
            family='exact_categorical',history=1000,change_after=5000,target='p_burst')
        primary[scenario]=_stratum(rows)
    uncertainty=stratified_welch(primary)
    measurement_secondary={}
    for scenario in sorted({r['scenario'] for r in records}):
        family='exact_categorical'
        roots=defaultdict(list)
        for row in records:
            if row['split']!=primary_split or row['scenario']!=scenario or row['template_family']!=family or row['arm']!='B':
                continue
            if int(row['history_length'])!=1000: continue
            roots[row['root_id']].append(abs(float(row['p_measurement'])-
                                              float(row['truth_p_measurement'])))
        if roots:
            per_root=[float(np.mean(v)) for v in roots.values()]
            measurement_secondary[scenario]={'root_count':len(per_root),
                'candidate_b_measurement_mae_mean':float(np.mean(per_root)),
                'root_maes':per_root}
    return {'schema':'qshift-finite-history-analysis-v1','primary_split':primary_split,
        'primary_metric':'mean post-change absolute burst error, B minus A, p_m step strata, N=1000',
        'primary_strata':primary,'primary_interval':uncertainty,
        'secondary_candidate_b_measurement_mae':measurement_secondary,
        'sampling_performed_by_analysis':False,
        'limitations':['interval is development-only and conditional on fixed analytical templates',
                       'no decoder or logical-error outcome is analyzed']}


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    payload=json.loads(args.results.read_text(encoding='utf-8'))
    summary=analyze_payload(payload)
    summary['provenance']={
        'input_results_sha256':hashlib.sha256(args.results.read_bytes()).hexdigest(),
        'analysis_script_sha256':hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest(),
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('primary_strata','secondary_candidate_b_measurement_mae')},indent=2))


if __name__=='__main__': main()
