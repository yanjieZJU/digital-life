<template>
  <div>
    <section class="page-hero">
      <h1 class="page-title">Skill Subscription</h1>
      <p class="page-subtitle">当前实例已订阅的能力 · 全局订阅在 /system/skills</p>
    </section>
    <div class="neon-grid" style="grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));">
      <div v-for="s in skills" :key="s.name + s.scope" class="neon-card"
           :class="s.subscribed ? '' : 'opacity-mute'">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong style="font-family: var(--font-display); color: var(--neon-cyan);">{{ s.name }}</strong>
            <el-tag size="small" effect="plain" :type="s.scope === 'shared' ? 'warning' : 'info'">
              {{ s.scope }}
            </el-tag>
          </div>
          <el-switch
            :model-value="!!s.subscribed"
            :loading="toggling.has(s.name)"
            @change="(v) => toggle(s, v)"
          />
        </div>
        <p class="brand-sub" style="color: var(--text-secondary); margin-top: 8px;">
          {{ s.description || '—' }}
        </p>
      </div>
    </div>
    <div v-if="!skills.length" class="dev-placeholder"><span class="mono">// skill catalog 为空</span></div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { systemApi } from '@/api/client'

const route = useRoute()
const iid = computed(() => route.params.iid)
const skills = ref([])
const toggling = reactive(new Set())

async function load() {
  const d = await systemApi.skills(iid.value)
  if (!d.error) skills.value = d.skills || []
}
async function toggle(s, subscribed) {
  toggling.add(s.name)
  const d = await systemApi.subscribeSkill(iid.value, s.name, subscribed)
  toggling.delete(s.name)
  if (d.error) return ElMessage.error(d.error)
  await load()
}
onMounted(load)
</script>

<style scoped>
.opacity-mute { opacity: 0.5; }
</style>
