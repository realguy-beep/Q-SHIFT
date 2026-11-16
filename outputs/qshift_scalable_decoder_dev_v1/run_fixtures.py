import subprocess,sys,json,time,pathlib
p=pathlib.Path('outputs/qshift_scalable_decoder_dev_v1'); out=[]
if (p/'fixture_results.json').exists(): raise FileExistsError('Preserve existing fixture evidence; use a new versioned directory')
for d in (3,5,7):
 for q in (0.0,0.01):
  try:
   t=time.monotonic();r=subprocess.run([sys.executable,str(p/'fixture.py'),str(d),str(q)],capture_output=True,text=True,timeout=120)
   out.append({'distance':d,'q':q,'exit':r.returncode,'wall_seconds':time.monotonic()-t,'result':json.loads(r.stdout) if r.returncode==0 else None,'error':r.stderr[-2000:]})
  except subprocess.TimeoutExpired:out.append({'distance':d,'q':q,'exit':'timeout','wall_seconds':120})
  (p/'fixture_results.json').write_text(json.dumps(out,indent=2)+'\n')
  if out[-1]['exit'] != 0: break
print(json.dumps([{'d':a['distance'],'q':a['q'],'exit':a['exit'],'wall':a['wall_seconds']} for a in out],indent=2))
