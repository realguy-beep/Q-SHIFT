"""Read-only paired-headroom recomputation from archived Q-SHIFT arrays.

Only new files under outputs/unified_headroom_audit are written. No simulator,
historical runner, frozen data, or held-out labels are modified.
"""
from __future__ import annotations
import csv, hashlib, json, time, re
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PAIR_ROWS: list[dict] = []
ROOT_ROWS: list[dict] = []
SOURCE_FILES: dict[str, dict] = {}

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def record_file(path: Path) -> None:
    SOURCE_FILES[str(path.relative_to(ROOT)).replace('\\','/')]={"sha256":sha256(path),"bytes":path.stat().st_size}

def scalar(z, key, default=None):
    if key not in z.files:return default
    a=z[key]
    return a.item() if a.shape==() else a

def add_root(study: str, stratum: str, root: str, y: np.ndarray, predictions: np.ndarray,
             decoder_names: list[str], source: Path, *, block_size: int|None=None) -> dict:
    y=np.asarray(y).reshape(-1).astype(np.uint8)
    p=np.asarray(predictions).astype(np.uint8)
    if p.ndim!=2 or p.shape[0]!=len(decoder_names) or p.shape[1]!=len(y):
        raise ValueError(f"prediction shape mismatch {source}: {p.shape}, y={y.shape}")
    if np.any((y>1)|(p>1)):
        raise ValueError(f"nonbinary labels/predictions in {source}")
    e=p!=y[None,:]
    errs=e.sum(axis=1).astype(int)
    # Hindsight per-shot oracle: the shot is called successful if any bank member
    # is correct. This is a label-informed upper bound, not an implementable policy.
    shot_oracle=int(np.all(e,axis=0).sum())
    # Hindsight per-block oracle, with blocks explicitly defined by contiguous
    # chunks in the archived stream (default one complete root if no block size).
    bs=block_size or len(y)
    block_oracle=0
    for lo in range(0,len(y),bs):block_oracle+=int(e[:,lo:min(lo+bs,len(y))].sum(axis=1).min())
    row={"study":study,"stratum":stratum,"root":str(root),"source":str(source.relative_to(ROOT)).replace('\\','/'),
         "shots":int(len(y)),"errors":errs.tolist(),"shot_oracle_errors":shot_oracle,
         "block_oracle_errors":block_oracle,"baseline_error_vector":None}
    ROOT_ROWS.append(row)
    for i in range(len(decoder_names)):
        for j in range(i+1,len(decoder_names)):
            ei=e[i];ej=e[j];dis=p[i]!=p[j]
            PAIR_ROWS.append({"study":study,"stratum":stratum,"root":str(root),
                "decoder_i":decoder_names[i],"decoder_j":decoder_names[j],"shots":len(y),
                "prediction_disagreements":int(dis.sum()),
                "i_only_wrong":int((ei&~ej).sum()),"j_only_wrong":int((~ei&ej).sum()),
                "both_wrong":int((ei&ej).sum()),"both_correct":int((~ei&~ej).sum()),
                "error_difference_i_minus_j":int(errs[i]-errs[j])})
    return row

def stratified_bootstrap_ci(rows: list[dict], baseline_index: int|None=None, oracle_key="shot_oracle_errors", reps=10000):
    """Descriptive root-cluster CI for paired fixed-minus-oracle headroom.

    The oracle is selected using the same archived labels, so the interval is
    explicitly descriptive and is not a generalization interval.
    """
    groups=defaultdict(list)
    for r in rows:groups[r['stratum']].append(r)
    if not groups:return None
    seed=int.from_bytes(hashlib.sha256(('unified-headroom|'+str(sorted(groups))).encode()).digest()[:4],'little')
    rng=np.random.default_rng(seed)
    names=sorted(groups)
    draws=np.empty(reps,dtype=float)
    obs=[]
    for g in names:
        rr=groups[g]; n=sum(x['shots'] for x in rr)
        if baseline_index is None:
            # baseline_error_vector is set to the policy count in each root
            b=np.array([x['baseline_errors'] for x in rr],dtype=float)
        else:b=np.array([x['errors'][baseline_index] for x in rr],dtype=float)
        o=np.array([x[oracle_key] for x in rr],dtype=float)
        obs.append((b.sum()-o.sum())/n)
        idx=rng.integers(0,len(rr),size=(reps,len(rr)))
        bboot=b[idx].sum(axis=1); oboot=o[idx].sum(axis=1)
        draws+=0 if len(obs)==1 else 0
        # hold each stratum's number of shots fixed and give strata equal weight
        if g==names[0]: mat=(bboot-oboot)/n
        else:mat += (bboot-oboot)/n
    draws=mat/len(names)
    return {"low":float(np.quantile(draws,.025)),"high":float(np.quantile(draws,.975)),
            "confidence":.95,"replicates":reps,"seed":seed,
            "unit":"root cluster resampled within each stratum; equal stratum weighting",
            "interpretation":"descriptive only; hindsight oracle uses the same outcome labels"}

