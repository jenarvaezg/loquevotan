<script setup>
const props = defineProps({
  type: {
    type: String,
    default: 'empty', // loading | empty | error
  },
  title: {
    type: String,
    default: '',
  },
  message: {
    type: String,
    default: '',
  },
  icon: {
    type: String,
    default: '',
  },
  actionLabel: {
    type: String,
    default: '',
  },
  actionTo: {
    type: String,
    default: '',
  },
  padded: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits(['action']);

function resolvedIcon() {
  if (props.icon) return props.icon;
  if (props.type === 'error') return '&#9888;';
  if (props.type === 'loading') return '';
  return '&#128270;';
}
</script>

<template>
  <div v-if="type === 'loading'" class="loading-wrap" :style="padded ? '' : 'padding:2rem'">
    <div class="loading-spinner"></div>
    <p v-if="message" class="loading-text">{{ message }}</p>
  </div>

  <div v-else class="empty-state">
    <div v-if="resolvedIcon()" class="empty-state-icon" v-html="resolvedIcon()"></div>
    <h2 v-if="title" style="margin-bottom:0.5rem">{{ title }}</h2>
    <p v-if="message" class="empty-state-text">{{ message }}</p>

    <router-link v-if="actionLabel && actionTo" :to="actionTo" class="btn btn--primary mt-2">
      {{ actionLabel }}
    </router-link>
    <button v-else-if="actionLabel" class="btn btn--primary mt-2" @click="emit('action')">
      {{ actionLabel }}
    </button>
  </div>
</template>
