<script setup>
import { ref, computed, watch } from 'vue'
import { useData } from '../composables/useData'
import html2canvas from 'html2canvas'

const { currentScopeId } = useData()

const quizSets = ref({ basic: null, advanced: null })
const selectedMode = ref('basic')
const selectedYAxis = ref('social') // 'social' | 'territorial'
const loading = ref(true)
const error = ref(null)
const captureArea = ref(null)
const hoveredPoint = ref(null)

const currentStep = ref(-1) // -1: Intro, 0-N: Questions, N+1: Results
const answers = ref({}) // qId -> 'si' | 'no' | 'abstencion'
const PARTIAL_MATCH_FACTOR = 0.35
const SOCIAL_AXIS_THRESHOLD = 15
const ECONOMIC_AXIS_THRESHOLD = 15
const TERRITORIAL_AXIS_THRESHOLD = 15
const COMPASS_MIN_QUESTIONS_FOR_HIGH_CONFIDENCE = 14
const COMPASS_DISPLAY_MARGIN = 8
const COMPASS_DISPLAY_SOFTNESS = 0.55
const COMPASS_EMPIRICAL_SCALE = 30
const COMPASS_EMPIRICAL_BLEND_BASE = 0.40
const COMPASS_SPREAD_FLOOR_FACTOR = 0.20
const COMPASS_SPREAD_FLOOR_MIN = 3.5

// Territorial axis: -100 (Centralista) to +100 (Regionalista/Nacionalista)
const PARTY_ANCHORS = {
  PSOE: { economic: -22, social: -16, territorial: -10, color: '#ef4444' },
  PP: { economic: 24, social: 14, territorial: -35, color: '#2563eb' },
  VOX: { economic: 62, social: 70, territorial: -88, color: '#16a34a' },
  SUMAR: { economic: -44, social: -54, territorial: 15, color: '#db2777' },
  PODEMOS: { economic: -62, social: -65, territorial: 25, color: '#7c3aed' },
  ERC: { economic: -30, social: -40, territorial: 95, color: '#f59e0b' },
  JUNTS: { economic: 8, social: -4, territorial: 98, color: '#0ea5e9' },
  PNV: { economic: 6, social: -8, territorial: 92, color: '#14b8a6' },

  CS: { economic: 24, social: 6, territorial: -70, color: '#f97316' },
  'UPL-SY': { economic: -8, social: -12, territorial: 75, color: '#a855f7' },
  UPL: { economic: -12, social: -15, territorial: 85, color: '#a855f7' },
  SY: { economic: -5, social: -10, territorial: 70, color: '#334155' },
  'SORIA ¡YA!': { economic: -5, social: -10, territorial: 70, color: '#334155' },
  XAV: { economic: 12, social: 4, territorial: 65, color: '#ffee00' },
  'POR ÁVILA': { economic: 12, social: 4, territorial: 65, color: '#ffee00' },
  'POR ANDALUCÍA': { economic: -46, social: -56, territorial: 25, color: '#ec4899' },
  ADELANTE: { economic: -54, social: -44, territorial: 80, color: '#8b5cf6' },

  'PSOE DE ANDALUCÍA': { economic: -22, social: -16, territorial: 5, color: '#ef4444' },
  'POPULAR ANDALUZ': { economic: 24, social: 14, territorial: -15, color: '#2563eb' },
  'VOX EN ANDALUCÍA': { economic: 62, social: 70, territorial: -88, color: '#16a34a' },
  'UNIDAS PODEMOS POR ANDALUCÍA': { economic: -56, social: -60, territorial: 25, color: '#7c3aed' },
  'ADELANTE ANDALUCÍA': { economic: -54, social: -44, territorial: 85, color: '#8b5cf6' },
  'MIXTO-ADELANTE ANDALUCÍA': { economic: -54, social: -44, territorial: 85, color: '#8b5cf6' },
  CIUDADANOS: { economic: 24, social: 6, territorial: -70, color: '#f97316' }
}

const PARTY_ALIAS = {
  'PSOE DE ANDALUCIA': 'PSOE DE ANDALUCÍA',
  'VOX EN ANDALUCIA': 'VOX EN ANDALUCÍA',
  'UNIDAS PODEMOS POR ANDALUCIA': 'UNIDAS PODEMOS POR ANDALUCÍA',
  'ADELANTE ANDALUCIA': 'ADELANTE ANDALUCÍA',
  'MIXTO-ADELANTE ANDALUCIA': 'MIXTO-ADELANTE ANDALUCÍA',
  'POR ANDALUCIA': 'POR ANDALUCÍA'
}

const NORMALIZED_PARTY_ANCHORS = Object.fromEntries(
  Object.entries(PARTY_ANCHORS).map(([key, value]) => [normalizeGroupKey(key), value])
)

const hasAdvanced = computed(() => !!quizSets.value.advanced)
const activeQuiz = computed(() => {
  if (selectedMode.value === 'advanced' && quizSets.value.advanced) return quizSets.value.advanced
  return quizSets.value.basic
})
const isAdvancedMode = computed(() => selectedMode.value === 'advanced' && !!quizSets.value.advanced)

const isResults = computed(() => activeQuiz.value && currentStep.value >= activeQuiz.value.questions.length)
const currentQuestion = computed(() => {
  if (!activeQuiz.value || currentStep.value < 0 || isResults.value) return null
  return activeQuiz.value.questions[currentStep.value]
})

function getQuestionWeight(question) {
  const rawWeight = Number(question?.weight)
  return Number.isFinite(rawWeight) && rawWeight > 0 ? rawWeight : 1
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}

function voteToFactor(vote) {
  if (vote === 'si') return 1
  if (vote === 'no') return -1
  return 0
}

function normalizeGroupKey(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toUpperCase()
}

function getPartyAnchor(groupName) {
  const rawKey = normalizeGroupKey(groupName)
  const canonical = PARTY_ALIAS[rawKey] || rawKey
  return NORMALIZED_PARTY_ANCHORS[normalizeGroupKey(canonical)] || null
}

function getPartyColor(groupName) {
  const anchor = getPartyAnchor(groupName)
  return anchor?.color || '#64748b'
}

function mean(values) {
  if (!values.length) return 0
  return values.reduce((acc, value) => acc + value, 0) / values.length
}

