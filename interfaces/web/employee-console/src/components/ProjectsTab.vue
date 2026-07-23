<script setup>
import { ref, computed, onMounted } from 'vue'
import { Refresh, Folder, ArrowLeft, Plus, User, Edit } from '@element-plus/icons-vue'

const props = defineProps({
  apiBase: { type: String, required: true },
})

const loading = ref(false)
const projects = ref([])
const error = ref('')
const selectedProject = ref(null)
const projectTasks = ref([])
const tasksLoading = ref(false)

const assigneeLabel = (aid) => {
  if (!aid) return '待分配'
  if (aid.startsWith('human:')) return aid.replace('human:', '')+ '（人类）'
  return aid.slice(0, 8)
}

async function loadProjects() {
  loading.value = true
  error.value = ''
  try {
    const r = await fetch(`${props.apiBase}/projects`)
    const d = await r.json()
    if (r.ok) projects.value = d.projects || []
    else error.value = d.error || `HTTP ${r.status}`
  } catch (e) {
    error.value = e.message || '网络错误'
  } finally {
    loading.value = false
  }
}

async function openProject(p) {
  selectedProject.value = p
  await loadProjectTasks(p.id)
}

async function loadProjectTasks(pid) {
  tasksLoading.value = true
  try {
    const r = await fetch(`${props.apiBase}/projects/${pid}/tasks`)
    const d = await r.json()
    if (r.ok) projectTasks.value = d.tasks || []
  } catch (e) {
    error.value = e.message
  } finally {
    tasksLoading.value = false
  }
}

// 把平铺的 task list 转成树
const taskTree = computed(() => {
  const map = new Map()
  const roots = []
  for (const t of projectTasks.value) {
    map.set(t.id, { ...t, children: [] })
  }
  for (const t of projectTasks.value) {
    const node = map.get(t.id)
    if (t.parent_task_id && map.has(t.parent_task_id)) {
      map.get(t.parent_task_id).children.push(node)
    } else {
      roots.push(node)
    }
  }
  return roots
})

const TYPE_LABELS = {
  project_root: '项目根',
  project_bootstrap: '项目分工',
  project_management: '项目管理',
  research: '调研',
  development: '开发',
  trading: '交易',
  reflection: '反思',
}

const TYPE_COLORS = {
  project_root: '',
  project_bootstrap: 'warning',
  project_management: 'success',
}

function backToList() {
  selectedProject.value = null
  projectTasks.value = []
}

// ── 创建项目 ──
const createDialogVisible = ref(false)
const creating = ref(false)
const createForm = ref({
  name: '',
  description: '',
  manager: '',
  group_chat_id: '',
})

function openCreateDialog() {
  createForm.value = { name: '', description: '', manager: '', group_chat_id: '' }
  createDialogVisible.value = true
}

