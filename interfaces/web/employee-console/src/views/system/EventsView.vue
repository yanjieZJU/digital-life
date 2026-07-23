<template>
  <div>
    <section class="page-hero">
      <div>
        <h1 class="page-title">Event Type Registry</h1>
        <p class="page-subtitle">数字生命可被触发的所有事件类型 · 写入 config/event-packages/manifest.yaml</p>
      </div>
      <div style="display: flex; gap: 8px;">
        <el-button @click="load"><el-icon><Refresh /></el-icon>刷新</el-button>
        <el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon>新建</el-button>
      </div>
    </section>

    <div class="neon-grid">
      <div v-for="ev in events" :key="ev.type_id" class="neon-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div style="flex: 1;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <strong style="font-family: var(--font-display); color: var(--neon-pink);">{{ ev.type_id }}</strong>
              <el-tag size="small" type="info" effect="plain">{{ ev.trigger_type || '—' }}</el-tag>
              <el-tag
                size="small"
                :type="ev.origin === 'manifest' ? 'success' : 'warning'"
                effect="plain"
              >
                {{ ev.origin === 'manifest' ? '✓ manifest' : 'legacy_yaml' }}
              </el-tag>
            </div>
            <div class="brand-sub" style="margin: 4px 0;">{{ ev.display_name }}</div>
            <div class="tag-row">
              <el-tag v-for="t in ev.allowed_tools" :key="t" size="small" effect="plain">{{ t }}</el-tag>
            </div>
            <div class="brand-sub mono" style="color: var(--text-muted); margin-top: 6px; font-size: 11px;">
              {{ ev.path }}
            </div>
            <div v-if="ev.origin === 'legacy_yaml'" class="brand-sub"
                 style="color: var(--text-muted); margin-top: 8px; font-size: 11px; font-style: italic;">
              ⚠ 来自 config/event_types.yaml（运行时事实源），前端只读。
              如需迁移，手动把字段搬到 manifest 后用 PUT /api/system/event-types/{type_id} 写入。
            </div>
          </div>
          <div v-if="ev.origin === 'manifest'" style="display: flex; flex-direction: column; gap: 4px;">
            <el-button size="small" @click="openEdit(ev)">编辑</el-button>
            <el-button size="small" type="danger" plain @click="remove(ev)">删除</el-button>
          </div>
        </div>
      </div>
      <div v-if="!events.length" class="dev-placeholder">
        <span class="mono">// no event packages</span>
      </div>
    </div>

    <!-- 增/改 dialog -->
    <el-dialog
      v-model="dlg.open"
      :title="dlg.isNew ? '新建事件类型' : `编辑 ${dlg.type_id}`"
      width="560px"
    >
      <div class="brand-sub" style="color: var(--text-muted); margin-bottom: 12px;">
        manifest.yaml schema：type_id / display_name / trigger_type / prompt / allowed_tools /
        context_policy / auth_policy
      </div>

      <el-form label-width="140px" :model="dlg.form">
        <el-form-item label="type_id">
          <el-input v-model="dlg.form.type_id" :disabled="!dlg.isNew" placeholder="唯一标识符" />
        </el-form-item>
        <el-form-item label="display_name">
          <el-input v-model="dlg.form.display_name" />
        </el-form-item>
        <el-form-item label="trigger_type">
          <el-input v-model="dlg.form.trigger_type" placeholder="message / routine / initiative …" />
        </el-form-item>
        <el-form-item label="prompt">
          <el-input v-model="dlg.form.prompt" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="allowed_tools">
          <el-select
            v-model="dlg.allowedToolsArr"
            multiple filterable allow-create
            placeholder="回车添加"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="context_policy">
          <el-input v-model="dlg.form.context_policy" placeholder="key=value,key=value" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dlg.open = false">取消</el-button>
        <el-button type="primary" :loading="dlg.saving" @click="submit">
          {{ dlg.isNew ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { systemApi } from '@/api/client'

const events = ref([])
const dlg = reactive({
  open: false,
  isNew: true,
  type_id: '',
  saving: false,
  form: {
    type_id: '', display_name: '', trigger_type: '',
    prompt: '', allowed_tools: '', context_policy: '', auth_policy: '',
  },
  allowedToolsArr: [],
})

async function load() {
  const d = await systemApi.eventTypes()
  if (d.error) return ElMessage.error(d.error)
  events.value = d.event_types || []
}

function openCreate() {
  dlg.open = true
  dlg.isNew = true
  dlg.type_id = ''
  Object.assign(dlg.form, {
    type_id: '', display_name: '', trigger_type: '',
    prompt: '', allowed_tools: '', context_policy: '', auth_policy: '',
  })
  dlg.allowedToolsArr = []
}

function openEdit(ev) {
  dlg.open = true
  dlg.isNew = false
  dlg.type_id = ev.type_id
  Object.assign(dlg.form, {
    type_id: ev.type_id,
    display_name: ev.display_name,
    trigger_type: ev.trigger_type,
    prompt: ev.prompt,
    allowed_tools: ev.allowed_tools.join(','),
    context_policy: ev.context_policy,
    auth_policy: ev.auth_policy,
  })
  dlg.allowedToolsArr = ev.allowed_tools.slice()
}

async function submit() {
  if (!dlg.form.type_id) return ElMessage.error('type_id required')
  dlg.saving = true
  dlg.form.allowed_tools = dlg.allowedToolsArr.join(',')
  try {
    const method = dlg.isNew ? systemApi.createEventType : systemApi.updateEventType
    const args = dlg.isNew ? [dlg.form] : [dlg.type_id, dlg.form]
    const d = await method(...args)
    if (d.error) return ElMessage.error(d.error)
    ElMessage.success(dlg.isNew ? '已创建' : '已保存')
    dlg.open = false
    await load()
  } finally {
    dlg.saving = false
  }
}

async function remove(ev) {
  try {
    await ElMessageBox.confirm(`删除事件类型 "${ev.type_id}"？`, '确认', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
  } catch { return }
  const d = await systemApi.deleteEventType(ev.type_id)
  if (d.error) return ElMessage.error(d.error)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>
