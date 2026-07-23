<template>
  <div class="content-actions-shell">
    <div class="content-actions-bar">
      <el-tooltip content="复制内容" placement="top">
        <el-button
          :icon="CopyDocument"
          circle
          size="small"
          :disabled="!resolvedCopyText"
          @click.stop="copyContent"
        />
      </el-tooltip>
      <el-tooltip content="全屏查看" placement="top">
        <el-button
          :icon="FullScreen"
          circle
          size="small"
          :disabled="!hasFullscreenContent"
          @click.stop="fullscreenOpen = true"
        />
      </el-tooltip>
    </div>

    <slot />

    <el-dialog
      v-model="fullscreenOpen"
      :title="fullscreenTitle || '内容查看'"
      width="82vw"
      class="content-actions-dialog"
      append-to-body
    >
      <div
        v-if="fullscreenHtml"
        class="content-actions-fullscreen markdown-body"
        v-html="fullscreenHtml"
      />
      <pre v-else class="content-actions-fullscreen-pre">{{ resolvedFullscreenText }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { CopyDocument, FullScreen } from '@element-plus/icons-vue'

const props = defineProps({
  copyText: [String, Number],
  fullscreenText: [String, Number],
  fullscreenHtml: String,
  fullscreenTitle: String,
})

const fullscreenOpen = ref(false)

const resolvedCopyText = computed(() => {
  return props.copyText === null || props.copyText === undefined ? '' : String(props.copyText)
})
const resolvedFullscreenText = computed(() => {
  if (props.fullscreenText !== null && props.fullscreenText !== undefined) return String(props.fullscreenText)
  return resolvedCopyText.value
})
const hasFullscreenContent = computed(() => Boolean(props.fullscreenHtml || resolvedFullscreenText.value))

async function copyContent() {
  if (!resolvedCopyText.value) return
  try {
    await navigator.clipboard.writeText(resolvedCopyText.value)
  } catch (_) {
    const textarea = document.createElement('textarea')
    textarea.value = resolvedCopyText.value
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    textarea.remove()
  }
}
</script>

<style scoped>
.content-actions-shell {
  position: relative;
}

.content-actions-shell:hover .content-actions-bar,
.content-actions-shell:focus-within .content-actions-bar {
  opacity: 1;
  transform: translateY(0);
}

.content-actions-bar {
  display: flex;
  gap: 6px;
  opacity: 0;
  position: absolute;
  right: 8px;
  top: 8px;
  transform: translateY(-2px);
  transition: opacity 0.16s ease, transform 0.16s ease;
  z-index: 5;
}

.content-actions-fullscreen {
  max-height: 72vh;
  overflow: auto;
  padding: 4px;
}

.content-actions-fullscreen-pre {
  background: #282c34;
  border-radius: 8px;
  color: #abb2bf;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.65;
  margin: 0;
  max-height: 72vh;
  overflow: auto;
  padding: 16px;
  white-space: pre-wrap;
}
</style>
