from itertools import product
import stim,pymatching
GRID=tuple(product((.001,.003,.006),repeat=2))
def build_bank(distance=3,rounds=5):
 bank=[]
 for gate,meas in GRID:
  c=stim.Circuit.generated('surface_code:rotated_memory_z',distance=distance,rounds=rounds,after_clifford_depolarization=gate,before_measure_flip_probability=meas)
  bank.append(pymatching.Matching.from_detector_error_model(c.detector_error_model(decompose_errors=True)))
 return bank
