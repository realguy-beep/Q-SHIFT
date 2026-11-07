"""Render publication-style summary figures from frozen result JSON."""
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
RESULT=ROOT/"results"/"composition_results_v4_guarded.json"
d=json.loads(RESULT.read_text(encoding="utf-8")); summary=d["aggregate"]
names=list(summary["static"])
decoders=("fixed_matching","oracle_matching","pooled_lookup","per_regime_lookup")
labels=("Fixed PyMatching","Noise-informed PyMatching","Pooled lookup","Per-regime lookup")
fig,ax=plt.subplots(figsize=(11,5.8)); x=np.arange(len(names)); width=.19
for i,(decoder,label) in enumerate(zip(decoders,labels)):
    rates=np.array([summary["static"][n]["decoders"][decoder]["rate"] for n in names])
    cis=np.array([summary["static"][n]["decoders"][decoder]["wilson95"] for n in names])
    lower=rates-cis[:,0];upper=cis[:,1]-rates
    pos=x+(i-1.5)*width
    ax.bar(pos,rates,width,label=label)
    ax.errorbar(pos,rates,yerr=np.vstack([lower,upper]),fmt="none",ecolor="black",elinewidth=.7,capsize=2)
ax.set_yscale("log");ax.set_xticks(x,names,rotation=20,ha="right");ax.set_ylabel("Residual observable error rate (log scale)")
ax.set_title("Noise-composition test, 10 seeds; Wilson 95% shot intervals");ax.legend(fontsize=8);fig.tight_layout()
fig.savefig(ROOT/"figures"/"composition_error_rates_ci.png",dpi=180);plt.close(fig)

fig,ax=plt.subplots(figsize=(6.8,4.8));names=("Fixed matching","Detector adaptive","Oracle true-composition")
keys=("fixed_matching","adaptive_schedule","oracle_schedule");s=summary["schedule"]
rates=[s[k]["rate"] for k in keys];cis=[s[k]["seed_bootstrap_rate_ci95"] for k in keys]
lo=[r-c[0] for r,c in zip(rates,cis)];hi=[c[1]-r for r,c in zip(rates,cis)]
ax.bar(names,rates,color=("#5470c6","#ee6666","#91cc75"));ax.errorbar(np.arange(3),rates,yerr=np.vstack([lo,hi]),fmt="none",ecolor="black",capsize=4)
ax.set_ylabel("Residual observable error rate");ax.set_title("Changing-composition stream; seed-bootstrap 95% intervals");fig.tight_layout()
fig.savefig(ROOT/"figures"/"adaptive_stream_seed_ci.png",dpi=180);plt.close(fig)
print("Saved figures under",ROOT/"figures")