def aggregate_study(study, rows, decoder_names, selected_by_stratum=None, global_fixed_index=None,
                    baseline_name=None, oracle_kind="shotwise"):
    selected_by_stratum=selected_by_stratum or {}
    def global_index_for(stratum):
        return global_fixed_index.get(stratum) if isinstance(global_fixed_index, dict) else global_fixed_index
    groups=defaultdict(list)
    for r in rows:groups[r['stratum']].append(r)
    stratum_results={}; fixed_rates=[]; specialist_rates=[]
    for s, rr in sorted(groups.items()):
        n=sum(x['shots'] for x in rr)
        sums=np.sum([x['errors'] for x in rr],axis=0).astype(int)
        best_eval=int(np.argmin(sums))
        fixed_index=global_index_for(s)
        chosen=selected_by_stratum.get(s,fixed_index)
        fixed=int(sums[chosen]) if chosen is not None else None
        per_block=sum(min(x['errors']) for x in rr)
        shot_oracle=sum(x['shot_oracle_errors'] for x in rr)
        pooled=int(sums[fixed_index]) if fixed_index is not None else None
        calibrated=int(sums[chosen]) if chosen is not None else None
        root_diffs=[int(x['errors'][chosen]-x['errors'][fixed_index]) for x in rr] if chosen is not None and fixed_index is not None else []
        stratum_results[s]={"roots":len(rr),"shots":int(n),"errors_by_decoder":sums.tolist(),
            "ler_by_decoder":(sums/n).tolist(),"calibration_selected_index":chosen,
            "calibration_selected_name":decoder_names[chosen] if chosen is not None else None,
            "calibration_selected_errors":fixed,"calibration_selected_ler":fixed/n if fixed is not None else None,
            "pooled_fixed_errors":pooled,"pooled_fixed_ler":pooled/n if pooled is not None else None,
            "calibration_selected_minus_pooled_errors":(calibrated-pooled) if pooled is not None else None,
            "calibration_selected_minus_pooled_ler":((calibrated-pooled)/n) if pooled is not None else None,
            "roots_specialist_better":sum(x<0 for x in root_diffs),"roots_specialist_worse":sum(x>0 for x in root_diffs),"roots_tied":sum(x==0 for x in root_diffs),
            "hindsight_best_regime_index":best_eval,"hindsight_best_regime_name":decoder_names[best_eval],
            "hindsight_best_regime_errors":int(sums[best_eval]),"hindsight_best_regime_ler":float(sums[best_eval]/n),
            "hindsight_per_root_oracle_errors":int(per_block),"hindsight_per_root_oracle_ler":float(per_block/n),
            "hindsight_per_shot_oracle_errors":int(shot_oracle),"hindsight_per_shot_oracle_ler":float(shot_oracle/n),
            "relative_hindsight_per_shot_reduction_vs_calibration_selected":((fixed-shot_oracle)/fixed if fixed else None)}
        if fixed is not None:
            fixed_rates.append(fixed/n); specialist_rates.append(shot_oracle/n)
    # Equal-weight stratum estimates, matching common frozen aggregate conventions.
    pooled_fixed_ler=float(np.mean(fixed_rates)) if fixed_rates else None
    shot_oracle_ler=float(np.mean(specialist_rates)) if specialist_rates else None
    ci=None
    if pooled_fixed_ler is not None:
        for r in rows:r['baseline_errors']=r['errors'][selected_by_stratum.get(r['stratum'],global_index_for(r['stratum']))]
        ci=stratified_bootstrap_ci(rows,baseline_index=None)
    fixed_names=({s:decoder_names[i] for s,i in global_fixed_index.items()}
                 if isinstance(global_fixed_index, dict) else
                 decoder_names[global_fixed_index] if global_fixed_index is not None else None)
    return {"study":study,"decoder_names":decoder_names,"global_fixed_index":global_fixed_index,
        "global_fixed_name":fixed_names,
        "per_stratum":stratum_results,"equal_stratum_fixed_ler":pooled_fixed_ler,
        "equal_stratum_hindsight_per_shot_oracle_ler":shot_oracle_ler,
        "equal_stratum_oracle_gap_fixed_minus_shotwise":(pooled_fixed_ler-shot_oracle_ler) if pooled_fixed_ler is not None else None,
        "relative_equal_stratum_oracle_reduction":((pooled_fixed_ler-shot_oracle_ler)/pooled_fixed_ler if pooled_fixed_ler else None),
        "descriptive_root_cluster_bootstrap_ci_for_oracle_gap":ci,
        "oracle_kind":oracle_kind,"root_count":len(rows),"total_shots":sum(x['shots'] for x in rows)}

