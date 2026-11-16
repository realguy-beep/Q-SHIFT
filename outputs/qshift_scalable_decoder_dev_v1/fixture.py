import sys,pathlib,time,json,os
import numpy as np,psutil,pymatching
sys.path.insert(0,str(pathlib.Path.cwd()));sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from factor_bp import FactorBP
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
from outputs.qshift_v1_4b_decoder_optimality.mld import ExactLogicalDecoder
D=int(sys.argv[1]);q=float(sys.argv[2]);p=psutil.Process();start=time.perf_counter();spec=m.CodeSpec(distance=D,rounds=5); support=m.burst_qubits(spec,'scaled_v1'); circuit=m.build_candidate_circuit(spec,q,support);dem=circuit.detector_error_model(decompose_errors=False,approximate_disjoint_errors=True); t=time.perf_counter();bp=FactorBP(dem);build=time.perf_counter()-t;events=m.extract_burst_events(spec,support);fixtures=[np.zeros(spec.detectors,dtype=np.uint8)]
for e in events[:5]:
 x=np.zeros(spec.detectors,dtype=np.uint8);x[list(e.detector_ids)]=1;fixtures.append(x)
t=time.perf_counter();pred=[bp.decode_one(x) for x in fixtures];elapsed=time.perf_counter()-t
exact=None
if D==3:
 dec=ExactLogicalDecoder(dem); a,b=dec.decode(np.stack(fixtures));exact=[{'prediction':int(y[0]),'p1':float(z)} for y,z in zip(a,b)]
print(json.dumps({'distance':D,'q':q,'detectors':spec.detectors,'variables':len(bp.p),'edges':len(bp.edges),'model_build_seconds':build,'inference_seconds':elapsed,'total_seconds':time.perf_counter()-start,'rss_bytes_at_end':p.memory_info().rss,'converged':sum(x['converged'] for x in pred),'fixtures':pred,'d3_exact':exact}))
