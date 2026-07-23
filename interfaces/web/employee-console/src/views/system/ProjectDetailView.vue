<template>
  <div v-if="loading" class="dev-placeholder"><span class="mono">loading project…</span></div>
  <div v-else-if="!project" class="dev-placeholder">
    <strong>// PROJECT NOT FOUND</strong>
    <span><RouterLink to="/system/projects">← 返回项目列表</RouterLink></span>
  </div>
  <div v-else>
    <!-- 顶 hero -->
    <section class="page-hero">
      <div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <RouterLink to="/system/projects" class="brand-sub">← 项目列表</RouterLink>
        </div>
        <h1 class="page-title">{{ project.name }}</h1>
        <div class="brand-sub mono" style="color: var(--text-muted); margin-top: 4px;">
          id: {{ project.id }} · {{ project.status }} · manager {{ project.manager_name || '—' }}
        </div>
        <p v-if="project.description" class="project-desc">{{ project.description }}</p>
      </div>
      <div style="display: flex; gap: 8px;">
        <el-button @click="load"><el-icon><Refresh /></el-icon>刷新</el-button>
        <el-button type="danger" plain @click="remove">
          <el-icon><Delete /></el-icon> 删除项目
        </el-button>
      </div>
    </section>

    <!-- section tabs -->
    <div class="kind-tabs" style="border-bottom: 1px solid var(--border-line); padding-bottom: 8px; margin-bottom: var(--space-4); display: flex; gap: 4px;">
      <button
        v-for="s in sections"
        :key="s.key"
        class="kind-tab"
        :class="{ active: activeSection === s.key }"
        @click="activeSection = s.key"
      >
        <span>{{ s.label }}</span>
        <span v-if="s.count" class="kind-count">{{ s.count }}</span>
      </button>
    </div>

    <!-- Overview -->
    <div v-if="activeSection === 'overview'" class="detail-grid">
      <div class="neon-card">
        <h3>项目经理</h3>
        <div class="info-row">
          <span class="brand-sub">display_name</span>
          <strong class="real-name">{{ project.manager_name || '—' }}</strong>
        </div>
        <div class="info-row mono">
          <span class="brand-sub">id</span>
          <span>{{ project.manager || '—' }}</span>
        </div>
        <div class="info-row" v-if="project.group_chat_id">
          <span class="brand-sub">group_chat</span>
          <span class="mono">{{ project.group_chat_id }}</span>
        </div>
      </div>

      <div class="neon-card">
        <h3>角色 / Positions</h3>
        <div v-for="pos in project.positions" :key="pos.id" class="position-row">
          <span class="pos-name">{{ pos.name }}</span>
          <span class="pos-assignees">{{ (pos.assignee_names || []).join(' / ') || '未分配' }}</span>
        </div>
      </div>

      <div class="neon-card">
        <h3>目标 / &lt;goal&gt;</h3>
        <p v-if="project.goal" class="goal-text">{{ project.goal }}</p>
        <p v-else class="brand-sub" style="color: var(--text-muted);">未设置；建议在 project.yaml 里加 `goal:` 字段</p>
      </div>

      <div class="neon-card">
        <h3>KPIs</h3>
        <ul v-if="project.kpis && project.kpis.length" class="kpi-list">
          <li v-for="(k, i) in project.kpis" :key="i" class="mono">{{ k }}</li>
        </ul>
        <p v-else class="brand-sub" style="color: var(--text-muted);">未设置</p>
      </div>
    </div>

    <!-- Tasks -->
    <div v-else-if="activeSection === 'tasks'">
      <div v-if="!tasks.length" class="dev-placeholder">
        <span class="mono">// 此项目暂无 todo / deliverable</span>
        <span class="brand-sub">数字生命在唤醒中通过 `todo_create` 工具创建时会自动归到这里。</span>
      </div>
      <div v-else class="neon-card task-table">
        <div class="task-row task-head-row">
          <span>状态</span>
          <span>标题</span>
          <span>分配给</span>
          <span>优先级</span>
          <span>类型</span>
        </div>
        <div v-for="t in tasks" :key="t.id" class="task-row">
          <span>
            <span class="status-dot" :class="taskStatusClass(t.status)"></span>
            {{ t.status }}
          </span>
          <span class="task-title">{{ t.title || '(无标题)' }}</span>
          <span class="real-name">{{ t.assignee_name || '—' }}</span>
          <span>
            <el-tag size="small" :type="priorityTag(t.priority)">{{ t.priority || 'med' }}</el-tag>
          </span>
          <span class="mono" style="color: var(--text-muted);">{{ t.type || '—' }}</span>
        </div>
      </div>
    </div>

    <!-- Workspace -->
    <div v-else-if="activeSection === 'workspace'">
      <div class="neon-card">
        <h3>项目工作区 / docs</h3>
        <p class="brand-sub" style="color: var(--text-muted); margin-bottom: 12px;">
          路径：<code class="mono">projects/{{ project.id }}/docs/</code>
          <span v-if="!project.workspace_dir" class="brand-sub" style="color: var(--neon-amber);">
            ⚠ 目录不存在
          </span>
        </p>
        <div v-if="workspaceFiles.length" class="file-list">
          <div v-for="f in workspaceFiles" :key="f.path" class="file-row">
            <span class="mono file-path">{{ f.path }}</span>
            <span class="brand-sub mono">{{ formatSize(f.size_bytes) }}</span>
          </div>
        </div>
        <p v-else class="brand-sub" style="color: var(--text-muted);">
          尚无文档；数字生命可以通过 terminal / docs-write 技能生成 PRD、设计文档、回顾等。
        </p>
      </div>
    </div>

    <!-- Memory -->
    <div v-else-if="activeSection === 'memory'">
      <div class="neon-card">
        <h3>项目记忆 / project memory</h3>
        <p class="brand-sub" style="color: var(--text-muted); margin-bottom: 12px;">
          每个项目的专属记忆目录 —— 区别于实例的 state.db memory，存放项目沉淀的"为什么这么定"、"为什么放弃 A 方案"等决策记录。
          <br>
          计划实现：路径 <code class="mono">projects/{{ project.id }}/memory/</code>，含
          <code class="mono">decisions.md</code> / <code class="mono">context.md</code> / <code class="mono">retro-YYYY-MM.md</code>。
        </p>
        <div v-if="project.memory_dir" class="brand-sub" style="color: var(--neon-lime);">
          ✓ 已存在目录：{{ project.memory_dir }}
        </div>
        <div v-else class="dev-placeholder" style="margin-top: 12px;">
          <strong>// 待实现</strong>
          <span>memory_dir 待初始化；这里后续可以做 markdown 编辑器 + 章节预览</span>
        </div>
      </div>
    </div>

    <!-- Files -->
    <div v-else-if="activeSection === 'files'">
      <div class="neon-card">
        <h3>项目目录树</h3>
        <div v-if="project.files && project.files.length" class="file-list">
          <div v-for="f in project.files" :key="f.path" class="file-row">
            <span class="mono file-path">{{ f.path }}</span>
            <span class="brand-sub mono">{{ formatSize(f.size_bytes) }}</span>
          </div>
        </div>
        <p v-else class="brand-sub" style="color: var(--text-muted);">空目录</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { Delete, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { systemApi } from '@/api/client'

const route = useRoute()
const router = useRouter()
const pid = computed(() => String(route.params.pid || ''))

const project = ref(null)
const tasks = ref([])
const loading = ref(true)
const activeSection = ref('overview')

const sections = computed(() => [
  { key: 'overview', label: '概览', count: 0 },
  { key: 'tasks', label: '任务', count: project.value?.task_count || tasks.value.length || 0 },
  { key: 'workspace', label: '工作区', count: workspaceFiles.value.length },
  { key: 'memory', label: '记忆', count: project.value?.memory_dir ? 1 : 0 },
  { key: 'files', label: '文件', count: project.value?.files?.length || 0 },
])

const workspaceFiles = computed(() =>
  (project.value?.files || []).filter(f => f.path.startsWith('docs/'))
)

function taskStatusClass(status) {
  return {
    done: 'live',
    in_progress: 'live',
    planned: 'idle',
    idea: 'idle',
    cancelled: 'down',
  }[String(status)] || 'idle'
}

function priorityTag(p) {
  return { high: 'danger', medium: 'warning', low: 'info' }[String(p)] || ''
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

async function load() {
  if (!pid.value) return
  loading.value = true
  try {
    const [d, td] = await Promise.all([
      systemApi.projectDetail(pid.value),
      systemApi.projectTasks(pid.value),
    ])
    if (d.error) { project.value = null; return }
    project.value = d.project || null
    if (!td.error) tasks.value = td.tasks || []
  } finally {
    loading.value = false
  }
}

async function remove() {
  if (!project.value) return
  try {
    await ElMessageBox.confirm(
      `删除项目 "${project.value.name}"？\nprojects/${pid.value}/ 目录将被物理删除，含 todos.db，不可恢复。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch { return }
  const d = await systemApi.deleteProject(pid.value)
  if (d.error) return ElMessage.error(d.error)
  ElMessage.success('已删除')
  router.push('/system/projects')
}

watch(pid, load)
onMounted(load)
</script>

<style scoped>
.project-desc {
  color: var(--text-secondary);
  margin: 12px 0 0;
  font-size: 14px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: var(--space-4);
}

h3 {
  font-family: var(--font-display);
  letter-spacing: 0.04em;
  color: var(--neon-cyan);
  font-size: 13px;
  margin: 0 0 var(--space-3);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  border-bottom: 1px solid var(--border-divider);
  font-size: 13px;
}
.real-name { color: var(--neon-pink); font-family: var(--font-display); }

.position-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px solid var(--border-divider);
  font-size: 13px;
}
.pos-name { color: var(--neon-cyan); font-family: var(--font-mono); min-width: 80px; }
.pos-assignees { color: var(--text-secondary); }

.goal-text {
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
  white-space: pre-wrap;
}

.kpi-list {
  margin: 0;
  padding-left: 18px;
  color: var(--text-secondary);
  font-size: 13px;
}
.kpi-list li { margin: 4px 0; }

.kind-tabs { display: flex; gap: 4px; }
.kind-tab {
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-secondary);
  padding: 8px 14px;
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 160ms ease;
}
.kind-tab:hover { color: var(--text-primary); background: var(--bg-overlay); }
.kind-tab.active {
  color: var(--neon-cyan);
  border-color: var(--border-line-strong);
  background: var(--neon-cyan-soft);
  box-shadow: var(--shadow-glow-cyan);
}
.kind-count {
  background: var(--bg-elevated);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--neon-cyan);
}

.task-table { padding: 0; overflow: hidden; }
.task-row {
  display: grid;
  grid-template-columns: 80px 1fr 120px 90px 100px;
  gap: 12px;
  padding: 10px 14px;
  font-size: 13px;
  border-bottom: 1px solid var(--border-divider);
  align-items: center;
}
.task-row:last-child { border: none; }
.task-head-row {
  background: var(--bg-deep);
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
.task-title { color: var(--text-primary); }

.file-list { display: flex; flex-direction: column; }
.file-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid var(--border-divider);
  font-size: 12px;
}
.file-path { color: var(--neon-cyan); }
</style>
