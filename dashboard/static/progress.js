/* Pure progress normalization shared by the dashboard and Node regression tests. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.QShiftProgress = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const numberOrNull = (value) => value == null || value === '' ? null :
    (Number.isFinite(Number(value)) ? Number(value) : null);
  const canShowGpuTelemetry = (progress, runStatus) =>
    runStatus === 'running' && progress?.device === 'cuda' && progress?.cuda_training_verified === true;
  const normalizeProgress = (event, config = {}) => {
    const total = numberOrNull(event?.total_shots) ??
      numberOrNull(config.training_shots + (config.validation_shots || 0) + (config.test_shots || 0)) ??
      numberOrNull(event?.total_training_shots);
    const completed = numberOrNull(event?.completed_shots) ??
      numberOrNull(event?.generated_training_shots) ??
      numberOrNull(event?.training_samples_processed) ?? 0;
    const processed = numberOrNull(event?.processed_shots) ??
      numberOrNull(event?.training_samples_processed) ?? completed;
    const safeDone = Math.max(0, completed);
    const pct = numberOrNull(event?.progress_percent) ?? (total > 0 ? safeDone * 100 / total : null);
    return {
      status: String(event?.status || 'unknown'),
      phase: String(event?.phase || event?.stage || 'preparing'),
      totalShots: total,
      completedShots: safeDone,
      processedShots: Math.max(0, processed),
      percent: pct == null ? null : Math.max(0, Math.min(100, pct)),
      phaseCompleted: numberOrNull(event?.phase_completed_shots ?? event?.stage_completed_shots),
      phaseTotal: numberOrNull(event?.phase_total_shots ?? event?.stage_total_shots),
      throughput: numberOrNull(event?.throughput_shots_s),
      etaSeconds: numberOrNull(event?.eta_seconds),
      stages: event?.stage_counts && typeof event.stage_counts === 'object' ? event.stage_counts : {},
      error: event?.error || null,
      device: event?.device || null,
      cudaTrainingVerified: event?.cuda_training_verified === true,
      gpuTelemetry: event?.gpu_telemetry || null,
    };
  };
  return { normalizeProgress, canShowGpuTelemetry };
});