def save_json(path, data):path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8')

def phase2a():
    d=ROOT/'outputs/phase2a_decoder_specialization'; cfg=json.loads((d/'config.json').read_text()); res=json.loads((d/'PHASE2A_RESULTS.json').read_text())
    cal=np.load(ROOT/'outputs/prototype_development/data/calibration_evidence.npz',allow_pickle=False)
    cerr=cal['errors'].sum(axis=2); cal_ler=cerr/cal['errors'].shape[2]
    pooled=int(np.argmin(cal_ler.mean(axis=0))); byreg=np.argmin(cal_ler,axis=1).astype(int).tolist()
    assert pooled==res['calibration_selection']['best_global_index'] and byreg==res['calibration_selection']['best_per_regime_indices']
    names=[f'decoder_{i}' for i in range(9)]; rows=[]
    for f in sorted((d/'data').glob('eval_*.npz')):
        record_file(f)
        with np.load(f,allow_pickle=False) as z:
            y=z['observable']; p=z['predictions']; reg=int(z['regime_id']); root=int(z['root_index'])
            row=add_root('phase2a_fresh_evaluation',cfg['regimes'][reg]['name'],str(root),y,p,names,f)
            row['baseline_errors']=row['errors'][pooled]; rows.append(row)
    out=aggregate_study('phase2a_fresh_evaluation',rows,names,{cfg['regimes'][i]['name']:byreg[i] for i in range(3)},pooled)
    out['selection_audit']={"calibration_source":"prototype_development/data/calibration_evidence.npz","shots_per_regime":20000,
        "recomputed_pooled_index":pooled,"recomputed_per_regime_indices":byreg,"matches_saved_phase2a_selection":True,
        "calibration_is_not_current_runtime_noise_telemetry":True}
    out['reported_summary_reconciliation']={"saved_aggregate_errors":res['oracle_headroom']['A_best_global_fixed_errors'],
        "recomputed_selected_fixed_errors":int(sum(x['errors'][pooled] for x in rows)),
        "saved_hindsight_per_regime_errors":res['oracle_headroom']['retrospective_oracle_per_regime_errors_total'],
        "recomputed_hindsight_per_regime_errors":sum(v['hindsight_best_regime_errors'] for v in out['per_stratum'].values()),
        "saved_per_shot_oracle_errors":res['oracle_headroom']['retrospective_oracle_per_shot_errors_total'],
        "recomputed_per_shot_oracle_errors":sum(v['hindsight_per_shot_oracle_errors'] for v in out['per_stratum'].values())}
    assert out['reported_summary_reconciliation']['saved_aggregate_errors']==out['reported_summary_reconciliation']['recomputed_selected_fixed_errors']
    assert out['reported_summary_reconciliation']['saved_hindsight_per_regime_errors']==out['reported_summary_reconciliation']['recomputed_hindsight_per_regime_errors']
    assert out['reported_summary_reconciliation']['saved_per_shot_oracle_errors']==out['reported_summary_reconciliation']['recomputed_per_shot_oracle_errors']
    return out, rows, cal_ler

