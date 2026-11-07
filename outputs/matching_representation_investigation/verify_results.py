"""Independent evidence rescoring using a sparse Python parity DP.

This verifier does not import the experiment runner or its result aggregation.
It rebuilds exact distributions by dictionary-based recurrences, reconstructs
PyMatching predictions, and compares them to every stored finite-syndrome map.
"""
from __future__ import annotations
from collections import defaultdict
import hashlib, json, math, sys
from pathlib import Path
import numpy as np
import pymatching, stim

HERE=Path(__file__).resolve().parent

def parse_events(dem):
    if isinstance(dem,str): dem=stim.DetectorErrorModel(dem)
    out=[]
    for inst in dem.flattened():
        if inst.type!='error': continue
        ds=set(); ls=set()
        for t in inst.targets_copy():
            if t.is_separator(): continue
            if t.is_relative_detector_id(): ds.symmetric_difference_update({int(t.val)})
            elif t.is_logical_observable_id(): ls.symmetric_difference_update({int(t.val)})
            else: raise ValueError(str(t))
        dm=sum(1<<i for i in ds); lm=sum(1<<i for i in ls)
        out.append((float(inst.args_copy()[0]),dm,lm))
    return dem,out

def sparse_dem_joint(d,o,events):
    # Independent sparse dictionary recurrence, separate from runner's NumPy XOR DP.
    state={0:1.0}
    for p,dm,lm in events:
        nxt=defaultdict(float)
        mask=dm|(lm<<d)
        for old,mass in state.items():
            nxt[old]+=mass*(1-p)
            nxt[old^mask]+=mass*p
        state=dict(nxt)
    return state

def exact_cat_profiles(profiles):
    # Exhaustive two-location categorical enumeration, including identity.
    pairs=("IX","IY","IZ","XI","XX","XY","XZ","YI","YX","YY","YZ","ZI","ZX","ZY","ZZ")
    locs=[]
    for j,(q0,q1) in enumerate(((0,1),(1,2))):
        outcomes=[(1-sum(profiles[j].values()),0,0)]
        for pair in pairs:
            x=[int(pair[0] in 'XY'),int(pair[1] in 'XY')]
            paulis=['I','I','I'];paulis[q0],paulis[q1]=pair
            d0=x[0]^x[1];d1=x[1] # correction: D1 only depends on q1 and q2 when this local pair is placed
            # Explicit full three-qubit syndrome and logical parity.
            bits=[int(p in 'XY') for p in paulis]
            dm=(bits[0]^bits[1])|((bits[1]^bits[2])<<1)
            lm=bits[0]^bits[1]^bits[2]
            outcomes.append((profiles[j][pair],dm,lm))
        locs.append(outcomes)
    state=defaultdict(float);state[0]=1.0
    for outcomes in locs:
        nxt=defaultdict(float)
        for old,mass in state.items():
            for p,dm,lm in outcomes:
                nxt[old^dm^(lm<<2)]+=mass*p
        state=nxt
    return dict(state)

def joint_by_s_l(state,d,o):
    n_s=1<<d;n_l=1<<o
    arr=np.zeros(n_s*n_l,dtype=np.float64)
    for combined,p in state.items(): arr[combined]=p
    return arr.reshape(n_l,n_s)

def metrics(joint):
    n_l,n_s=joint.shape;pred=[];risk=0.0;ties=[]
    for s in range(n_s):
        v=joint[:,s];m=float(v.max());w=[i for i,x in enumerate(v) if abs(float(x)-m)<=1e-15]
        c=min(w);pred.append(c);ties.append(s) if len(w)>1 else None
        risk+=float(v.sum()-v[c])
    return np.asarray(pred,dtype=int),risk,ties

def py_predictions(dem,correlated,feasible):
    matcher=pymatching.Matching.from_detector_error_model(dem,enable_correlations=correlated)
    d=int(dem.num_detectors);n=1<<d
    idx=np.flatnonzero(feasible)
    ids=idx.astype(np.uint32)
    synd=((ids[:,None]>>np.arange(d,dtype=np.uint32))&1).astype(np.uint8)
    result=np.zeros(n,dtype=np.uint8)
    if len(idx):
        try:
            x=np.asarray(matcher.decode_batch(synd,enable_correlations=correlated),dtype=np.uint8).reshape(len(idx),-1)
            result[idx]=x[:,0]
        except ValueError as e:
            if 'No perfect matching' not in str(e): raise
            for j,row in enumerate(synd):
                try: result[idx[j]]=int(np.asarray(matcher.decode(row,enable_correlations=correlated)).reshape(-1)[0])
                except ValueError as one:
                    if 'No perfect matching' not in str(one): raise
    return result