function standardDeviation(values) {
  if (values.length < 2) return 0
  const avg = mean(values)
  const variance = mean(values.map((value) => (value - avg) ** 2))
  return Math.sqrt(variance)
}

function pearsonCorrelation(xs, ys) {
  if (!xs.length || xs.length !== ys.length) return 0
  const avgX = mean(xs)
  const avgY = mean(ys)
  const stdX = standardDeviation(xs)
  const stdY = standardDeviation(ys)
  if (!stdX || !stdY) return 0

  let covariance = 0
  for (let i = 0; i < xs.length; i++) {
    covariance += (xs[i] - avgX) * (ys[i] - avgY)
  }
  covariance /= xs.length
  return clamp(covariance / (stdX * stdY), -1, 1)
}

function normalizeAxisScore(score, maxScore) {
  if (!maxScore) return 0
  return clamp(Math.round((score / maxScore) * 100), -100, 100)
}

function normalizeAxisScoreEmpirical(score, center, spread, spreadFloor = 0, empiricalScale = COMPASS_EMPIRICAL_SCALE) {
  const effectiveSpread = Math.max(spread || 0, spreadFloor || 0)
  if (!effectiveSpread) return 0
  return clamp(Math.round(((score - center) / effectiveSpread) * empiricalScale), -100, 100)
}

function blendAxisScore(score, maxScore, center, spread, empiricalBlend, spreadFloor = 0) {
  const theoretical = normalizeAxisScore(score, maxScore)
  const empirical = normalizeAxisScoreEmpirical(score, center, spread, spreadFloor)
  return clamp(
    Math.round((theoretical * (1 - empiricalBlend)) + (empirical * empiricalBlend)),
    -100,
    100
  )
}

function dampenForDisplay(value, factor) {
  return clamp(Math.round((Number(value) || 0) * factor), -100, 100)
}

function classifyCompassConfidence(confidence, answeredQuestions) {
  if (confidence >= 78 && answeredQuestions >= COMPASS_MIN_QUESTIONS_FOR_HIGH_CONFIDENCE) return 'alta'
  if (confidence >= 58) return 'media'
  return 'baja'
}

function calibrateQuestionForCompass(question, groups) {
  const manualAxis = question?.axis || {}
  const hasManualAxis =
    Number.isFinite(Number(manualAxis.economic)) ||
    Number.isFinite(Number(manualAxis.social)) ||
    Number.isFinite(Number(manualAxis.territorial))

  const manualEconomic = Number.isFinite(Number(manualAxis.economic))
    ? clamp(Number(manualAxis.economic), -1, 1)
    : 0
  const manualSocial = Number.isFinite(Number(manualAxis.social))
    ? clamp(Number(manualAxis.social), -1, 1)
    : 0
  const manualTerritorial = Number.isFinite(Number(manualAxis.territorial))
    ? clamp(Number(manualAxis.territorial), -1, 1)
    : 0

  const samples = groups
    .map((group) => {
      const anchor = getPartyAnchor(group)
      const vote = voteToFactor(question?.votes?.[group])
      if (!anchor) return null
      return {
        vote,
        economic: anchor.economic / 100,
        social: anchor.social / 100,
        territorial: (anchor.territorial || 0) / 100
      }
    })
    .filter(Boolean)

  const votes = samples.map((sample) => sample.vote)
  const economicAnchors = samples.map((sample) => sample.economic)
  const socialAnchors = samples.map((sample) => sample.social)
  const territorialAnchors = samples.map((sample) => sample.territorial)

  const inferredEconomic = pearsonCorrelation(votes, economicAnchors)
  const inferredSocial = pearsonCorrelation(votes, socialAnchors)
  const inferredTerritorial = pearsonCorrelation(votes, territorialAnchors)

  const inferredStrength = clamp((Math.abs(inferredEconomic) + Math.abs(inferredSocial) + Math.abs(inferredTerritorial)) / 2.2, 0, 1)
  const coverage = groups.length ? clamp(samples.length / groups.length, 0, 1) : 0
  const voteSpread = clamp(standardDeviation(votes) / 0.9, 0, 1)

  const blendManual = hasManualAxis ? 0.65 : 0
  const blendInferred = hasManualAxis ? 0.35 : 1
  const blendedEconomic = (manualEconomic * blendManual) + (inferredEconomic * blendInferred)
  const blendedSocial = (manualSocial * blendManual) + (inferredSocial * blendInferred)
  const blendedTerritorial = (manualTerritorial * blendManual) + (inferredTerritorial * blendInferred)

  const consistency = hasManualAxis
    ? clamp(1 - ((Math.abs(manualEconomic - inferredEconomic) + Math.abs(manualSocial - inferredSocial) + Math.abs(manualTerritorial - inferredTerritorial)) / 6), 0, 1)
    : inferredStrength

  const discriminationBase = Number(question?.discrimination)
  const base = Number.isFinite(discriminationBase) && discriminationBase > 0 ? discriminationBase : 1
  const discrimination = clamp(
    base
      * (0.72 + (0.58 * inferredStrength))
      * (0.8 + (0.32 * voteSpread))
      * (0.82 + (0.25 * coverage))
      * (0.85 + (0.3 * consistency)),
    0.65,
    1.85
  )

  return {
    axis: {
      economic: clamp(blendedEconomic, -1, 1),
      social: clamp(blendedSocial, -1, 1),
      territorial: clamp(blendedTerritorial, -1, 1)
    },
    discrimination,
    inferredStrength,
    consistency,
    coverage
  }
}

async function loadQuiz() {
  loading.value = true
  error.value = null

  try {
    const scopePath = currentScopeId.value === 'nacional' ? '' : `${currentScopeId.value}/`
    const baseUrl = `${import.meta.env.BASE_URL}data/${scopePath}`

    const basicResp = await fetch(`${baseUrl}quiz.json`)
    if (!basicResp.ok) throw new Error('Basic quiz not available for this scope')
    const basicQuiz = await basicResp.json()

    let advancedQuiz = null
    try {
      const advancedResp = await fetch(`${baseUrl}quiz_advanced.json`)
      if (advancedResp.ok) advancedQuiz = await advancedResp.json()
    } catch (_) {
      // Optional file
    }

    quizSets.value = { basic: basicQuiz, advanced: advancedQuiz }
    if (selectedMode.value === 'advanced' && !advancedQuiz) selectedMode.value = 'basic'
  } catch (err) {
    error.value = 'No hay un test de afinidad disponible para este parlamento en este momento.'
  } finally {
    loading.value = false
  }
}