def phase2b():
    d=ROOT/'outputs/phase2b_pauli_bias';sel=json.loads((d/'CALIBRATION_SELECTION.json').read_text()); cfg=json.loads((d/'config.json').read_text())
    bmap={k:int(v['global_index']) for k,v in sel['selected_models'].items()}; names=['bank_0','bank_1','bank_2'];rows=[]
    for f in sorted((d/'data/heldout').glob('test_*.npz')):
        record_file(f)
        with np.load(f,allow_pickle=False) as z:
            basis='z' if int(z['basis_id'])==0 else 'x';reg=['x_biased','balanced','z_biased'][int(z['regime_id'])];root=int(z['root_index'])
            row=add_root('phase2b_pauli_bias_heldout',f'{basis}/{reg}',str(root),z['observable'],z['predictions'],names,f)
            row['baseline_errors']=row['errors'][bmap[basis]]; rows.append(row)
    selected={s:bmap[s.split('/')[0]] for s in {r['stratum'] for r in rows}}
    out=aggregate_study('phase2b_pauli_bias_heldout',rows,names,selected,
                        {s:bmap[s.split('/')[0]] for s in selected})
    out['selection_audit']={"calibration_selection":bmap,"per_regime_indices_equal_global_by_basis":True,
        "calibration_shots_per_basis_regime":20000,"heldout_roots_per_basis_regime":20,
        "heldout_shots":sum(x['shots'] for x in rows)}
    saved=json.loads((d/'ORACLE_HEADROOM.json').read_text())
    computed_fixed=sum(sum(v['errors_by_decoder'][bmap[b]] for s,v in out['per_stratum'].items() if s.startswith(b+'/')) for b in ['x','z'])
    computed_oracle=sum(v['hindsight_per_shot_oracle_errors'] for v in out['per_stratum'].values())
    out['reported_summary_reconciliation']={"saved_fixed_errors":saved['calibration_selected_global_fixed_errors'],"recomputed_fixed_errors":computed_fixed,
        "saved_regime_informed_errors":saved['calibration_selected_regime_informed_errors'],"recomputed_regime_informed_errors":computed_fixed,
        "saved_per_shot_oracle_errors":saved['retrospective_per_shot_oracle_errors'],"recomputed_per_shot_oracle_errors":computed_oracle}
    assert computed_fixed==saved['calibration_selected_global_fixed_errors']==saved['calibration_selected_regime_informed_errors']
    assert computed_oracle==saved['retrospective_per_shot_oracle_errors']
    return out,rows

