<template>
  <div>
    <section class="page-hero">
      <h1 class="page-title">Participating Projects</h1>
      <p class="page-subtitle">我作为 position.assignee 或 manager 参与的项目</p>
    </section>
    <div class="neon-grid">
      <div v-for="p in projects" :key="p.id" class="neon-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <strong style="font-family: var(--font-display); color: var(--neon-cyan);">{{ p.name }}</strong>
          <el-tag size="small" type="success" effect="plain" v-if="p.viewer_position">
            {{ p.viewer_position }}
          </el-tag>
        </div>
        <p class="brand-sub" style="color: var(--text-secondary); margin: 6px 0;">{{ p.description || '—' }}</p>
        <div class="tag-row">
          <el-tag size="small" effect="plain" v-for="pos in p.positions" :key="pos.id">{{ pos.name }}</el-tag>
        </div>
      </div>
      <div v-if="!projects.length" class="dev-placeholder"><span class="mono">// 未参与任何项目</span></div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { systemApi } from '@/api/client'

const route = useRoute()
const iid = computed(() => route.params.iid)
const projects = ref([])

async function load() {
  const d = await systemApi.projects(iid.value)
  if (!d.error) projects.value = d.projects || []
}
onMounted(load)
</script>
