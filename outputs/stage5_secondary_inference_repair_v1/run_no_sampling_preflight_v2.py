"""Run and persist only the active v2 no-shot Stage 5 preflight."""
from __future__ import annotations
import json, os, time
from pathlib import Path
from stage5_sampling_runner_v2 import HERE, no_shot_preflight

TARGET=HERE/'STAGE5_NO_SAMPLING_PREFLIGHT_V2.json'

def main():
 if TARGET.exists(): raise RuntimeError('refusing to overwrite v2 no-sampling preflight evidence')
 start=time.perf_counter()
 result=no_shot_preflight()
 result['preflight_runtime_seconds']=time.perf_counter()-start
 result['sampling_invoked']=False
 result['stage5_evaluation_shots_generated']=0
 tmp=TARGET.with_suffix('.json.tmp')
 tmp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 os.replace(tmp,TARGET)
 print(json.dumps({'status':result['status'],'runtime_seconds':result['preflight_runtime_seconds'],
    'stage5_evaluation_shots_generated':0,'resource_snapshot':result['resources']},indent=2))

if __name__=='__main__': main()