def headroom():
    d=ROOT/'outputs/headroom_feasibility'; raw=d/'raw'; names9=[f'decoder_{i}' for i in range(9)]; names3=['decoder_0','decoder_1','decoder_2']
    # Reconstruct calibration-only pooled and regime-specific selections.
    calgroups=defaultdict(dict); calmodels={}
    calshots=defaultdict(lambda:defaultdict(int));calroots=defaultdict(lambda:defaultdict(int))
    evalrows_by_bank=defaultdict(list);bankmeta={}
    for f in sorted(raw.glob('cal_*.npz')):
        record_file(f)
        with np.load(f,allow_pickle=False) as z:
            fam=str(scalar(z,'family'));dist=int(scalar(z,'distance'));mem=str(scalar(z,'memory'));reg=str(scalar(z,'regime'));bank=f'{fam}_d{dist}_{mem}'
            p=z['predictions'];y=z['observable'];n=p.shape[1]
            if bank not in calmodels:calmodels[bank]=p.shape[0]
            if calmodels[bank]!=p.shape[0]:raise ValueError(f'inconsistent bank width for {bank}')
            if reg not in calgroups[bank]:calgroups[bank][reg]=np.zeros(p.shape[0],dtype=np.int64)
            calgroups[bank][reg]+=np.count_nonzero(p!=y[None,:],axis=1);calshots[bank][reg]+=n;calroots[bank][reg]+=1;bankmeta[bank]=(fam,dist,mem)
    calibration_selected={};selection_rows=[]
    for bank,groups in sorted(calgroups.items()):
        regimes=sorted(groups)
        rates=np.stack([groups[r]/calshots[bank][r] for r in regimes])
        pooled=int(np.argmin(rates.mean(axis=0)))
        perreg={r:int(np.argmin(groups[r]/calshots[bank][r])) for r in regimes}
        reported=next(x for x in json.loads((d/'HEADROOM_RESULTS.json').read_text())['banks'] if x['bank']==bank)
        assert pooled==reported['pooled_fixed_index'],(bank,pooled,reported['pooled_fixed_index'])
        assert perreg==reported['regime_specialist_indices'],(bank,perreg,reported['regime_specialist_indices'])
        calibration_selected[bank]={"pooled_fixed_index":pooled,"per_regime_indices":perreg,
            "shots_by_regime":dict(calshots[bank]),"roots_by_regime":dict(calroots[bank]),
            "reconciles_saved_bank_selection":True}
        fam,dist,mem=bankmeta[bank]
        for r in regimes:
            for i in range(calmodels[bank]):selection_rows.append({"bank":bank,"family":fam,"distance":dist,"memory":mem,"regime":r,
                "decoder_index":i,"calibration_errors":int(groups[r][i]),"calibration_shots":calshots[bank][r],
                "calibration_ler":float(groups[r][i]/calshots[bank][r]),"pooled_fixed_index":pooled,
                "per_regime_calibrated_index":perreg[r]})
    # Read paired heldout archives.
    for f in sorted(raw.glob('eval_*.npz')):
        record_file(f)
        with np.load(f,allow_pickle=False) as z:
            fam=str(scalar(z,'family'));dist=int(scalar(z,'distance'));mem=str(scalar(z,'memory'));reg=str(scalar(z,'regime'));bank=f'{fam}_d{dist}_{mem}'
            dyn_names=names9 if z['predictions'].shape[0]==9 else names3
            row=add_root(f'headroom_{bank}',reg,str(f.stem),z['observable'],z['predictions'],dyn_names,f)
            row['baseline_errors']=row['errors'][calibration_selected[bank]['pooled_fixed_index']]
            evalrows_by_bank[bank].append(row)
    results={};allrows=[]
    for bank,rows in sorted(evalrows_by_bank.items()):
        sel=calibration_selected[bank]; perreg={r:i for r,i in sel['per_regime_indices'].items()}
        dyn_names=names9 if calmodels[bank]==9 else names3
        out=aggregate_study(f'headroom_{bank}',rows,dyn_names,perreg,sel['pooled_fixed_index'])
        out.update({"bank":bank,"family":bankmeta[bank][0],"distance":bankmeta[bank][1],"memory":bankmeta[bank][2],"calibration_selection":sel})
        results[bank]=out; allrows.extend(rows)
    flat=[]
    for b,v in results.items():
        for r,s in v['per_stratum'].items():
            for i,(err,ler) in enumerate(zip(s['errors_by_decoder'],s['ler_by_decoder'])):
                flat.append({"bank":b,"family":v['family'],"distance":v['distance'],"memory":v['memory'],"regime":r,
                    "decoder_index":i,"errors":err,"shots":s['shots'],"ler":ler,
                    "pooled_fixed_index":v['global_fixed_index'],"pooled_fixed_errors":s['calibration_selected_errors'],
                    "calibrated_regime_index":s['calibration_selected_index'],"calibrated_regime_errors":s['calibration_selected_errors'],
                    "hindsight_best_index":s['hindsight_best_regime_index'],"hindsight_best_errors":s['hindsight_best_regime_errors']})
    gate=json.loads((d/'HEADROOM_GATE.json').read_text())
    return {"banks":results,"calibration_selection":calibration_selected,"predeclared_gate_passed":gate['passed'],
        "gate_criteria":gate['criteria'],"calibration_cells":len(selection_rows),"evaluation_roots":len(allrows),
        "evaluation_shots":sum(x['shots'] for x in allrows)},allrows,selection_rows,flat

