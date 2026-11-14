"""Exact single-fault support collision audit for injected burst pairs."""
from __future__ import annotations
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from outputs.qshift_method_landscape_research_v1.categorical_circuit_feature_expectations import categorical_sites,extract_sites
from simulator import build_spatial_burst_circuit
PAIRS=((8,10),(16,18),(24,26),(32,34),(36,38))
def main():
 c=build_spatial_burst_circuit(memory_basis='z',regime='balanced',distance=3,rounds=5,gate_p=.003,measurement_p=.003,bias_ratio=10.,burst_probability=.01,burst_pair=(8,10)); mapped,stats=categorical_sites(c); raw=extract_sites(c); by_pair={pair:{'burst_site_count':0,'nonburst_matching_alternative_count':0,'nonburst_physical_site_count':0} for pair in PAIRS}; collisions={pair:set() for pair in PAIRS}
 for (ix,qid,alts),(_,mapped_alts) in zip(raw,mapped):
  isburst=c[ix].name=='E'
  for p,support,obs,paulis in mapped_alts:
   key=tuple(sorted(support))
   if key not in by_pair:continue
   if isburst:by_pair[key]['burst_site_count']+=1
   else:
    by_pair[key]['nonburst_matching_alternative_count']+=1;collisions[key].add(ix)
 for pair in PAIRS:by_pair[pair]['nonburst_physical_site_count']=len(collisions[pair])
 if any(v['burst_site_count']!=1 for v in by_pair.values()):raise RuntimeError('expected one exact burst site per declared pair support')
 result={'classification':'DETERMINISTIC_EXACT_CATEGORICAL_SINGLE_FAULT_SUPPORT_AUDIT','configuration':{'distance':3,'rounds':5,'gate_p':.003,'measurement_p':.003,'burst_p':.01,'stim_version':__import__('stim').__version__},'mapping_statistics':stats,'support_collision_counts':{f'D{a}&D{b}':by_pair[(a,b)] for a,b in PAIRS},'interpretation_limits':['No baseline categorical single-fault alternative maps to any of the five exact burst detector supports if all nonburst counts are zero.','This is single-fault support uniqueness only; multi-fault combinations, finite-history mean-profile aliases, and gate/readout nuisance remain separate.','No stochastic sampling, decoder call, logical outcome, or protected data.'],'sampling_calls':0,'decoder_calls':0}
 p=HERE/'BURST_CIRCUIT_SUPPORT_COLLISION_AUDIT.json';p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'output':p.relative_to(ROOT).as_posix(),'support_collisions':result['support_collision_counts']},indent=2))
if __name__=='__main__':main()
