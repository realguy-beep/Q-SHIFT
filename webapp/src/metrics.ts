export function formatPercent(value: number, digits = 3): string {
  if (!Number.isFinite(value)) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

export function ler(errors: number, shots: number): number {
  if (!Number.isInteger(errors) || !Number.isInteger(shots) || shots <= 0 || errors < 0 || errors > shots) {
    throw new RangeError('Expected 0 ≤ errors ≤ shots and shots > 0')
  }
  return errors / shots
}

export function detectorGroups(bits: string): string[] {
  if (!/^[01]+$/.test(bits) || bits.length !== 40) throw new RangeError('Expected 40 binary detector bits')
  return Array.from({ length: 5 }, (_, i) => bits.slice(i * 8, (i + 1) * 8))
}
