<template>
  <div class="tool-card express">
    <div v-if="error || !parsed.sent" class="err">
      发送失败: {{ error || parsed.error || '（未知原因，sent=false）' }}
    </div>
    <div v-else>
      <div class="row">
        <span class="lbl">渠道</span>
        <span class="val">{{ parsed.channel || '—' }}</span>
        <span v-if="parsed.chat_id" class="hint">@ {{ parsed.chat_id.slice(0, 24) }}</span>
      </div>
      <div class="row">
        <span class="lbl">发送内容</span>
      </div>
      <div class="msg-text">{{ parsed.text || content }}</div>
    </div>
    <details v-if="!parsed.sent" class="err-detail">
      <summary>查看模型尝试发送的内容</summary>
      <div class="row"><span class="lbl">渠道</span><span class="val dim">{{ parsed.channel || '—' }}</span></div>
      <div class="msg-text muted">{{ parsed.text || content }}</div>
    </details>
  </div>
</template>

<script setup>
import { computed } from 'vue'

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
</script>

<style scoped>
.tool-card.express {
  background: linear-gradient(180deg, #f0f9eb, #fff);
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 12px;
}
.row {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 4px;
  color: #606266;
}
.lbl {
  font-size: 10px;
  color: #909399;
  letter-spacing: 0.5px;
  background: rgba(103, 194, 58, 0.1);
  padding: 1px 5px;
  border-radius: 3px;
}
.val { color: #67c23a; font-family: 'Menlo', monospace; font-size: 11px; }
.hint { font-size: 10px; color: #c0c4cc; }
.msg-text {
  white-space: pre-wrap;
  word-break: break-word;
  color: #1f2329;
  padding: 6px 8px;
  background: rgba(103, 194, 58, 0.06);
  border-radius: 4px;
  line-height: 1.6;
  margin-top: 2px;
}
.err {
  color: #f56c6c;
  font-size: 12px;
  background: rgba(245, 108, 108, 0.08);
  padding: 6px 8px;
  border-radius: 4px;
}
.err-detail {
  margin-top: 6px;
  font-size: 11px;
  color: #909399;
}
.err-detail summary {
  cursor: pointer;
  color: #c0c4cc;
}
.muted { color: #909399; opacity: 0.6; }
.val.dim { color: #c0c4cc; }
</style>
