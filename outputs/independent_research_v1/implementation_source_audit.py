"""Fetch and hash pinned official implementation documentation/source used in the audit."""
from __future__ import annotations
import hashlib,json,urllib.request
from pathlib import Path
import importlib.metadata as metadata
import qecsim.models.planar
import inspect
HERE=Path(__file__).resolve().parent

SOURCES={
 'stim_cli':('https://raw.githubusercontent.com/quantumlib/Stim/v1.16.0/doc/usage_command_line.md',['PAULI_CHANNEL_2','attempts to do this']),
 'stim_dem_format':('https://raw.githubusercontent.com/quantumlib/Stim/v1.16.0/doc/file_format_dem_detector_error_model.md',['independent','correlated errors']),
 'pymatching_readme':('https://raw.githubusercontent.com/oscarhiggott/PyMatching/v2.4.0/README.md',['correlation','enable_correlations']),
 'qecsim_mps_source':('https://raw.githubusercontent.com/qecsim/qecsim/1.0b9/src/qecsim/models/planar/_planarmpsdecoder.py',['chi=None','exponentially slow','most probable']),
}

def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'QSHIFT-independent-research-source-audit/1.0'})
 with urllib.request.urlopen(req,timeout=15) as response:
  return response.status,response.read(),response.headers.get('ETag')

def excerpt(lines,needle):
 target=needle.lower()
 for i,line in enumerate(lines):
  if target in line.lower():return '\n'.join(lines[max(0,i-1):min(len(lines),i+3)])[:1200]
 return None

def main():
 rows={}
 for key,(url,needles) in SOURCES.items():
  status,body,etag=fetch(url);text=body.decode('utf-8','replace');lines=text.splitlines()
  rows[key]={'url':url,'http_status':status,'sha256':hashlib.sha256(body).hexdigest(),'etag':etag,
             'bytes':len(body),'matches':{n:excerpt(lines,n) for n in needles}}
 local=Path(inspect.getfile(qecsim.models.planar.PlanarMPSDecoder))
 remote=rows['qecsim_mps_source']
 _,remote_body,_=fetch(SOURCES['qecsim_mps_source'][0])
 local_body=local.read_bytes()
 rows['qecsim_local_comparison']={'installed_version':metadata.version('qecsim'),
   'local_source_path':str(local),'local_sha256':hashlib.sha256(local_body).hexdigest(),
   'tag_source_sha256':remote['sha256'],'byte_identical':local_body==remote_body}
 out={'status':'pinned_official_source_retrieval_passed','retrieval_date_utc':'2026-11-18',
   'sources':rows,
   'paper_record_access':{'arxiv_api':'proxy 403','crossref_api':'proxy 403'},
   'scope':'official pinned source/docs; verifies implementation claims, not a systematic literature search or novelty claim'}
 (HERE/'implementation_source_audit.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'status':out['status'],'qecsim_local_matches_tag':rows['qecsim_local_comparison']['byte_identical'],
   'sources':{k:{'http_status':v.get('http_status'),'sha256':v.get('sha256')} for k,v in rows.items() if 'url' in v}},indent=2))

if __name__=='__main__':main()
