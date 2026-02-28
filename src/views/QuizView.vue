<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useData } from '../composables/useData'

const { currentScopeId } = useData()
const router = useRouter()

const quizData = ref(null)
const loading = ref(true)
const error = ref(null)

const currentStep = ref(-1) // -1: Intro, 0-N: Questions, N+1: Results
const answers = ref({}) // qId -> 'si' | 'no' | 'abstencion'

const isResults = computed(() => quizData.value && currentStep.value >= quizData.value.questions.length)
const currentQuestion = computed(() => {
  if (!quizData.value || currentStep.value < 0 || isResults.value) return null
  return quizData.value.questions[currentStep.value]
})

async function loadQuiz() {
  loading.value = true
  error.value = null
  try {
    const scopePath = currentScopeId.value === "nacional" ? "" : `${currentScopeId.value}/`
    const url = `${import.meta.env.BASE_URL}data/${scopePath}quiz.json`
    const resp = await fetch(url)
    if (!resp.ok) throw new Error('Quiz not available for this scope')
    quizData.value = await resp.json()
  } catch (err) {
    error.value = "No hay un test de afinidad disponible para este parlamento en este momento."
  } finally {
    loading.value = false
  }
}

watch(currentScopeId, () => {
  currentStep.value = -1
  answers.value = {}
  loadQuiz()
}, { immediate: true })

function startQuiz() {
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
  if (!quizData.value || !isResults.value) return []
  
  const scores = {}
  quizData.value.groups.forEach(g => { scores[g] = 0 })
  
  const total = quizData.value.questions.length
  
  quizData.value.questions.forEach(q => {
    const userVote = answers.value[q.id]
    quizData.value.groups.forEach(g => {
      const groupVote = q.votes[g]
      if (groupVote === userVote) {
        scores[g] += 1
      } else if ((groupVote === 'abstencion' || userVote === 'abstencion') && groupVote !== userVote) {
        scores[g] += 0.5 // partial match for abstention differences
      }
    })
  })
  
  return Object.entries(scores)
    .map(([group, score]) => ({
      group,
      pct: Math.round((score / total) * 100)
    }))
    .sort((a, b) => b.pct - a.pct)
})

function finishQuiz() {
  // Try to push to dataLayer for Google Analytics if available
  try {
    const topMatch = affinities.value[0]
    const eventData = {
      event: 'quiz_completed',
      quiz_scope: currentScopeId.value,
      top_match_group: topMatch ? topMatch.group : 'none',
      top_match_pct: topMatch ? topMatch.pct : 0
    }
    if (window.dataLayer) {
      window.dataLayer.push(eventData)
    } else {
      console.log("[Analytics Dummy] Quiz completed:", eventData)
    }
  } catch (e) {
    // ignore
  }
}

function shareResults() {
  const top = affinities.value[0]
  const text = `He hecho el test ciego de votaciones de @LoQueVotan y mi mayor afinidad es con ${top.group} (${top.pct}%). ¡Descubre la tuya!`
  const url = window.location.href
  
  if (navigator.share) {
    navigator.share({ title: 'Lo Que Votan - Test de Afinidad', text, url }).catch(() => {})
  } else {
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`, '_blank')
  }
}

function resetQuiz() {
  answers.value = {}
  currentStep.value = -1
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

    <div v-else-if="quizData" class="quiz-content">
      
      <!-- INTRO -->
      <div v-if="currentStep === -1" class="quiz-intro">
        <h1>{{ quizData.title }}</h1>
        <p class="lead-text">{{ quizData.description }}</p>
        
        <div class="methodology-box">
          <h3>¿Cómo funciona?</h3>
          <ul>
            <li>Te mostraremos <strong>{{ quizData.questions.length }} votaciones reales</strong> que tuvieron lugar en el parlamento.</li>
            <li>No te diremos quién propuso la ley para evitar sesgos.</li>
            <li>Al finalizar, calcularemos matemáticamente tu porcentaje de afinidad con los votos reales de cada partido.</li>
          </ul>
        </div>

        <button class="btn btn--primary btn--lg quiz-start-btn" @click="startQuiz">
          Empezar el Test &rarr;
        </button>
      </div>

      <!-- QUESTIONS -->
      <div v-else-if="!isResults" class="quiz-question-view">
        <div class="quiz-progress">
          <div class="quiz-progress-text">Pregunta {{ currentStep + 1 }} de {{ quizData.questions.length }}</div>
          <div class="quiz-progress-bar">
            <div class="quiz-progress-fill" :style="{ width: `${(currentStep / quizData.questions.length) * 100}%` }"></div>
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

      <!-- RESULTS -->
      <div v-else class="quiz-results">
        <div class="results-header">
          <h2>Tu Afinidad Política</h2>
          <p>Basado en {{ quizData.questions.length }} votaciones reales de esta legislatura.</p>
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

        <div class="results-actions">
          <button class="btn btn--primary btn--lg" @click="shareResults">
            Compartir Resultado
          </button>
          <button class="btn btn--outline" @click="resetQuiz">
            Repetir Test
          </button>
        </div>

        <div class="results-disclaimer">
          <strong>Metodología:</strong> Estos resultados son puramente matemáticos basados en el sentido de voto (A favor, En contra, Abstención). Una coincidencia exacta suma 1 punto, una coincidencia parcial (uno se abstiene y el otro no) suma 0.5 puntos.
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.quiz-container {
  max-width: 700px;
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

/* Intro */
.quiz-intro {
  text-align: center;
  animation: fadeIn 0.4s ease;
}

.quiz-intro h1 {
  font-size: 2.5rem;
  margin-bottom: 1rem;
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

/* Question View */
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
  max-width: 400px;
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

/* Results */
.quiz-results {
  animation: fadeIn 0.6s ease;
}

.results-header {
  text-align: center;
  margin-bottom: 2.5rem;
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

.results-list {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  margin-bottom: 2.5rem;
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
  width: 120px;
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
  .result-group { width: 90px; }
  .result-name { font-size: 0.85rem; }
  .results-actions { flex-direction: column; }
}
</style>
