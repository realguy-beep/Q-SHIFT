"""Write human-readable Pilot 2 analyses from independently audited artifacts."""
import csv,json
from pathlib import Path
OUT=Path(__file__).resolve().parent
cfg=json.loads((OUT/'PILOT2_CONFIG.json').read_text(encoding='utf-8'))
audit=json.loads((OUT/'PILOT2_AUDIT.json').read_text(encoding='utf-8'))
rt=json.loads((OUT/'PILOT2_RUNTIME.json').read_text(encoding='utf-8'))
tune=json.loads((OUT/'PILOT2_TUNING_CANDIDATES.json').read_text(encoding='utf-8'))
rows=list(csv.DictReader((OUT/'PILOT2_RESULTS.csv').open(encoding='utf-8',newline='')))
policies=cfg['policies']; scenarios=cfg['allocation']['evaluation_scenarios']; modes=['False','True']
def fnum(x,d=3): return f'{float(x):.{d}f}'
def pp(x): return f'{float(x)*100:.4f}'
def get_rows(mode=None,policy=None,scenario=None):
    return [r for r in rows if (mode is None or r['correlation_decode']==mode) and (policy is None or r['policy']==policy) and (scenario is None or r['scenario']==scenario)]
def pooled(mode,pol):
    q=get_rows(mode,pol); e=sum(int(x['errors']) for x in q); n=sum(int(x['scored_shots']) for x in q); return e,n,e/n