def no_separator_dem(dem):
    d=int(dem.num_detectors);o=int(dem.num_observables);_,ev=parse_events(dem)
    lines=[f'detector D{i}' for i in range(d)]+[f'logical_observable L{i}' for i in range(o)]
    for p,dm,lm in ev:
        ts=[f'D{i}' for i in range(d) if (dm>>i)&1]+[f'L{i}' for i in range(o) if (lm>>i)&1]
        lines.append(f'error({p:.17g}) '+ ' '.join(ts))
    return stim.DetectorErrorModel('\n'.join(lines)+'\n'),ev

def check_case(case, fail):
    dem,events=parse_events(case['dem_text']);d=int(dem.num_detectors);o=int(dem.num_observables)
    state=sparse_dem_joint(d,o,events);joint=joint_by_s_l(state,d,o)
    dem_map,dem_risk,ties=metrics(joint)
    if not np.array_equal(dem_map,np.asarray(case['prediction_maps']['exact_independent_dem_map'],dtype=int)):
        fail.append(f"{case['name']}: exact DEM MAP decisions")
    if abs(dem_risk-case['exact_independent_dem_map_risk'])>1e-11: fail.append(f"{case['name']}: DEM exact risk")
    if abs(float(joint.sum())-1)>1e-10: fail.append(f"{case['name']}: DEM mass")
    ref=joint
    cat_map=None
    if 'categorical_profiles' in case:
        cat_state=exact_cat_profiles(case['categorical_profiles']);cat_joint=joint_by_s_l(cat_state,d,o)
        cat_map,cat_risk,_=metrics(cat_joint);ref=cat_joint
        if abs(cat_risk-case['exact_reference_risk'])>1e-11: fail.append(f"{case['name']}: categorical exact risk")
    expected_risks={}
    maps=case['prediction_maps']
    for name,pred in maps.items():
        arr=np.asarray(pred,dtype=int)
        if arr.shape!=(1<<d,) or not np.isin(arr,(0,1)).all(): fail.append(f"{case['name']}/{name}: map schema");continue
        rr=float(sum(ref[:,s].sum()-ref[int(arr[s]),s] for s in range(1<<d)))
        expected_risks[name]=rr
        if abs(rr-case['risk_by_decoder'][name])>1e-11: fail.append(f"{case['name']}/{name}: saved risk")
    feasible=ref.sum(axis=0)>0
    for name,corr in (("pymatching_standard",False),("pymatching_correlated",True)):
        p=py_predictions(dem,corr,feasible)
        if not np.array_equal(p,np.asarray(maps[name],dtype=np.uint8)): fail.append(f"{case['name']}/{name}: prediction re-decode")
    transformed,tev=no_separator_dem(dem)
    valid=all(int(x[1]).bit_count()<=2 for x in tev)
    if valid and 'separator_free_standard' in maps:
        for name,corr in (("separator_free_standard",False),("separator_free_correlated",True)):
            p=py_predictions(transformed,corr,feasible)
            if not np.array_equal(p,np.asarray(maps[name],dtype=np.uint8)):fail.append(f"{case['name']}/{name}: transformed re-decode")
    elif not valid and 'separator_free_standard' in maps:
        fail.append(f"{case['name']}: invalid separator-free predictions were reported as candidate")
    if valid and 'separator_free_standard' in maps:
        transformed_state=sparse_dem_joint(d,o,tev);trans_joint=joint_by_s_l(transformed_state,d,o)
        if not np.allclose(trans_joint,joint,rtol=0,atol=1e-13):fail.append(f"{case['name']}: separator-free event distribution")
    if cat_map is not None:
        if not np.array_equal(cat_map,np.asarray(maps['exact_categorical_map'])):fail.append(f"{case['name']}: categorical exact MAP")
        tv=0.5*float(np.abs(ref-joint).sum())
        if abs(tv-case['categorical_vs_independent_dem_joint_tv_distance'])>1e-11:fail.append(f"{case['name']}: TV distance")
    if 'local_restricted_posterior' in maps:
        local_pred=[]
        for s in range(1<<d):
            selected=[e for e in events if (e[1]&s) or e[1]==0]
            if len(selected)>12:
                local_pred.append(int(maps['pymatching_standard'][s]));continue
            local={0:1.0}
            for p,dm,lm in selected:
                nxt=defaultdict(float);mask=dm|(lm<<d)
                for old,mass in local.items():nxt[old]+=mass*(1-p);nxt[old^mask]+=mass*p
                local=dict(nxt)
            posterior=[local.get(s|(l<<d),0.0) for l in range(1<<o)]
            if sum(posterior)<=0:local_pred.append(int(maps['pymatching_standard'][s]));continue
            mx=max(posterior);local_pred.append(min(l for l,v in enumerate(posterior) if abs(v-mx)<=1e-15))
        if not np.array_equal(np.asarray(local_pred),np.asarray(maps['local_restricted_posterior'])):fail.append(f"{case['name']}: local posterior re-evaluation")
    return {'name':case['name'],'mass':float(joint.sum()),'exact_dem_risk':dem_risk,'saved_predictions_rescored':len(maps),'checks_pass':not any(case['name'] in e for e in fail)}

