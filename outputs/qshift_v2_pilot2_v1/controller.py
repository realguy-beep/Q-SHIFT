"""Pilot 2 event detection and generic pair-summary utilities."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
import numpy as np

PAIRS=((8,10),(16,18),(24,26),(32,34),(36,38))

def categories(detectors, kind):
    d=np.asarray(detectors,dtype=np.uint8)
    joint=np.stack([d[:,a]&d[:,b] for a,b in PAIRS],axis=1)
    if kind=='all5': return joint.sum(axis=1).astype(np.int8)
    if kind=='first3': return joint[:,:3].sum(axis=1).astype(np.int8)
    if kind=='any5': return (joint.sum(axis=1)>0).astype(np.int8)
    raise ValueError(f'unknown pair summary {kind}')

def profile(batches, kind, grid):
    maxcat={'all5':5,'first3':3,'any5':1}[kind]+1
    ps=sorted(set(float(p) for p,_ in batches)); rows=[]
    for p in ps:
        c=np.concatenate([categories(d,kind) for q,d in batches if float(q)==p])
        rows.append((np.bincount(c,minlength=maxcat)+.5)/(len(c)+.5*maxcat))
    tab=np.asarray(rows); out=np.column_stack([np.interp(grid,ps,tab[:,j]) for j in range(maxcat)])
    out=np.maximum(out,1e-12); return out/out.sum(axis=1,keepdims=True)

@dataclass
class EventGLR:
    grid: np.ndarray
    likelihoods: np.ndarray
    active_p: float
    threshold: float
    history_blocks: int
    min_dwell_blocks: int
    hysteresis: float
    pair_summary: str
    def __post_init__(self):
        self.grid=np.asarray(self.grid,float); self.lp=np.log(np.asarray(self.likelihoods,float))
        if self.lp.shape[0]!=len(self.grid) or not np.isfinite(self.lp).all(): raise ValueError('bad GLR likelihood table')
        self.buf=deque(maxlen=int(self.history_blocks)); self.block=0; self.last_alarm=-10**9
        self.accepted_alarms=0; self.raw_crossings=0; self.switches=0; self.glr_checks=0
    def observe(self, detector_block, estimate_fn):
        """Call strictly after predictions for detector_block are committed."""
        c=categories(detector_block,self.pair_summary)
        if np.any(c>=self.lp.shape[1]): raise ValueError('category outside fitted support')
        self.buf.append(np.bincount(c,minlength=self.lp.shape[1]).astype(float)); self.block+=1
        if len(self.buf)<self.history_blocks: return self.active_p,False,0.0
        counts=np.sum(np.stack(self.buf),axis=0); active=int(np.argmin(np.abs(self.grid-self.active_p)))
        scores=self.lp@counts-self.lp[active]@counts; scores[active]=-np.inf
        glr=float(np.max(scores)); self.glr_checks+=1
        if glr>self.threshold: self.raw_crossings+=1
        if glr<=self.threshold or self.block-self.last_alarm<self.min_dwell_blocks: return self.active_p,False,glr
        self.accepted_alarms+=1; self.last_alarm=self.block; self.buf.clear()
        new=float(np.clip(estimate_fn(),self.grid[0],self.grid[-1])); idx=int(np.argmin(np.abs(self.grid-new))); new=float(self.grid[idx])
        changed=abs(new-self.active_p)>=self.hysteresis and idx!=int(np.argmin(np.abs(self.grid-self.active_p)))
        if changed: self.active_p=new; self.switches+=1
        return self.active_p,True,glr

def snap(p,grid): return float(grid[int(np.argmin(np.abs(np.asarray(grid,float)-float(p))))])