watch(currentScopeId, () => {
  currentStep.value = -1
  answers.value = {}
  selectedMode.value = 'basic'
  loadQuiz()
}, { immediate: true })

function selectMode(mode) {
  if (mode === 'advanced' && !hasAdvanced.value) return
  selectedMode.value = mode
  answers.value = {}
  currentStep.value = -1
}

function startQuiz() {
  if (!activeQuiz.value) return
  currentStep.value = 0
}

function answer(vote) {
  if (currentQuestion.value) {
    answers.value[currentQuestion.value.id] = vote
    currentStep.value++

    if (isResults.value) {
      finishQuiz()
    }
  }
}

const affinities = computed(() => {
  if (!activeQuiz.value || !isResults.value) return []

  const calibratedMap = calibratedAdvancedQuestionModel.value

  const scores = {}
  activeQuiz.value.groups.forEach((group) => {
    scores[group] = 0
  })

  const totalWeight = activeQuiz.value.questions.reduce((acc, question) => {
    const baseWeight = getQuestionWeight(question)
    const calibration = calibratedMap[question.id]
    const effectiveWeight = isAdvancedMode.value ? baseWeight * (calibration?.discrimination || 1) : baseWeight
    return acc + effectiveWeight
  }, 0)

  activeQuiz.value.questions.forEach((question) => {
    const userVote = answers.value[question.id]
    const baseWeight = getQuestionWeight(question)
    const calibration = calibratedMap[question.id]
    const weight = isAdvancedMode.value ? baseWeight * (calibration?.discrimination || 1) : baseWeight

    activeQuiz.value.groups.forEach((group) => {
      const groupVote = question.votes[group]
      if (groupVote === userVote) {
        scores[group] += weight
      } else if ((groupVote === 'abstencion' || userVote === 'abstencion') && groupVote !== userVote) {
        scores[group] += weight * PARTIAL_MATCH_FACTOR
      }
    })
  })

  return Object.entries(scores)
    .map(([group, score]) => ({
      group,
      pct: Math.round((score / (totalWeight || 1)) * 100)
    }))
    .sort((a, b) => b.pct - a.pct)
})

const calibratedAdvancedQuestionModel = computed(() => {
  if (!isAdvancedMode.value || !activeQuiz.value) return {}

  const model = {}
  const groups = activeQuiz.value.groups || []
  activeQuiz.value.questions.forEach((question) => {
    model[question.id] = calibrateQuestionForCompass(question, groups)
  })
  return model
})

