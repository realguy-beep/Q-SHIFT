export type Method = {
  id: string
  label: string
  errors: number
  shots: number
  ler: number
  wilson_95: [number, number]
  prediction_disagreements_vs_fixed: number
  candidate_only_vs_fixed: number
  fixed_only_vs_candidate: number
  mcnemar_exact_p_vs_fixed: number
}

export type LiveResult = {
  mode: 'live_simulation'
  generating_burst_probability: number
  estimated_burst_probability: number
  estimation_error: number
  calibration_shots: number
  profile_shots_per_probability: number
  evaluation_shots: number
  runtime_seconds: number
  seed_block_id: number
  derived_seeds: Record<string, number>
  methods: Method[]
  no_decoding_reference: { label: string; errors: number; shots: number; ler: number }
  records: Array<{ index: number; detectors: string; observable: number; fixed_prediction: number; estimated_prediction: number; privileged_prediction: number; fixed_residual_error: number; estimated_residual_error: number; detector_slices: Array<{ time: number; detector_ids: number[]; bits: string }> }>
  limitations: string[]
}

export type ResearchReplay = {
  mode: 'saved_replay'
  study: string
  status: string
  gate_status: string
  aggregate: Record<string, unknown>
  estimation_diagnostics: Record<string, unknown>
  statistics: Record<string, unknown>
  per_condition: Array<Record<string, number>>
  audit: string
  summary_hash_matches_audit: boolean
  coverage_matches_audit: boolean
  independent_test_accessed: boolean
  claim_boundary: string
}
