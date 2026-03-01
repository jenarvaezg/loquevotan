<script setup>
import { onMounted } from 'vue'

onMounted(() => {
  document.title = 'Metodología | Lo Que Votan'
})
</script>

<template>
  <section class="methodology-page">
    <div class="container container--narrow" style="padding-top: 2rem; padding-bottom: 4rem;">
      <h1 class="mb-4">Metodología y Transparencia</h1>
      
      <div class="card methodology-card mb-4">
        <p class="lead">
          <strong>Lo Que Votan</strong> es un proyecto independiente de datos abiertos que busca acercar la actividad parlamentaria a la ciudadanía. Para garantizar la neutralidad y el rigor, explicamos aquí cómo procesamos la información.
        </p>
      </div>

      <div class="methodology-section">
        <h2>1. Origen de los Datos</h2>
        <p>
          Toda la información proviene exclusivamente de fuentes oficiales públicas:
        </p>
        <ul>
          <li><strong>Congreso de los Diputados:</strong> Archivos de datos abiertos (Open Data) y Diarios de Sesiones.</li>
          <li><strong>Parlamento de Andalucía:</strong> Boletín Oficial (BOPA) y sistema de votos nominales.</li>
          <li><strong>Cortes de Castilla y León:</strong> Diario de Sesiones y registros de votaciones nominales.</li>
        </ul>
        <p>
          Utilizamos algoritmos de <em>scraping</em> para extraer los votos individuales y modelos de Inteligencia Artificial (Gemini 2.0) para "traducir" los títulos técnicos de los expedientes a un lenguaje que cualquier ciudadano pueda entender, sin alterar el sentido de la votación.
        </p>
      </div>

      <div class="methodology-section">
        <h2>2. Cálculo de Afinidad</h2>
        <p>
          La afinidad entre un usuario y un representante (o entre dos partidos) se calcula comparando sus votos en los mismos asuntos:
        </p>
        <ul>
          <li><strong>Coincidencia total:</strong> Ambos votan lo mismo (ej. ambos "Sí"). Suma 1 punto.</li>
          <li><strong>Coincidencia parcial:</strong> Uno vota "Sí" o "No" y el otro se abstiene. Suma 0.35 puntos (penaliza la falta de posicionamiento claro).</li>
          <li><strong>Discrepancia:</strong> Uno vota "Sí" y el otro "No". Suma 0 puntos.</li>
        </ul>
        <p>
          El porcentaje final es la suma de puntos obtenida dividida entre el total de votaciones en las que ambos han participado.
        </p>
      </div>

      <div class="methodology-section">
        <h2>3. El Mapa Político (Compass)</h2>
        <p>
          A diferencia de otros tests políticos que se basan en "lo que los partidos dicen que piensan", nuestro mapa se basa en <strong>lo que los partidos votan realmente</strong>.
        </p>
        <h3>Ejes:</h3>
        <ul>
          <li><strong>Eje Económico (X):</strong> Izquierda (mayor intervención/gasto público) vs Derecha (menor presión fiscal/libre mercado).</li>
          <li><strong>Eje Social (Y):</strong> Progresista/Libertario (derechos civiles, libertades individuales) vs Conservador/Autoritario (orden, valores tradicionales).</li>
          <li><strong>Eje Territorial (T):</strong> Regionalista/Soberanista (más autonomía local) vs Centralista (estado unitario fuerte).</li>
        </ul>
        <h3>Cálculo matemático:</h3>
        <p>
          Utilizamos el <strong>Coeficiente de Correlación de Pearson</strong>. El sistema analiza la relación entre los votos de cada partido en una sesión y sus "anclajes ideológicos" conocidos. 
          Si un partido vota sistemáticamente a favor de leyes de un bloque ideológico, esa votación adquiere un "peso" automático en ese eje. La posición del usuario se calcula proyectando sus respuestas sobre este modelo calibrado empíricamente.
        </p>
      </div>

      <div class="methodology-section">
        <h2>4. Definición de "Rebeldía"</h2>
        <p>
          En este proyecto, un diputado se considera <strong>Rebelde</strong> cuando su voto individual (Sí, No, Abstención) difiere de la mayoría absoluta de los votos emitidos por los miembros de su propio grupo parlamentario en esa misma votación. No se cuenta como rebeldía la ausencia o la no emisión de voto.
        </p>
      </div>

      <div class="methodology-section">
        <h2>5. Limitaciones del Modelo</h2>
        <p>
          Ningún modelo matemático puede capturar la complejidad total de la política. Algunas limitaciones son:
        </p>
        <ul>
          <li><strong>Votos tácticos:</strong> A veces los partidos votan en contra de algo que apoyan por estrategia parlamentaria o por errores en la redacción de enmiendas.</li>
          <li><strong>Unanimidad:</strong> Las votaciones donde todos los partidos coinciden no sirven para diferenciar posiciones en el mapa y tienen un peso menor en el cálculo.</li>
          <li><strong>Categorización por IA:</strong> Aunque supervisada, la categorización de temas por IA puede cometer errores en expedientes extremadamente técnicos o ambiguos.</li>
        </ul>
      </div>

      <div class="methodology-footer text-center mt-5">
        <p class="text-muted">Última revisión de metodología: 1 de marzo de 2026</p>
        <router-link to="/" class="btn btn--outline mt-3">Volver al inicio</router-link>
      </div>
    </div>
  </section>
</template>

<style scoped>
.methodology-page {
  line-height: 1.6;
}

.methodology-section {
  margin-bottom: 3rem;
}

.methodology-section h2 {
  font-size: 1.5rem;
  color: var(--color-primary);
  margin-bottom: 1rem;
  border-bottom: 2px solid var(--color-primary-light);
  padding-bottom: 0.5rem;
  display: inline-block;
}

.methodology-section h3 {
  font-size: 1.1rem;
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
}

.methodology-card {
  padding: 2rem;
  background: var(--color-primary-lighter);
  border-left: 4px solid var(--color-primary);
}

.lead {
  font-size: 1.1rem;
  color: var(--color-text);
}

ul {
  padding-left: 1.5rem;
  margin-bottom: 1rem;
}

li {
  margin-bottom: 0.5rem;
}

.container--narrow {
  max-width: 800px;
}

@media (max-width: 768px) {
  .methodology-card {
    padding: 1.25rem;
  }
}
</style>
