"""Causal detector-window estimator and hysteretic decoder controller."""
from collections import deque
import numpy as np

class NoiseEstimator:
    def __init__(self, profiles, window=256): self.profiles=np.asarray(profiles);self.window=window;self.buf=deque(maxlen=window)
    def observe(self, detectors):
        self.buf.extend(np.asarray(detectors,dtype=np.uint8));
        if len(self.buf)<self.window:return None,0.0
        x=np.asarray(self.buf);k=x.sum(0);p=self.profiles
        ll=(k*np.log(p)+(len(x)-k)*np.log1p(-p)).sum(1);z=np.exp(ll-ll.max());post=z/z.sum();return int(post.argmax()),float(post.max()),post

class Controller:
    def __init__(self, fallback=1, confidence=.8, hysteresis=2, dwell=2, switch_penalty=0.):
        self.current=fallback;self.confidence=confidence;self.hysteresis=hysteresis;self.dwell=dwell;self.penalty=switch_penalty;self.streak=0;self.pending=None;self.age=0
    def choose(self, estimate, confidence, utility_scores=None):
        self.age+=1
        candidate=estimate
        if utility_scores is not None:
            candidate=int(np.argmin(utility_scores))
            if candidate==self.current or utility_scores[self.current]-utility_scores[candidate]<=self.penalty:candidate=None
        if candidate is not None and confidence>=self.confidence and candidate!=self.current:
            if self.pending==candidate:self.streak+=1
            else:self.pending=candidate;self.streak=1
        else:self.pending=None;self.streak=0
        if self.age>=self.dwell and self.streak>=self.hysteresis:
            self.current=self.pending;self.age=0;self.streak=0;self.pending=None
        return self.current

def evaluate_block(detectors,observables,models,decoder_index):
    pred=models[decoder_index].decode_batch(detectors)[:,0].astype(bool);return int(np.count_nonzero(pred^observables)),pred
