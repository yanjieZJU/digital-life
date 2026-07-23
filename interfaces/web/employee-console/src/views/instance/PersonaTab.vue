<template>
  <div>
    <section class="page-hero">
      <h1 class="page-title">Persona · Prompts</h1>
      <p class="page-subtitle">数字生命的身份底色（LIFE_PERSONA）+ 提示词覆盖</p>
    </section>

    <div class="neon-card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <strong style="font-family: var(--font-display); color: var(--neon-pink);">LIFE_PERSONA</strong>
        <el-tag effect="plain">人设核心</el-tag>
      </div>
      <el-input v-model="personaText" type="textarea" :rows="20"
                placeholder="数字生命的性格、人格底色、行为原则…" />
      <div style="display: flex; gap: 8px; margin-top: 12px;">
        <el-button @click="reload">还原</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </div>
    </div>

    <div class="neon-card" style="margin-top: var(--space-5);">
      <strong>其它已注册提示词</strong>
      <div class="brand-sub" style="color: var(--text-muted); margin-top: 4px;">
        非人设的核心提示词（如 L4_LIFECYCLE_PROMPT）。
        完整编辑 / 列表见
        <RouterLink :to="`/legacy/employee/${iid}/`">旧版控制台 → Prompts tab</RouterLink>。
      </div>
      <div class="tag-row" style="margin-top: 12px;">
        <el-tag v-for="p in otherPrompts" :key="p.key || p.name" effect="plain" :type="p.is_default ? 'info' : 'success'">
          {{ p.key || p.name }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { ElMessage } from 'element-plus'
import { instanceApi } from '@/api/client'

const route = useRoute()
const iid = computed(() => String(route.params.iid || ''))
const personaText = ref('')
const saving = ref(false)
const prompts = ref([])

const lifePersona = computed(() =>
  prompts.value.find(p => String(p.key || p.name) === 'LIFE_PERSONA')
)
const otherPrompts = computed(() =>
  prompts.value.filter(p => String(p.key || p.name) !== 'LIFE_PERSONA')
)

async function reload() {
  const d = await instanceApi(iid.value).prompts()
  if (d.error) return
  prompts.value = d.prompts || []
  // LIFE_PERSONA 的当前生效内容（含内置默认 + override 合并结果）
  personaText.value = String(lifePersona.value?.content || '')
}

async function save() {
  saving.value = true
  try {
    const d = await instanceApi(iid.value).updatePrompt('LIFE_PERSONA', { content: personaText.value })
    if (d.error) return ElMessage.error(d.error)
    ElMessage.success('人设已更新 · 下次唤醒生效')
    await reload()
  } finally { saving.value = false }
}

onMounted(reload)
</script>
