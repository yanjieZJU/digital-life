<script setup>
import { ref, onMounted, computed } from 'vue'
import { Refresh, CircleCheck, Folder, User, ArrowRight, Clock, Plus } from '@element-plus/icons-vue'

const props = defineProps({
  apiBase: { type: String, required: true },
})

const loading = ref(false)
const todos = ref([])
const error = ref('')
const filterStatus = ref('')
const expandedTodos = ref({})
const activeGroups = ref([])  // el-collapse v-model — 加载后自动展开有活跃 todo 的组

const STATUS_LABELS = {
  idea: '构想',
  planned: '计划',
  in_progress: '进行中',
  paused: '暂停',
  done: '已完成',
  cancelled: '已取消',
}

const STATUS_TYPES = {
  idea: 'info',
  planned: 'info',
  in_progress: 'warning',
  paused: 'info',
  done: 'success',
  cancelled: 'info',
}

const STATUS_RANK = ['in_progress', 'planned', 'idea', 'paused', 'done', 'cancelled']

const filtered = computed(() => {
  let r = todos.value
  if (filterStatus.value) r = r.filter(t => t.status === filterStatus.value)
  return r
})

const projectGroups = computed(() => {
  const buckets = {}
  for (const t of filtered.value) {
    const pid = t.project_id || ''
    if (!buckets[pid]) buckets[pid] = []
    buckets[pid].push(t)
  }
  const groups = []
  for (const pid of Object.keys(buckets)) {
    const items = buckets[pid]
    const activeCount = items.filter(t =>
      ['planned', 'in_progress', 'idea'].includes(t.status)).length
    const doneCount = items.filter(t => t.status === 'done').length
    const cancelledCount = items.filter(t => t.status === 'cancelled').length
    groups.push({
      key: pid || '_personal',
      project_id: pid,
      label: pid || '个人待办',
      isPersonal: !pid,
      icon: pid ? Folder : User,
      todos: sortByStatus(items),
      activeCount,
      doneCount,
      cancelledCount,
      total: items.length,
    })
  }
  return groups.sort((a, b) => {
    if (a.isPersonal !== b.isPersonal) return a.isPersonal ? 1 : -1
    return b.activeCount - a.activeCount
  })
})

function sortByStatus(items) {
  return [...items].sort((a, b) => {
    const d = STATUS_RANK.indexOf(a.status) - STATUS_RANK.indexOf(b.status)
    if (d) return d
    return new Date(b.updated_at || 0) - new Date(a.updated_at || 0)
  })
}

const stats = computed(() => {
  const items = filtered.value
  return {
    total: items.length,
    active: items.filter(t => ['planned', 'in_progress', 'idea'].includes(t.status)).length,
    done: items.filter(t => t.status === 'done').length,
    groups: projectGroups.value.length,
  }
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const r = await fetch(`${props.apiBase}/todos`)
    const d = await r.json()
    if (r.ok) {
      todos.value = d.todos || []
      // 自动展开有活跃 todo 的 group
      const activeKeys = new Set()
      for (const t of todos.value) {
        if (['in_progress', 'planned', 'idea'].includes(t.status)) {
          activeKeys.add(t.project_id || '_personal')
        }
      }
      activeGroups.value = Array.from(activeKeys)
    } else {
      error.value = d.reason || `HTTP ${r.status}`
    }
  } catch (e) {
    error.value = e.message || '网络错误'
  } finally {
    loading.value = false
  }
}

