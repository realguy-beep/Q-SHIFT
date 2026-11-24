"""Sampler-free X03 constructor probe and B/X09 DEM moment checks."""
from pathlib import Path
import json,sys,math
import numpy as np
from scipy.stats import binom
sys.path.insert(0,str(Path("outputs/qshift_decoder_bank_v9").resolve()))
import db8_config as C
import re1,learner_d5 as LD
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as M
from outputs.qshift_scalable_decoder_dev_v3_2.ldpc_bposd import LdpcBPOSD
import stim
def no_sampler(*a,**k): raise RuntimeError("sampling forbidden")
stim.Circuit.compile_sampler = stim.Circuit.compile_detector_sampler = no_sampler
spec=C.spec(gate_p=C.P0,measurement_p=C.P0)
x03=(3,25,34)
try: re1.decoders(spec,x03)
except ValueError as ex: print("X03 pair constructor failure:",ex)
else: raise AssertionError("X03 unexpectedly builds")
c=M.build_candidate_circuit(spec,re1.R.L2_PRIOR,x03)
d=c.detector_error_model(decompose_errors=False,approximate_disjoint_errors=True)
x=LdpcBPOSD(d,LD.L2); print("X03 actual L2 component builds",d.num_detectors,d.num_observables)
def fingerprints(sup):
 c=M.build_candidate_circuit(spec,C.C2.C1.BURST_Q,tuple(sup))
 d=c.detector_error_model(decompose_errors=False,approximate_disjoint_errors=True)
 sign=np.ones(c.num_detectors)
 pair=np.ones((len(sign),len(sign)))
 for op in d.flattened():
  if op.type != "error": continue
  v=np.zeros(len(sign),bool)
  for t in op.targets_copy():
   if t.is_relative_detector_id(): v[t.val]^=True
  p=op.args_copy()[0]
  sign[v]*=(1-2*p)
  pair[np.logical_xor(v[:,None],v[None,:])]*=(1-2*p)
 r=(1-sign)/2
 cov=(pair-sign[:,None]*sign[None,:])/4
 cofire=cov+r[:,None]*r[None,:]
 return r,cov,cofire
xx,covx,px=fingerprints(C.support("UN"))
bb,covb,pb=fingerprints(C.support("B"))
tpl=np.array(json.loads((C.DB1/"TRAINING.json").read_text())["templates"]["B"])
N=2000
def kl(x, y):
 z=np.clip(x,1e-12,1-1e-12)
 return z*np.log(z/y)+(1-z)*np.log((1-z)/(1-y))
k=np.arange(N+1)
expect=np.sum(2*N*kl(k/N,tpl[:,None])*binom.pmf(k,N,xx[:,None]))
print("N/d/expected fit/lambda",N,len(xx),expect,2*N*kl(xx,tpl).sum())
for nm,v,w in [('marginal',xx,bb),('cofire',px,pb)]:
 delta=np.abs(v-w)
 if v.ndim==2: np.fill_diagonal(delta,-1)
 at=np.unravel_index(delta.argmax(),delta.shape)
 def err(aa,bb): return .5*np.minimum(binom.pmf(k,N,aa),binom.pmf(k,N,bb)).sum()
 print(nm,at,"two rates",v[at],w[at],"model-conditional single-feature error",err(v[at],w[at]))
qcov=covx/np.sqrt(np.outer(np.diag(covx),np.diag(covx)))
e=np.linalg.eigvalsh(qcov); qcov-=np.eye(len(qcov))
print("correlation eigen min/max eff dimension max offdiag",e[0],e[-1],len(e)**2/(e@e),np.max(np.abs(qcov)))
