<template>
  <div>
    <section class="page-hero">
      <div>
        <h1 class="page-title">Skill Market</h1>
        <p class="page-subtitle">全局可用能力 · 选实例 → 订阅它</p>
      </div>
      <div style="display: flex; align-items: center; gap: 12px;">
        <span class="brand-sub">为实例订阅：</span>
        <el-select v-model="selectedInstance" placeholder="选择实例…" filterable style="width: 180px;">
          <el-option v-for="i in instances" :key="i.id" :label="i.display_name" :value="i.id" />
        </el-select>
        <el-button @click="loadAll"><el-icon><Refresh /></el-icon></el-button>
      </div>
    </section>

    <div class="neon-grid" style="grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));">
      <div
        v-for="skill in skills"
        :key="skill.name + '-' + skill.scope"
        class="neon-card"
        :class="skill.scope === 'shared' ? 'glow-pink' : ''"
      >
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <strong style="font-family: var(--font-display); color: var(--neon-cyan);">
                {{ skill.name }}
              </strong>
              <el-tag size="small" :type="skill.scope === 'shared' ? 'warning' : 'info'" effect="plain">
                {{ skill.scope }}
              </el-tag>
            </div>
            <p class="brand-sub" style="color: var(--text-secondary); margin-top: 6px; min-height: 32px;">
              {{ skill.description || '—' }}
            </p>
          </div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
          <span class="brand-sub mono" style="color: var(--text-muted);">
            {{ skill.path }}
          </span>
          <el-switch
            v-if="selectedInstance"
            :model-value="!!skill.subscribed"
            :loading="toggling.has(skill.name)"
            active-text="订阅"
            inactive-text=""
            @change="(v) => toggleSubscribe(skill, v)"
          />
          <span v-else class="brand-sub" style="color: var(--text-muted);">选实例…</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { systemApi } from '@/api/client'

const instances = ref([])
const skills = ref([])
const selectedInstance = ref('')
const toggling = reactive(new Set())

async function loadInstances() {
  const d = await systemApi.instances()
  if (d.error) return
  instances.value = d.instances || []
  if (!selectedInstance.value && instances.value.length) {
    selectedInstance.value = instances.value[0].id
  }
}

async function loadSkills() {
  const d = await systemApi.skills(selectedInstance.value)
  if (d.error) return
  skills.value = d.skills || []
}

async function loadAll() {
  await loadInstances()
  await loadSkills()
}

async function toggleSubscribe(skill, subscribed) {
  if (!selectedInstance.value) return
  toggling.add(skill.name)
  const d = await systemApi.subscribeSkill(selectedInstance.value, skill.name, subscribed)
  toggling.delete(skill.name)
  if (d.error) {
    ElMessage.error(d.error)
    return
  }
  ElMessage.success(`${skill.name} ${subscribed ? '已订阅' : '已退订'} · ${d.skills.length} 项`)
  await loadSkills()
}

watch(selectedInstance, loadSkills)
onMounted(loadAll)
</script>
