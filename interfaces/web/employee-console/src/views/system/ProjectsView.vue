<template>
  <div>
    <section class="page-hero">
      <div>
        <h1 class="page-title">Projects</h1>
        <p class="page-subtitle">跨实例共享的工作载体 · 点击进入项目详情</p>
      </div>
      <div style="display: flex; gap: 8px;">
        <el-button @click="load"><el-icon><Refresh /></el-icon>刷新</el-button>
        <el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon>新建</el-button>
      </div>
    </section>

    <div class="neon-grid" style="grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));">
      <div
        v-for="p in projects"
        :key="p.id"
        class="neon-card project-card"
        @click="goto(p.id)"
      >
        <div class="card-head">
          <strong class="project-name">{{ p.name }}</strong>
          <div style="display: flex; gap: 6px; align-items: center;">
            <el-tag size="small" effect="plain" :type="tagType(p.status)">{{ p.status }}</el-tag>
            <el-button size="small" type="danger" plain @click.stop="remove(p)">
              删除
            </el-button>
          </div>
        </div>
        <p class="project-desc">{{ p.description || '—' }}</p>

        <div class="project-manager">
          <el-icon><User /></el-icon>
          <span class="brand-sub">项目经理：</span>
          <strong class="real-name">{{ p.manager_name || '—' }}</strong>
        </div>

        <div class="position-tags">
          <div v-for="pos in p.positions" :key="pos.id" class="position-chip">
            <span class="pos-name">{{ pos.name }}</span>
            <span class="pos-assignees">
              {{ (pos.assignee_names || []).join(' / ') || '未分配' }}
            </span>
          </div>
        </div>

        <div class="project-footer">
          <span v-if="p.group_chat_id" class="brand-sub mono">
            chat {{ safeSlice(p.group_chat_id, 0, 14) }}…
          </span>
          <span class="brand-sub" style="margin-left: auto; color: var(--neon-cyan);">
            查看详情 →
          </span>
        </div>
      </div>
      <div v-if="!projects.length" class="dev-placeholder">
        <span class="mono">// 还没有项目，点新建开始</span>
      </div>
    </div>

    <!-- 新建 dialog -->
    <el-dialog v-model="dlg.open" title="新建项目" width="640px">
      <el-form label-width="120px" :model="dlg.form">
        <el-form-item label="名称" required>
          <el-input v-model="dlg.form.name" placeholder="项目名" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="dlg.form.description" type="textarea" :rows="3" placeholder="30-50 字说清楚这个项目要解决什么" />
        </el-form-item>
        <el-form-item label="项目经理" required>
          <el-select v-model="dlg.form.manager" filterable style="width: 100%;">
            <el-option
              v-for="i in instances"
              :key="i.id"
              :label="`${i.display_name}${i.tagline ? ' · ' + i.tagline : ''}`"
              :value="i.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="飞书群 chat_id">
          <el-input v-model="dlg.form.group_chat_id" placeholder="oc_xxx…可空" />
        </el-form-item>
        <el-form-item label="项目目标">
          <el-input v-model="dlg.form.goal" type="textarea" :rows="2" placeholder="长期目标，写完后会被生命周期记得" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlg.open = false">取消</el-button>
        <el-button type="primary" :loading="dlg.saving" @click="create">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Refresh, User } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { systemApi } from '@/api/client'
// safeSlice 来自 globalProperties（main.js 已注册）

const router = useRouter()
const projects = ref([])
const instances = ref([])
const dlg = reactive({
  open: false,
  saving: false,
  form: { name: '', description: '', manager: '', group_chat_id: '', goal: '' },
})

function goto(pid) {
  router.push(`/system/projects/${pid}`)
}

function tagType(status) {
  return { active: 'success', paused: 'warning', archived: 'info' }[status] || ''
}

async function load() {
  const [pd, id] = await Promise.all([
    systemApi.projects(),
    systemApi.instances(),
  ])
  if (!pd.error) projects.value = pd.projects || []
  if (!id.error) instances.value = id.instances || []
}

function openCreate() {
  dlg.open = true
  Object.assign(dlg.form, { name: '', description: '', manager: '', group_chat_id: '', goal: '' })
}

async function create() {
  if (!dlg.form.name) return ElMessage.error('名称必填')
  if (!dlg.form.manager) return ElMessage.error('请选择项目经理')
  dlg.saving = true
  try {
    const d = await systemApi.createProject({
      name: dlg.form.name,
      description: dlg.form.description,
      manager: dlg.form.manager,
      group_chat_id: dlg.form.group_chat_id,
    })
    if (d.error) return ElMessage.error(d.error)
    ElMessage.success(`已创建项目 ${d.project.name}`)
    dlg.open = false
    await load()
    // 直接跳到详情页让用户继续完善
    if (d.project?.id) goto(d.project.id)
  } finally { dlg.saving = false }
}

async function remove(p) {
  try {
    await ElMessageBox.confirm(
      `删除项目 "${p.name}"？\nprojects/${p.id}/ 目录将被物理删除，不可恢复。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch { return }
  const d = await systemApi.deleteProject(p.id)
  if (d.error) return ElMessage.error(d.error)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<style scoped>
.project-card { cursor: pointer; transition: all 200ms ease; padding-bottom: 12px; }
.project-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow-cyan);
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}
.project-name { font-family: var(--font-display); letter-spacing: 0.04em; font-size: 16px; color: var(--neon-cyan); }
.project-desc { color: var(--text-secondary); margin: 0 0 12px; font-size: 13px; line-height: 1.5; }
.project-manager {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 12px;
  padding: 8px 10px;
  background: var(--bg-deep);
  border-radius: var(--radius-sm);
}
.real-name { color: var(--neon-pink); font-family: var(--font-display); }

.position-tags { display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }
.position-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  background: var(--bg-overlay);
  border-radius: var(--radius-sm);
  font-size: 12px;
}
.pos-name {
  color: var(--neon-cyan);
  font-family: var(--font-mono);
  min-width: 80px;
}
.pos-assignees { color: var(--text-secondary); }
.project-footer {
  display: flex;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid var(--border-divider);
  margin-top: 4px;
}
</style>
