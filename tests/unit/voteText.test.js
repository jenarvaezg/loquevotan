import { describe, it, expect } from 'vitest'
import { parseFecha, formatFecha, voteQuestion, RESULT_ANSWER } from '../../src/utils.js'

describe('parseFecha and formatFecha', () => {
  it('reads national ISO dates and regional D/M/YYYY dates alike', () => {
    expect(parseFecha('2026-02-26')).toEqual({ y: 2026, m: 2, d: 26 })
    expect(parseFecha('26/2/2026')).toEqual({ y: 2026, m: 2, d: 26 })
    expect(parseFecha('mañana')).toBeNull()
  })

  it('formats long and short dates in Spanish', () => {
    expect(formatFecha('2026-02-26')).toBe('26 de febrero de 2026')
    expect(formatFecha('05/09/2025', 'short')).toBe('5 sep 2025')
    expect(formatFecha('sin fecha')).toBe('sin fecha')
  })
})

describe('voteQuestion', () => {
  it('reads a proposal as the question the vote answered', () => {
    expect(voteQuestion('Garantizar educación sexual integral en escuelas')).toBe('¿Garantizar educación sexual integral en escuelas?')
    expect(voteQuestion('¿Subir pensiones?.')).toBe('¿Subir pensiones?')
    expect(voteQuestion('')).toBe('')
  })

  it('answers with the result', () => {
    expect(RESULT_ANSWER.Rechazada).toBe('No')
  })
})
