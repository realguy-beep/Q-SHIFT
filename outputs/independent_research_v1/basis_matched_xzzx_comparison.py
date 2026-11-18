"""Exploratory equal-resource comparison of native XZZX with aligned CSS."""
from __future__ import annotations
import json
from pathlib import Path
from scipy.stats import beta
from basis_alignment_distance7 import build as build_css
from xzzx_native_xcx import native_transform, resources as circuit_resources

HERE=Path(__file__).resolve().parent
ROOT=HERE/'RESULTS.json'


def rr_ci(a,na,b,nb):
    """Exact conditional interval for independent rare-event counts/rates."""
    total=a+b
    p_lo=0.0 if a==0 else beta.ppf(.025,a,b+1)
    p_hi=1.0 if b==0 else beta.ppf(.975,a+1,b)
    return {"point_rate_ratio":(a/na)/(b/nb),
            "conditional_exact_95_ci":[float(p_lo/(1-p_lo)*nb/na),float(p_hi/(1-p_hi)*nb/na)],
            "conditioning":"independent Poisson counts conditional on total failures; equal-tail beta interval"}


def main():
    ledger=json.loads(ROOT.read_text())
    xzzx=ledger['xzzx_native_xcx']
    css3=ledger['known_profile_memory_basis_alignment']
    css5=ledger['known_profile_memory_basis_distance5']
    points=[]
    for d,aligned_record in ((3,css3),(5,css5)):
        row=next(x for x in xzzx['conditions'] if x['distance']==d and x['profile']=='x_biased' and x['code']=='xzzx')
        if d==3:
            css=next(x for x in aligned_record['conditions'] if x['regime']=='x_biased')['per_basis']['x']
            resources=next(x for x in aligned_record['conditions'] if x['regime']=='x_biased')['matched_resources']
            n_css=resources['physical_qubits'];dets=resources['detectors'];obs=resources['observables'];pairs=120
        else:
            css=next(x for x in aligned_record['conditions'] if x['memory_basis']=='x' and x['regime']=='x_biased')
            n_css=css['physical_qubits'];dets=css['detectors'];obs=css['observables'];pairs=css['two_qubit_channel_pairs']
        xres=row['resources']
        css_circuit=build_css('x','x_biased',distance=d,rounds=2*d-1,bias_ratio=10.)
        xzzx_source=build_css('z','x_biased',distance=d,rounds=2*d-1,bias_ratio=10.)
        xzzx_circuit,_,_,_=native_transform(xzzx_source)
        css_resources=circuit_resources(css_circuit);xzzx_resources=circuit_resources(xzzx_circuit)
        css_resources['measurement_flip_targets']=sum(len(i.targets_copy()) for i in css_circuit.flattened() if i.name in ('X_ERROR','Z_ERROR'))
        xzzx_resources['measurement_flip_targets']=sum(len(i.targets_copy()) for i in xzzx_circuit.flattened() if i.name in ('X_ERROR','Z_ERROR'))
        compared=('qubits','detectors','observables','two_qubit_interactions','one_qubit_noise_targets','ticks','measurement_flip_targets')
        if any(css_resources[k]!=xzzx_resources[k] for k in compared):
            raise RuntimeError(f'd{d} resource mismatch: CSS={css_resources}, XZZX={xzzx_resources}')
        xdesc={'shots':row['shots'],'failures':row['failures'],'physical_qubits':xres['qubits'],
               'detectors':xres['detectors'],'observables':xres['observables'],
               'two_qubit_interactions':xres['two_qubit_interactions'],
               'one_qubit_noise_targets':xres['one_qubit_noise_targets'],'ticks':xres['ticks']}
        cdesc={'shots':css['shots'],'failures':css['failures'],'physical_qubits':n_css,
               'detectors':dets,'observables':obs,'two_qubit_interactions':pairs,
               'rounds':2*d-1,'gate_probability':.003,'measurement_probability':.003}
        assert (xdesc['physical_qubits'],xdesc['detectors'],xdesc['observables'],xdesc['two_qubit_interactions'],xdesc['one_qubit_noise_targets'],xdesc['ticks']) == (n_css,dets,obs,pairs,css_resources['one_qubit_noise_targets'],css_resources['ticks'])
        assert xzzx['bias_ratio']==10.0 and xzzx['gate_meas_p']==.003
        points.append({'distance':d,'rounds':2*d-1,'profile':'x_biased','bias_ratio':10.0,
                       'xzzx_native_xcx':{**xdesc,'ler':row['failures']/row['shots']},
                       'css_x_aligned':{**cdesc,'ler':css['failures']/css['shots']},
                       'xzzx_over_aligned_css':rr_ci(row['failures'],row['shots'],css['failures'],css['shots']),
                       'css_resources':css_resources,'xzzx_resources':xzzx_resources,
                       'resource_match_verified':['physical_qubits','detectors','observables','two_qubit_interactions','one_qubit_noise_targets','ticks','measurement_flip_targets']})
    old=[]
    for d in (3,5):
        row=next(x for x in xzzx['xzzx_vs_css'] if x['distance']==d and x['profile']=='x_biased')
        old.append({'distance':d,'xzzx_over_css_z_mismatched_point':row['xzzx_over_css_rate_ratio']['ratio']})
    out={'status':'exploratory_existing_data_comparator_audit',
         'question':'Does the native-XCX XZZX advantage under X bias survive comparison with CSS memory aligned to X noise?',
         'data_sources':['xzzx_native_xcx','known_profile_memory_basis_alignment','known_profile_memory_basis_distance5'],
         'new_samples_generated':0,'conditions':points,
         'original_comparator_ratios':old,
         'interpretation':'XZZX beat CSS Z-memory (the mismatched basis) by the original reported factors, but lost to X-aligned CSS at both tested distances under equal counted qubit, detector, observable, and two-qubit interaction budgets. The compared streams are independent and the memory observable differs; this is a cross-screen descriptive comparison, not a paired decoder or universal-code result.',
         'limitations':['Native CX/XCX/CZ duration and PAULI_CHANNEL_2 equivalence is an explicit unverified hardware assumption.',
                       'Only d3/d5 and one XZZX orientation are available.',
                       'Streams are independent, so uncertainty uses a conditional count-rate ratio.',
                       'Logical memory basis differs; arbitrary-state performance and worst-case XZZX memory are untested.',
                       'One-factor-at-a-time code-design conclusions do not establish an asymptotic threshold.']}
    (HERE/'basis_matched_xzzx_comparison_results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'status':out['status'],'comparisons':[{'d':p['distance'],'ratio':p['xzzx_over_aligned_css']['point_rate_ratio'],'ci':p['xzzx_over_aligned_css']['conditional_exact_95_ci']} for p in points]},indent=2))

if __name__=='__main__':main()
