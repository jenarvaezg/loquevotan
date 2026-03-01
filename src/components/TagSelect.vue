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

<style scoped>
.tag-select { position: relative; }
.tag-select-input-wrap { position: relative; }

.tag-select-dropdown {
  position: absolute;
  top: calc(100% + 2px);
  left: 0;
  right: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-lg);
  max-height: 240px;
  overflow-y: auto;
  z-index: 50;
}

.tag-select-option {
  display: block;
  width: 100%;
  padding: 0.5rem 0.75rem;
  text-align: left;
  font-size: 0.85rem;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-text);
  transition: background 0.1s;
}

.tag-select-option:hover,
.tag-select-option--active {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.tag-select-option--selected {
  font-weight: 600;
  color: var(--color-primary);
}

.active-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-top: 0.4rem;
  margin-bottom: 0.2rem;
}

.tag-active {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  padding: 0.25em 0.6em;
  border-radius: 50px;
  font-size: 0.8rem;
  font-weight: 600;
  background: var(--color-primary);
  color: #fff;
}

.tag-remove {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 1rem;
  padding: 0 0.15em;
  margin: 0;
  line-height: 1;
  opacity: 0.7;
}

.tag-remove:hover { opacity: 1; }
</style>
