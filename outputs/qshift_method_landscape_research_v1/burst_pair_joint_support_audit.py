"""Map nonburst single-fault alternatives that jointly flip each burst pair."""
from __future__ import annotations
import json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from outputs.qshift_method_landscape_research_v1.categorical_circuit_feature_expectations import categorical_sites,extract_sites
from simulator import build_spatial_burst_circuit

PAIRS=((8,10),(16,18),(24,26),(32,34),(36,38))

def main():
    c=build_spatial_burst_circuit(memory_basis='z',regime='balanced',distance=3,rounds=5,
        gate_p=.003,measurement_p=.003,bias_ratio=10.,burst_probability=.01,burst_pair=(8,10))
    mapped,stats=categorical_sites(c); raw=extract_sites(c)
    out={pair:{'nonburst_alternative_count':0,'nonburst_physical_site_count':0,'exact_support_count':0,
               'higher_order_support_count':0,'categorical_site_groups_touching_both':0,
               'support_size_counts':{},'examples':[],'categorical_group_examples':[]} for pair in PAIRS}
    sites={pair:set() for pair in PAIRS}
    for (ix,_qid,alts),(_old_qid,mapped_alts) in zip(raw,mapped):
        if c[ix].name=='E': continue
        for pair in PAIRS:
            flips_i=any(pair[0] in support for _p,support,_o,_paulis in mapped_alts)
            flips_j=any(pair[1] in support for _p,support,_o,_paulis in mapped_alts)
            if flips_i and flips_j:
                out[pair]['categorical_site_groups_touching_both']+=1
                if len(out[pair]['categorical_group_examples'])<4:
                    out[pair]['categorical_group_examples'].append({'instruction_index':ix,
                        'instruction':str(c[ix]),'one_alternative_flips_i':True,
                        'another_alternative_flips_j':True})
        for prob,support,obs,paulis in mapped_alts:
            s=tuple(sorted(support))
            for pair in PAIRS:
                if pair[0] not in s or pair[1] not in s: continue
                r=out[pair]; r['nonburst_alternative_count']+=1; sites[pair].add(ix)
                r['support_size_counts'][str(len(s))]=r['support_size_counts'].get(str(len(s)),0)+1
                r['exact_support_count']+=int(s==pair)
                r['higher_order_support_count']+=int(len(s)>2)
                if len(r['examples'])<4:
                    r['examples'].append({'instruction_index':ix,'instruction':str(c[ix]),
                        'probability':prob,'pauli_alternative':list(paulis),'detector_support':list(s),
                        'observable_flip':list(obs)})
    for pair in PAIRS: out[pair]['nonburst_physical_site_count']=len(sites[pair])
    result={'classification':'DETERMINISTIC_NONBURST_JOINT_PAIR_SUPPORT_AUDIT',
        'configuration':{'regime':'balanced','gate_p':.003,'measurement_p':.003,'burst_p':.01,
            'distance':3,'rounds':5,'stim_version':__import__('stim').__version__},
        'mapping_statistics':stats,
        'pairs':{f'D{a}&D{b}':out[(a,b)] for a,b in PAIRS},
        'limitations':['This is a complete single-fault-alternative support audit for the declared categorical channel sites. It does not enumerate multi-fault combinations or correlated readout nuisances.','It is deterministic single-Pauli propagation only; no shot sampling, decoding, or logical outcomes.'],
        'sampling_calls':0,'decoder_calls':0}
    p=HERE/'BURST_PAIR_JOINT_SUPPORT_AUDIT.json';p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':p.name,'pairs':{k:{x:v[x] for x in ('nonburst_alternative_count','nonburst_physical_site_count','exact_support_count','higher_order_support_count','categorical_site_groups_touching_both')} for k,v in result['pairs'].items()}},indent=2))

if __name__=='__main__': main()
