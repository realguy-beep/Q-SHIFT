import numpy as np
REGIMES={'data_heavy':(.006,.001),'nominal':(.003,.003),'measurement_heavy':(.001,.006)}
def schedule(kind,seed,blocks=8,dwell=256):
 if kind=='data_to_measurement':return ['data_heavy']*4+['measurement_heavy']*4
 if kind=='measurement_to_data':return ['measurement_heavy']*4+['data_heavy']*4
 if kind=='nominal_measurement_nominal':return ['nominal']*3+['measurement_heavy']*2+['nominal']*3
 if kind=='random':
  r=np.random.default_rng(seed);return [str(r.choice(list(REGIMES))) for _ in range(blocks)]
 if kind=='slow':return (['data_heavy']*8+['measurement_heavy']*8+['nominal']*8)[:blocks]
 if kind=='rapid':return [list(REGIMES)[(i//2)%3] for i in range(blocks)]
 if kind=='stationary':return ['nominal']*blocks
 raise ValueError(kind)
