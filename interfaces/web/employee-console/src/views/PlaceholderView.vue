<template>
  <div>
    <section class="page-hero">
      <div>
        <h1 class="page-title">{{ title || '建设中' }}</h1>
        <p class="page-subtitle">
          {{ subtitle || '本视图将在 commit 6-7 落地' }}
        </p>
      </div>
      <div class="mono">
        <span class="brand-sub" style="color: var(--text-muted)">{{ route.path }}</span>
      </div>
    </section>

    <div class="dev-placeholder">
      <strong>// DIGITAL LIFE · NEON ON DARK</strong>
      <p>视图占位器。当前 commit 已完成：路由 + 主题 + 骨架 + layout。</p>
      <p>下一步：
        <span class="mono">commit 6 — 全局台 5 个 view（overview / instances / projects / skills / events）</span>
      </p>
      <p>
        当前 route meta:
        <span class="mono" style="color: var(--neon-cyan)">
          {{ JSON.stringify(route.meta || {}) }}
        </span>
      </p>
    </div>

    <!-- 全局卡片示例：显示实例概况，佐证 token 体系 + neon-card 都生效 -->
    <section class="page-hero">
      <div>
        <h2 class="page-title" style="font-size: 20px">实例快照（验证元数据通路）</h2>
        <p class="page-subtitle">从 <code class="mono">GET /api/system/overview</code> 实时拉取</p>
      </div>
    </section>

    <div class="neon-grid" style="grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));">
      <div
        v-for="inst in instances"
        :key="inst.id"
        class="neon-card accent-override"
        :style="{ '--instance-accent': inst.accent_color || 'var(--neon-cyan)' }"
      >
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
          <span class="status-dot" :class="inst.status"></span>
          <strong style="font-family: var(--font-display); letter-spacing: 0.08em; color: var(--instance-accent);">
            {{ inst.display_name }}
          </strong>
        </div>
        <p v-if="inst.tagline" style="color: var(--text-secondary); margin: 0 0 12px;">
          {{ inst.tagline }}
        </p>
        <div class="mono" style="font-size: 12px; color: var(--text-muted);">
          <div>energy: <span style="color: var(--neon-cyan)">{{ Math.round(inst.energy) }}%</span></div>
          <div>active: {{ inst.active }}</div>
          <div>id: {{ inst.id.slice(0, 8) }}…</div>
        </div>
      </div>
      <div v-if="loadingInstances" class="dev-placeholder">
        <strong>loading…</strong>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { systemApi } from '../api/client'

const route = useRoute()
const title = computed(() => route.meta?.title || '')
const subtitle = computed(() => route.meta?.subtitle || '')

const instances = ref([])
const loadingInstances = ref(true)

async function loadOverview() {
  const d = await systemApi.overview()
  loadingInstances.value = false
  if (!d.error) instances.value = d.instances || []
}

onMounted(loadOverview)
</script>
