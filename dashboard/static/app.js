(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const state = { runId: null, run: null, metrics: [], socket: null, retry: 0, retryTimer: null,
                  pollTimer: null, generation: 0, telemetry: null, awaitingConfirmation: null };
  const pretty = (n) => new Intl.NumberFormat('en-US').format(Number(n || 0));
  const pct = (x, digits = 3) => Number.isFinite(Number(x)) ? `${(Number(x) * 100).toFixed(digits)}%` : '—';
  const seconds = (v) => {
    if (v == null || !Number.isFinite(Number(v))) return '—';
    const s = Math.max(0, Math.round(Number(v)));
    if (s < 60) return `${s}s`;
    if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`;
    return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
  };
  const mib = (v) => Number.isFinite(Number(v)) ? `${(Number(v) / (1024 ** 2)).toFixed(0)} MB` : '—';

  function toast(message, kind = '') {
    const el = document.createElement('div');
    el.className = `toast ${kind}`;
    el.textContent = message;
    $('toast-stack').appendChild(el);
    setTimeout(() => el.remove(), 5200);
  }

  async function api(path, options = {}) {
    const response = await fetch(path, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail || body);
      const error = new Error(detail || `Request failed (${response.status})`);
      error.status = response.status;
      throw error;
    }
    return body;
  }

  function displayRunStatus(status) {
    const label = status === 'stopped' ? 'CANCELLED / STOPPED' : (status || 'idle').toUpperCase();
    const el = $('run-status');
    el.className = `run-status ${status || 'idle'}`;
    el.innerHTML = `<span class="status-led"></span> ${label}`;
    $('start-btn').disabled = ['running', 'queued', 'pausing'].includes(status);
    $('pause-btn').disabled = status !== 'running';
    $('stop-btn').disabled = !['running', 'pausing'].includes(status);
    $('checkpoint-btn').disabled = status !== 'running';
    const canResume = ['paused', 'stopped', 'interrupted'].includes(status) &&
      (state.run?.state?.summary?.checkpoint || state.run?.config?.worker_kind === 'structured_3d_cnn');
    $('resume-btn').hidden = !canResume;
  }

  function setConnection(kind, label) {
    const e = $('connection-state');
    e.className = `connection-pill ${kind || ''}`;
    e.innerHTML = `<span class="status-led"></span><span>${label}</span>`;
  }

  function renderTelemetry(t, runProgress = null) {
    if (!t) return;
    state.telemetry = t;
    const gpuActive = window.QShiftProgress.canShowGpuTelemetry(runProgress, state.run?.status);
    const gpu = gpuActive ? (runProgress?.gpu_telemetry?.gpu || t.gpu || {}) : {};
    const sys = t.system || {};
    $('gpu-name').textContent = gpuActive ? (gpu.name || 'CUDA training active') : (t.gpu?.available ? 'GPU detected · not used by this run' : 'GPU use not verified');
    $('gpu-source').textContent = gpuActive ? `${gpu.source || 'NVML'} · verified current run` : 'GPU readings are hidden unless this run records CUDA training';
    $('gpu-util').textContent = gpu.available && gpu.utilization_percent != null ? `${Math.round(gpu.utilization_percent)}%` : '—';
    $('gpu-util-bar').style.width = `${Math.max(0, Math.min(100, Number(gpu.utilization_percent || 0)))}%`;
    $('gpu-memory').textContent = gpu.available && gpu.memory_percent != null ? `${Number(gpu.memory_percent).toFixed(0)}%` : '—';
    $('gpu-memory-bar').style.width = `${Math.max(0, Math.min(100, Number(gpu.memory_percent || 0)))}%`;
    $('gpu-memory-detail').textContent = gpu.available && gpu.memory_used_bytes != null && gpu.memory_total_bytes != null
      ? `${mib(gpu.memory_used_bytes)} / ${mib(gpu.memory_total_bytes)} VRAM`
      : (gpu.unavailable_reason || 'VRAM telemetry unavailable; unsupported fields are left blank.');
    $('gpu-temp').textContent = gpu.available && gpu.temperature_c != null ? `${Math.round(gpu.temperature_c)}°C` : '—';
    $('gpu-power').textContent = gpu.available && gpu.power_watts != null ? `${Number(gpu.power_watts).toFixed(0)} W` : '—';
    $('cpu-util').textContent = sys.cpu_percent != null ? `${Number(sys.cpu_percent).toFixed(0)}%` : '—';
    $('ram-used').textContent = sys.ram_used_bytes != null ? `${mib(sys.ram_used_bytes)} / ${mib(sys.ram_total_bytes)}` : '—';
    const chip = $('cuda-chip');
    if (gpuActive) {
      chip.textContent = 'CUDA ACTIVE'; chip.className = 'gpu-chip good';
      $('device-label').textContent = `CUDA training · ${runProgress.cuda_device_name || t.cuda_device_name || 'GPU'}`;
    } else if (t.cuda_available) {
      chip.textContent = 'CUDA AVAILABLE'; chip.className = 'gpu-chip warn';
      $('device-label').textContent = runProgress?.device === 'cpu'
        ? 'CPU run · CUDA available but not used'
        : 'CUDA is available; this run has not verified GPU training';
    } else {
      chip.textContent = 'CUDA UNAVAILABLE'; chip.className = 'gpu-chip warn';
      $('device-label').textContent = 'CPU fallback · ' + (t.cuda_unavailable_reason || 'CUDA unavailable');
    }
  }

  function updateProgress(e) {
    if (!e) return;
    const p = window.QShiftProgress.normalizeProgress(e, state.run?.config || {});
    const done = p.completedShots;
    const total = p.totalShots;
    const percent = p.percent;
    $('progress-percent').innerHTML = percent == null ? '—' : `${percent.toFixed(0)}<span>%</span>`;
    $('progress-fill').style.width = `${percent == null ? 0 : percent}%`;
    $('processed-shots').textContent = pretty(done);
    $('target-shots').textContent = total == null ? '—' : pretty(total);
    $('generated-shots').textContent = e.generated_shots == null ? pretty(done) : pretty(e.generated_shots);
    $('trained-shots').textContent = pretty(p.processedShots);
    $('throughput').textContent = p.throughput == null ? '—' : pretty(Math.round(p.throughput));
    $('eta').textContent = seconds(p.etaSeconds);
    $('elapsed').textContent = `elapsed ${seconds(e.elapsed_seconds)}`;
    $('step-caption').textContent = `step ${pretty(e.step || 0)} / ${pretty(e.steps_total || 0)}`;
    $('phase-caption').textContent = p.phase.replaceAll('_', ' ');
    $('phase-shot-count').textContent = p.phaseCompleted == null ? 'stage count not reported' :
      `${pretty(p.phaseCompleted)} / ${p.phaseTotal == null ? '—' : pretty(p.phaseTotal)} shots`;
    $('val-count').textContent = e.generated_validation_shots == null ? '—' : pretty(e.generated_validation_shots);
    $('test-count').textContent = e.generated_test_shots == null ? '—' : pretty(e.generated_test_shots);
    $('sample-passes').textContent = e.training_sample_passes == null ? '—' : pretty(e.training_sample_passes);
    const stages = p.stages || {};
    for (const stage of ['simulation', 'calibration', 'decoding', 'analysis']) {
      const value = stages[stage];
      $( `stage-${stage}` ).textContent = value == null ? 'Not reported' :
        (typeof value === 'object' ? `${pretty(value.completed ?? value.shots ?? 0)} / ${value.total == null ? '—' : pretty(value.total)}` : pretty(value));
    }
    if (e.device) {
      const verified = e.cuda_training_verified === true;
      $('device-label').textContent = verified
        ? `CUDA training · ${e.cuda_device_name || 'GPU'}${e.mixed_precision ? ' · AMP' : ''}`
        : `${String(e.device).toUpperCase()}${e.mixed_precision ? ' · AMP' : ''}`;
    }
    if (e.gpu_telemetry) renderTelemetry(e.gpu_telemetry, e);
    if (e.candidate) $('architecture-label').textContent = `Training · ${e.candidate}`;
    else if (e.model_selection) $('architecture-label').textContent = e.model_selection === 'direct_mlp' ? 'Direct detector-to-logical MLP' : e.model_selection === 'structured_3d_cnn' ? 'Geometry-aware structured 3D CNN' : 'Direct MLP + residual MLP';
    $('progress-panel').classList.toggle('running', e.status === 'running');
    $('last-update').textContent = `UPDATED ${new Date().toLocaleTimeString()}`;
    const error = $('progress-error');
    error.hidden = !p.error;
    error.textContent = p.error ? `Worker error: ${p.error}` : '';
    if (e.validation_ler != null) $('test-state').textContent = 'VALIDATION LIVE';
    renderCharts();
  }

  function setExperimentMetadata(run, historical = false) {
    if (!run) return;
    state.run = run;
    state.runId = run.id;
    $('run-id').textContent = run.id.toUpperCase();
    $('console-run-label').textContent = historical ? 'HISTORICAL SQLITE RECORD · NOT THE AUTONOMOUS RUN' : 'ACTIVE DASHBOARD WORKER';
    const consoleName = run.config.worker_kind === 'structured_3d_cnn' ? 'Q-SHIFT · multi-regime structured training' : `Q-SHIFT · ${run.config.noise_regime || 'run'} training`;
    $('experiment-name').textContent = historical ? `Historical · ${consoleName}` : consoleName;
    $('architecture-label').textContent = run.config.worker_kind === 'structured_3d_cnn' ? 'Geometry-aware structured 3D CNN · multi-regime' : run.config.model_selection === 'direct_mlp' ? 'Direct detector-to-logical MLP' : 'Direct MLP + residual MLP';
    $('code-label').textContent = `Rotated surface · d=${run.config.distance} · ${run.config.rounds} rounds · ${String(run.config.memory_basis).toUpperCase()} memory`;
    $('noise-label').textContent = run.config.worker_kind === 'structured_3d_cnn' ? 'X-biased · balanced · Z-biased regimes · test reserved' : `Categorical Pauli · ${run.config.noise_regime} · gate ${run.config.gate_p} / meas ${run.config.measurement_p}`;
    $('seed-label').textContent = pretty(run.config.seed);
    $('target-shots').textContent = pretty(run.config.training_shots);
    if (run.execution?.label) $('device-label').textContent = run.execution.label;
    displayRunStatus(run.status);
    const progress = run.state?.progress;
    if (progress) updateProgress(progress);
    if (run.state?.summary?.metrics) renderComparison(run.state.summary.metrics);
  }

  function setAutonomousStatus(status) {
    const label = $('autonomous-status');
    label.className = `run-status ${status || 'unknown'}`;
    const led = document.createElement('span'); led.className = 'status-led';
    label.replaceChildren(led, document.createTextNode(` ${String(status || 'unknown').toUpperCase()}`));
  }

  function formatAutonomousRuntime(value) {
    if (value == null || !Number.isFinite(Number(value))) return '—';
    return seconds(value);
  }

  function displayCount(value) {
    return value != null && Number.isFinite(Number(value)) ? pretty(value) : '—';
  }

  function displayPercent(value) {
    return value != null && Number.isFinite(Number(value)) ? pct(value, 3) : '—';
  }

  function drawAutonomousHistory(result) {
    const points = result?.history || [];
    const canvas = $('autonomous-learning-chart');
    $('autonomous-learning-empty').style.display = points.length ? 'none' : 'grid';
    if (!points.length) {
      drawChart(canvas, []);
      return;
    }
    const values = points.map(point => Number(point.monitor_nll));
    const max = Math.max(...values, 0.001);
    drawChart(canvas, [{ values, color: '#a28aff', min: 0, max: max * 1.08 }],
      { labels: ['higher NLL', '', '', 'lower NLL'] });
  }

  function renderAutonomousResults(results) {
    const body = $('autonomous-results-body');
    const select = $('autonomous-job-select');
    body.replaceChildren();
    select.replaceChildren();
    if (!Array.isArray(results) || !results.length) {
      const row = document.createElement('tr');
      const cell = document.createElement('td'); cell.colSpan = 8;
      cell.textContent = 'No completed result with a matching prediction-file hash is available yet.';
      row.appendChild(cell); body.appendChild(row);
      select.disabled = true;
      const option = document.createElement('option'); option.textContent = 'No verified completed jobs'; select.appendChild(option);
      drawAutonomousHistory(null);
      $('autonomous-results-state').textContent = 'NO VERIFIED RESULTS';
      return;
    }
    const ordered = [...results].sort((a, b) => (a.root_id - b.root_id) || a.model.localeCompare(b.model)
      || a.train_size_per_regime - b.train_size_per_regime);
    for (const result of ordered) {
      const option = document.createElement('option');
      option.value = result.job_id;
      option.textContent = `root ${String(result.root_id).padStart(2, '0')} · ${result.model_label} · ${pretty(result.train_size_per_regime)} train/regime`;
      select.appendChild(option);
      const regimes = Object.entries(result.per_regime || {});
      for (const [regime, metrics] of regimes) {
        const row = document.createElement('tr');
        const values = [
          result.model_label, `root ${String(result.root_id).padStart(2, '0')}`,
          pretty(result.train_size_per_regime), regime,
          displayCount(metrics.shots), displayPercent(metrics.ler), displayPercent(metrics.pymatching_ler),
          metrics.ler != null && metrics.pymatching_ler != null
            && Number.isFinite(Number(metrics.ler)) && Number.isFinite(Number(metrics.pymatching_ler))
            ? `${Number(metrics.ler - metrics.pymatching_ler) >= 0 ? '+' : ''}${(100 * (metrics.ler - metrics.pymatching_ler)).toFixed(3)} pp`
            : '—',
        ];
        for (const value of values) {
          const cell = document.createElement('td'); cell.textContent = String(value); row.appendChild(cell);
        }
        body.appendChild(row);
      }
    }
    select.disabled = false;
    select.value = ordered[ordered.length - 1].job_id;
    const selected = () => ordered.find(result => result.job_id === select.value);
    select.onchange = () => drawAutonomousHistory(selected());
    drawAutonomousHistory(selected());
    $('autonomous-results-state').textContent = `${ordered.length} HASH-VERIFIED JOBS`;
  }

  function renderAutonomous(snapshot) {
    setAutonomousStatus(snapshot.status);
    $('autonomous-jobs').textContent = `${pretty(snapshot.completed_jobs)} / ${pretty(snapshot.total_jobs)}`;
    $('autonomous-verified').textContent = `Verified result files: ${pretty(snapshot.verified_jobs)}`;
    const root = snapshot.current_root;
    const jobLabel = snapshot.current_job || 'No persisted job record';
    $('autonomous-root').textContent = root == null ? '—' : `${snapshot.status === 'completed' ? 'Last root' : 'Root'} ${String(root).padStart(2, '0')}`;
    $('autonomous-job').textContent = snapshot.last_progress_step == null ? jobLabel : `${jobLabel} · step ${pretty(snapshot.last_progress_step)}`;
    $('autonomous-runtime').textContent = formatAutonomousRuntime(snapshot.active_runtime_seconds);
    $('autonomous-gpu-time').textContent = formatAutonomousRuntime(snapshot.gpu_training_seconds);
    const counts = snapshot.shot_counts;
    $('autonomous-shot-counts').textContent = counts
      ? `Persisted, hash-verified generated shots across ${counts.verified_roots} roots · train ${pretty(counts.train)} · monitor ${pretty(counts.monitor)} · calibration ${pretty(counts.calibration)} · threshold selection ${pretty(counts.threshold_selection)} · final development evaluation ${pretty(counts.final_development_evaluation)}. Counts come from committed sample manifests, not job totals.`
      : 'Generated-shot counts are omitted until sample manifests and paired arrays are hash-verified.';
    $('autonomous-test-status').textContent = `Independent-test status: ${snapshot.independent_test_status || 'not recorded'}`;
    renderAutonomousResults(snapshot.results || []);
    const warnings = snapshot.warnings || [];
    const warningBox = $('autonomous-warnings');
    warningBox.hidden = !warnings.length;
    warningBox.textContent = warnings.join(' ');
  }

  let autonomousPollInFlight = false;
  async function loadAutonomousRun() {
    if (autonomousPollInFlight) return;
    autonomousPollInFlight = true;
    try {
      renderAutonomous(await api('/api/autonomous-research'));
    } catch (_) {
      $('autonomous-test-status').textContent = 'Autonomous persisted status is temporarily unavailable; the training console remains separate.';
    } finally { autonomousPollInFlight = false; }
  }

  function renderComparison(metrics) {
    if (!metrics) return;
    const order = [
      ['identity_no_decode', 'No decode / identity', 'gray'],
      ['pymatching', 'Frozen PyMatching', 'cyan'],
      ['direct_neural', 'Direct neural MLP', 'purple'],
      ['pymatching_neural_residual', 'PyMatching + neural residual', 'blue'],
      ['structured_neural', 'Structured 3D CNN', 'purple'],
    ];
    const body = $('comparison-body');
    body.innerHTML = '';
    for (const [key, label, color] of order) {
      const v = metrics[key];
      if (!v) continue;
      const tr = document.createElement('tr');
      const ci = v.wilson95 ? `${pct(v.wilson95[0], 2)} – ${pct(v.wilson95[1], 2)}` : '—';
      tr.innerHTML = `<td class="decoder-name"><span class="decoder-dot ${color}"></span>${label}</td><td>${pretty(v.errors)}</td><td>${pct(v.ler, 3)}</td><td>${ci}</td>`;
      body.appendChild(tr);
    }
    const structured = document.createElement('tr');
    structured.className = 'unavailable-row';
    structured.innerHTML = '<td class="decoder-name"><span class="decoder-dot muted"></span>Structured neural</td><td colspan="3">Not implemented · no results reported</td>';
    body.appendChild(structured);
    const direct = metrics.direct_neural?.paired_vs_pymatching;
    const residual = metrics.pymatching_neural_residual?.paired_vs_pymatching;
    const bits = [];
    for (const [name, x] of [['Direct', direct], ['Residual', residual]]) {
      if (x) bits.push(`<b>${name}</b>: ${pretty(x.candidate_only_failures)} neural-only failures / ${pretty(x.pymatching_only_failures)} matching-only failures · ${pretty(x.prediction_disagreements)} disagreements · paired p=${Number(x.exact_mcnemar_two_sided_p_descriptive).toExponential(2)}`);
    }
    $('paired-summary').innerHTML = `<span class="paired-mark">↔</span><span>${bits.length ? bits.join('<br>') : 'Paired fixes, introduced failures and confidence intervals will be calculated from the same held-out detector shots.'}</span>`;
    $('test-state').textContent = 'TEST COMPLETE';
  }

  function drawChart(canvas, series, options = {}) {
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(rect.width * dpr);
    canvas.height = Math.floor(rect.height * dpr);
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    const w = rect.width, h = rect.height;
    const pad = { l: 34, r: 12, t: 12, b: 22 };
    const cw = w - pad.l - pad.r, ch = h - pad.t - pad.b;
    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = 'rgba(119,137,169,.14)'; ctx.lineWidth = 1;
    ctx.fillStyle = '#61708b'; ctx.font = '8px "DM Mono", monospace';
    for (let i = 0; i <= 3; i++) {
      const y = pad.t + ch * i / 3;
      ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
      if (options.labels) ctx.fillText(options.labels[i] || '', 0, y + 3);
    }
    const nonempty = series.filter(s => s.values?.some(v => Number.isFinite(v)));
    if (!nonempty.length) return;
    const maxLen = Math.max(...nonempty.map(s => s.values.length));
    for (const s of nonempty) {
      const vals = s.values.filter(v => Number.isFinite(v));
      if (!vals.length) continue;
      const min = s.min != null ? s.min : Math.min(...vals);
      let max = s.max != null ? s.max : Math.max(...vals);
      if (max <= min) max = min + 1e-6;
      ctx.strokeStyle = s.color; ctx.lineWidth = s.width || 1.7; ctx.setLineDash(s.dash ? [4, 4] : []);
      ctx.beginPath(); let begun = false;
      s.values.forEach((v, i) => {
        if (!Number.isFinite(v)) return;
        const x = pad.l + (maxLen <= 1 ? 0 : i * cw / (maxLen - 1));
        const y = pad.t + ch - ((v - min) / (max - min)) * ch;
        if (!begun) { ctx.moveTo(x, y); begun = true; } else ctx.lineTo(x, y);
      });
      if (begun) ctx.stroke();
      ctx.setLineDash([]);
    }
  }

  function renderCharts() {
    const progress = state.metrics.filter(x => x.type === 'progress');
    const numericOrGap = (value) => value == null || !Number.isFinite(Number(value)) ? null : Number(value);
    const losses = progress.map(x => numericOrGap(x.train_loss));
    const validation = progress.map(x => numericOrGap(x.validation_ler));
    const base = progress.map(x => numericOrGap(x.pymatching_validation_ler));
    const hasLearningData = losses.some(v => v != null) || validation.some(v => v != null);
    $('learning-empty').style.display = hasLearningData ? 'none' : 'grid';
    drawChart($('learning-chart'), [
      { values: losses, color: '#a28aff', min: 0, max: Math.max(.75, ...losses, 0.75) },
      { values: validation, color: '#65e6e2', min: 0, max: .04 },
      { values: base, color: '#7c8ba5', min: 0, max: .04, dash: true, width: 1.1 },
    ], { labels: ['high', '', '', 'low'] });
    const throughput = progress.map(x => Number.isFinite(Number(x.throughput_shots_s)) ? Number(x.throughput_shots_s) : null);
    const gpuMemory = progress.map(x => numericOrGap(x.gpu_telemetry?.gpu?.memory_percent));
    $('throughput-empty').style.display = throughput.some(v => v != null) || gpuMemory.some(v => v != null) ? 'none' : 'grid';
    const maxThrough = Math.max(100, ...throughput.filter(Number.isFinite), 100);
    drawChart($('throughput-chart'), [
      { values: throughput, color: '#7395ff', min: 0, max: maxThrough },
      { values: gpuMemory, color: '#ad8bf0', min: 0, max: 100, dash: true },
    ], { labels: ['high', '', '', 'low'] });
  }

  function addEvent(event) {
    if (!event) return;
    if (event.type === 'progress') {
      if (state.run) state.run.status = event.status || 'running';
      state.metrics.push({ type: 'progress', ...event });
      if (state.metrics.length > 2000) state.metrics.splice(0, state.metrics.length - 2000);
      updateProgress(event);
      displayRunStatus(event.status || 'running');
    } else if (event.type === 'snapshot') {
      setExperimentMetadata(event.run);
      state.metrics = (event.metrics || []).map(m => ({ type: m.type, ...(m.payload || {}) })).filter(m => m.type === 'progress');
      if (event.run?.state?.summary?.metrics) renderComparison(event.run.state.summary.metrics);
      renderCharts();
    } else if (['completed', 'failed', 'paused', 'stopped', 'cancelled', 'interrupted'].includes(event.type)) {
      state.run = state.run || {};
      state.run.status = event.status || event.type;
      if (event.summary) state.run.state = { ...(state.run.state || {}), summary: event.summary };
      displayRunStatus(event.status || event.type);
      if (event.error) { $('progress-error').hidden = false; $('progress-error').textContent = `Worker ${event.type}: ${event.error}`; }
      if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
      if (event.metrics || event.summary?.metrics) renderComparison(event.metrics || event.summary.metrics);
      if (event.type === 'completed' && state.run?.config?.worker_kind === 'structured_3d_cnn') {
        $('test-state').textContent = 'DEVELOPMENT VALIDATION';
        $('paired-summary').lastElementChild.textContent = 'Paired validation comparison only. The reserved final test stream was not generated or opened; these metrics selected the development model.';
      }
      if (event.type === 'completed') toast(state.run?.config?.worker_kind === 'structured_3d_cnn' ? 'Structured training completed. Validation evidence is saved; the reserved test stream was not opened.' : 'Run completed. Test metrics are paired on saved detector shots.', 'success');
      if (event.type === 'failed') toast(event.error || 'Training failed. See the run record for details.', 'error');
      if (event.type === 'paused' || event.type === 'stopped') $('resume-hint').textContent = 'Safe checkpoint saved; the same run can resume.';
    }
  }

  function connect(runId) {
    if (!runId) return;
    if (state.socket) { try { state.socket.close(); } catch (_) {} }
    const generation = ++state.generation;
    const scheme = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${scheme}//${location.host}/ws/${encodeURIComponent(runId)}`);
    state.socket = ws;
    setConnection('', 'Connecting');
    ws.onopen = () => { if (generation !== state.generation) return; state.retry = 0; setConnection('', 'Live stream connected'); };
    ws.onmessage = (message) => {
      if (generation !== state.generation) return;
      try { const event = JSON.parse(message.data); if (event.type !== 'heartbeat') addEvent(event); }
      catch (_) { /* Ignore malformed telemetry frame; reconnect remains available. */ }
    };
    ws.onerror = () => { setConnection('offline', 'Stream error'); };
    ws.onclose = () => {
      if (generation !== state.generation) return;
      if (state.run && ['completed', 'failed', 'paused', 'stopped', 'cancelled', 'interrupted'].includes(state.run.status)) {
        setConnection('', 'Saved locally'); return;
      }
      state.retry += 1;
      const wait = Math.min(30000, 500 * (2 ** Math.min(state.retry, 6)));
      setConnection('reconnecting', `Reconnecting · ${Math.ceil(wait / 1000)}s`);
      clearTimeout(state.retryTimer);
      state.retryTimer = setTimeout(() => connect(runId), wait);
    };
  }

  function startProgressPolling(runId) {
    if (state.pollTimer) clearInterval(state.pollTimer);
    let lastProgressKey = null;
    let busy = false;
    const poll = async () => {
      if (!runId || busy) return;
      busy = true;
      try {
        const snapshot = await api(`/api/runs/${encodeURIComponent(runId)}/progress`);
        if (state.runId !== runId) return;
        state.run = { ...(state.run || {}), id: runId, status: snapshot.status,
          updated_at: snapshot.updated_at, error: snapshot.error,
          state: { ...(state.run?.state || {}), progress: snapshot.progress, summary: snapshot.summary } };
        if (snapshot.progress) {
          const key = JSON.stringify(snapshot.progress);
          if (key !== lastProgressKey) {
            lastProgressKey = key;
            state.metrics.push({ type: 'progress', ...snapshot.progress });
            if (state.metrics.length > 2000) state.metrics.splice(0, state.metrics.length - 2000);
            updateProgress(snapshot.progress);
            renderCharts();
          }
        }
        displayRunStatus(snapshot.status);
        if (snapshot.error) { $('progress-error').hidden = false; $('progress-error').textContent = `Worker error: ${snapshot.error}`; }
        if (['completed', 'failed', 'paused', 'stopped', 'cancelled', 'interrupted'].includes(snapshot.status)) {
          if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
          setConnection('', 'Saved locally');
        }
      } catch (error) {
        setConnection('offline', `Progress API retry · ${error.message}`);
      } finally { busy = false; }
    };
    poll();
    state.pollTimer = setInterval(poll, 2500);
  }

  async function loadState() {
    try {
      const data = await api('/api/state');
      // The latest SQLite row is history, not a live worker and not the separate
      // autonomous controller. Keep showing it for continuity, but label it.
      const historical = !data.active_run;
      const run = data.active_run || data.runs?.[0];
      if (run) {
        setExperimentMetadata(run, historical);
        const detail = await api(`/api/runs/${run.id}`);
        setExperimentMetadata(detail.run, historical);
        renderTelemetry(data.telemetry, detail.run.state?.progress || detail.run.execution);
        state.metrics = (detail.metrics || []).map(m => ({ type: m.type, ...(m.payload || {}) })).filter(m => m.type === 'progress');
        if (detail.run.state?.summary?.metrics) renderComparison(detail.run.state.summary.metrics);
        renderCharts();
        if (['running', 'queued', 'pausing'].includes(detail.run.status)) {
          connect(run.id); startProgressPolling(run.id);
        } else { renderTelemetry(data.telemetry, detail.run.state?.progress || detail.run.execution); setConnection('', 'Saved locally'); }
      } else {
        $('console-run-label').textContent = 'NO DASHBOARD WORKER RUN';
        $('experiment-name').textContent = 'No active dashboard training run';
        displayRunStatus('idle');
        renderTelemetry(data.telemetry, null);
        if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
        setConnection('', 'Local service ready');
      }
    } catch (error) {
      setConnection('offline', 'Backend unavailable');
      toast(error.message, 'error');
    }
  }

  function presetBudget() {
    const preset = $('preset-select').value;
    const map = { smoke: 8000, pipeline: 100000, initial: 1000000,
                  architecture: 10000000, scaling: 100000000, extended: 1000000000 };
    return map[preset] || 8000;
  }

  function configFromForm() {
    const structured = $('model-select').value === 'structured_3dcnn';
    return {
      preset: $('preset-select').value,
      training_shots: structured ? 70000 : presetBudget(), validation_shots: structured ? 15000 : 1000, test_shots: structured ? 15000 : 1000,
      batch_size: structured ? 256 : Number($('batch-size').value), learning_rate: structured ? 0.001 : Number($('learning-rate').value),
      noise_regime: structured ? 'balanced' : $('noise-regime').value, memory_basis: structured ? 'z' : $('memory-basis').value,
      gate_p: structured ? 0.003 : Number($('gate-p').value), measurement_p: structured ? 0.003 : Number($('measurement-p').value),
      bias_ratio: 10, validation_frequency_steps: Number($('validation-freq').value),
      checkpoint_frequency_steps: Number($('checkpoint-freq').value), seed: Number($('random-seed').value),
      device: $('device-select').value, distance: 3, rounds: 5, mixed_precision: true,
      model_selection: structured ? 'direct_plus_residual' : $('model-select').value,
      ...(structured ? { worker_kind: 'structured_3d_cnn', mode: 'official_100k', max_wall_seconds_per_invocation: 28800 } : {}),
    };
  }

  function askLargeConfirmation(cfg, extreme) {
    return new Promise(resolve => {
      const dialog = $('large-confirm');
      $('confirm-title').textContent = extreme ? 'Confirm extended training run' : 'Confirm long training run';
      $('confirm-copy').textContent = cfg.worker_kind === 'structured_3d_cnn'
        ? 'This runs the frozen multi-regime structured-decoder protocol: 70,000 training shots and 15,000 validation shots. The 15,000-shot final test allocation stays unopened.'
        : extreme
        ? 'This is a 100M or 1B training run. It may take a long time and consume substantial GPU and storage resources. It will run only after this confirmation and a second explicit confirmation.'
        : 'This training budget can take a while and consume GPU resources. It will not be started automatically. Test data remain isolated until training finishes.';
      $('confirm-details').textContent = `${pretty(cfg.training_shots)} train shots · batch ${cfg.batch_size} · ${cfg.device.toUpperCase()} · ${cfg.noise_regime} noise · ${cfg.memory_basis.toUpperCase()} memory`;
      state.awaitingConfirmation = resolve;
      dialog.showModal();
    });
  }

  $('confirm-cancel').addEventListener('click', () => { $('large-confirm').close(); state.awaitingConfirmation?.(false); state.awaitingConfirmation = null; });
  $('confirm-continue').addEventListener('click', () => { $('large-confirm').close(); state.awaitingConfirmation?.(true); state.awaitingConfirmation = null; });
  $('large-confirm').addEventListener('cancel', (event) => { event.preventDefault(); $('large-confirm').close(); state.awaitingConfirmation?.(false); state.awaitingConfirmation = null; });

  $('start-btn').addEventListener('click', async () => {
    const cfg = configFromForm();
    const large = cfg.training_shots > 10000;
    const extreme = cfg.training_shots >= 100000000;
    if (large && !(await askLargeConfirmation(cfg, false))) return;
    if (extreme && !(await askLargeConfirmation(cfg, true))) return;
    $('start-btn').disabled = true;
    try {
      const data = await api('/api/runs', { method: 'POST', body: JSON.stringify({ config: cfg, confirmed_large: large, confirmed_extreme: extreme }) });
      state.runId = data.run_id;
      state.metrics = [];
      $('test-state').textContent = cfg.worker_kind === 'structured_3d_cnn' ? 'AWAITING VALIDATION' : 'AWAITING TEST';
      $('comparison-body').innerHTML = '<tr><td class="decoder-name"><span class="decoder-dot gray"></span>No decode / identity</td><td>—</td><td>—</td><td>—</td></tr><tr><td class="decoder-name"><span class="decoder-dot cyan"></span>Frozen PyMatching</td><td>—</td><td>—</td><td>—</td></tr><tr><td class="decoder-name"><span class="decoder-dot purple"></span>Direct neural MLP</td><td>—</td><td>—</td><td>—</td></tr>';
      await loadState();
      connect(data.run_id);
      toast(cfg.worker_kind === 'structured_3d_cnn' ? 'Structured multi-regime worker started. Its reserved final test stream will remain unopened.' : 'Training worker started. Samples will be generated by Stim in a separate process.', 'success');
    } catch (error) {
      toast(error.message, 'error');
      $('start-btn').disabled = false;
    }
  });

  async function control(action) {
    if (!state.runId) return;
    try {
      const data = await api(`/api/runs/${state.runId}/control`, { method: 'POST', body: JSON.stringify({ action }) });
      if (action === 'resume') {
        await loadState(); connect(state.runId); toast('Resumed from the latest atomic checkpoint.', 'success');
      } else if (action === 'pause' || action === 'stop') {
        toast(`${action === 'pause' ? 'Pause' : 'Stop'} requested; worker will finish the current mini-batch first.`);
      } else toast('Checkpoint requested; it will save at a safe batch boundary.');
    } catch (error) { toast(error.message, 'error'); }
  }
  $('pause-btn').addEventListener('click', () => control('pause'));
  $('stop-btn').addEventListener('click', () => control('stop'));
  $('checkpoint-btn').addEventListener('click', () => control('checkpoint'));
  $('resume-btn').addEventListener('click', () => control('resume'));
  $('refresh-btn').addEventListener('click', () => { loadState(); loadAutonomousRun(); });
  $('reset-config').addEventListener('click', () => {
    $('preset-select').value = 'smoke'; $('model-select').value = 'direct_plus_residual';
    $('batch-size').value = '256'; $('learning-rate').value = '0.001'; $('noise-regime').value = 'balanced';
    $('memory-basis').value = 'z'; $('gate-p').value = '0.003'; $('measurement-p').value = '0.003';
    $('validation-freq').value = '8'; $('checkpoint-freq').value = '8'; $('random-seed').value = '1800000001'; $('device-select').value = 'auto';
  });
  $('nav-runs').addEventListener('click', async () => {
    try {
      const data = await api('/api/runs');
      const names = (data.runs || []).slice(0, 6).map(r => `${r.id.slice(0, 8)} · ${r.execution?.label || 'device not recorded'} · ${r.status} · ${new Date(r.created_at * 1000).toLocaleString()}`).join('\n');
      toast(names || 'No saved runs yet. Run records and metrics persist locally in SQLite.');
    } catch (error) { toast(error.message, 'error'); }
  });
  $('nav-autonomous').addEventListener('click', () => $('autonomous-view').scrollIntoView({ behavior: 'smooth', block: 'start' }));
  $('nav-dashboard').addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

  $('preset-select').addEventListener('change', () => {
    const shots = presetBudget();
    const budget = shots === 8000 ? '1,000 / 1,000' : '1,000 / 1,000';
    $('eval-budget').innerHTML = `<span>Validation / test split</span><b>${budget} independent shots</b><small>${shots === 8000 ? 'Smoke preset total: 10,000 generated samples.' : `${pretty(shots)} training samples + 2,000 evaluation samples.`}</small>`;
  });

  window.addEventListener('resize', () => renderCharts());
  loadState();
  loadAutonomousRun();
  setInterval(loadAutonomousRun, 5000);
  setInterval(async () => {
    try { const h = await api('/api/health'); renderTelemetry(h.telemetry, state.run?.state?.progress || state.run?.execution || null); }
    catch (_) { if (!state.run) setConnection('offline', 'Backend unavailable'); }
  }, 3000);
})();