async function updateStatus(todo, status) {
  try {
    await fetch(`${props.apiBase}/todos/${todo.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
    await load()
  } catch (e) {
    error.value = e.message
  }
}

function toggleDetail(todoId) {
  expandedTodos.value = { ...expandedTodos.value, [todoId]: !expandedTodos.value[todoId] }
}

function isExpanded(todoId) {
  return !!expandedTodos.value[todoId]
}

// fold/unfold 整组(模拟 el-collapse v-model 行为,但更轻量)
function isGroupOpen(key) {
  return activeGroups.value.includes(key)
}
function toggleGroup(key) {
  if (isGroupOpen(key)) {
    activeGroups.value = activeGroups.value.filter(k => k !== key)
  } else {
    activeGroups.value = [...activeGroups.value, key]
  }
}

function fmtTime(s) {
  if (!s) return ''
  const m = s.match(/(\d+-\d+-\d+)T(\d+:\d+)/)
  if (m) return `${m[1].slice(5)} ${m[2]}`
  return s.slice(0, 16)
}

function isActiveStatus(status) {
  return ['in_progress', 'planned', 'idea', 'paused'].includes(status)
}

onMounted(load)
</script>

<template>
  <div class="todos-page">
    <!-- 顶部 -->
    <header class="page-header">
      <div class="header-left">
        <h2>待办</h2>
        <div class="stat-pills">
          <el-tag effect="plain" round size="small">{{ stats.total }} 条</el-tag>
          <el-tag v-if="stats.active" type="warning" effect="plain" round size="small">{{ stats.active }} 活跃</el-tag>
          <el-tag v-if="stats.done" type="success" effect="plain" round size="small">{{ stats.done }} 完成</el-tag>
          <el-tag type="info" effect="plain" round size="small">{{ stats.groups }} 组</el-tag>
        </div>
      </div>
      <div class="header-actions">
        <el-radio-group v-model="filterStatus" size="small">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="in_progress">执行中</el-radio-button>
          <el-radio-button value="planned">计划</el-radio-button>
          <el-radio-button value="done">已完成</el-radio-button>
          <el-radio-button value="cancelled">已取消</el-radio-button>
        </el-radio-group>
        <el-button :icon="Refresh" @click="load" :loading="loading" circle size="small" />
      </div>
    </header>

    <div v-if="error" class="error-banner">
      ⚠ {{ error }}
    </div>

    <!-- 主分组 -->
    <div v-if="projectGroups.length" class="groups-list">
      <section v-for="grp in projectGroups" :key="grp.key" class="group-card">
        <!-- 组 header -->
        <div class="group-header" @click="toggleGroup(grp.key)">
          <el-icon class="group-icon" :class="{ personal: grp.isPersonal }">
            <component :is="grp.icon" />
          </el-icon>
          <span class="group-name">{{ grp.label }}</span>
          <div class="group-counts">
            <span v-if="grp.activeCount" class="count-pill active">{{ grp.activeCount }}</span>
            <span v-if="grp.doneCount" class="count-pill done">{{ grp.doneCount }}</span>
            <span v-if="grp.cancelledCount" class="count-pill cancelled">{{ grp.cancelledCount }}</span>
          </div>
          <el-icon class="collapse-arrow" :class="{ collapsed: !isGroupOpen(grp.key) }">
            <ArrowRight />
          </el-icon>
        </div>

        <!-- 组内 todos -->
        <div v-if="isGroupOpen(grp.key)" class="todos-list">
          <div
            v-for="t in grp.todos"
            :key="t.id"
            class="todo-item"
            :class="['is-' + t.status, { expanded: isExpanded(t.id) }]"
          >
            <div class="todo-summary" @click="toggleDetail(t.id)">
              <el-icon class="expand-icon" :class="{ rotated: isExpanded(t.id) }">
                <ArrowRight />
              </el-icon>
              <span class="status-dot" :class="'dot-' + t.status" />
              <span class="todo-title" :title="t.title">{{ t.title }}</span>
              <el-tag
                v-if="t.priority === 'high'"
                size="small"
                type="danger"
                effect="dark"
                round
                class="priority-tag"
              >高优先</el-tag>
              <span v-if="t.deadline" class="deadline-chip">
                <el-icon :size="11"><Clock /></el-icon>
                {{ fmtTime(t.deadline) }}
              </span>
              <el-tag
                size="small"
                :type="STATUS_TYPES[t.status]"
                effect="light"
                round
                class="status-tag"
              >{{ STATUS_LABELS[t.status] }}</el-tag>
            </div>

            <!-- 详情 -->
            <transition name="expand">
              <div v-if="isExpanded(t.id)" class="todo-detail">
                <div v-if="t.description" class="detail-description">{{ t.description }}</div>
                <div class="detail-grid">
                  <div class="detail-field">
                    <span class="field-label">项目</span>
                    <span class="field-value">{{ t.project_id || '（个人）' }}</span>
                  </div>
                  <div class="detail-field">
                    <span class="field-label">优先级</span>
                    <span class="field-value">{{ t.priority }}</span>
                  </div>
                  <div class="detail-field">
                    <span class="field-label">截止</span>
                    <span class="field-value">{{ fmtTime(t.deadline) || '—' }}</span>
                  </div>
                  <div class="detail-field">
                    <span class="field-label">父待办</span>
                    <span class="field-value">{{ t.parent_id || '—' }}</span>
                  </div>
                  <div class="detail-field">
                    <span class="field-label">类型</span>
                    <span class="field-value">{{ t.type || '普通' }}</span>
                  </div>
                  <div class="detail-field">
                    <span class="field-label">分配</span>
                    <span class="field-value">{{ t.assignee_kind === 'instance' ? '实例' : (t.assignee_kind || '—') }}</span>
                  </div>
                  <div class="detail-field">
                    <span class="field-label">创建</span>
                    <span class="field-value">{{ fmtTime(t.created_at) }}</span>
                  </div>
                  <div class="detail-field">
                    <span class="field-label">更新</span>
                    <span class="field-value">{{ fmtTime(t.updated_at) }}</span>
                  </div>
                </div>
                <div v-if="t.tags && t.tags.length" class="detail-tags">
                  <el-tag v-for="tag in t.tags" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
                </div>
                <div class="detail-actions">
                  <span class="todo-id">#{{ t.id.slice(0, 8) }}</span>
                  <div class="action-buttons">
                    <el-button v-if="isActiveStatus(t.status)" size="small" type="success" :icon="CircleCheck" @click.stop="updateStatus(t, 'done')">完成</el-button>
                    <el-button v-if="t.status === 'in_progress'" size="small" @click.stop="updateStatus(t, 'paused')">暂停</el-button>
                    <el-button v-if="['planned', 'idea', 'paused'].includes(t.status)" size="small" type="primary" @click.stop="updateStatus(t, 'in_progress')">开始</el-button>
                    <el-button v-if="isActiveStatus(t.status)" size="small" type="danger" plain @click.stop="updateStatus(t, 'cancelled')">取消</el-button>
                  </div>
                </div>
              </div>
            </transition>
          </div>
        </div>
      </section>
    </div>

    <div v-else-if="!loading" class="empty-state">
      <el-icon :size="40"><Plus /></el-icon>
      <p>没有待办。</p>
      <p class="empty-sub">可能是新实例或全部已完成。</p>
    </div>
  </div>
</template>

<style scoped>
.todos-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 8px 0;
}

/* 顶部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.header-left { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.page-header h2 { margin: 0; font-size: 18px; }
.stat-pills { display: flex; gap: 6px; }
.header-actions { display: flex; align-items: center; gap: 8px; }

.error-banner {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
  padding: 8px 14px;
  border-radius: var(--el-border-radius-base);
  font-size: 13px;
  border-left: 3px solid var(--el-color-danger);
}

/* 组 card */
.groups-list { display: flex; flex-direction: column; gap: 14px; }
.group-card {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 10px;
  overflow: hidden;
  transition: box-shadow 0.2s;
}
.group-card:hover { box-shadow: 0 1px 10px rgba(0, 0, 0, 0.04); }

/* 组 header */
.group-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  cursor: pointer;
  user-select: none;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color-lighter);
  transition: background 0.15s;
}
.group-header:hover { background: var(--el-fill-color); }
.group-icon { font-size: 16px; color: var(--el-color-primary); }
.group-icon.personal { color: var(--el-color-info); }
.group-name { font-weight: 600; font-size: 14px; flex: 1; }
.group-counts { display: flex; gap: 6px; }
.count-pill {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--el-fill-color-dark);
  color: var(--el-text-color-secondary);
}
.count-pill.active { background: var(--el-color-warning-light-9); color: var(--el-color-warning); }
.count-pill.done { background: var(--el-color-success-light-9); color: var(--el-color-success); }
.count-pill.cancelled { background: var(--el-fill-color-dark); color: var(--el-text-color-placeholder); }
.collapse-arrow {
  color: var(--el-text-color-secondary);
  transition: transform 0.2s;
  font-size: 12px;
}
.collapse-arrow.collapsed { transform: rotate(-90deg); }

/* 组内 todos */
.todos-list { display: flex; flex-direction: column; }

/* 每个 todo */
.todo-item {
  border-bottom: 1px solid var(--el-border-color-lighter);
  transition: background 0.15s;
}
.todo-item:last-child { border-bottom: none; }
.todo-item:hover { background: var(--el-fill-color-light); }
.todo-item.is-done .todo-title { text-decoration: line-through; color: var(--el-text-color-placeholder); }
.todo-item.is-cancelled { opacity: 0.55; }
.todo-item.is-cancelled .todo-title { text-decoration: line-through; }
.todo-item.expanded { background: var(--el-fill-color); }

.todo-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px;
  cursor: pointer;
  user-select: none;
}
.expand-icon {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  transition: transform 0.2s;
}
.expand-icon.rotated { transform: rotate(90deg); }

/* 状态色点(替代左侧色带——更细腻) */
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--el-color-info);
}
.status-dot.dot-in_progress { background: var(--el-color-warning); box-shadow: 0 0 6px var(--el-color-warning-light-5); }
.status-dot.dot-planned { background: var(--el-color-primary); }
.status-dot.dot-done { background: var(--el-color-success); }
.status-dot.dot-idea { background: var(--el-color-info-light-5); }
.status-dot.dot-paused { background: var(--el-text-color-placeholder); }

.todo-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 500;
}
.priority-tag { flex-shrink: 0; }
.deadline-chip {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-variant-numeric: tabular-nums;
}
.status-tag { flex-shrink: 0; }

/* 详情 */
.todo-detail {
  padding: 12px 18px 14px 38px;
  background: var(--el-fill-color-lighter);
  border-top: 1px solid var(--el-border-color-lighter);
}
.detail-description {
  font-size: 13px;
  color: var(--el-text-color-regular);
  margin-bottom: 12px;
  line-height: 1.6;
  padding: 8px 12px;
  background: var(--el-bg-color);
  border-radius: var(--el-border-radius-base);
  border-left: 3px solid var(--el-color-primary-light-5);
}
.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px 16px;
  margin-bottom: 10px;
}
.detail-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.field-label {
  font-size: 10px;
  color: var(--el-text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}
.field-value {
  font-size: 13px;
  color: var(--el-text-color-primary);
  font-variant-numeric: tabular-nums;
}
.detail-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.detail-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 8px;
}
.todo-id {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  font-family: monospace;
}
.action-buttons { display: flex; gap: 6px; }

/* 动画 */
.expand-enter-active, .expand-leave-active {
  transition: all 0.2s ease;
  max-height: 500px;
  overflow: hidden;
}
.expand-enter-from, .expand-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--el-text-color-placeholder);
}
.empty-state p { margin: 8px 0 0; font-size: 14px; }
.empty-sub { font-size: 12px !important; }
</style>
