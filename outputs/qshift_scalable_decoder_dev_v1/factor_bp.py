"""Bounded detector-factor BP; logical parity is a free output, not an observed check."""
import math
import numpy as np

class FactorBP:
    def __init__(self, dem, iterations=50, damping=0.5, tolerance=1e-8, clip=1e-12):
        if dem.num_observables != 1: raise ValueError('exactly one observable required')
        self.n=dem.num_detectors; self.iterations=iterations; self.damping=damping; self.tolerance=tolerance; self.clip=clip
        self.p=[]; self.det=[]; self.logical=[]
        for ins in dem.flattened():
            if ins.type!='error':
                if ins.type not in ('detector','logical_observable'): raise ValueError('unsupported DEM instruction')
                continue
            ds=set(); logical=0
            for t in ins.targets_copy():
                if t.is_separator(): continue  # XOR components of a single mechanism, not independent events
                if t.is_relative_detector_id(): ds.symmetric_difference_update({t.val})
                elif t.is_logical_observable_id():
                    if t.val!=0: raise ValueError('unsupported observable ID')
                    logical ^= 1
                else: raise ValueError('unsupported DEM target')
            p=float(ins.args_copy()[0])
            if not 0 <= p <= 1: raise ValueError('invalid probability')
            if p==0: continue
            self.p.append(p); self.det.append(tuple(sorted(ds))); self.logical.append(logical)
        if len(self.p)>50000 or sum(map(len,self.det))>50000: raise ValueError('model exceeds limits')
        self.p=np.asarray(self.p,float); self.logical=np.asarray(self.logical,bool)
        self.edges=[(v,c) for v,ds in enumerate(self.det) for c in ds]
        self.by_v=[[] for _ in self.p]; self.by_c=[[] for _ in range(self.n)]
        for e,(v,c) in enumerate(self.edges):
            if not 0<=c<self.n: raise ValueError('detector out of bounds')
            self.by_v[v].append(e);self.by_c[c].append(e)
        self.prior=np.log(np.clip(1-self.p,clip,1)/np.clip(self.p,clip,1))
    def decode_one(self, syndrome):
        x=np.asarray(syndrome)
        if x.shape!=(self.n,) or not np.isin(x,[0,1]).all():raise ValueError('invalid detector syndrome')
        if any(x[c] and not self.by_c[c] for c in range(self.n)):raise ValueError('impossible disconnected syndrome')
        vc=np.array([self.prior[v] for v,c in self.edges],float); cv=np.zeros(len(self.edges)); converged=False
        for it in range(self.iterations):
            new=np.zeros_like(cv)
            for c,es in enumerate(self.by_c):
                for e in es:
                    prod=-1.0 if x[c] else 1.0
                    for other in es:
                        if other!=e:prod*=math.tanh(vc[other]/2)
                    new[e]=2*np.arctanh(np.clip(prod,-1+self.clip,1-self.clip))
            new=self.damping*cv+(1-self.damping)*new
            nxt=np.empty_like(vc)
            for v,es in enumerate(self.by_v):
                total=self.prior[v]+sum(new[e] for e in es)
                for e in es:nxt[e]=total-new[e]
            delta=float(np.max(np.abs(new-cv))) if len(cv) else 0.0
            cv,vc=new,nxt
            if delta<self.tolerance:converged=True;break
        llr=np.array([self.prior[v]+sum(cv[e] for e in es) for v,es in enumerate(self.by_v)])
        parity=1.0
        for v in np.flatnonzero(self.logical):parity*=math.tanh(llr[v]/2)
        p1=float(np.clip((1-parity)/2,0,1))
        return {'prediction':int(p1>0.5),'p1':p1,'converged':converged,'iterations':it+1}