const compassData = computed(() => {
  if (!isAdvancedMode.value || !activeQuiz.value || !isResults.value) return null

  const calibratedMap = calibratedAdvancedQuestionModel.value
  const groups = activeQuiz.value.groups
  const partyScores = {}
  groups.forEach((group) => {
    partyScores[group] = { economic: 0, social: 0, territorial: 0 }
  })

  let userEconomic = 0
  let userSocial = 0
  let userTerritorial = 0
  let maxEconomic = 0
  let maxSocial = 0
  let maxTerritorial = 0
  let totalModelWeight = 0
  let answeredDirectionalWeight = 0
  let weightedStrength = 0
  let weightedConsistency = 0
  let answeredQuestions = 0

  activeQuiz.value.questions.forEach((question) => {
    const calibration = calibratedMap[question.id] || {}
    const axis = calibration.axis || question.axis || {}
    const baseWeight = getQuestionWeight(question)
    const discrimination = calibration.discrimination || 1
    const effectiveWeight = baseWeight * discrimination
    const economicDelta = Number(axis.economic) || 0
    const socialDelta = Number(axis.social) || 0
    const territorialDelta = Number(axis.territorial) || 0

    maxEconomic += Math.abs(economicDelta * effectiveWeight)
    maxSocial += Math.abs(socialDelta * effectiveWeight)
    maxTerritorial += Math.abs(territorialDelta * effectiveWeight)
    totalModelWeight += effectiveWeight
    weightedStrength += (calibration.inferredStrength || 0) * effectiveWeight
    weightedConsistency += (calibration.consistency || 0) * effectiveWeight

    const userFactor = voteToFactor(answers.value[question.id])
    userEconomic += userFactor * economicDelta * effectiveWeight
    userSocial += userFactor * socialDelta * effectiveWeight
    userTerritorial += userFactor * territorialDelta * effectiveWeight
    if (userFactor !== 0) {
      answeredDirectionalWeight += effectiveWeight
      answeredQuestions += 1
    }

    groups.forEach((group) => {
      const groupFactor = voteToFactor(question.votes[group])
      partyScores[group].economic += groupFactor * economicDelta * effectiveWeight
      partyScores[group].social += groupFactor * socialDelta * effectiveWeight
      partyScores[group].territorial += groupFactor * territorialDelta * effectiveWeight
    })
  })

  const partyEconomicValues = groups.map((group) => partyScores[group].economic)
  const partySocialValues = groups.map((group) => partyScores[group].social)
  const partyTerritorialValues = groups.map((group) => partyScores[group].territorial)
  const economicCenter = mean(partyEconomicValues)
  const socialCenter = mean(partySocialValues)
  const territorialCenter = mean(partyTerritorialValues)
  const economicSpread = standardDeviation(partyEconomicValues)
  const socialSpread = standardDeviation(partySocialValues)
  const territorialSpread = standardDeviation(partyTerritorialValues)
  const economicSpreadFloor = Math.max(maxEconomic * COMPASS_SPREAD_FLOOR_FACTOR, COMPASS_SPREAD_FLOOR_MIN)
  const socialSpreadFloor = Math.max(maxSocial * COMPASS_SPREAD_FLOOR_FACTOR, COMPASS_SPREAD_FLOOR_MIN)
  const territorialSpreadFloor = Math.max(maxTerritorial * COMPASS_SPREAD_FLOOR_FACTOR, COMPASS_SPREAD_FLOOR_MIN)
  const spreadReliability = mean([
    clamp(economicSpread / (economicSpreadFloor || 1), 0, 1),
    clamp(socialSpread / (socialSpreadFloor || 1), 0, 1),
    clamp(territorialSpread / (territorialSpreadFloor || 1), 0, 1)
  ])
  const empiricalBlend = clamp(
    COMPASS_EMPIRICAL_BLEND_BASE
      + ((8 - groups.length) * 0.03)
      + (spreadReliability * 0.14),
    0.36,
    0.62
  )

  const user = {
    economic: blendAxisScore(
      userEconomic,
      maxEconomic,
      economicCenter,
      economicSpread,
      empiricalBlend,
      economicSpreadFloor
    ),
    social: blendAxisScore(
      userSocial,
      maxSocial,
      socialCenter,
      socialSpread,
      empiricalBlend,
      socialSpreadFloor
    ),
    territorial: blendAxisScore(
      userTerritorial,
      maxTerritorial,
      territorialCenter,
      territorialSpread,
      empiricalBlend,
      territorialSpreadFloor
    )
  }

  const affinityOrder = affinities.value.map((result) => result.group)
  const partiesByAffinity = groups
    .map((group) => ({
      group,
      economic: blendAxisScore(
        partyScores[group].economic,
        maxEconomic,
        economicCenter,
        economicSpread,
        empiricalBlend,
        economicSpreadFloor
      ),
      social: blendAxisScore(
        partyScores[group].social,
        maxSocial,
        socialCenter,
        socialSpread,
        empiricalBlend,
        socialSpreadFloor
      ),
      territorial: blendAxisScore(
        partyScores[group].territorial,
        maxTerritorial,
        territorialCenter,
        territorialSpread,
        empiricalBlend,
        territorialSpreadFloor
      )
    }))
    .sort((a, b) => affinityOrder.indexOf(a.group) - affinityOrder.indexOf(b.group))

  const responseCoverage = totalModelWeight ? answeredDirectionalWeight / totalModelWeight : 0
  const avgStrength = totalModelWeight ? weightedStrength / totalModelWeight : 0
  const avgConsistency = totalModelWeight ? weightedConsistency / totalModelWeight : 0
  const axisBalance = Math.max(maxEconomic, maxSocial, maxTerritorial)
    ? Math.min(maxEconomic, maxSocial, maxTerritorial) / Math.max(maxEconomic, maxSocial, maxTerritorial)
    : 0
  const confidenceScore = clamp(
    Math.round(((
      (0.45 * responseCoverage) +
      (0.25 * avgStrength) +
      (0.2 * avgConsistency) +
      (0.1 * axisBalance)
    ) * 100)),
    0,
    100
  )
  const confidenceLabel = classifyCompassConfidence(confidenceScore, answeredQuestions)
  const axisUncertainty = {
    economic: Math.round(clamp((100 - confidenceScore) * 0.26 + (1 - spreadReliability) * 10 + (1 - avgConsistency) * 8, 6, 34)),
    social: Math.round(clamp((100 - confidenceScore) * 0.26 + (1 - spreadReliability) * 10 + (1 - avgStrength) * 8, 6, 34)),
    territorial: Math.round(clamp((100 - confidenceScore) * 0.26 + (1 - spreadReliability) * 10 + (1 - avgStrength) * 8, 6, 34))
  }
  const displayScale = clamp(0.70 + (confidenceScore * 0.0022), 0.70, 0.92)

  const userForDisplay = {
    ...user,
    displayEconomic: dampenForDisplay(user.economic, displayScale),
    displaySocial: dampenForDisplay(user.social, displayScale),
    displayTerritorial: dampenForDisplay(user.territorial, displayScale)
  }
  const partiesWithDisplay = partiesByAffinity.map((party) => ({
    ...party,
    displayEconomic: dampenForDisplay(party.economic, displayScale),
    displaySocial: dampenForDisplay(party.social, displayScale),
    displayTerritorial: dampenForDisplay(party.territorial, displayScale)
  }))
  const partiesByDistanceForDisplay = partiesWithDisplay
    .map((party) => ({
      ...party,
      distance: Math.hypot(user.economic - party.economic, user.social - party.social)
    }))
    .sort((a, b) => a.distance - b.distance)

  return {
    user: userForDisplay,
    partiesByAffinity: partiesWithDisplay,
    partiesByDistance: partiesByDistanceForDisplay,
    quality: {
      confidenceScore,
      confidenceLabel,
      responseCoverage: Math.round(responseCoverage * 100),
      modelStrength: Math.round(avgStrength * 100),
      axisUncertainty
    }
  }
})

const topCompassParties = computed(() => {
  if (!compassData.value) return []
  return compassData.value.partiesByDistance.slice(0, 5)
})

const userCompassLabel = computed(() => {
  if (!compassData.value) return ''

  const { economic, social } = compassData.value.user
  const economicLabel = economic < -ECONOMIC_AXIS_THRESHOLD
    ? 'izquierda económica'
    : economic > ECONOMIC_AXIS_THRESHOLD
      ? 'derecha económica'
      : 'centro económico'
  const socialLabel = social > SOCIAL_AXIS_THRESHOLD
    ? 'más conservador/autoritario'
    : social < -SOCIAL_AXIS_THRESHOLD
      ? 'más progresista/libertario'
      : 'centro social'
  const nearest = compassData.value.partiesByDistance[0]
  const nearestLabel = nearest ? ` El partido más cercano en mapa es ${nearest.group}.` : ''

  return `Tu posición cae en ${economicLabel} y ${socialLabel}.${nearestLabel}`
})

function pointStyle(point) {
  const rawEconomic = Number.isFinite(Number(point?.displayEconomic))
    ? Number(point.displayEconomic)
    : Number(point?.economic) || 0

  const isTerritorial = selectedYAxis.value === 'territorial'
  const rawY = isTerritorial
    ? (Number.isFinite(Number(point?.displayTerritorial)) ? Number(point.displayTerritorial) : Number(point?.territorial) || 0)
    : (Number.isFinite(Number(point?.displaySocial)) ? Number(point.displaySocial) : Number(point?.social) || 0)

  const x = squashAxisForDisplay(rawEconomic)
  const y = squashAxisForDisplay(rawY)

  return {
    left: `${axisToBoardPercent(x)}%`,
    top: `${axisToBoardPercent(-y)}%`
  }
}

