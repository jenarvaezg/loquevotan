<script setup>
import { ref, computed } from 'vue'
import { normalize, fmt } from '../utils'

const props = defineProps({
  tags: Array,
  modelValue: Array,
})

const emit = defineEmits(['update:modelValue'])

const query = ref('')
const open = ref(false)
const activeIdx = ref(-1)

const filtered = computed(() => {
  const q = normalize(query.value.trim())
  if (!q) return props.tags.slice(0, 20)
  return props.tags.filter(t => normalize(t).includes(q)).slice(0, 20)
})

function select(tag) {
  if (!props.modelValue.includes(tag)) {
    emit('update:modelValue', [...props.modelValue, tag])
  }
  query.value = ''
  open.value = false
  activeIdx.value = -1
}

function remove(tag) {
  emit('update:modelValue', props.modelValue.filter(t => t !== tag))
}

function onKeydown(e) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIdx.value = Math.min(activeIdx.value + 1, filtered.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIdx.value = Math.max(activeIdx.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (activeIdx.value >= 0 && filtered.value[activeIdx.value]) {
      select(filtered.value[activeIdx.value])
    } else if (query.value.trim()) {
      select(query.value.trim().replace(/ /g, '_'))
    }
  } else if (e.key === 'Escape') {
    open.value = false
  }
}

function onFocus() {
  open.value = true
  activeIdx.value = -1
}

function onBlur() {
  setTimeout(() => { open.value = false }, 150)
}
</script>

<template>
  <div class="tag-select">
    <div class="tag-select-input-wrap">
      <input
        :value="query"
        type="search"
        class="filter-input"
        placeholder="Buscar etiqueta..."
        @input="query = $event.target.value; open = true; activeIdx = -1"
        @focus="onFocus"
        @blur="onBlur"
        @keydown="onKeydown"
      >
      <div v-if="open && filtered.length" class="tag-select-dropdown">
        <button
          v-for="(tag, i) in filtered"
          :key="tag"
          type="button"
          class="tag-select-option"
          :class="{ 'tag-select-option--active': i === activeIdx, 'tag-select-option--selected': modelValue.includes(tag) }"
          @mousedown.prevent="select(tag)"
        >
          {{ fmt(tag) }}
        </button>
      </div>
    </div>
    <div v-if="modelValue.length" class="active-tags">
      <span v-for="tag in modelValue" :key="tag" class="tag-active">
        {{ fmt(tag) }}
        <button type="button" class="tag-remove" @click="remove(tag)">&times;</button>
      </span>
    </div>
  </div>
</template>
