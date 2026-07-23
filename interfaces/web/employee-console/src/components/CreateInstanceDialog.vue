<script setup>
import { ref, watch } from 'vue'
import { Plus } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  apiBase: { type: String, required: true },
})

const emit = defineEmits(['update:modelValue', 'created'])

const displayName = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')

watch(() => props.modelValue, (v) => {
  if (v) {
    displayName.value = ''
    error.value = ''
    success.value = ''
    loading.value = false
  }
})

async function doCreate() {
  const n = displayName.value.trim()
  if (!n) {
    error.value = '实例显示名称不能为空'
    return
  }
  if (n.length > 64) {
    error.value = '实例显示名称不能超过 64 个字符'
    return
  }
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    const url = props.apiBase.replace(/\/[^/]+$/, '') + '/instances'
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: n }),
    })
    const data = await r.json()
    if (r.ok && data.ok) {
      success.value = data.hint || '实例已创建'
      displayName.value = ''
      emit('created', data.display_name || n)
    } else {
      error.value = data.reason || `HTTP ${r.status}`
    }
  } catch (e) {
    error.value = e.message || '网络错误'
  } finally {
    loading.value = false
  }
}

function close() {
  emit('update:modelValue', false)
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    title="创建新实例"
    width="440px"
    :close-on-click-modal="false"
  >
    <el-form @submit.prevent="doCreate" label-position="top">
      <el-form-item label="实例显示名称">
        <el-input
          v-model="displayName"
          placeholder="例如 Zero、小助手"
          :disabled="loading"
          maxlength="64"
          clearable
        />
        <div class="form-hint">支持中文、字母、数字，用于界面展示，可后续修改</div>
      </el-form-item>

      <div v-if="error" class="create-error"><el-icon><component :is="'WarningFilled'" /></el-icon> {{ error }}</div>
      <div v-if="success" class="create-success"><el-icon><component :is="'SuccessFilled'" /></el-icon> {{ success }}</div>
    </el-form>

    <template #footer>
      <el-button @click="close" :disabled="loading">取消</el-button>
      <el-button type="primary" :loading="loading" @click="doCreate">
        <el-icon v-if="!loading"><Plus /></el-icon>
        创建
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.form-hint {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
.create-error {
  color: #f56c6c;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 8px;
}
.create-success {
  color: #67c23a;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 8px;
}
</style>