def stage2():
    d=ROOT/'outputs/phase4c_strong_baselines/stage2';base=json.loads((ROOT/'outputs/phase4c_strong_baselines/PHASE4C_BASELINE_FREEZE.json').read_text())
    names=['calibrated','pooled_fixed','nominal_fixed','minimax_fixed','condition_specific'];rows=[];records=json.loads((d/'STAGE2_RECOVERED_RESULTS.json').read_text())
    for f in sorted((d/'raw').glob('*.npz.quarantined')):
        record_file(f)
        with np.load(f,allow_pickle=False) as z:
            packed=z['detectors']; unpacked=np.unpackbits(packed,axis=1,bitorder='little')[:,:int(scalar(z,'detector_count'))]
            if unpacked.shape!=(30000,40):raise ValueError(f'bad detector encoding {f}')
            y=z['observable'].astype(np.uint8);p=z['predictions'].astype(np.uint8)
            if p.shape!=(5,30000):raise ValueError(f'bad prediction shape {f}')
            cond=next(c for c in ['data_heavy','nominal','measurement_heavy'] if f.name.startswith(c+'_'))
            root=int(re.search(r'_(\d+)\.npz',f.name).group(1));choice=int(scalar(z,'choice'))
            if choice<0 or choice>8:raise ValueError(f'bad calibrated choice {f}')
            row=add_root('phase4c_stage2_recovered',cond,str(root),y,p,names,f)
            row['choice']=choice;row['baseline_errors']=row['errors'][1];rows.append(row)
    if len(rows)!=60 or sum(x['shots'] for x in rows)!=1800000:raise ValueError('Stage 2 evidence coverage mismatch')
    out=aggregate_study('phase4c_stage2_recovered',rows,names,global_fixed_index=1)
    out['baseline_definitions']={"pooled_fixed":base['pooled_fixed'],"minimax_fixed":base['minimax_fixed'],"condition_specific":base['condition_specific'],"nominal_fixed":[.003,.003]}
    out['calibration_provenance']='Incomplete: no calibration detector arrays saved; checkpoint choices are read but not independently refit.'
    out['saved_result_audit_count']=len(records['audit']);out['saved_result_redecoding_status']='Historical independent re-decoding passed for all raw arrays; this calculation independently recomputes error aggregates from the stored prediction/observable pairs.'
    out['per_regime_hindsight']= {s:v['hindsight_best_regime_name'] for s,v in out['per_stratum'].items()}
    out['per_regime_reported_reconciliation']={}
    saved=json.loads((d/'STAGE2_RECOVERED_RESULTS.json').read_text())
    for s,v in out['per_stratum'].items():
        rec=saved['per_regime'][s]
        out['per_regime_reported_reconciliation'][s]={"saved":rec['errors'],"recomputed":dict(zip(names,v['errors_by_decoder']))}
        assert rec['errors']==dict(zip(names,v['errors_by_decoder']))
    return out,rows

def phase4_ab(folder):
    d=ROOT/folder; names=['fixed','calibrated','model_informed'];rows=[]
    for f in sorted((d/'raw').glob('test_*.npz')):
        record_file(f)
        with np.load(f,allow_pickle=False) as z:
            cond=next((c for c in ['data_heavy','nominal','measurement_heavy'] if c in f.stem),f.stem)
            p=np.stack([z['prediction_fixed'],z['prediction_calibrated'],z['prediction_model_informed']])
            row=add_root(folder.replace('/','_'),cond,f.stem,z['observable_audit_only'],p,names,f);row['baseline_errors']=row['errors'][0];rows.append(row)
    return aggregate_study(folder.replace('/','_'),rows,names,global_fixed_index=0),rows

def correlation_pilot():
    d=ROOT/'outputs/correlation_pilot';names=['pooled_uncorrelated','pooled_correlated','regime_uncorrelated','regime_correlated'];rows=[]
    for f in sorted((d/'checkpoints').glob('*.npz')):
        record_file(f)
        with np.load(f,allow_pickle=False) as z:
            stratum=f"{str(scalar(z,'basis'))}/{str(scalar(z,'regime'))}";root=int(scalar(z,'root_index'))
            row=add_root('correlation_pilot',stratum,str(root),z['observable'],z['predictions'],names,f);row['baseline_errors']=row['errors'][0];rows.append(row)
    return aggregate_study('correlation_pilot',rows,names,global_fixed_index=0),rows

