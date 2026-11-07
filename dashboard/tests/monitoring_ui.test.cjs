const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { normalizeProgress, canShowGpuTelemetry } = require('../static/progress.js');

test('progress uses persisted shot counts and clamps actual percentage', () => {
  const p = normalizeProgress({ type: 'progress', phase: 'simulation', completed_shots: 125,
    processed_shots: 100, total_shots: 500, throughput_shots_s: 25, eta_seconds: 15,
    phase_completed_shots: 125, phase_total_shots: 200 });
  assert.equal(p.completedShots, 125);
  assert.equal(p.percent, 25);
  assert.equal(p.throughput, 25);
  assert.equal(p.etaSeconds, 15);
  assert.equal(p.phase, 'simulation');
});

test('unknown totals and missing measurements remain unavailable, not fabricated', () => {
  const p = normalizeProgress({ phase: 'preparing' }, {});
  assert.equal(p.totalShots, null);
  assert.equal(p.percent, null);
  assert.equal(p.throughput, null);
  assert.equal(p.etaSeconds, null);
});

test('legacy worker progress maps real processed training rows and configured total', () => {
  const p = normalizeProgress({ training_samples_processed: 256, total_training_shots: 1024,
    generated_training_shots: 256 }, { training_shots: 1024, validation_shots: 100, test_shots: 100 });
  assert.equal(p.completedShots, 256);
  assert.equal(p.totalShots, 1224);
  assert.equal(p.percent, 25600 / 1224);
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
  for (const id of ['processed-shots', 'target-shots', 'throughput', 'eta', 'phase-caption', 'progress-error']) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
  assert.match(html, /progress\.js/);
});
