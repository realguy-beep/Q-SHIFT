import { useEffect, useMemo, useState } from 'react'
import { Activity, ArrowRight, Atom, BarChart3, BookOpen, CheckCircle2, CircleHelp, Database, FlaskConical, Gauge, Play, ShieldCheck, Sparkles, Waves } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { LiveResult, ResearchReplay } from './types'
import { formatPercent } from './metrics'

type Tab = 'overview' | 'simulator' | 'dataset' | 'evidence'

const API = ''
const nav: Array<{ id: Tab; label: string; icon: typeof Activity }> = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'simulator', label: 'Live simulator', icon: FlaskConical },
  { id: 'dataset', label: 'Syndrome explorer', icon: Database },
  { id: 'evidence', label: 'Research evidence', icon: BarChart3 },
]

function StatCard({ label, value, note, accent = false }: { label: string; value: string; note: string; accent?: boolean }) {
  return <div className={`stat-card ${accent ? 'stat-accent' : ''}`}><span className="eyebrow">{label}</span><strong>{value}</strong><small>{note}</small></div>
}

function App() {
  const [tab, setTab] = useState<Tab>('overview')
  const [health, setHealth] = useState('checking')
  const [history, setHistory] = useState<ResearchReplay | null>(null)
  const [live, setLive] = useState<LiveResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [burst, setBurst] = useState(0.008)
  const [shots, setShots] = useState(2000)
  const [calibration, setCalibration] = useState(1000)
  const [seed, setSeed] = useState(7)

  useEffect(() => {
    fetch(`${API}/api/health`).then(r => r.json()).then(d => setHealth(d.status === 'ready' ? 'online' : 'unavailable')).catch(() => setHealth('offline'))
    fetch(`${API}/api/research`).then(r => r.json()).then(setHistory).catch(() => setHistory(null))
  }, [])

  async function runSimulation() {
    setBusy(true); setError('')
    try {
      const response = await fetch(`${API}/api/simulate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ burst_probability: burst, shots, calibration_shots: calibration, seed }) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Simulation request failed')
      setLive(data); setTab('simulator')
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not reach the local simulation service.') }
    finally { setBusy(false) }
  }

  const graphData = useMemo(() => live ? [
    { name: 'No correction', LER: live.no_decoding_reference.ler * 100 },
    ...live.methods.map(x => ({ name: x.id === 'fixed_nominal' ? 'Fixed' : x.id === 'detector_estimated' ? 'Estimated' : 'Privileged', LER: x.ler * 100 })),
  ] : [], [live])
  const historicalFixed = Number((history?.aggregate.evaluation_totals as any)?.fixed_nominal?.ler)
  const historicalEstimated = Number((history?.aggregate.evaluation_totals as any)?.detector_estimated?.ler)
  const historicalFixedErrors = Number((history?.aggregate.evaluation_totals as any)?.fixed_nominal?.errors)
  const historicalEstimatedErrors = Number((history?.aggregate.evaluation_totals as any)?.detector_estimated?.errors)
  const primaryCI = history?.statistics?.primary_bootstrap_95ci as [number, number] | undefined
  const currentNav = nav.find(x => x.id === tab)?.label ?? 'Overview'

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Atom size={21} /></div><div><b>Q-SHIFT</b><small>QUANTUM ERROR-CORRECTION LAB</small></div></div>
      <div className="side-label">WORKSPACE</div>
      <nav>{nav.map(item => <button key={item.id} className={tab === item.id ? 'nav-item active' : 'nav-item'} onClick={() => setTab(item.id)}><item.icon size={17} /><span>{item.label}</span>{item.id === 'simulator' && <span className="nav-dot" />}</button>)}</nav>
      <div className="sidebar-spacer" />
      <div className="side-project"><div className="small-icon"><Waves size={17} /></div><div><b>Research prototype</b><small>SIMULATION ONLY</small></div></div>
      <div className="side-footer"><span className={`health-dot ${health === 'online' ? 'ok' : ''}`} /> Local engine {health === 'online' ? 'ready' : health}</div>
    </aside>
    <main className="main-area">
      <header className="topbar"><div><span className="crumb">Q-SHIFT LAB</span><span className="crumb-sep">/</span><b>{currentNav}</b></div><div className="top-status"><span className="health-dot ok" /> Offline-ready <span className="status-divider" /> <span className="chip">D3 · 5 rounds</span></div></header>
      <div className="content">
        {tab === 'overview' && <>
          <section className="hero">
            <div className="hero-copy"><div className="hero-tag"><Sparkles size={13} /> LOCAL RESEARCH DEMO</div><h1>When noise shifts,<br /><em>decoding adapts.</em></h1><p>Explore how detector measurements can reveal a changing error pattern — and how a noise-aware decoder compares with a fixed baseline.</p><div className="hero-actions"><button className="button button-dark" onClick={() => setTab('simulator')}><FlaskConical size={16} /> Open simulator <ArrowRight size={15} /></button><button className="button button-plain" onClick={() => setTab('evidence')}>View research evidence</button></div></div>
            <div className="hero-art" aria-label="Illustrative syndrome grid"><div className="grid-caption">ILLUSTRATIVE GRID <span>NOT A LIVE SHOT</span></div><div className="syndrome-grid">{Array.from({ length: 40 }, (_, i) => <span key={i} className={`syndrome-cell ${[3, 9, 10, 17, 24, 31].includes(i) ? 'lit' : ''}`} />)}</div><div className="round-labels">{[1, 2, 3, 4, 5].map(i => <span key={i}>R{i}</span>)}</div><div className="signal-foot"><span>Decorative preview</span><span>40 detector bits</span></div></div>
          </section>
          <div className="saved-label"><BookOpen size={13}/> Saved Stage 4 development summary · values loaded from committed results</div><div className="stats-row"><StatCard label="PAIRED EVALUATION" value={history?Number(history.aggregate.paired_evaluation_shots).toLocaleString():'—'} note="Same shots across decoder arms" accent/><StatCard label="FIXED PyMATCHING" value={Number.isFinite(historicalFixed)?formatPercent(historicalFixed):'—'} note={Number.isFinite(historicalFixedErrors)?`${historicalFixedErrors.toLocaleString()} logical errors`:''}/><StatCard label="DETECTOR-ESTIMATED" value={Number.isFinite(historicalEstimated)?formatPercent(historicalEstimated):'—'} note={Number.isFinite(historicalEstimatedErrors)?`${historicalEstimatedErrors.toLocaleString()} logical errors`:''}/><StatCard label="RECORDED AUDIT" value={history?.audit ?? '…'} note={history?.summary_hash_matches_audit?'Summary hash matches audit':'Saved summary hash differs from audit snapshot'}/></div>
          <div className="section-heading"><div><span className="eyebrow">THE Q-SHIFT PIPELINE</span><h2>From syndrome to smarter weights</h2></div><button className="text-link" onClick={() => setTab('simulator')}>Try a live run <ArrowRight size={14} /></button></div>
          <div className="pipeline">{[{icon: Waves,title:'Measure',text:'Stim generates detector outcomes from a simulated memory circuit.'},{icon: Gauge,title:'Estimate',text:'A separate calibration batch estimates synthetic burst strength.'},{icon: ShieldCheck,title:'Reconfigure',text:'The estimated model rebuilds a PyMatching decoder.'},{icon: BarChart3,title:'Compare',text:'All decoders score identical held-out simulation shots.'}].map((x,i)=><div className="pipeline-item" key={x.title}><div className="pipeline-icon"><x.icon size={18}/></div><span className="step">0{i+1}</span><h3>{x.title}</h3><p>{x.text}</p>{i<3&&<span className="pipeline-arrow">→</span>}</div>)}</div>
          <div className="milestones"><div><span className="milestone-state pass">PASS · DEVELOPMENT</span><b>Detector-calibrated PyMatching</b><small>Stage 4B saved-data audit reports a pass for its synthetic conditions.</small></div><div><span className="milestone-state pending">NOT CONFIRMED</span><b>Generalization</b><small>Independent confirmation remains separate and is not bundled here.</small></div><div><span className="milestone-state neutral">NOT CONNECTED</span><b>Quantum hardware</b><small>This app runs local simulation only.</small></div></div>
          <div className="bottom-grid"><div className="notice-card"><div className="notice-icon"><CircleHelp size={18}/></div><div><b>What this prototype demonstrates</b><p>Detector-only estimation can configure a conventional decoder in a controlled simulator. The published Stage 4 result is promising development evidence for one synthetic noise family; it is not independent confirmation.</p></div></div><div className="quick-card"><span className="eyebrow">QUICK START</span><b>Run a paired simulation</b><p>Choose a burst rate, then compare fixed, estimated, and privileged reference decoders.</p><button className="button button-green" onClick={() => { setTab('simulator'); }}>Configure simulation <ArrowRight size={14}/></button></div></div>
        </>}
        {tab === 'simulator' && <>
          <div className="page-title"><div><span className="eyebrow">INTERACTIVE EXPERIMENT</span><h1>Live simulator</h1><p>Generate a fresh Stim sample and compare decoders on the exact same shots.</p></div><span className="live-badge"><i/> LIVE, LOCAL COMPUTATION</span></div>
          <div className="sim-layout"><section className="panel form-panel"><div className="panel-head"><div className="panel-icon"><FlaskConical size={17}/></div><div><b>Noise & run settings</b><small>Distance 3 rotated Z-memory · 5 rounds</small></div></div>
            <label className="field-label">Synthetic burst probability <strong>{burst.toFixed(3)}</strong></label><input aria-label="Burst probability" className="range" type="range" min="0" max="0.02" step="0.001" value={burst} onChange={e => setBurst(Number(e.target.value))}/><div className="range-labels"><span>0.000 · nominal</span><span>0.020</span></div>
            <label className="field-label" htmlFor="shots">Evaluation shots</label><select id="shots" value={shots} onChange={e => setShots(Number(e.target.value))}>{[500,1000,2000,5000,10000].map(n=><option key={n} value={n}>{n.toLocaleString()} shots</option>)}</select>
            <label className="field-label" htmlFor="calshots">Calibration shots <span className="field-hint">detector-only</span></label><select id="calshots" value={calibration} onChange={e => setCalibration(Number(e.target.value))}>{[500,1000,2000,5000].map(n=><option key={n} value={n}>{n.toLocaleString()} shots</option>)}</select>
            <label className="field-label" htmlFor="seed">Reproducibility seed</label><input id="seed" type="number" min="0" max="100000" value={seed} onChange={e => setSeed(Math.min(100000, Math.max(0, Number(e.target.value))))}/>
            <div className="info-strip"><ShieldCheck size={16}/><span>Estimation uses calibration detectors only. Test labels are used after predictions for scoring.</span></div>
            <button className="button button-dark run-button" onClick={runSimulation} disabled={busy || health !== 'online'}>{busy ? <><span className="spinner"/> Running Stim + PyMatching…</> : <><Play size={15} fill="currentColor"/> Run paired simulation</>}</button>
            {error&&<div className="error-box" role="alert">{error}</div>}
          </section>
          <section className="panel results-panel"><div className="panel-head"><div className="panel-icon mint"><BarChart3 size={17}/></div><div><b>Decoder comparison</b><small>{live ? `${live.evaluation_shots.toLocaleString()} paired evaluation samples` : 'Waiting for a live simulation'}</small></div>{live&&<span className="run-pill">LIVE RESULT</span>}</div>
            {live ? <><div className="estimate-banner"><span>Detector-only estimate</span><strong>{live.estimated_burst_probability.toFixed(5)}</strong><small>selected burst p {live.generating_burst_probability.toFixed(3)} · error {live.estimation_error >= 0 ? '+' : ''}{live.estimation_error.toFixed(5)}</small></div><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={graphData} margin={{top:10,right:12,left:0,bottom:0}}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5eae5"/><XAxis dataKey="name" tick={{fontSize:11,fill:'#60716a'}} axisLine={false} tickLine={false}/><YAxis tick={{fontSize:10,fill:'#60716a'}} axisLine={false} tickLine={false} tickFormatter={v=>`${v.toFixed(1)}%`}/><Tooltip formatter={(v:any)=>`${Number(v).toFixed(3)}% LER`}/><Bar dataKey="LER" radius={[5,5,0,0]} fill="#194f40"/></BarChart></ResponsiveContainer></div><div className="method-table"><div className="method-row table-head"><span>DECODER</span><span>ERRORS</span><span>LER · 95% Wilson</span></div><div className="method-row"><span>No correction (raw observable)</span><b>{live.no_decoding_reference.errors}/{live.no_decoding_reference.shots}</b><span>{formatPercent(live.no_decoding_reference.ler)} <small>identity reference</small></span></div>{live.methods.map((m,i)=><div className="method-row" key={m.id}><span><i className={`legend-dot legend-${i}`}/>{m.label}{m.id==='privileged_reference'&&<em className="priv-tag">REFERENCE</em>}</span><b>{m.errors}/{m.shots}</b><span>{formatPercent(m.ler)} <small>({formatPercent(m.wilson_95[0])}–{formatPercent(m.wilson_95[1])})</small></span></div>)}</div><div className="paired-note"><CheckCircle2 size={15}/><span>Estimated vs fixed: {live.methods[1].candidate_only_vs_fixed} new failures · {live.methods[1].fixed_only_vs_candidate} corrected fixed failures · exact paired McNemar p={live.methods[1].mcnemar_exact_p_vs_fixed.toPrecision(3)}</span></div><div className="runtime-note">Completed in {live.runtime_seconds}s · {live.calibration_shots.toLocaleString()} calibration + {live.profile_shots_per_probability.toLocaleString()} profile shots × 3 + {live.evaluation_shots.toLocaleString()} paired test shots. Seeds: {Object.values(live.derived_seeds).join(", ") }</div></> : <div className="empty-state"><div className="empty-art"><Activity size={34}/></div><b>Your live results will appear here</b><p>Choose settings and start a simulation. The chart will report computed error rates, not a replay.</p><span className="empty-safe"><CheckCircle2 size={14}/> Independent test is not used</span></div>}
          </section></div>
          {live&&<div className="science-note"><b>Interpretation boundary</b><span>{live.limitations.join(' ')}</span></div>}
        </>}
        {tab === 'dataset' && <>
          <div className="page-title"><div><span className="eyebrow">SAMPLE-LEVEL VIEW</span><h1>Syndrome explorer</h1><p>Inspect real detector rows generated by your most recent live simulation.</p></div><span className="chip">No sealed data bundled</span></div>
          <section className="panel dataset-panel"><div className="panel-head"><div className="panel-icon"><Database size={17}/></div><div><b>Detector sample records</b><small>{live ? `Live run · seed block ${live.seed_block_id} · ${live.evaluation_shots.toLocaleString()} total shots` : 'Run a live simulation to create sample records'}</small></div></div>
            {!live ? <div className="empty-state compact"><div className="empty-art"><Database size={28}/></div><b>No live sample in this session</b><p>Historical Stage 4B raw bundles are intentionally not copied into the web worktree. Run the simulator to generate inspectable examples.</p><button className="button button-green" onClick={()=>setTab('simulator')}>Open simulator</button></div> : <><div className="data-callout"><span className="callout-chip">LIVE GENERATED</span><span>40 detector bits · observable flip · decoder predictions · paired row alignment verified</span></div><div className="records">{live.records.map(r=><article className="record-card" key={r.index}><div className="record-head"><b>Shot {String(r.index+1).padStart(2,'0')}</b><span>observable <strong>{r.observable}</strong></span><span className={r.fixed_residual_error?'error-state':'success-state'}>{r.fixed_residual_error?'Fixed failed':'Fixed corrected'}</span></div><div className="rounds">{r.detector_slices.map((slice,i)=><div className="round-row" key={slice.time}><small>{slice.time===0?'T0':`R${i}`}</small><div>{slice.bits.split('').map((bit,j)=><i key={j} className={bit==='1'?'active':''} title={`time ${slice.time}, detector ${slice.detector_ids[j]}: ${bit}`}/>)}</div><code>{slice.detector_ids.join(',')}</code></div>)}</div><div className="record-preds"><span>Fixed <b>{r.fixed_prediction}</b></span><span>Estimated <b>{r.estimated_prediction}</b></span><span>Privileged ref. <b>{r.privileged_prediction}</b></span></div></article>)}</div><p className="dataset-foot"><CircleHelp size={15}/> Detector slices use Stim's detector coordinates: T0 is the initial boundary; R1–R5 are the five measurement rounds. Full detector-ID order remains in the 40-bit string.</p></>}
          </section>
        </>}
        {tab === 'evidence' && <>
          <div className="page-title"><div><span className="eyebrow">SAVED, AUDITED RESULTS</span><h1>Research evidence</h1><p>Historical Stage 4 development data — replayed from committed summaries, not re-simulated.</p></div><span className="replay-badge"><BookOpen size={14}/> SAVED REPLAY</span></div>
          {!history ? <div className="panel"><p>Committed Stage 4B summary is unavailable in this worktree.</p></div> : <>
            <div className="evidence-banner"><ShieldCheck size={19}/><div><b>Independent saved-data audit: {history.audit} · Frozen development gate: {history.gate_status}</b><p>{history.claim_boundary} The sealed independent test was not accessed.</p>{(!history.summary_hash_matches_audit||!history.coverage_matches_audit)&&<p className="integrity-warning">The committed summary bytes do not fully match the audit snapshot metadata. Counts remain labeled as the current saved summary; consult the audit files for provenance.</p>}</div></div>
            <div className="stats-row evidence-stats"><StatCard label="UNIQUE SIMULATED SHOTS" value={Number(history.aggregate.total_unique_shots).toLocaleString()} note="Profile + calibration + evaluation"/><StatCard label="PAIRED EVALUATION" value={Number(history.aggregate.paired_evaluation_shots).toLocaleString()} note="Same held-out shots per decoder"/><StatCard label="ROOT-CLUSTER 95% CI" value={primaryCI ? `${(primaryCI[0]*100).toFixed(3)} to ${(primaryCI[1]*100).toFixed(3)} pp` : "Unavailable"} note="Equal-weight nonzero condition effect" accent/><StatCard label="NO HARDWARE TEST" value="SIMULATION" note="Stim circuit · PyMatching decoding"/></div>
            <section className="panel evidence-panel"><div className="panel-head"><div className="panel-icon mint"><BarChart3 size={17}/></div><div><b>Results by burst probability</b><small>Stage 4 development · 7 roots per condition</small></div></div><div className="table-wrap"><table><thead><tr><th>Burst p</th><th>Shots</th><th>Fixed</th><th>Detector-est.</th><th>True-p ref.</th><th>Est. − fixed</th><th>Root CI</th></tr></thead><tbody>{history.per_condition.map(row=><tr key={row.probability}><td>{Number(row.probability).toFixed(3)}</td><td>{Number(row.shots).toLocaleString()}</td><td>{Number(row.fixed_nominal_errors)} · {formatPercent(Number(row.fixed_nominal_ler))}</td><td>{Number(row.detector_estimated_errors)} · {formatPercent(Number(row.detector_estimated_ler))}</td><td>{Number(row.privileged_true_probability_errors)} · {formatPercent(Number(row.privileged_true_probability_ler))}</td><td className={Number(row.estimated_minus_fixed)<=0?'good-delta':'bad-delta'}>{Number(row.estimated_minus_fixed)>=0?'+':''}{(Number(row.estimated_minus_fixed)*100).toFixed(3)} pp</td><td>{Array.isArray(row.estimated_minus_fixed_bootstrap_95ci)?`${(Number(row.estimated_minus_fixed_bootstrap_95ci[0])*100).toFixed(3)} to ${(Number(row.estimated_minus_fixed_bootstrap_95ci[1])*100).toFixed(3)} pp`: '—'}</td></tr>)}</tbody></table></div><div className="evidence-limit"><CircleHelp size={16}/><span>Stage 4B used one distance-3 Z-memory circuit family and a synthetic spatial burst on qubits 8 and 10. Its development gate passed, but the result is not independent confirmation, hardware validation, or evidence of general decoder superiority.</span></div></section>
          </>}
        </>}
        <footer className="footer"><span>Q-SHIFT · LOCAL SIMULATION LAB</span><span>Research prototype · no quantum hardware connection</span><span>v1.0</span></footer>
      </div>
    </main>
  </div>
}

export default App