def prototype_dynamic():
    d=ROOT/'outputs/prototype_development';cfg=json.loads((d/'config.json').read_text());names=[f'decoder_{i}' for i in range(9)]
    schedules=defaultdict(list);choice_audit=[]
    for f in sorted((d/'data').glob('eval_*.npz')):
        record_file(f)
        with np.load(f,allow_pickle=False) as z:
            sch=f.stem.split('_rep')[0].replace('eval_','');y=z['observables'];p=z['grid_predictions'].astype(np.uint8);adaptive=z['adaptive_predictions'].astype(np.uint8)
            choices=z['choice_by_block'].astype(int);block_size=len(y)//len(choices)
            regenerated=np.concatenate([p[choices[b],b*block_size:(b+1)*block_size] for b in range(len(choices))])
            match=bool(np.array_equal(regenerated,adaptive));choice_audit.append({"file":f.name,"choices":choices.tolist(),"stored_adaptive_matches_chosen_model":match})
            row=add_root('prototype_dynamic',sch,f.stem,y,p,names,f,block_size=block_size)
            row['adaptive_errors']=int(np.count_nonzero(adaptive!=y));row['pooled_fixed_errors']=int(row['errors'][int(cfg['decoder_grid']['pooled_fixed_index'])]);row['nominal_errors']=int(row['errors'][int(cfg['decoder_grid']['nominal_fixed_index'])]);row['adaptive_choices']=choices.tolist()
            # Hindsight oracle by realized hidden state: score only; never fed into policy.
            state=z['state_ids'].astype(int); state_oracle=0
            for s in np.unique(state):
                mask=state==s
                state_oracle+=int(np.min(np.count_nonzero(p[:,mask]!=y[mask][None,:],axis=1)))
            row['hindsight_state_oracle_errors']=state_oracle;schedules[sch].append(row)
    summary={};
    for sch,rr in sorted(schedules.items()):
        n=sum(x['shots'] for x in rr); pooled=sum(x['pooled_fixed_errors'] for x in rr); adapt=sum(x['adaptive_errors'] for x in rr); oracle=sum(x['shot_oracle_errors'] for x in rr);block=sum(x['block_oracle_errors'] for x in rr);state=sum(x['hindsight_state_oracle_errors'] for x in rr)
        summary[sch]={"roots":len(rr),"shots":n,"pooled_fixed_errors":pooled,"pooled_fixed_ler":pooled/n,"adaptive_errors":adapt,"adaptive_ler":adapt/n,
            "adaptive_minus_pooled_errors":adapt-pooled,"adaptive_minus_pooled_ler":(adapt-pooled)/n,
            "nominal_errors":sum(x['nominal_errors'] for x in rr),"per_shot_bank_oracle_errors":oracle,"per_shot_bank_oracle_ler":oracle/n,
            "per_block_hindsight_oracle_errors":block,"per_block_hindsight_oracle_ler":block/n,
            "hindsight_state_matched_errors":state,"hindsight_state_matched_ler":state/n,
            "choice_sequences_match_saved_adaptive_predictions":all(x['stored_adaptive_matches_chosen_model'] for x in choice_audit if x['file'].startswith('eval_'+sch+'_'))}
    return {"schedules":summary,"choice_audit":choice_audit,"total_roots":sum(len(v) for v in schedules.values()),"total_shots":sum(x['shots'] for rr in schedules.values() for x in rr)},[x for rr in schedules.values() for x in rr]

def phase3b_summary_only():
    d=json.loads((ROOT/'outputs/phase3b_independent_replication/RESULTS.json').read_text())
    return {"status":"raw detectors and labels saved, decoder predictions not saved in the raw NPZ bundles",
        "raw_roots":len(d['raw_files']),"shots_per_root_condition":30000,"conditions":list(d['raw_observable_errors']),
        "fixed_and_specialist_counts_available_in_summary":True,
        "shot_level_oracle_recomputation_possible_without_redecoding":False,
        "primary_statistical_analysis":d['primary_statistical_analysis']}

