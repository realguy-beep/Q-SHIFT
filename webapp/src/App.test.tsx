import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from './App'

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('Q-SHIFT evidence dashboard', () => {
  it('labels saved research as an audited replay and shows no hardware claim', async () => {
    vi.stubGlobal('fetch', vi.fn((url: string) => Promise.resolve({
      json: () => Promise.resolve(url.includes('/api/health')
        ? { status: 'ready' }
        : { mode: 'saved_replay', study: 'Stage 4', status: 'completed', gate_status: 'PASS',
            aggregate: { total_unique_shots: 175500, paired_evaluation_shots: 87500 },
            per_condition: [], audit: 'PASS', independent_test_accessed: false,
            statistics: { primary_bootstrap_95ci: [-0.0019, -0.0013] },
            summary_hash_matches_audit: true, coverage_matches_audit: true,
            claim_boundary: 'Simulation only.' }),
    } as Response)))
    render(<App />)
    await waitFor(() => expect(screen.getByText('Local engine ready')).toBeInTheDocument())
    expect(screen.getByText('Q-SHIFT')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Research evidence' }))
    expect(await screen.findByText(/Simulation only/)).toBeInTheDocument()
    expect(screen.queryByText(/quantum hardware connection/i)).toBeInTheDocument()
  })
})
