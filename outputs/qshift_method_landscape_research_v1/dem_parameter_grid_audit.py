"""Deterministic coarse burst/measurement profile screen on approximate Q-SHIFT DEMs.
No sampling, decoding, or logical outcomes. A coarse grid is not proof of global
identifiability or finite-history accuracy.
Run: python outputs/qshift_method_landscape_research_v1/dem_parameter_grid_audit.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from outputs.qshift_method_landscape_research_v1.dem_feature_expectations import build_dem, direct_feature_covariance, feature_means
BG=np.linspace(.002,.018,9); MG=np.linspace(.001,.005,9); H=1e-4

def mean_at(b,m): return feature_means(build_dem(float(b),float(m))[1])
def main():
 profiles={(float(b),float(m)):mean_at(b,m) for b in BG for m in MG}
 if any(v.shape!=(45,) or not np.isfinite(v).all() or np.any((v<0)|(v>1)) for v in profiles.values()): raise RuntimeError('invalid feature profile')
 _,cov=direct_feature_covariance(build_dem(.010,.003)[1]); scale=np.sqrt(np.maximum(np.diag(cov),1e-12)); rows=sorted(profiles)
 nearest={'distance':float('inf'),'left':None,'right':None}; min_b=float('inf'); min_m=float('inf'); min_both=float('inf')
 for i,a in enumerate(rows):
  for b in rows[i+1:]:
   d=float(np.linalg.norm((profiles[a]-profiles[b])/scale)/np.sqrt(45))
   if a[0]!=b[0]: min_b=min(min_b,d)
   if a[1]!=b[1]: min_m=min(min_m,d)
   if a[0]!=b[0] and a[1]!=b[1]: min_both=min(min_both,d)
   if d<nearest['distance']: nearest={'distance':d,'left':a,'right':b}
 probes=[(.002,.001),(.018,.001),(.002,.005),(.018,.005),(.010,.003),(.006,.004),(.014,.002)]; sens=[]
 for b,m in probes:
  jb=(mean_at(b+H,m)-mean_at(b-H,m))/(2*H); jm=(mean_at(b,m+H)-mean_at(b,m-H))/(2*H); J=np.column_stack((jb,jm)); sv=np.linalg.svd(J,compute_uv=False); Jw=J/scale[:,None]; svw=np.linalg.svd(Jw,compute_uv=False)
  sens.append({'burst_p':b,'measurement_p':m,'rank':int(np.linalg.matrix_rank(J)),'singular_values_raw':sv.tolist(),'condition_ratio_raw':float(sv[0]/sv[-1]),'singular_values_nominal_variance_standardized':svw.tolist(),'condition_ratio_nominal_variance_standardized':float(svw[0]/svw[-1]),'column_cosine':float(np.dot(jb,jm)/(np.linalg.norm(jb)*np.linalg.norm(jm)))})
 result={'classification':'DETERMINISTIC_APPROXIMATE_DEM_COARSE_GRID_SCREEN','model':{'gate_p':.003,'bias_ratio':10.,'burst_pair':[8,10],'distance':3,'rounds':5,'dem_options':{'decompose_errors':True,'approximate_disjoint_errors':True},'feature_count':45},'parameter_grids':{'burst_probability':BG.tolist(),'measurement_probability':MG.tolist(),'note':'Measurement range is exploratory around nominal 0.003, not a frozen protocol condition.'},'profile_count':len(profiles),'distance_definition':'RMS Euclidean distance between 45 population mean vectors standardized by nominal approximate-DEM single-shot feature standard deviations.','nearest_distinct_grid_profiles':nearest,'minimum_distance_burst_differs':min_b,'minimum_distance_measurement_differs':min_m,'minimum_distance_both_parameters_differ':min_both,'local_jacobian_probes':sens,'limitations':['Finite coarse grid cannot prove global injectivity or exclude off-grid collisions.','Distances are population mean separation, not sample-size-adjusted estimator accuracy.','Expectations are exact only for converted approximate independent-event DEM, not original categorical circuit distribution.','Gate noise, temporal drift, correlated readout, and finite-history estimator covariance are not varied.','Measurement range is exploratory, not owner-approved.'],'sampling_calls':0,'decoder_calls':0}
 p=HERE/'DEM_PARAMETER_GRID_AUDIT.json'; p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(json.dumps({'output':p.relative_to(ROOT).as_posix(),'profiles':len(profiles),'nearest':nearest,'min_burst_different':min_b,'min_measurement_different':min_m,'min_both_different':min_both,'ranks':[x['rank'] for x in sens]},indent=2))
if __name__=='__main__': main()