def make_pair_analysis():
    L=['# Q-SHIFT v2 Pilot 2 paired analysis','',
       'All estimates are development-only and use unconditional logical errors (decoder prediction XOR the shared observable). The two PyMatching modes replay the same detector/observable streams. There are 20 independent roots per scenario; shots within a stream are not treated as independent replicates.', '',
       '## Aggregate arm results','', '| Policy | Ordinary errors / 208,000 | Ordinary LER | Correlation-aware errors / 208,000 | Correlation-aware LER |','|---|---:|---:|---:|---:|']
    for pol in policies:
        e0,n0,l0=pooled('False',pol); e1,n1,l1=pooled('True',pol)
        L.append(f'| `{pol}` | {e0:,} / {n0:,} | {l0*100:.4f}% | {e1:,} / {n1:,} | {l1*100:.4f}% |')
    L+=['','The privileged true-p row is nondeployable and is not a performance lower bound. Static p was selected independently for each decoder mode from 5,500 labeled development shots: p=.008 ordinary and p=.014 correlation-aware. The result selected p per mode was not selected on evaluation outcomes.','',
       '## Prespecified paired primary comparisons','',
       'The effect is the equally weighted eight-scenario average of stream-level paired LER differences. Intervals are two-sided 95% percentile intervals from 20,000 stratified cluster-bootstrap draws, resampling the 20 roots within each scenario; seed 8,820,261,108. Values below are percentage points (pp).']
    for key,label in [('False','ordinary matching'),('True','explicit correlation-aware matching')]:
        L+=['',f'### {label}','', '| Comparator | Event − comparator (pp) | 95% stream-cluster interval (pp) | Relative LER difference | Paired event-only / comparator-only errors |','|---|---:|---:|---:|---:|']
        for comp in ('static_dev','ewma_08'):
            st=audit['statistics'][f'{key}:{comp}']; lo,hi=st['ci95_cluster_bootstrap']
            L.append(f"| `{comp}` | {pp(st['event_minus_comparator'])} | [{pp(lo)}, {pp(hi)}] | {st['relative_ler_difference']*100:.2f}% | {st['paired_event_only_total']} / {st['paired_comparator_only_total']} |")
    L+=['','Interpretation under the frozen LER rule: in ordinary mode, event GLR beats the static comparator by the interval criterion, but its interval against EWMA includes zero. In correlation-aware mode, event beats EWMA, but its interval against static includes zero. Thus no mode clears both co-primary LER comparisons. These are development intervals, not independent confirmation.','',
       '## Per-scenario event comparisons','',
       'Each scenario contains 20 roots × 1,300 scored shots. Entries show errors for event/static/EWMA and paired event-only versus comparator-only discordances (20 roots pooled). Descriptive scenario results are not separately powered.','',
       '| Scenario | Mode | Event errors | Static errors | EWMA errors | Event-only vs static / static-only | Event-only vs EWMA / EWMA-only |','|---|---|---:|---:|---:|---:|---:|']
    for mode in modes:
      for sc in scenarios:
        st=audit['statistics'][f'{mode}:static_dev']['per_scenario'][sc]
        ew=audit['statistics'][f'{mode}:ewma_08']['per_scenario'][sc]
        L.append(f"| {sc} | {'corr-aware' if mode=='True' else 'ordinary'} | {st['event_errors']} | {st['comparator_errors']} | {ew['comparator_errors']} | {st['paired_event_only']} / {st['paired_comparator_only']} | {ew['paired_event_only']} / {ew['paired_comparator_only']} |")
    L+=['','## Static-noise performance and alarms','',
       'For the event arm, evaluation false alarms are alarms during constant burst-p segments, including the constant-p measurement-mismatch scenario; smooth drift is not a constant-p false-alarm condition. In the three correctly specified stationary scenarios, it recorded 31 accepted alarms over 78,000 scored shots (0.397 per 1,000); by p, counts were 3/20 at p=0, 18/20 at p=.008, and 10/20 at p=.016. Under measurement mismatch it recorded 17 alarms over 26,000 shots (0.654 per 1,000), with burst p fixed at .008. The 20-stream stationary counts are imprecise.', '',
       'Selected GLR C00 had threshold 4, four-block history, two-block dwell, zero hysteresis, 100-shot profile window, and `any5` pair summary. On separate stationary calibration data, it had 14 accepted alarms over 28,800 scored shots (0.486 per 1,000): 6/9,600 at p=0, 6/9,600 at p=.008, and 2/9,600 at p=.016. It met the frozen target of no more than 1 alarm per 1,000 pooled and at each p. All 24 candidates met eligibility; the selected one had the lowest tuning delay by the frozen tie-break rule.', '',
       'Mean evaluation delay for event GLR was 45 shots after the step-up, 95 after the step-down, and 40 during the 100-shot transient (20 roots each; 50-shot blocks). The corresponding EWMA means were:']
    for sc in ('step_up','step_down','transient'):
        q=get_rows('False','ewma_08',sc); vals=[int(x['detection_delay_shots']) for x in q if x['detection_delay_shots']!='']
        L.append(f'- {sc}: {sum(vals)/len(vals):.1f} shots.')
    L+=['','Event GLR therefore used fewer cached models but responded more slowly than EWMA on the step-down. It recorded 163 graph switches across 160 streams (1.02 per stream); EWMA recorded 3,360 (21.0 per stream). Graph-switch savings alone do not establish a win.','',
       '## Limitations','',
       '- The 20 independent streams per scenario improve on Pilot 1 but still leave broad root-level uncertainty; several primary intervals are near zero.','- The static selection set has 500 shots per candidate burst p; selection is separate from evaluation but remains noisy.','- Noise is a synthetic distance-3, five-round Stim model. The measurement mismatch changes measurement-flip probability from .003 to .006; it is not hardware drift.','- The correlation-aware mode operates on the decomposed DEM approximation, not exact circuit-level maximum-likelihood decoding.','- The paired CSV was repaired after the independent audit found a `uint8` bitwise-negation error in derived contingency cells. Primary errors were independently checked against the unchanged paired archive. The original CSV and intermediate repair attempts remain preserved.','- Three execution/audit failures and their fixes are logged as artifacts. The successful evaluation used the same predeclared seed allocation; no new evaluation seeds were added.','- No Stage 5 outcomes or frozen evaluation seeds were opened, and no independent confirmation was conducted.']
    (OUT/'PILOT2_PAIRED_ANALYSIS.md').write_text('\n'.join(L)+'\n',encoding='utf-8')

