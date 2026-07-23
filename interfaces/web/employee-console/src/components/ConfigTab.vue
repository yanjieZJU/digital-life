<template>
  <div class="config-center">
    <section class="config-hero">
      <div>
        <span class="section-kicker">Configuration Center</span>
        <h2>数字员工运行参数</h2>
        <p>可见字段都是实际被代码读取并生效的项。敏感字段（API Key）以密文显示，留空保存即保留当前值。</p>
      </div>
      <div class="config-hero-actions">
        <el-button :icon="Refresh" @click="resetDraft">还原</el-button>
        <el-button type="warning" plain :icon="MagicStick" @click="recoverEnergyNow">
          手动恢复精力
        </el-button>
        <el-button type="primary" :icon="Check" :disabled="!dirtyCount" @click="submitChanges">
          保存 {{ dirtyCount || '' }}
        </el-button>
      </div>
    </section>

    <section class="config-summary">
      <div class="config-summary-item">
        <span>配置文件</span>
        <strong>{{ shortPath(paths.config_path) }}</strong>
      </div>
      <div class="config-summary-item">
        <span>密钥文件</span>
        <strong>{{ shortPath(paths.env_path) }}</strong>
      </div>
      <div class="config-summary-item">
        <span>可编辑项</span>
        <strong>{{ editableCount }}</strong>
      </div>
      <div class="config-summary-item">
        <span>待保存</span>
        <strong>{{ dirtyCount }}</strong>
      </div>
    </section>

    <el-tabs v-model="activeSection" class="config-tabs">
      <el-tab-pane
        v-for="section in sections"
        :key="section.key"
        :label="section.label"
        :name="section.key"
      />
    </el-tabs>

    <section v-if="currentSection" class="config-section-card">
      <div class="config-section-head">
        <div>
          <h3>{{ currentSection.label }}</h3>
          <p>{{ currentSection.description }}</p>
        </div>
        <el-tag effect="plain">{{ editableFields(currentSection).length }} editable</el-tag>
      </div>

      <div class="config-field-list">
        <div
          v-for="field in currentSection.fields"
          :key="field.key"
          class="config-field-row"
          :class="{ readonly: field.readonly }"
        >
          <div class="config-field-meta">
            <div class="config-field-title">
              <span>{{ field.label }}</span>
              <el-tag v-if="field.secret" size="small" effect="plain" type="warning">secret</el-tag>
              <el-tag v-if="field.restart_required" size="small" effect="plain">restart</el-tag>
              <el-tag v-if="field.readonly" size="small" effect="plain" type="info">read only</el-tag>
            </div>
            <p v-if="field.description">{{ field.description }}</p>
            <div class="config-field-origin">
              <span>{{ field.key }}</span>
              <span>{{ field.origin || field.source }}</span>
              <span :class="{ configured: field.configured }">{{ field.configured ? '已配置' : '未配置' }}</span>
            </div>
          </div>

          <div class="config-field-control">
            <template v-if="field.readonly">
              <code>{{ displayValue(field.value) }}</code>
            </template>
            <el-switch
              v-else-if="field.type === 'boolean'"
              v-model="draft[field.key]"
            />
            <el-select
              v-else-if="field.type === 'array'"
              v-model="draft[field.key]"
              multiple
              filterable
              allow-create
              default-first-option
              :reserve-keyword="false"
              placeholder="回车添加条目"
              class="config-array-control"
            >
              <el-option
                v-for="item in draft[field.key] || []"
                :key="item"
                :label="item"
                :value="item"
              />
            </el-select>
            <el-input-number
              v-else-if="field.type === 'number'"
              v-model="draft[field.key]"
              :step="numberStep(field)"
              controls-position="right"
            />
            <el-select
              v-else-if="field.options?.length"
              v-model="draft[field.key]"
              filterable
            >
              <el-option
                v-for="option in field.options"
                :key="option"
                :label="option"
                :value="option"
              />
            </el-select>
            <el-input
              v-else
              v-model="draft[field.key]"
              :type="field.secret ? 'password' : 'text'"
              :placeholder="field.secret && field.configured ? '留空表示保留当前密钥' : ''"
              :show-password="field.secret"
            />
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Check, MagicStick, Refresh } from '@element-plus/icons-vue'

const props = defineProps({
  configCenter: Object,
  saveConfig: Function,
  recoverEnergy: Function,
})

const activeSection = ref('employee')
const draft = ref({})
const baseline = ref({})
const ENERGY_RECOVERY_AMOUNT = 30

const sections = computed(() => props.configCenter?.sections || [])
const paths = computed(() => props.configCenter?.paths || {})
const currentSection = computed(() => {
  return sections.value.find(section => section.key === activeSection.value) || sections.value[0]
})
const editableCount = computed(() => {
  return sections.value.reduce((count, section) => count + editableFields(section).length, 0)
})
const dirtyCount = computed(() => Object.keys(changes.value).length)
const changes = computed(() => {
  const changed = {}
  for (const section of sections.value) {
    for (const field of editableFields(section)) {
      if (field.secret && draft.value[field.key] === '') continue
      if (!sameValue(draft.value[field.key], baseline.value[field.key])) {
        changed[field.key] = draft.value[field.key]
      }
    }
  }
  return changed
})

watch(
  sections,
  next => {
    const nextDraft = {}
    for (const section of next) {
      for (const field of section.fields || []) {
        if (field.readonly) continue
        nextDraft[field.key] = normalizeFieldValue(field)
      }
    }
    draft.value = nextDraft
    baseline.value = { ...nextDraft }
    if (!next.some(section => section.key === activeSection.value)) {
      activeSection.value = next[0]?.key || 'model'
    }
  },
  { immediate: true }
)

function editableFields(section) {
  return (section?.fields || []).filter(field => !field.readonly)
}

function normalizeFieldValue(field) {
  if (field.secret) return ''
  if (field.type === 'array') {
    if (Array.isArray(field.value)) return field.value.filter(v => v != null && String(v).trim() !== '')
    return []
  }
  if (field.type === 'boolean') return Boolean(field.value)
  if (field.type === 'number') return Number(field.value || 0)
  return field.value ?? ''
}

function sameValue(a, b) {
  if (Array.isArray(a) || Array.isArray(b)) {
    const aa = Array.isArray(a) ? a : []
    const bb = Array.isArray(b) ? b : []
    if (aa.length !== bb.length) return false
    return aa.every((v, i) => String(v ?? '') === String(bb[i] ?? ''))
  }
  if (typeof a === 'number' || typeof b === 'number') return Number(a) === Number(b)
  return String(a ?? '') === String(b ?? '')
}

function numberStep(field) {
  const value = Number(field.value)
  return Number.isInteger(value) ? 1 : 0.1
}

function resetDraft() {
  draft.value = { ...baseline.value }
}

async function submitChanges() {
  if (!dirtyCount.value) return
  await props.saveConfig(changes.value)
}

async function recoverEnergyNow() {
  if (!props.recoverEnergy) return
  await props.recoverEnergy(ENERGY_RECOVERY_AMOUNT)
}

function shortPath(path) {
  const text = String(path || '')
  if (!text) return '—'
  const idx = text.indexOf('/life-system/')
  return idx >= 0 ? text.slice(idx + 1) : text
}

function displayValue(value) {
  if (Array.isArray(value)) return value.join(', ')
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}
</script>
