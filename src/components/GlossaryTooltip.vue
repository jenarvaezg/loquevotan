<script setup>
import { computed } from 'vue'

const props = defineProps({
  term: {
    type: String,
    required: true
  }
})

const GLOSSARY = {
  'Votación final': 'La votación definitiva sobre el texto completo de una ley o propuesta tras debatir todas sus partes.',
  'Enmienda a la totalidad': 'Propuesta de un grupo para rechazar el texto completo enviado por el Gobierno y devolverlo o sustituirlo por otro.',
  'Enmienda transaccional': 'Acuerdo de última hora entre varios partidos para redactar un texto intermedio que todos puedan aceptar.',
  'Voto particular': 'Propuesta que un grupo mantiene viva para ser votada en el Pleno a pesar de haber sido rechazada previamente en comisión.',
  'Enmienda': 'Propuesta de modificación de un texto legal (añadir, quitar o cambiar palabras).',
  'Votación separada': 'Cuando se pide votar un artículo o punto concreto de forma independiente al resto del paquete.',
  'Dictamen': 'El texto final de una ley tal como queda después de haber sido discutido y modificado en una comisión parlamentaria.',
  'Propuesta de resolución': 'Propuesta que no tiene rango de ley pero que insta al Gobierno a realizar una acción concreta.',
  'Otro': 'Votaciones sobre procedimientos internos, calendarios o asuntos administrativos.',
  'final': 'La votación definitiva sobre el texto completo de una ley o propuesta tras debatir todas sus partes.',
  'totalidad': 'Propuesta de un grupo para rechazar el texto completo enviado por el Gobierno y devolverlo o sustituirlo por otro.',
  'transaccional': 'Acuerdo de última hora entre varios partidos para redactar un texto intermedio que todos puedan aceptar.',
  'particular': 'Propuesta que un grupo mantiene viva para ser votada en el Pleno a pesar de haber sido rechazada previamente en comisión.',
  'enmienda': 'Propuesta de modificación de un texto legal (añadir, quitar o cambiar palabras).',
  'separada': 'Cuando se pide votar un artículo o punto concreto de forma independiente al resto del paquete.',
  'dictamen': 'El texto final de una ley tal como queda después de haber sido discutido y modificado en una comisión parlamentaria.',
  'propuesta': 'Propuesta que no tiene rango de ley pero que insta al Gobierno a realizar una acción concreta.',
  'otro': 'Votaciones sobre procedimientos internos, calendarios o asuntos administrativos.'
}

const definition = computed(() => GLOSSARY[props.term] || GLOSSARY[props.term.toLowerCase()] || null)
</script>

<template>
  <span v-if="definition" class="glossary-term" :title="definition">
    <slot />
  </span>
  <slot v-else />
</template>

<style scoped>
.glossary-term {
  cursor: help;
  text-decoration: underline dashed var(--color-muted);
  text-underline-offset: 3px;
}

.glossary-term:hover {
  color: var(--color-primary);
  text-decoration-color: var(--color-primary);
}
</style>