def make_runtime():
    L=['# Q-SHIFT v2 Pilot 2 runtime analysis','',
       '## Measured run cost','',
       f"- Total runner wall time: {rt['seconds_wall']:.2f} s; process CPU: {rt['seconds_process_cpu']:.2f} s.",
       f"- Evaluation replay: {rt['evaluation_replay_cpu_s']:.2f} CPU s for 160 streams, eight policies and two decoder modes.",
       f"- Cached decoder-bank construction: {rt['graph_bank_cpu_s']:.3f} CPU s ({rt['graph_bank_wall_s']:.3f} s wall); privileged exact-p graph construction added {rt['oracle_extra_graph_cpu_s']:.3f} CPU s.",
       f"- Profile template generation/fitting: {rt['profile_training_cpu_s']:.3f} CPU s; static selection data generation {rt['static_selection_data_generation_cpu_s']:.3f} s and scoring {rt['static_selection_cpu_s']:.3f} s.",
       f"- Stationary GLR and change-tuning data generation: {rt['calibration_and_tuning_data_generation_cpu_s']:.3f} CPU s; 24-candidate detector-only calibration/tuning replay: {rt['candidate_calibration_and_tuning_cpu_s']:.3f} CPU s.",
       f"- Peak process RSS: {rt['peak_process_rss_bytes']:,} bytes ({rt['peak_process_rss_bytes']/1048576:.1f} MiB); Python tracemalloc peak: {rt['peak_tracemalloc_bytes']:,} bytes ({rt['peak_tracemalloc_bytes']/1048576:.1f} MiB). RSS is process-wide and cannot be attributed to a single C++ matcher.",
       '', '## Per-stream online CPU comparison','',
       'For this paired two-mode replay, decoder time is summed across ordinary and correlation-aware modes; shared initial detector-profile calibration and policy adaptation are charged once per stream because the same detector-only decisions serve both modes. One-time graph-bank and template-training costs are shown separately above.']
    online={}
    for pol in policies:
        total=0; streams=sorted(set(r['stream_key'] for r in get_rows(policy=pol)))
        for stream in streams:
            q=[r for r in get_rows(policy=pol) if r['stream_key']==stream]
            decode=sum(float(x['decoder_cpu_s']) for x in q)
            q0=q[0]; shared=float(q0['shared_initial_calibration_cpu_s'])
            adapt=sum(float(q0[k]) for k in ('estimator_cpu_s','change_detection_cpu_s','graph_selection_cpu_s'))
            total+=decode+shared+adapt
        online[pol]=total/len(streams)
    L+=['','| Policy | Two-mode online CPU / stream (s) |','|---|---:|']
    for pol in policies: L.append(f'| `{pol}` | {online[pol]:.6f} |')
    evt=online['event_glr']; ew=online['ewma_08']; save=(1-evt/ew)*100
    event_switch=sum(int(x['graph_switches']) for x in get_rows('False','event_glr'))/160
    ewma_switch=sum(int(x['graph_switches']) for x in get_rows('False','ewma_08'))/160
    L+=['',f'Online operational replay gives event GLR {save:.1f}% lower CPU per stream than EWMA and {1-event_switch/ewma_switch:.1%} fewer graph switches ({event_switch:.2f} vs {ewma_switch:.2f} per stream). Event-minus-EWMA LER is within the prespecified +0.10 pp noninferiority margin in both modes. This operational result depends on treating threshold/tuning data costs as one-time setup.','',
       '## Calibration-inclusive sensitivity','']
    tuning_cpu=rt['candidate_calibration_and_tuning_cpu_s']+rt['calibration_and_tuning_data_generation_cpu_s']
    ev_allin=evt*160+tuning_cpu+rt['profile_training_cpu_s']+rt['graph_bank_cpu_s']
    ew_allin=ew*160+rt['profile_training_cpu_s']+rt['graph_bank_cpu_s']
    breakeven=tuning_cpu/(ew-evt)
    L.append(f'Event-specific candidate-tuning replay and stationary/tuning data generation cost {tuning_cpu:.3f} CPU s. Across 160 streams, that is {tuning_cpu/160:.6f} s per stream if charged to this run. Including shared profile and graph-bank setup, event totals {ev_allin:.3f} CPU s and EWMA {ew_allin:.3f} CPU s. Event is {(ev_allin/ew_allin-1)*100:.1f}% higher on this strict pilot-horizon all-in accounting. Online savings amortize the event-only setup after about {breakeven:.0f} streams if calibration remains valid and reusable.')
    L+=['','The frozen protocol separated one-time calibration/training costs from replay costs but did not explicitly state whether the decision-rule CPU comparison should amortize event-only GLR tuning over future streams. These accounting views cannot be collapsed into a post-hoc GO claim. This ambiguity is carried into the final decision.','',
       '## Instrumentation limits','',
       '- Decoder CPU uses `time.process_time()` around batch decode calls; estimator, GLR, and graph-selection sections are timed separately. Timer overhead and machine scheduling are not subtracted.','- Peak RSS is sampled process-wide every 50 ms; it is a reliable run-level bound, not per-arm memory attribution.','- The evaluation includes shared profile initialization per stream. It excludes hardware communication and live calibration data acquisition latency.',
       '- Software: Python '+rt['python']+', NumPy '+rt['numpy']+', Stim '+rt['stim']+', PyMatching '+rt['pymatching']+', psutil '+rt['psutil']+'. Platform: '+rt['platform']+'.']
    (OUT/'PILOT2_RUNTIME_ANALYSIS.md').write_text('\n'.join(L)+'\n',encoding='utf-8')

