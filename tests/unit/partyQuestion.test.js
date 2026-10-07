import { describe, it, expect } from 'vitest'
import {
  questionParties, topicAnswer, positionOf, answerLead, answerDetail, partyName,
} from '../../src/partyQuestion.js'

const questions = { groups: ['GMx', 'GP', 'GS', 'GSUMAR'] }

describe('questionParties', () => {
  it('drops groups without a party line and seats the rest left to right', () => {
    expect(questionParties(questions).map((p) => p.label)).toEqual(['Sumar', 'PSOE', 'PP'])
  })

  it('handles missing questions', () => {
    expect(questionParties(null)).toEqual([])
  })
})

describe('topicAnswer and positionOf', () => {
  const pp = { label: 'PP', codes: ['GP'] }

  it('sums the tally of every code of the party', () => {
    const topic = { tally: { GP: [5, 1, 1], GS: [0, 7, 0] } }
    expect(topicAnswer(topic, pp)).toEqual({ counts: { 1: 5, 2: 1, 3: 1 }, n: 7 })
  })

  it('returns no position when the group was split', () => {
    expect(positionOf({ pos: { GP: 2 } }, pp)).toBe(2)
    expect(positionOf({ pos: { GS: 1 } }, pp)).toBeNull()
  })
})

describe('answer copy', () => {
  it('turns the share of votes in favour into a plain answer', () => {
    expect(answerLead({ counts: { 1: 7, 2: 0, 3: 0 }, n: 7 })).toBe('Sí, casi siempre.')
    expect(answerLead({ counts: { 1: 2, 2: 3, 3: 2 }, n: 7 })).toBe('Pocas veces.')
    expect(answerLead({ counts: { 1: 0, 2: 0, 3: 0 }, n: 0 })).toMatch(/No hay votaciones/)
  })

  it('lists only the positions that happened', () => {
    expect(answerDetail({ counts: { 1: 7, 2: 0, 3: 0 }, n: 7 }, 'subir_pensiones', 'PP'))
      .toBe('En 7 votaciones de esta legislatura sobre subir pensiones, el PP votó a favor 7 veces.')
    expect(answerDetail({ counts: { 1: 0, 2: 3, 3: 1 }, n: 4 }, 'subir_pensiones', 'VOX'))
      .toBe('En 4 votaciones de esta legislatura sobre subir pensiones, Vox votó en contra 3 veces y se abstuvo 1 vez.')
  })

  it('names parties with their article', () => {
    expect(partyName('PSOE')).toBe('el PSOE')
    expect(partyName('Sumar')).toBe('Sumar')
  })
})