def check_grid(rows,fail):
    for r in rows:
        _,a=parse_events(r['separator_dem_text']);_,b=parse_events(r['separator_free_dem_text'])
        sig=lambda e:sorted((round(p,15),dm,lm) for p,dm,lm in e)
        if sig(a)!=sig(b):fail.append(f"grid {(r['p'],r['q'],r['r'])}: representation event distribution changed")
        for field,correlated in (("separator_dem_text",False),("separator_dem_text",True),("separator_free_dem_text",False),("separator_free_dem_text",True)):
            dem,ev=parse_events(r[field]);d=int(dem.num_detectors);o=int(dem.num_observables)
            state=sparse_dem_joint(d,o,ev);joint=joint_by_s_l(state,d,o);feasible=joint.sum(axis=0)>0
            name={('separator_dem_text',False):'separator_standard_decisions',('separator_dem_text',True):'separator_correlated_decisions',('separator_free_dem_text',False):'separator_free_standard_decisions',('separator_free_dem_text',True):'separator_free_correlated_decisions'}[(field,correlated)]
            pred=py_predictions(dem,correlated,feasible)
            if not np.array_equal(pred,np.asarray(r[name],dtype=np.uint8)):fail.append(f"grid {(r['p'],r['q'],r['r'])}/{name}: redecode")
            risk=float(sum(joint[:,s].sum()-joint[int(pred[s]),s] for s in range(1<<d)))
            riskkey={"separator_standard_decisions":"separator_standard_risk","separator_correlated_decisions":"separator_correlated_risk","separator_free_standard_decisions":"separator_free_standard_risk","separator_free_correlated_decisions":"separator_free_correlated_risk"}[name]
            if abs(risk-r[riskkey])>1e-11:fail.append(f"grid {(r['p'],r['q'],r['r'])}/{riskkey}: rescore")
            if field=="separator_dem_text" and not correlated:
                _,exrisk,_=metrics(joint)
                if abs(exrisk-r['exact_dem_risk'])>1e-11:fail.append(f"grid {(r['p'],r['q'],r['r'])}: exact risk")

def main():
    r=json.loads((HERE/'RESULTS.json').read_text(encoding='utf-8'));fails=[];rows=[]
    cases=[r['historical_reproduction']]+r['categorical_seed_cases']
    for fi in r['decomposition_fixtures']:
        cases.append(fi['primary'])
        if fi['alternate_decomposition']:cases.append(fi['alternate_decomposition'])
    cases+=r['reduced_surface_fragments']
    for case in cases:rows.append(check_case(case,fails))
    check_grid(r['separator_grid'],fails)
    summary={'status':'PASS' if not fails else 'FAIL','independently_rescored_cases':len(rows),'predeclared_grid_cells':len(r['separator_grid']),
             'per_case':rows,'failures':fails,'stochastic_shots':0,
             'method':'Sparse dictionary XOR posterior recurrence, independent from runner NumPy array recurrence; PyMatching recreated from stored DEM text.'}
    (HERE/'INDEPENDENT_AUDIT.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':summary['status'],'cases':len(rows),'grid':len(r['separator_grid']),'failures':len(fails),'output':str(HERE/'INDEPENDENT_AUDIT.json')},indent=2))
    if fails:raise SystemExit(2)

if __name__=='__main__':main()