function partyPointStyle(party) {
  return {
    ...pointStyle(party),
    backgroundColor: getPartyColor(party.group)
  }
}

function finishQuiz() {
  try {
    const topMatch = affinities.value[0]
    const compass = compassData.value
    const eventData = {
      event: 'quiz_completed',
      quiz_scope: currentScopeId.value,
      quiz_mode: selectedMode.value,
      top_match_group: topMatch ? topMatch.group : 'none',
      top_match_pct: topMatch ? topMatch.pct : 0,
      compass_economic: compass ? compass.user.economic : null,
      compass_social: compass ? compass.user.social : null,
      compass_confidence: compass ? compass.quality.confidenceScore : null
    }

    if (window.dataLayer) {
      window.dataLayer.push(eventData)
    } else {
      console.log('[Analytics Dummy] Quiz completed:', eventData)
    }
  } catch (e) {
    // ignore
  }
}

function shareResults() {
  const top = affinities.value[0]
  if (!top) return

  const modeLabel = selectedMode.value === 'advanced' ? 'avanzado' : 'basico'
  const compass = compassData.value
  const compassSnippet = compass
    ? ` Mi posicion en el mapa: X ${compass.user.economic}, Y ${compass.user.social} (confianza ${compass.quality.confidenceScore}%).`
    : ''

  const text = `He hecho el test ${modeLabel} de @LoQueVotan y mi mayor afinidad es con ${top.group} (${top.pct}%).${compassSnippet} ¡Descubre la tuya!`
  const url = window.location.href

  if (navigator.share) {
    navigator.share({ title: 'Lo Que Votan - Test de Afinidad', text, url }).catch(() => {})
  } else {
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`, '_blank')
  }
}

async function downloadImage() {
  if (!captureArea.value) return

  const watermark = captureArea.value.querySelector('.quiz-watermark')
  if (watermark) watermark.style.display = 'block'

  try {
    const canvas = await html2canvas(captureArea.value, {
      scale: 2,
      backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--color-bg'),
      useCORS: true
    })
    const url = canvas.toDataURL('image/png')
    const a = document.createElement('a')
    a.href = url
    a.download = `loquevotan-afinidad-${currentScopeId.value}-${selectedMode.value}.png`
    a.click()
  } catch (err) {
    console.error('Error generating image:', err)
  } finally {
    if (watermark) watermark.style.display = 'none'
  }
}

function resetQuiz() {
  answers.value = {}
  currentStep.value = -1
}

function squashAxisForDisplay(axisValue) {
  const raw = clamp(Number(axisValue) || 0, -100, 100)
  const normalized = raw / 100
  const softened = Math.tanh(normalized * COMPASS_DISPLAY_SOFTNESS) / Math.tanh(COMPASS_DISPLAY_SOFTNESS)
  return clamp(softened * 100, -100, 100)
}

function axisToBoardPercent(axisValue) {
  const usableRange = 100 - (COMPASS_DISPLAY_MARGIN * 2)
  return COMPASS_DISPLAY_MARGIN + (((axisValue + 100) / 200) * usableRange)
}
</script>

<template>
  <div class="quiz-container">
    <div v-if="loading" class="loading-wrap"><div class="loading-spinner"></div></div>

    <div v-else-if="error" class="error-state">
      <h2>Oops!</h2>
      <p>{{ error }}</p>
      <router-link to="/" class="btn btn--primary mt-2">Volver al inicio</router-link>
    </div>

    <div v-else-if="activeQuiz" class="quiz-content">
      <div v-if="currentStep === -1" class="quiz-intro">
        <h1>{{ activeQuiz.title }}</h1>

        <div v-if="hasAdvanced" class="mode-switch">
          <button
            class="mode-pill"
            :class="{ 'mode-pill--active': selectedMode === 'basic' }"
            @click="selectMode('basic')"
          >
            <span>Básico</span>
            <small>{{ quizSets.basic.questions.length }} preguntas</small>
          </button>
          <button
            class="mode-pill"
            :class="{ 'mode-pill--active': selectedMode === 'advanced' }"
            @click="selectMode('advanced')"
          >
            <span>Avanzado</span>
            <small>{{ quizSets.advanced.questions.length }} preguntas + mapa</small>
          </button>
        </div>

        <p class="lead-text">{{ activeQuiz.description }}</p>

        <div class="methodology-box">
          <h2>¿Cómo funciona?</h2>
          <ul>
            <li>Te mostraremos <strong>{{ activeQuiz.questions.length }} votaciones reales</strong> que tuvieron lugar en el parlamento.</li>
            <li>No te diremos quién propuso la ley para evitar sesgos.</li>
            <li>Al finalizar, calcularemos matemáticamente tu afinidad con los votos de cada partido.</li>
            <li v-if="isAdvancedMode">Además, en el test avanzado te ubicamos en un mapa político de dos ejes (económico y social) usando calibración empírica por patrones de voto.</li>
            <li v-else>Algunas preguntas tienen más peso porque ayudan a separar partidos con votos muy parecidos.</li>
          </ul>
        </div>

        <button class="btn btn--primary btn--lg quiz-start-btn" @click="startQuiz">
          Empezar {{ isAdvancedMode ? 'Test Avanzado' : 'Test Básico' }} &rarr;
        </button>
      </div>

      <div v-else-if="!isResults" class="quiz-question-view">
        <div class="quiz-progress">
          <div class="quiz-progress-text">Pregunta {{ currentStep + 1 }} de {{ activeQuiz.questions.length }}</div>
          <div class="quiz-progress-bar">
            <div class="quiz-progress-fill" :style="{ width: `${(currentStep / activeQuiz.questions.length) * 100}%` }"></div>
          </div>
        </div>

        <div class="question-card">
          <div class="question-topic">{{ currentQuestion.topic }}</div>
          <h2 class="question-text">«{{ currentQuestion.text }}»</h2>
          <p class="question-prompt">¿Qué habrías votado tú?</p>

          <div class="vote-buttons">
            <button class="btn-vote btn-vote--favor" @click="answer('si')">
              <span class="vote-icon">👍</span> A Favor
            </button>
            <button class="btn-vote btn-vote--contra" @click="answer('no')">
              <span class="vote-icon">👎</span> En Contra
            </button>
            <button class="btn-vote btn-vote--abstencion" @click="answer('abstencion')">
              <span class="vote-icon">🤷</span> Me Abstengo
            </button>
          </div>
        </div>
      </div>

      <div v-else class="quiz-results">
        <div ref="captureArea" class="quiz-capture-area">
          <div
            class="quiz-watermark"
            style="display:none; text-align:center; margin-bottom:1rem; font-weight:800; font-size:1.5rem; color:var(--color-primary);"
          >
            Lo Que Votan
          </div>

          <div class="results-header">
            <h2>Tu Afinidad Política</h2>
            <p>
              Resultado del test {{ isAdvancedMode ? 'avanzado' : 'básico' }}
              basado en {{ activeQuiz.questions.length }} votaciones.
            </p>
          </div>

          <div v-if="isAdvancedMode && compassData" class="compass-card">
            <div class="compass-header">
              <h3>Mapa político (tipo compass)</h3>
              <div class="axis-switcher">
                <button
                  class="axis-btn"
                  :class="{ 'axis-btn--active': selectedYAxis === 'social' }"
                  @click="selectedYAxis = 'social'"
                >
                  Social
                </button>
                <button
                  class="axis-btn"
                  :class="{ 'axis-btn--active': selectedYAxis === 'territorial' }"
                  @click="selectedYAxis = 'territorial'"
                >
                  Territorial
                </button>
              </div>
            </div>
            <p class="compass-summary">{{ userCompassLabel }}</p>

            <div class="compass-board">
              <div class="compass-axis compass-axis--horizontal"></div>
              <div class="compass-axis compass-axis--vertical"></div>

              <!-- Corner Labels -->
              <template v-if="selectedYAxis === 'social'">
                <div class="compass-corner compass-corner--tl">Izq. / Autoritario</div>
                <div class="compass-corner compass-corner--tr">Der. / Autoritario</div>
                <div class="compass-corner compass-corner--bl">Izq. / Libertario</div>
                <div class="compass-corner compass-corner--br">Der. / Libertario</div>
              </template>
              <template v-else>
                <div class="compass-corner compass-corner--tl">Izq. / Regionalista</div>
                <div class="compass-corner compass-corner--tr">Der. / Regionalista</div>
                <div class="compass-corner compass-corner--bl">Izq. / Centralista</div>
                <div class="compass-corner compass-corner--br">Der. / Centralista</div>
              </template>

              <div
                v-for="(party, idx) in topCompassParties"
                :key="`party-${party.group}`"
                class="compass-point compass-point--party"
                :style="partyPointStyle(party)"
                @mouseenter="hoveredPoint = { ...party, label: party.group }"
                @mouseleave="hoveredPoint = null"
              >
                <span class="compass-point-index">{{ idx + 1 }}</span>
              </div>

              <div
                class="compass-point compass-point--user"
                :style="pointStyle(compassData.user)"
                @mouseenter="hoveredPoint = { ...compassData.user, label: 'Tú' }"
                @mouseleave="hoveredPoint = null"
              >
                <span class="compass-point-label compass-point-label--user">Tú</span>
              </div>

              <!-- Tooltip -->
              <div v-if="hoveredPoint" class="compass-tooltip" :style="pointStyle(hoveredPoint)">
                <div class="tooltip-content">
                  <strong>{{ hoveredPoint.label }}</strong>
                  <span v-if="selectedYAxis === 'social'">X {{ hoveredPoint.economic }}, Y {{ hoveredPoint.social }}</span>
                  <span v-else>X {{ hoveredPoint.economic }}, T {{ hoveredPoint.territorial }}</span>
                </div>
              </div>
            </div>

            <div class="compass-legend">
              <div class="compass-legend-row compass-legend-row--user">
                <span class="compass-legend-swatch compass-legend-swatch--user"></span>
                <span class="compass-legend-name">Tú</span>
                <span v-if="selectedYAxis === 'social'" class="compass-legend-coords">X {{ compassData.user.economic }}, Y {{ compassData.user.social }}</span>
                <span v-else class="compass-legend-coords">X {{ compassData.user.economic }}, T {{ compassData.user.territorial }}</span>
              </div>
              <div
                v-for="(party, idx) in topCompassParties"
                :key="`legend-${party.group}`"
                class="compass-legend-row"
              >
                <span class="compass-legend-rank">{{ idx + 1 }}.</span>
                <span class="compass-legend-swatch" :style="{ backgroundColor: getPartyColor(party.group) }"></span>
                <span class="compass-legend-name">{{ party.group }}</span>
                <span v-if="selectedYAxis === 'social'" class="compass-legend-coords">X {{ party.economic }}, Y {{ party.social }}</span>
                <span v-else class="compass-legend-coords">X {{ party.economic }}, T {{ party.territorial }}</span>
              </div>
            </div>

            <p class="compass-values">
              Eje X (económico): <strong>{{ compassData.user.economic }}</strong> |
              <template v-if="selectedYAxis === 'social'">
                Eje Y (social): <strong>{{ compassData.user.social }}</strong>
              </template>
              <template v-else>
                Eje T (territorial): <strong>{{ compassData.user.territorial }}</strong>
              </template>
            </p>
            <p class="compass-quality">
              Calibración: <strong>{{ compassData.quality.confidenceLabel }}</strong>
              ({{ compassData.quality.confidenceScore }}%).
              Cobertura de respuestas: {{ compassData.quality.responseCoverage }}%.
              <router-link to="/metodologia" class="methodology-link">¿Cómo se calcula esto?</router-link>
            </p>
            <p class="compass-quality compass-quality--uncertainty">
              Rango orientativo: ±{{ compassData.quality.axisUncertainty.economic }} en eje económico y
              ±{{ compassData.quality.axisUncertainty.social }} en eje social.
            </p>
            <p class="compass-note">
              El mapa resume patrones de voto observados; no sustituye la lectura ideológica completa de cada partido.
            </p>
          </div>

          <div class="results-list">
            <div v-for="(res, idx) in affinities" :key="res.group" class="result-row" :class="{ 'result-row--winner': idx === 0 }">
              <div class="result-group">
                <span class="result-rank">{{ idx + 1 }}</span>
                <span class="result-name">{{ res.group }}</span>
              </div>
              <div class="result-bar-wrap">
                <div class="result-bar" :style="{ width: `${res.pct}%`, backgroundColor: idx === 0 ? 'var(--color-primary)' : 'var(--color-border-hover)' }"></div>
              </div>
              <div class="result-pct">{{ res.pct }}%</div>
            </div>
          </div>
        </div>

        <div class="results-actions">
          <button class="btn btn--primary btn--lg" @click="shareResults">Compartir Link</button>
          <button class="btn btn--outline btn--lg" @click="downloadImage">📸 Bajar Imagen</button>
          <button class="btn" style="background:transparent;border:none;text-decoration:underline" @click="resetQuiz">Repetir Test</button>
        </div>

        <div class="results-disclaimer">
          <strong>Metodología de afinidad:</strong> Coincidencia exacta suma el peso completo de la pregunta; coincidencia parcial (uno se abstiene y el otro no) suma el 35% de ese peso.
          <template v-if="isAdvancedMode">
            <br />
            <strong>Metodología del mapa:</strong> Modelo calibrado con anclajes ideológicos por partido y poder de discriminación empírico por pregunta. Cada respuesta desplaza tu posición en dos ejes (económico y social), normalizados entre -100 y +100.
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.quiz-container {
  max-width: 860px;
  margin: 0 auto;
  padding: 2rem 1.25rem;
  min-height: calc(100vh - var(--nav-height));
  display: flex;
  flex-direction: column;
}

.quiz-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.quiz-intro {
  text-align: center;
  animation: fadeIn 0.4s ease;
}

.quiz-intro h1 {
  font-size: 2.5rem;
  margin-bottom: 1rem;
  color: var(--color-primary);
}

.mode-switch {
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  margin: 0.75rem auto 1.5rem;
  flex-wrap: wrap;
}

.mode-pill {
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  border-radius: 999px;
  padding: 0.65rem 1rem;
  min-width: 210px;
  cursor: pointer;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  color: var(--color-text-secondary);
  transition: border-color 0.15s, color 0.15s, box-shadow 0.15s;
}

.mode-pill span {
  font-weight: 700;
  color: inherit;
}

.mode-pill small {
  font-size: 0.78rem;
  opacity: 0.9;
}

.mode-pill:hover {
  border-color: var(--color-primary);
  color: var(--color-text);
}

.mode-pill--active {
  border-color: var(--color-primary);
  box-shadow: 0 3px 10px rgba(37, 99, 235, 0.18);
  color: var(--color-primary);
}

.lead-text {
  font-size: 1.2rem;
  color: var(--color-text-secondary);
  margin-bottom: 2rem;
  line-height: 1.6;
}

.methodology-box {
  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 1.5rem;
  text-align: left;
  margin-bottom: 2.5rem;
}

.methodology-box h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1.1rem;
}

.methodology-box ul {
  margin: 0;
  padding-left: 1.5rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.methodology-box li {
  margin-bottom: 0.5rem;
}

.quiz-start-btn {
  font-size: 1.25rem;
  padding: 1rem 3rem;
  border-radius: 50px;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
  transition: transform 0.2s, box-shadow 0.2s;
}

.quiz-start-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
}

.quiz-question-view {
  animation: slideIn 0.3s ease;
  width: 100%;
}

.quiz-progress {
  margin-bottom: 2rem;
}

.quiz-progress-text {
  font-size: 0.85rem;
  color: var(--color-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.quiz-progress-bar {
  height: 8px;
  background: var(--color-border);
  border-radius: 4px;
  overflow: hidden;
}

.quiz-progress-fill {
  height: 100%;
  background: var(--color-primary);
  transition: width 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.question-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 2.5rem 2rem;
  box-shadow: var(--shadow-md);
  text-align: center;
}

.question-topic {
  display: inline-block;
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-weight: 700;
  font-size: 0.8rem;
  padding: 0.3rem 0.8rem;
  border-radius: 50px;
  margin-bottom: 1.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.question-text {
  font-size: 1.6rem;
  line-height: 1.4;
  margin-bottom: 2rem;
  font-family: var(--font-serif);
  color: var(--color-text);
}

.question-prompt {
  font-size: 1.1rem;
  color: var(--color-text-secondary);
  font-weight: 500;
  margin-bottom: 1.5rem;
}

.vote-buttons {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: 420px;
  margin: 0 auto;
}

.btn-vote {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 1.25rem;
  font-size: 1.1rem;
  font-weight: 700;
  border-radius: var(--radius-md);
  border: 2px solid transparent;
  cursor: pointer;
  background: var(--color-surface-muted);
  color: var(--color-text);
  transition: all 0.2s;
}

.btn-vote:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.btn-vote--favor:hover { border-color: var(--color-favor); color: var(--color-favor); background: rgba(34, 197, 94, 0.05); }
.btn-vote--contra:hover { border-color: var(--color-contra); color: var(--color-contra); background: rgba(239, 68, 68, 0.05); }
.btn-vote--abstencion:hover { border-color: var(--color-abstencion); color: var(--color-abstencion); background: rgba(245, 158, 11, 0.05); }

.vote-icon {
  font-size: 1.4rem;
}

.quiz-results {
  animation: fadeIn 0.6s ease;
}

.quiz-capture-area {
  padding: 1rem;
  background: var(--color-bg);
  border-radius: var(--radius-md);
  margin-bottom: 1.5rem;
}

.results-header {
  text-align: center;
  margin-bottom: 1.75rem;
}

.results-header h2 {
  font-size: 2.2rem;
  color: var(--color-primary);
  margin-bottom: 0.5rem;
}

.results-header p {
  color: var(--color-text-secondary);
  font-size: 1.1rem;
}

.compass-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.2rem;
  margin-bottom: 1.5rem;
  box-shadow: var(--shadow-sm);
}

.compass-card h3 {
  margin: 0;
  font-size: 1.15rem;
}

.compass-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.6rem;
  gap: 1rem;
}

.axis-switcher {
  display: flex;
  background: var(--color-bg);
  padding: 2px;
  border-radius: 20px;
  border: 1px solid var(--color-border);
}

.axis-btn {
  border: none;
  background: transparent;
  padding: 0.35rem 0.85rem;
  border-radius: 18px;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.axis-btn--active {
  background: var(--color-primary);
  color: white;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.2);
}

.axis-btn:hover:not(.axis-btn--active) {
  color: var(--color-text);
  background: rgba(0, 0, 0, 0.05);
}

.compass-summary {
  margin: 0 0 1rem;
  color: var(--color-text-secondary);
}

.compass-board {
  position: relative;
  width: 100%;
  max-width: 460px;
  aspect-ratio: 1 / 1;
  margin: 0 auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background:
    linear-gradient(to right, rgba(37, 99, 235, 0.07), rgba(37, 99, 235, 0.02) 50%, rgba(239, 68, 68, 0.07));
  overflow: hidden;
}

.compass-axis {
  position: absolute;
  background: var(--color-border);
  opacity: 0.6;
}

.compass-axis--horizontal {
  left: 0;
  right: 0;
  top: 50%;
  height: 1px;
}

.compass-axis--vertical {
  top: 0;
  bottom: 0;
  left: 50%;
  width: 1px;
}

.compass-corner {
  position: absolute;
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  padding: 0.25rem 0.45rem;
  border-radius: 6px;
  box-shadow: var(--shadow-sm);
  z-index: 1;
}

.compass-corner--tl { left: 0.4rem; top: 0.4rem; }
.compass-corner--tr { right: 0.4rem; top: 0.4rem; }
.compass-corner--bl { left: 0.4rem; bottom: 0.4rem; }
.compass-corner--br { right: 0.4rem; bottom: 0.4rem; }

.compass-point {
  position: absolute;
  transform: translate(-50%, -50%);
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.compass-point--party {
  background: #64748b;
  border: 1.5px solid rgba(255, 255, 255, 0.78);
  width: 11px;
  height: 11px;
  z-index: 2;
}

.compass-point--user {
  background: var(--color-primary);
  width: 13px;
  height: 13px;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.22);
  z-index: 3;
}

.compass-point-label {
  position: absolute;
  top: -1.1rem;
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.68rem;
  font-weight: 700;
  white-space: nowrap;
  color: var(--color-text);
}

.compass-point-label--user {
  top: -1.25rem;
}

.compass-point-index {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.48rem;
  font-weight: 800;
  color: #0f172a;
}

.compass-tooltip {
  position: absolute;
  pointer-events: none;
  z-index: 100;
  min-width: 120px;
}

.tooltip-content {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  background: #1e293b;
  color: white;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.1rem;
  white-space: nowrap;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.tooltip-content::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: #1e293b;
}

.tooltip-content strong {
  font-size: 0.85rem;
  color: var(--color-primary-light, #60a5fa);
}

.tooltip-content span {
  opacity: 0.8;
  font-family: monospace;
}

.compass-legend {
  margin: 0.8rem auto 0;
  max-width: 460px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-muted);
  padding: 0.5rem 0.65rem;
}

.compass-legend-row {
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr) auto;
  gap: 0.45rem;
  align-items: center;
  font-size: 0.8rem;
  padding: 0.2rem 0;
}

.compass-legend-row + .compass-legend-row {
  border-top: 1px dashed var(--color-border);
}

.compass-legend-row--user {
  font-weight: 700;
}

.compass-legend-rank {
  color: var(--color-muted);
  font-weight: 700;
  width: 1rem;
}

.compass-legend-swatch {
  width: 0.62rem;
  height: 0.62rem;
  border-radius: 50%;
  border: 1px solid var(--color-border);
}

.compass-legend-swatch--user {
  background: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.22);
}

.compass-legend-name {
  font-weight: 600;
  color: var(--color-text);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.compass-legend-coords {
  color: var(--color-text-secondary);
  font-variant-numeric: tabular-nums;
}

.compass-values {
  margin: 0.9rem 0 0;
  text-align: center;
  color: var(--color-text-secondary);
}

.compass-quality {
  margin: 0.45rem 0 0;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 0.88rem;
}

.methodology-link {
  display: inline-block;
  margin-top: 0.35rem;
  color: var(--color-primary);
  font-weight: 600;
  text-decoration: underline;
  transition: opacity 0.2s;
  font-size: 0.85rem;
}

.methodology-link:hover {
  opacity: 0.8;
}

.compass-quality--uncertainty {
  margin-top: 0.2rem;
  font-size: 0.82rem;
}

.compass-note {
  margin: 0.4rem 0 0;
  text-align: center;
  color: var(--color-muted);
  font-size: 0.76rem;
}

.results-list {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  margin-bottom: 2.2rem;
  box-shadow: var(--shadow-sm);
}

.result-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 0;
  border-bottom: 1px solid var(--color-border);
}

.result-row:last-child {
  border-bottom: none;
}

.result-row--winner .result-name {
  font-weight: 800;
  font-size: 1.2rem;
  color: var(--color-text);
}

.result-row--winner .result-pct {
  font-weight: 800;
  font-size: 1.2rem;
  color: var(--color-primary);
}

.result-group {
  width: 150px;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.result-rank {
  font-weight: 700;
  color: var(--color-muted);
  width: 20px;
  text-align: center;
}

.result-name {
  font-weight: 600;
  color: var(--color-text-secondary);
}

.result-bar-wrap {
  flex: 1;
  height: 12px;
  background: var(--color-bg);
  border-radius: 6px;
  overflow: hidden;
}

.result-bar {
  height: 100%;
  border-radius: 6px;
  transition: width 1s cubic-bezier(0.16, 1, 0.3, 1);
}

.result-pct {
  width: 50px;
  text-align: right;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.results-actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.results-disclaimer {
  font-size: 0.85rem;
  color: var(--color-muted);
  background: var(--color-surface-muted);
  padding: 1rem;
  border-radius: var(--radius-sm);
  line-height: 1.5;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .quiz-intro h1 { font-size: 2rem; }
  .question-card { padding: 1.5rem 1rem; }
  .question-text { font-size: 1.3rem; }
  .result-group { width: 100px; }
  .result-name { font-size: 0.85rem; }
  .results-actions { flex-direction: column; }
  .mode-pill { min-width: 170px; }
  .compass-point-label { font-size: 0.62rem; }
  .compass-corner { font-size: 0.58rem; }
  .compass-legend-row {
    grid-template-columns: auto auto minmax(0, 1fr);
    row-gap: 0.15rem;
  }
  .compass-legend-coords {
    grid-column: 3;
    font-size: 0.72rem;
  }
}
</style>