def main():
    start=time.perf_counter(); summaries={}
    p2a,rows2a,cal2a=phase2a();summaries['phase2a']=p2a
    p2b,rows2b=phase2b();summaries['phase2b']=p2b
    h,hr,selrows,flat=headroom();summaries['headroom_feasibility']=h
    s2,rows2=stage2();summaries['phase4c_stage2']=s2
    p4a,r4a=phase4_ab('outputs/phase4a_model_adequacy');summaries['phase4a']=p4a
    p4b,r4b=phase4_ab('outputs/phase4b_replication');summaries['phase4b']=p4b
    cp,rcp=correlation_pilot();summaries['correlation_pilot']=cp
    proto,rproto=prototype_dynamic();summaries['prototype_development']=proto
    summaries['phase3b_summary_only']=phase3b_summary_only()
    summaries['phase2a']['phase2a_calibration_rates']=(cal2a.tolist())
    # Reconcile Stage 2 plus source-level summaries without loading any test results into a tuner.
    bundle={"generated_local_timestamp":"not recorded to avoid implying experimental freeze timing","studies":summaries,
        "recomputation_scope":{"archived_raw_prediction_bundles_read":len(SOURCE_FILES),"paired_roots":sum(x['root_count'] for x in [p2a,p2b,p4a,p4b,cp,s2]),
            "new_simulation_shots":0,"new_decoder_training_or_model_selection":False,"test_labels_used_only_for_retrospective_oracle_diagnostics":True},
        "limitations":["Hindsight per-shot, per-root, and per-regime oracles select using labels in the same evaluation arrays and are biased upper bounds, not deployable policies.",
          "Oracle headroom is conditional on each archived bank and cannot upper-bound unseen decoder families.",
          "Calibration arrays are missing for Phase 4C Stage 2; its selected calibrated predictions are verifiable but the fit is not independently reproduced.",
          "Phase 5E schedule summaries do not retain shot-level evaluation arrays in their own output; counts are summary-only and not pooled with raw archives.",
          "Phase 3B raw files preserve detectors/labels but not decoder predictions; no shot-level oracle was reconstructed for it.",
          "Exact categorical and independent-DEM posterior results concern separate probability models and are not combined with shot-based physical-channel LER."]}
    save_json(OUT/'RESULTS.json',bundle)
    save_json(OUT/'SOURCE_FILE_HASHES.json',SOURCE_FILES)
    save_json(OUT/'ADAPTIVE_EVIDENCE.json',{"prototype_dynamic":proto,"phase5d_result":json.loads((ROOT/'outputs/phase4c_strong_baselines/adaptive/PHASE5D_RESULTS.json').read_text()),
        "phase5e_findings":str((ROOT/'outputs/phase4c_strong_baselines/adaptive/PHASE5E_FINDINGS.md').read_text(encoding='utf-8')),
        "competition_gate":json.loads((ROOT/'outputs/competition_pivot/GATE_ANALYSIS_RESULTS.json').read_text())})
    with (OUT/'PAIRWISE_COMPLEMENTARITY.csv').open('w',newline='',encoding='utf-8') as f:
        fields=list(PAIR_ROWS[0]) if PAIR_ROWS else [];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(PAIR_ROWS)
    with (OUT/'PER_ROOT_ORACLE_COUNTS.csv').open('w',newline='',encoding='utf-8') as f:
        fields=list(dict.fromkeys(k for row in ROOT_ROWS for k in row));w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(ROOT_ROWS)
    with (OUT/'HEADROOM_CALIBRATION_RECOMPUTATION.csv').open('w',newline='',encoding='utf-8') as f:
        fields=list(selrows[0]) if selrows else [];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(selrows)
    with (OUT/'HEADROOM_PER_REGIME_DECODER_ERRORS.csv').open('w',newline='',encoding='utf-8') as f:
        fields=list(flat[0]) if flat else [];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(flat)
    machine={"status":"COMPLETED_READ_ONLY_ARCHIVE_RECOMPUTATION","studies":{k:{"roots":v.get('root_count',v.get('total_roots')),"shots":v.get('total_shots'),"fixed_ler":v.get('equal_stratum_fixed_ler')} for k,v in summaries.items()},
        "source_npz_count":len(SOURCE_FILES),"pairwise_rows":len(PAIR_ROWS),"per_root_rows":len(ROOT_ROWS),"elapsed_seconds":time.perf_counter()-start}
    save_json(OUT/'RUN_AUDIT.json',machine)
    print(json.dumps(machine,indent=2))

if __name__=='__main__':main()