def make_decision():
    keys={k:v for k,v in audit['statistics'].items()}
    ordinary_static=keys['False:static_dev']; ordinary_ewma=keys['False:ewma_08']; corr_static=keys['True:static_dev']; corr_ewma=keys['True:ewma_08']
    L=['# Q-SHIFT v2 Pilot 2 final decision','',
       '**Decision: NO-GO for launching the 11.736M-shot study on the current evidence.** This is a decision about readiness, not a claim that causal adaptation cannot work. The development pilot is not independent confirmation.','',
       '## Frozen decision-rule result','',
       'The LER GO rule required event GLR to have a 95% stream-cluster interval entirely below zero against both the development-selected static decoder and EWMA in at least one decoder mode. It did not:',
       f"- Ordinary: event vs static {pp(ordinary_static['event_minus_comparator'])} pp [{pp(ordinary_static['ci95_cluster_bootstrap'][0])}, {pp(ordinary_static['ci95_cluster_bootstrap'][1])}]; vs EWMA {pp(ordinary_ewma['event_minus_comparator'])} pp [{pp(ordinary_ewma['ci95_cluster_bootstrap'][0])}, {pp(ordinary_ewma['ci95_cluster_bootstrap'][1])}].",
       f"- Correlation-aware: event vs static {pp(corr_static['event_minus_comparator'])} pp [{pp(corr_static['ci95_cluster_bootstrap'][0])}, {pp(corr_static['ci95_cluster_bootstrap'][1])}]; vs EWMA {pp(corr_ewma['event_minus_comparator'])} pp [{pp(corr_ewma['ci95_cluster_bootstrap'][0])}, {pp(corr_ewma['ci95_cluster_bootstrap'][1])}].",
       '',
       'The operational cost/accuracy comparison is promising: event was within the +0.10 pp noninferiority margin versus EWMA in both modes, used about 95% fewer graph switches, and used about 81% less online CPU per stream. But when the event-specific 6.922 CPU seconds of threshold calibration/tuning data generation and replay are charged to this 160-stream pilot, event has higher total CPU. The frozen protocol did not define the amortization horizon for this one-time cost. Since the cost GO rule says lower total CPU, the result is not sufficient to pass it without a predeclared cost accounting.','',
       '## Evidence and recommendation','',
       '- The event arm had 1,223 ordinary errors vs 1,239 static and 1,237 EWMA; with correlation-aware decoding it had 1,552 vs 1,551 static and 1,580 EWMA, each out of 208,000 scored shots. Effects are small; cluster intervals remain important.','- Selected GLR met its stationary calibration target (0.486 alarms/1,000 calibration shots) but showed 31 evaluation alarms in the three correctly specified stationary scenarios and 17 in the constant-burst measurement-mismatch scenario.','- Change response was 45 shots step-up, 95 step-down, and 40 transient, slower than EWMA on average.','- The independent audit passed after repairing paired contingency and derived CPU columns from the saved aligned outcomes. All failed execution/audit attempts and intermediate CSVs are retained.','- Retain static and EWMA as strong references. Keep the event controller as a development candidate, not a selected replacement. Do not launch the full study.','',
       'A follow-up should first freeze an explicit calibration amortization horizon and cost formula, retain paired per-shot outputs, and use the repaired contingency helper before any new sample. The current 298,500-shot pilot budget has been consumed; any further development sampling needs a separately approved allocation. No Stage 5 or sealed data were accessed.','',
       '## Reproducibility and source hashes','',
       f"Branch/worktree: `qshift-v2-dev`; current base/commit is recorded in Git. Frozen config SHA-256: `{rt['config_sha256']}`. Seed inventory SHA-256: `{rt['seed_inventory_sha256']}`. Final repaired results SHA-256: `{rt['results_sha256']}`. Paired archive SHA-256: `{rt['paired_outcomes_sha256']}`.", '', 'Final source SHA-256:']
    for n,h in rt['final_source_hashes_sha256'].items(): L.append(f'- `{n}`: `{h}`')
    L+=['',f"Astra research report input SHA-256: `{rt['input_report_hashes_sha256']['astra_research_report']}`. Pilot 1 report input SHA-256: `{rt['input_report_hashes_sha256']['pilot1_report']}`.",'',
       'Commands: `python -m outputs.qshift_v2_pilot2_v1.prepare_pilot2 --freeze` (seed plan already frozen); `python -m outputs.qshift_v2_pilot2_v1.preflight_audit`; `python -m outputs.qshift_v2_pilot2_v1.test_pilot2`; `python -m outputs.qshift_v2_pilot2_v1.run_pilot2`; `python -m outputs.qshift_v2_pilot2_v1.repair_paired_metrics`; `python -m outputs.qshift_v2_pilot2_v1.independent_audit`. The repaired result file carries the original pre-repair hash and source-at-execution hash in `PILOT2_RUNTIME.json`.']
    (OUT/'PILOT2_FINAL_DECISION.md').write_text('\n'.join(L)+'\n',encoding='utf-8')

make_pair_analysis(); make_runtime(); make_decision()
print('wrote paired, runtime, and final-decision reports')
