"""Run frozen v3.4.2 tests and persist a small reproducibility summary."""
import json, sys, time, unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from ownership_runtime_v4 import atomic_json
import test_safety_v4

suite=unittest.defaultTestLoader.loadTestsFromModule(test_safety_v4)
names=[]
def walk(s):
    for item in s:
        if isinstance(item,unittest.TestSuite): walk(item)
        else: names.append(item.id())
walk(suite)
started=time.monotonic()
result=unittest.TextTestRunner(verbosity=2).run(suite)
report={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),
        'failure_messages':[msg[-3000:] for _,msg in result.failures],
        'error_messages':[msg[-3000:] for _,msg in result.errors],
        'test_names':names,'platform':sys.platform,'runtime_seconds':time.monotonic()-started,
        'evidence_root':str(test_safety_v4.EVIDENCE_ROOT.resolve()),
        'stage5_evaluation_shots_generated':0,
        'stage5_run_directory_exists':(HERE.parents[1]/'outputs/stage5_secondary_inference_repair_v1/run').exists()}
atomic_json(HERE/'SAFETY_TEST_RESULTS_V4.json',report)
print(json.dumps(report,indent=2))
raise SystemExit(0 if result.wasSuccessful() else 1)
