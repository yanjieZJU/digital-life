<template>
  <div class="ex-text" :class="{ mono }">
    <div v-if="!expanded" class="ex-truncated">
      <div v-if="markdown && renderedHtml" class="ex-md-block" v-html="renderedHtml"></div>
      <div v-else class="ex-plain">{{ previewText }}</div>
      <a v-if="canExpand" href="#" class="ex-toggle" @click.prevent="expanded = true">
        展开全文 ↓
      </a>
    </div>
    <div v-else class="ex-full">
      <div v-if="markdown && renderedHtml" class="ex-md-block markdown-body" v-html="renderedHtml"></div>
      <pre v-else>{{ text }}</pre>
      <a href="#" class="ex-toggle" @click.prevent="expanded = false">
        收起 ↑
      </a>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  text: { type: String, default: '' },
  limit: { type: Number, default: 200 },
  mono: { type: Boolean, default: false },
  markdown: { type: Boolean, default: false },
  renderFn: { type: Function, default: null },
  external: { type: Object, default: null },
})

const expanded = ref(false)

const previewText = computed(() => {
  const v = props.text || ''
  return v.length > props.limit ? v.slice(0, props.limit) + '…' : v
})
const canExpand = computed(() => (props.text || '').length > props.limit)
const renderedHtml = computed(() => {
  if (!props.markdown) return ''
  if (typeof props.renderFn !== 'function') return ''
  try {
    return props.renderFn(props.external || { role: 'assistant', content: props.text }) || ''
  } catch {
    return ''
  }
})
</script>

<style scoped>
.ex-text {
  font-size: 13px;
  line-height: 1.55;
  color: #303133;
  display: block;
  width: 100%;
}
.ex-text.mono {
  font-family: 'Menlo', monospace;
  font-size: 12px;
  color: #606266;
}
.ex-truncated, .ex-full {
  display: block;
  width: 100%;
}
.ex-plain {
  white-space: pre-wrap;
  word-break: break-word;
  display: block;
  color: #303133;
  background: rgba(0, 0, 0, 0.02);
  padding: 4px 6px;
  border-radius: 3px;
  border-left: 2px solid transparent;
}
.ex-md-block {
  white-space: normal;
  word-break: break-word;
  display: block;
}
.ex-md-block :deep(p) { margin: 4px 0; }
.ex-md-block :deep(h1),
.ex-md-block :deep(h2),
.ex-md-block :deep(h3) {
  font-size: 14px;
  margin: 6px 0 4px;
}
.ex-md-block :deep(ul),
.ex-md-block :deep(ol) { margin: 4px 0; padding-left: 18px; }
.ex-md-block :deep(code) {
  background: rgba(0, 0, 0, 0.04);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
}
.ex-md-block :deep(pre) {
  background: rgba(0, 0, 0, 0.04);
  padding: 6px 8px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 11px;
}
.ex-full pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Menlo', monospace;
  font-size: 12px;
  line-height: 1.5;
  display: block;
  background: rgba(0, 0, 0, 0.02);
  padding: 6px 8px;
  border-radius: 4px;
}
.ex-toggle {
  display: inline-block;
  margin-top: 4px;
  color: #409eff;
  font-size: 11px;
  text-decoration: none;
  cursor: pointer;
  user-select: none;
}
.ex-toggle:hover {
  text-decoration: underline;
}
</style>
