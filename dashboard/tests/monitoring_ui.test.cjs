const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { normalizeProgress, canShowGpuTelemetry } = require('../static/progress.js');

test('progress uses persisted shot counts and clamps actual percentage', () => {
  const p = normalizeProgress({ type: 'progress', phase: 'simulation', completed_shots: 125,
    generated_shots: 180, processed_shots: 100, total_shots: 500, throughput_shots_s: 25, eta_seconds: 15,
    phase_completed_shots: 125, phase_total_shots: 200 });
  assert.equal(p.completedShots, 125);
  assert.equal(p.generatedShots, 180);
  assert.equal(p.processedShots, 100);
  assert.equal(p.percent, 25);
  assert.equal(p.throughput, 25);
  assert.equal(p.etaSeconds, 15);
  assert.equal(p.phase, 'simulation');
});

test('missing counters never borrow generated or training-processed counts', () => {
  const p = normalizeProgress({ phase: 'training', generated_shots: 40,
    generated_training_shots: 32, training_samples_processed: 16,
    total_shots: 100, total_training_shots: 80, progress_percent: 80,
    throughput_shots_s: 4, eta_seconds: 15 });
  assert.equal(p.completedShots, null);
  assert.equal(p.generatedShots, 40);
  assert.equal(p.processedShots, null);
  assert.equal(p.percent, null);
  assert.equal(p.etaSeconds, null);
});

test('missing totals keep percentage and ETA unavailable despite reported completion', () => {
  const p = normalizeProgress({ phase: 'preparing', completed_shots: 0,
    progress_percent: 90, throughput_shots_s: 10, eta_seconds: 5 }, {});
  assert.equal(p.totalShots, null);
  assert.equal(p.completedShots, 0);
  assert.equal(p.percent, null);
  assert.equal(p.etaSeconds, null);
});

test('zero-shot initial state is a measured zero while ETA stays unavailable without throughput', () => {
  const p = normalizeProgress({ status: 'running', completed_shots: 0, generated_shots: 0,
    processed_shots: 0, total_shots: 100, throughput_shots_s: 0, eta_seconds: 999 });
  assert.equal(p.completedShots, 0);
  assert.equal(p.generatedShots, 0);
  assert.equal(p.processedShots, 0);
  assert.equal(p.percent, 0);
  assert.equal(p.etaSeconds, null);
});

test('partially generated batches keep generated, completed and processed counters distinct', () => {
  const p = normalizeProgress({ status: 'running', generated_shots: 90,
    completed_shots: 40, processed_shots: 25, total_shots: 200,
    throughput_shots_s: 5 }, {});
  assert.equal(p.generatedShots, 90);
  assert.equal(p.completedShots, 40);
  assert.equal(p.processedShots, 25);
  assert.equal(p.percent, 20);
  assert.equal(p.etaSeconds, 32);
});

test('completed terminal state reports 100 percent only from explicit complete counts', () => {
  const reported = normalizeProgress({ status: 'completed', completed_shots: 200,
    generated_shots: 200, processed_shots: 200, total_shots: 200,
    throughput_shots_s: 10 });
  assert.equal(reported.status, 'completed');
  assert.equal(reported.percent, 100);
  assert.equal(reported.etaSeconds, 0);

  const unreported = normalizeProgress({ status: 'completed', generated_shots: 200,
    processed_shots: 200, total_shots: 200, throughput_shots_s: 10 });
  assert.equal(unreported.completedShots, null);
  assert.equal(unreported.percent, null);
  assert.equal(unreported.etaSeconds, null);
});

test('GPU telemetry is eligible for display only after verified CUDA training', () => {
  const cpu = normalizeProgress({ device: 'cpu', cuda_training_verified: false, gpu_telemetry: { gpu: { available: true } } });
  const gpu = normalizeProgress({ device: 'cuda', cuda_training_verified: true, gpu_telemetry: { gpu: { available: true } } });
  assert.equal(cpu.cudaTrainingVerified, false);
  assert.equal(gpu.cudaTrainingVerified, true);
  assert.equal(canShowGpuTelemetry({ device: 'cuda', cuda_training_verified: true }, 'running'), true);
  assert.equal(canShowGpuTelemetry({ device: 'cuda', cuda_training_verified: true }, 'completed'), false);
  assert.equal(canShowGpuTelemetry({ device: 'cpu', cuda_training_verified: false }, 'running'), false);
});

test('dashboard wires persisted progress polling to actual progress fields', () => {
  const root = path.resolve(__dirname, '..');
  const app = fs.readFileSync(path.join(root, 'static', 'app.js'), 'utf8');
  const html = fs.readFileSync(path.join(root, 'static', 'index.html'), 'utf8');
  assert.match(app, /\/api\/runs\/\$\{encodeURIComponent\(runId\)\}\/progress/);
  assert.match(app, /QShiftProgress\.normalizeProgress/);
  assert.match(app, /generated-shots'\)\.textContent = reportedCount\(p\.generatedShots\)/);
  assert.doesNotMatch(app, /generated_shots == null \? pretty\(done\)/);
  for (const id of ['processed-shots', 'target-shots', 'throughput', 'eta', 'phase-caption', 'progress-error']) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
  assert.match(html, /progress\.js/);
});
