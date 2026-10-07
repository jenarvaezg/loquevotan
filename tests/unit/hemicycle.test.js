import { describe, it, expect } from 'vitest'
import { seatLayout, ballotsFromGroups, ballotsFromTotals, partyRank } from '../../src/hemicycle.js'

describe('seatLayout', () => {
  it('places one seat per deputy inside the upper half-disc', () => {
    const { seats, radius } = seatLayout(350)
    expect(seats).toHaveLength(350)
    expect(radius).toBeGreaterThan(0)
    for (const s of seats) {
      expect(s.y).toBeLessThanOrEqual(1e-9)
      expect(Math.hypot(s.x, s.y)).toBeLessThanOrEqual(1 + 1e-9)
    }
  })

  it('orders seats from left to right', () => {
    const { seats } = seatLayout(109)
    expect(seats[0].x).toBeLessThan(0)
    expect(seats.at(-1).x).toBeGreaterThan(0)
  })

  it('handles an empty chamber', () => {
    expect(seatLayout(0).seats).toEqual([])
  })
})

describe('ballotsFromGroups', () => {
  it('seats parties left to right and groups each party by vote', () => {
    const ballots = ballotsFromGroups({
      GP: [1, 2, 0, 0],
      GS: [2, 0, 1, 1],
    })
    expect(ballots.map((b) => `${b.label}:${b.voto}`)).toEqual([
      'PSOE:1', 'PSOE:1', 'PSOE:3', 'PSOE:4',
      'PP:1', 'PP:2', 'PP:2',
    ])
    expect(partyRank('PSOE')).toBeLessThan(partyRank('PP'))
  })

  it('merges groups that share a label', () => {
    const ballots = ballotsFromGroups({ GR: [1, 0, 0, 0], GER: [1, 0, 0, 0] })
    expect(new Set(ballots.map((b) => b.label))).toEqual(new Set(['ERC']))
  })
})

describe('ballotsFromTotals', () => {
  it('draws only the cast votes, without parties', () => {
    const ballots = ballotsFromTotals({ favor: 2, contra: 1, abstencion: 1 })
    expect(ballots.map((b) => b.voto)).toEqual([1, 1, 3, 2])
    expect(ballots.every((b) => b.color === null)).toBe(true)
  })
})