async function submitCreateProject() {
  if (!createForm.value.name || !createForm.value.manager) {
    error.value = '项目名和项目经理必填'
    return
  }
  creating.value = true
  error.value = ''
  try {
    const r = await fetch(`${props.apiBase}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(createForm.value),
    })
    const d = await r.json()
    if (r.ok && d.ok) {
      createDialogVisible.value = false
      await loadProjects()
    } else {
      error.value = d.reason || d.error || '创建失败'
    }
  } catch (e) {
    error.value = e.message || '网络错误'
  } finally {
    creating.value = false
  }
}

onMounted(loadProjects)
</script>

<template>
  <div class="projects-workbench">
    <!-- 项目列表视图 -->
    <template v-if="!selectedProject">
      <header class="projects-head">
        <div>
          <div class="eyebrow">Projects</div>
          <h2>项目</h2>
          <p class="hint">点击项目卡片查看任务树和进度。</p>
        </div>
        <div class="actions">
          <el-button type="primary" :icon="Plus" @click="openCreateDialog">新建项目</el-button>
          <el-button :icon="Refresh" @click="loadProjects" :loading="loading">刷新</el-button>
        </div>
      </header>

      <!-- 创建项目 Modal -->
      <el-dialog v-model="createDialogVisible" title="新建项目" width="500px">
        <el-form label-position="top">
          <el-form-item label="项目名称" required>
            <el-input v-model="createForm.name" placeholder="如：模拟炒股" />
          </el-form-item>
          <el-form-item label="项目描述">
            <el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="一句话描述项目做什么" />
          </el-form-item>
          <el-form-item label="项目经理（实例 ID）" required>
            <el-input v-model="createForm.manager" placeholder="实例 UUID" />
          </el-form-item>
          <el-form-item label="关联群 chat_id（可选）">
            <el-input v-model="createForm.group_chat_id" placeholder="oc_xxx" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="createDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="creating" @click="submitCreateProject">创建</el-button>
        </template>
      </el-dialog>

      <div v-if="error" class="error-msg">⚠ {{ error }}</div>

      <div v-if="loading && !projects.length" class="loading">加载中...</div>

      <div class="project-grid" v-else>
        <div
          v-for="p in projects"
          :key="p.id"
          class="project-card"
          @click="openProject(p)"
        >
          <div class="card-head">
            <el-icon :size="20"><Folder /></el-icon>
            <span class="card-title">{{ p.name }}</span>
            <el-tag size="small" :type="p.status === 'active' ? 'success' : 'info'" effect="plain">
              {{ p.status }}
            </el-tag>
          </div>
          <div class="card-desc">{{ p.description || '—' }}</div>
          <div class="card-meta">
            <span v-if="p.manager">管理者: {{ assigneeLabel(p.manager) }}</span>
            <span>{{ p.positions?.length || 0 }} 个岗位</span>
          </div>
        </div>
      </div>

      <div v-if="!loading && !projects.length" class="empty">
        没有项目。
      </div>
    </template>

    <!-- 单项目详情视图 -->
    <template v-else>
      <header class="project-detail-head">
        <el-button :icon="ArrowLeft" plain size="small" @click="backToList">返回项目列表</el-button>
        <h2>{{ selectedProject.name }}</h2>
      </header>

      <div class="project-body">
        <!-- 概览 -->
        <div class="info-block">
          <div class="info-label">描述</div>
          <div class="info-value">{{ selectedProject.description || '—' }}</div>
        </div>

        <div class="info-row">
          <div class="info-block">
            <div class="info-label">状态</div>
            <div class="info-value">
              <el-tag :type="selectedProject.status === 'active' ? 'success' : 'info'">{{ selectedProject.status }}</el-tag>
            </div>
          </div>
          <div class="info-block">
            <div class="info-label">管理者</div>
            <div class="info-value">{{ assigneeLabel(selectedProject.manager) }}</div>
          </div>
        </div>

        <!-- 岗位 -->
        <div class="section-title">👥 岗位分工</div>
        <el-table :data="selectedProject.positions" stripe size="small">
          <el-table-column label="岗位" prop="name" width="120" />
          <el-table-column label="承担人">
            <template #default="{ row }">
              <el-tag v-for="a in row.assignees" :key="a" size="small" effect="plain" class="assignee-tag">
                {{ assigneeLabel(a) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="职责">
            <template #default="{ row }">
              <span v-for="(r, i) in row.responsibilities" :key="i" class="resp-item">{{ r }}</span>
            </template>
          </el-table-column>
        </el-table>

        <!-- 任务树 -->
        <div class="section-title">📋 任务树</div>
        <el-table :data="projectTasks" v-loading="tasksLoading" row-key="id"
                  :tree-props="{ children: 'children', hasChildren: 'hasChildren' }" stripe size="small"
                  default-expand-all>
          <el-table-column label="任务" min-width="200">
            <template #default="{ row }">
              <span :style="{ fontWeight: row.type === 'project_root' ? 'bold' : 'normal' }">{{ row.title }}</span>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="130">
            <template #default="{ row }">
              <el-tag v-if="row.type" size="small" :type="TYPE_COLORS[row.type] || ''" effect="plain">
                {{ TYPE_LABELS[row.type] || row.type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="承担人" width="150">
            <template #default="{ row }">
              {{ assigneeLabel(row.assignee_instance) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === 'in_progress' ? 'success' : row.status === 'done' ? 'info' : ''" effect="plain">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.projects-workbench { padding: 8px 0; }
.projects-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 16px; }
.projects-head h2 { margin: 4px 0; }
.projects-head .hint { color: var(--el-text-color-secondary); font-size: 13px; margin: 0; }
.project-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
.project-card { background: var(--el-bg-color); border: 1px solid var(--el-border-color-light); border-radius: 8px; padding: 14px 16px; cursor: pointer; transition: all 0.2s; }
.project-card:hover { border-color: var(--el-color-primary-light-3); box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.card-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.card-title { font-size: 16px; font-weight: 600; }
.card-desc { font-size: 13px; color: var(--el-text-color-secondary); margin-bottom: 8px; min-height: 18px; }
.card-meta { display: flex; gap: 12px; font-size: 12px; color: var(--el-text-color-placeholder); }

.project-detail-head { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.project-detail-head h2 { margin: 0; }
.project-body { }
.info-block { margin-bottom: 12px; }
.info-label { font-size: 12px; color: var(--el-text-color-secondary); margin-bottom: 2px; }
.info-value { font-size: 14px; }
.info-row { display: flex; gap: 20px; margin-bottom: 12px; }
.info-row .info-block { margin-bottom: 0; }
.section-title { font-size: 14px; font-weight: 600; margin: 20px 0 8px; }
.assignee-tag { margin-right: 4px; }
.resp-item { font-size: 12px; margin-right: 8px; }
.error-msg { background: var(--el-color-danger-light-9); color: var(--el-color-danger); padding: 8px 12px; border-radius: 4px; margin-bottom: 12px; font-size: 13px; }
.empty, .loading { text-align: center; color: var(--el-text-color-placeholder); padding: 40px; font-size: 14px; }
</style>
