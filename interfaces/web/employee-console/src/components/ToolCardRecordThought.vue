<template>
  <div class="tool-card thought">
    <div class="icon-row">
      <span class="thought-icon">💭</span>
      <span class="thought-label">{{ natureLabel }}</span>
    </div>
    <div class="thought-text">
      <ExpandableText :text="parsed.content || content" :limit="200" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ExpandableText from './ExpandableText.vue'

const props = defineProps({
  content: { type: String, default: '' },
  error: { type: String, default: '' },
})

const parsed = computed(() => {
  try {
    return JSON.parse(props.content || '{}')
  } catch {
    return {}
  }
})

const natureLabel = computed(() => {
  const n = parsed.value.nature || ''
  const map = {
    reflection: '反思',
    observation: '观察',
    lesson: '教训',
    insight: '洞察',
    question: '疑问',
  }
  return map[n] || (n ? n : '思绪')
})
</script>

<style scoped>
.tool-card.thought {
  background: linear-gradient(180deg, #fcf7ff, #fff);
  border: 1px solid rgba(147, 112, 219, 0.15);
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 12px;
}
.icon-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.thought-icon { font-size: 14px; }
.thought-label {
  color: #9370db;
  font-size: 11px;
  background: rgba(147, 112, 219, 0.1);
  padding: 1px 6px;
  border-radius: 3px;
}
.thought-text {
  font-style: italic;
  color: #5e4b8b;
  line-height: 1.6;
}
</style>
