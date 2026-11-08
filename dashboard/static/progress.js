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
      numberOrNull(config.training_shots + (config.validation_shots || 0) + (config.test_shots || 0));
    // These counters describe different work. Missing completion must stay
    // unknown; generated or training-only counts are not completion evidence.
    const completed = numberOrNull(event?.completed_shots);
    const generated = numberOrNull(event?.generated_shots);
    const processed = numberOrNull(event?.processed_shots);
    const safeCompleted = completed == null ? null : Math.max(0, completed);
    const safeGenerated = generated == null ? null : Math.max(0, generated);
    const safeProcessed = processed == null ? null : Math.max(0, processed);
    const hasCompletionDenominator = safeCompleted != null && total != null && total > 0;
    const pct = hasCompletionDenominator
      ? Math.max(0, Math.min(100, safeCompleted * 100 / total))
      : null;
    const throughput = numberOrNull(event?.throughput_shots_s);
    const hasEtaInputs = hasCompletionDenominator && throughput != null && throughput > 0;
    const eta = hasEtaInputs
      ? Math.max(0, (total - safeCompleted) / throughput)
      : null;
    return {
      status: String(event?.status || 'unknown'),
      phase: String(event?.phase || event?.stage || 'preparing'),
      totalShots: total,
      completedShots: safeCompleted,
      generatedShots: safeGenerated,
      processedShots: safeProcessed,
      percent: pct,
      phaseCompleted: numberOrNull(event?.phase_completed_shots ?? event?.stage_completed_shots),
      phaseTotal: numberOrNull(event?.phase_total_shots ?? event?.stage_total_shots),
      throughput,
      etaSeconds: eta,
      stages: event?.stage_counts && typeof event.stage_counts === 'object' ? event.stage_counts : {},
      error: event?.error || null,
      device: event?.device || null,
      cudaTrainingVerified: event?.cuda_training_verified === true,
      gpuTelemetry: event?.gpu_telemetry || null,
    };
  };
  return { normalizeProgress, canShowGpuTelemetry };
});
