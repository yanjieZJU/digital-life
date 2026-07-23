<template>
  <div class="tool-card terminal">
    <div v-if="error" class="err">命令失败: exit_code={{ exitCode }}</div>
    <div v-else-if="exitCode !== null && exitCode !== 0" class="warn">非 0 退出: exit_code={{ exitCode }}</div>

    <div v-if="cwd" class="row meta-row">
      <span class="cursor">~</span>
      <span class="cwd">{{ cwd }}</span>
    </div>
    <div v-if="command" class="command-line">
      <span class="dollar">$</span>
      <code>{{ command }}</code>
    </div>
    <div v-if="output" class="output-block">
      <div class="output-head">{{ error ? '错误输出' : '输出' }}</div>
      <ExpandableText :text="output" :limit="200" :mono="true" />
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
const exitCode = computed(() => parsed.value.exit_code ?? null)
const output = computed(() => parsed.value.output || '')
const cwd = computed(() => parsed.value.cwd || '')
const command = computed(() => parsed.value.command || '')
</script>

<style scoped>
.tool-card.terminal {
  background: #1e1e1e;
  color: #d4d4d4;
  border-radius: 6px;
  padding: 8px 10px;
  font-family: 'Menlo', monospace;
  font-size: 11px;
}
.meta-row {
  display: flex;
  gap: 4px;
  color: #808080;
  margin-bottom: 4px;
}
.cursor { color: #67c23a; }
.cwd { color: #c0c4cc; }
.command-line {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
  align-items: baseline;
}
.dollar { color: #67c23a; }
.command-line code {
  color: #d4d4d4;
  font-family: inherit;
}
.output-block { margin-top: 4px; }
.output-head {
  color: #808080;
  font-size: 10px;
  margin-bottom: 2px;
}
.output-block pre {
  white-space: pre-wrap;
  word-break: break-word;
  background: rgba(0, 0, 0, 0.3);
  padding: 6px 8px;
  border-radius: 4px;
  color: #ccc;
  max-height: 200px;
  overflow-y: auto;
  margin: 0;
}
.err, .warn {
  background: rgba(245, 108, 108, 0.15);
  padding: 4px 6px;
  border-radius: 3px;
  color: #ff8888;
  font-size: 11px;
  margin-bottom: 4px;
}
.warn { background: rgba(230, 162, 60, 0.15); color: #ffb74d; }
</style>
