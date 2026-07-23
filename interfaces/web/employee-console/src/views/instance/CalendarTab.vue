<template>
  <div>
    <section class="page-hero">
      <div>
        <h1 class="page-title">Calendar</h1>
        <p class="page-subtitle">本周作息 / 闹钟 / 事件视图</p>
      </div>
      <div class="week-nav">
        <el-button size="small" circle @click="prevWeek">◀</el-button>
        <span class="week-range">{{ weekRangeText }}</span>
        <el-button size="small" circle @click="nextWeek">▶</el-button>
        <el-button size="small" @click="goToday" style="margin-left: 8px;">今天</el-button>
        <el-button type="primary" size="small" @click="openCreate">+ 新建</el-button>
      </div>
    </section>

    <!-- 周网格 -->
    <div class="neon-card week-card">
      <div class="week-grid-wrapper">
        <div class="week-grid" ref="gridRef">
          <div class="grid-header">
            <div class="time-axis-header"></div>
            <div
              v-for="day in days"
              :key="day.date"
              class="day-header"
              :class="{ 'is-today': day.is_today }"
            >
              <div class="day-name">{{ day.weekday }}</div>
              <div class="day-date">{{ dayDate(day.date) }}</div>
            </div>
          </div>
          <div
            v-for="h in 24"
            :key="h"
            class="grid-row"
            :class="{ 'current-hour': h - 1 === currentHour && isCurrentWeek }"
          >
            <div class="time-label">{{ pad2(h - 1) }}:00</div>
            <div
              v-for="day in days"
              :key="day.date"
              class="day-cell"
              :class="{ 'col-today': day.is_today }"
            >
              <div class="cell-events" v-if="day.hourGroups && day.hourGroups[h - 1]">
                <div
                  v-for="(ev, ei) in day.hourGroups[h - 1].visible"
                  :key="ev.id"
                  class="event-card"
                  :class="[cardClass(ev), { consumed: ev.consumed }]"
                  :style="cardStyle(day.hourGroups[h - 1], ei)"
                  @click="openItem(ev)"
                  :title="ev.time + ' ' + ev.name"
                >
                  <span class="card-time">{{ ev.time }}</span>
                  <span class="card-name">{{ ev.name }}</span>
                </div>
                <div
                  v-if="day.hourGroups[h - 1].hidden.length"
                  class="event-card more-card"
                  @click="showMore(day, h - 1)"
                >
                  +{{ day.hourGroups[h - 1].hidden.length }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 已消费会话 -->
    <div class="neon-card" v-if="consumedSessions.length">
      <h3 class="group-title">最近已消费 ({{ consumedSessions.length }})</h3>
      <div
        v-for="sess in consumedSessions"
        :key="sess.session_id"
        class="session-group"
        @click="goConsumed(sess)"
      >
        <div class="session-head">
          <strong class="session-name">{{ sess.name || sess.session_id }}</strong>
          <span class="session-time">{{ sess.ended_at_display }}</span>
        </div>
        <div class="brand-sub" style="font-size: 12px; margin-top: 2px; color: var(--text-muted);">
          <code class="mono">{{ sess.session_id }}</code>
          · {{ sess.message_count }} 条 · {{ sess.tool_call_count }} 次工具 · {{ sess.end_reason }}
        </div>
        <div v-if="sess.title" style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">{{ sess.title }}</div>
      </div>
    </div>

    <!-- 详情 Dialog -->
    <el-dialog v-model="detailVisible" :title="detailTitle" width="560px">
      <template v-if="detailSession">
        <div class="session-info">
          <code class="session-link mono" @click="goSession(detailSession.session_id)">{{ detailSession.session_id }}</code>
          <span class="session-time">{{ detailSession.ended_at_display }}</span>
        </div>
        <el-descriptions :column="1" border size="small" style="margin-top: 12px;">
          <el-descriptions-item label="来源">{{ detailSession.source }}</el-descriptions-item>
          <el-descriptions-item label="消息数">{{ detailSession.message_count }}</el-descriptions-item>
          <el-descriptions-item label="工具调用">{{ detailSession.tool_call_count }}</el-descriptions-item>
          <el-descriptions-item label="结束原因">{{ detailSession.end_reason }}</el-descriptions-item>
          <el-descriptions-item v-if="detailSession.title" label="标题">{{ detailSession.title }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <template v-else-if="detailEvent">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="类型">{{ kindLabel(detailEvent.kind) }}</el-descriptions-item>
          <el-descriptions-item label="名称">{{ detailEvent.name }}</el-descriptions-item>
          <el-descriptions-item label="时间">{{ detailEvent.fire_at }}</el-descriptions-item>
          <el-descriptions-item v-if="detailEvent.description" label="说明">{{ detailEvent.description }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <template #footer>
        <el-button v-if="detailSession" type="primary" @click="goSession(detailSession.session_id)">查看会话</el-button>
        <el-button v-else-if="detailEvent && !detailEvent.consumed && isEditableSource(detailEvent)" type="primary" @click="detailVisible = false; openEdit(detailEvent)">编辑</el-button>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 新建/编辑 Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isNew ? '新建日程' : '编辑日程'"
      width="560px"
      :close-on-click-modal="false"
    >
      <el-form label-width="80px" :model="form">
        <el-form-item label="类型">
          <el-radio-group v-model="form.isAlarm" :disabled="!isNew">
            <el-radio :value="false">作息（循环）</el-radio>
            <el-radio :value="true">闹钟（单次）</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="ID">
          <el-input v-model="form.id" :disabled="!isNew" placeholder="唯一标识，如 morning_plan" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="如 早起计划" />
        </el-form-item>
        <el-form-item v-if="form.isAlarm" label="日期">
          <el-date-picker v-model="form.date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="时间">
          <el-time-picker v-model="form.timeObj" format="HH:mm" value-format="HH:mm" placeholder="选择时间" style="width: 100%;" />
        </el-form-item>
        <el-form-item v-if="!form.isAlarm" label="循环规则">
          <el-select v-model="form.recurrence" style="width: 100%;">
            <el-option label="每天" value="daily" />
            <el-option label="工作日" value="weekdays" />
            <el-option label="周末" value="weekends" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" placeholder="简短说明" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="form.priority" :min="1" :max="10" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <el-form-item label="Prompt">
          <el-input v-model="form.prompt_template" type="textarea" :rows="3" placeholder="该日程触发时发送给模型的提示词" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button v-if="!isNew" type="danger" @click="confirmDelete" style="float: left;">删除</el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 查看更多 Dialog -->
    <el-dialog v-model="moreVisible" title="时间槽内更多事件" width="400px">
      <div v-for="ev in moreEvents" :key="ev.id" class="more-item" @click="openEvent(ev); moreVisible = false;">
        <div class="more-item-head">
          <strong>{{ ev.name }}</strong>
          <span style="font-size: 11px; color: var(--text-muted); margin-left: auto;">{{ ev.time }}</span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { instanceApi } from '@/api/client'

const route = useRoute()
const router = useRouter()
const iid = computed(() => String(route.params.iid || ''))

function pad2(n) { return String(n).padStart(2, '0') }

const weekStart = ref(getMonday(new Date()))
const days = ref([])
const consumedSessions = ref([])
const currentHour = ref(new Date().getHours())
const gridRef = ref(null)

const dialogVisible = ref(false)
const isNew = ref(true)
const editingId = ref('')
const form = ref(makeForm())
const saving = ref(false)

const detailVisible = ref(false)
const detailEvent = ref(null)
const detailSession = ref(null)

const detailTitle = computed(() => {
  if (detailSession.value) return detailSession.value.session_id
  if (detailEvent.value) return detailEvent.value.name || kindLabel(detailEvent.value.kind)
  return '详情'
})

const moreVisible = ref(false)
const moreEvents = ref([])

const isCurrentWeek = computed(() => {
  const monday = getMonday(new Date())
  return weekStart.value.toDateString() === monday.toDateString()
})

const weekRangeText = computed(() => {
  const end = new Date(weekStart.value)
  end.setDate(end.getDate() + 6)
  const sy = weekStart.value.getFullYear()
  const sm = weekStart.value.getMonth() + 1
  const sd = weekStart.value.getDate()
  const ey = end.getFullYear()
  const em = end.getMonth() + 1
  const ed = end.getDate()
  if (sy === ey) return `${sy}年 ${sm}月${sd}日 - ${em}月${ed}日`
  return `${sy}/${sm}/${sd} - ${ey}/${em}/${ed}`
})

function getMonday(d) {
  const date = new Date(d)
  const day = date.getDay()
  const diff = day === 0 ? -6 : 1 - day
  date.setDate(date.getDate() + diff)
  date.setHours(0, 0, 0, 0)
  return date
}

function prevWeek() {
  const d = new Date(weekStart.value)
  d.setDate(d.getDate() - 7)
  weekStart.value = d
}
function nextWeek() {
  const d = new Date(weekStart.value)
  d.setDate(d.getDate() + 7)
  weekStart.value = d
}
function goToday() {
  weekStart.value = getMonday(new Date())
}

function dayDate(dateStr) {
  const parts = String(dateStr || '').split('-')
  return `${parseInt(parts[1])}/${parseInt(parts[2])}`
}

function cardClass(ev) {
  return 'kind-' + (ev.kind || 'other')
}
function cardStyle(group, index) {
  const total = Math.min(group.total, 3)
  const width = total > 0 ? (100 / total) : 100
  return { width: `calc(${width}% - 4px)`, flexShrink: 0 }
}

function formatDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

async function loadCalendar() {
  const ws = formatDate(weekStart.value)
  const d = await instanceApi(iid.value).calendar(ws)
  if (d.error) { ElMessage.error(d.error); return }
  for (const day of (d.days || [])) {
    day.hourGroups = {}
    for (const item of (day.items || [])) {
      const h = parseInt(String(item.time || '0').split(':')[0])
      if (!day.hourGroups[h]) day.hourGroups[h] = []
      day.hourGroups[h].push(item)
    }
    for (const h of Object.keys(day.hourGroups)) {
      const group = day.hourGroups[h]
      group.sort((a, b) => String(a.time).localeCompare(String(b.time)))
      group.total = group.length
      group.visible = group.slice(0, 3)
      group.hidden = group.slice(3)
    }
  }
  days.value = d.days || []
  consumedSessions.value = d.consumed_sessions || []
}

function makeForm() {
  return {
    id: '', name: '', isAlarm: false, date: '', timeObj: '08:00',
    description: '', prompt_template: '', recurrence: 'daily',
    priority: 4, enabled: true,
  }
}

function openCreate() {
  isNew.value = true
  editingId.value = ''
  form.value = makeForm()
  dialogVisible.value = true
}

function openEdit(item) {
  isNew.value = false
  editingId.value = item.schedule_id || ''
  const payload = item.payload || {}
  const isAlarm = item.source === 'alarm' || payload.recurrence === 'once'
  form.value = {
    id: item.schedule_id || '',
    name: payload.name || item.name || '',
    isAlarm,
    date: payload.date || (item.fire_at ? String(item.fire_at).slice(0, 10) : ''),
    timeObj: item.time || payload.time || '08:00',
    description: payload.description || '',
    prompt_template: payload.prompt_template || '',
    recurrence: isAlarm ? 'daily' : (payload.recurrence || 'daily'),
    priority: payload.priority || 4,
    enabled: payload.enabled !== false,
  }
  dialogVisible.value = true
}

async function save() {
  if (!form.value.id) return ElMessage.warning('ID 不能为空')
  saving.value = true
  try {
    const recurrence = form.value.isAlarm ? 'once' : form.value.recurrence
    const body = {
      id: form.value.id, name: form.value.name, time: form.value.timeObj,
      description: form.value.description, prompt_template: form.value.prompt_template,
      recurrence, priority: form.value.priority, enabled: form.value.enabled,
    }
    if (form.value.isAlarm) body.date = form.value.date
    const api = instanceApi(iid.value)
    if (isNew.value) {
      const r = await api.createSchedule(body)
      if (r.error) { ElMessage.error(r.error); return }
      ElMessage.success('创建成功')
    } else {
      const r = await api.updateSchedule(body.id, body)
      if (r.error) { ElMessage.error(r.error); return }
      ElMessage.success('更新成功')
    }
    dialogVisible.value = false
    await loadCalendar()
  } finally { saving.value = false }
}

async function confirmDelete() {
  try {
    await ElMessageBox.confirm(`确定删除「${form.value.name}」？`, '确认删除', { type: 'warning' })
  } catch { return }
  await instanceApi(iid.value).deleteSchedule(form.value.id)
  ElMessage.success('已删除')
  dialogVisible.value = false
  await loadCalendar()
}

function openItem(ev) {
  if (ev.kind === 'session') {
    detailSession.value = ev.payload || ev.session || {}
    detailEvent.value = null
  } else {
    detailEvent.value = ev
    detailSession.value = null
  }
  detailVisible.value = true
}
function openEvent(ev) { openItem(ev) }

function showMore(day, hour) {
  const group = day.hourGroups[hour]
  if (!group) return
  moreEvents.value = group.hidden
  moreVisible.value = true
}

function isEditableSource(ev) {
  return ev.source === 'routine' || ev.source === 'alarm'
}

function kindLabel(k) {
  const labels = {
    routine: '作息', alarm: '闹钟', vital_threshold: '阈值', task_reminder: '任务',
    task_momentum: '惯性', message: '消息', timer: '定时', initiative: '探索',
    nurture_energy: '鸡腿', awaiting_reply: '等待回复', routine_reminder: '作息提醒',
  }
  return labels[k] || k
}

function goSession(sid) {
  // sid 可能是 string(session_id) — 优先用 wake_id(后端 calendar 解析好了),
  // 退化场景走 session_id(老 payload)
  detailVisible.value = false
  const wakeId = (detailEvent.value || {}).wake_id || (detailSession.value || {}).wake_id
  const targetWake = wakeId || sid
  if (targetWake) {
    router.push({ path: `/instance/${iid.value}/sessions`, query: { wake_id: targetWake } })
  } else {
    router.push(`/instance/${iid.value}/sessions`)
  }
}

function goConsumed(sess) {
  // consumed_sessions 列表点击入口 —— 也是优先 wake_id
  const target = sess.wake_id || sess.session_id
  if (target) {
    router.push({ path: `/instance/${iid.value}/sessions`, query: { wake_id: target } })
  } else {
    router.push(`/instance/${iid.value}/sessions`)
  }
}

let hourTimer = null
onMounted(() => {
  loadCalendar()
  hourTimer = setInterval(() => { currentHour.value = new Date().getHours() }, 60000)
})

import { onUnmounted } from 'vue'
onUnmounted(() => { if (hourTimer) clearInterval(hourTimer) })

watch(weekStart, () => { loadCalendar() })

watch(days, () => {
  nextTick(() => {
    setTimeout(() => {
      if (gridRef.value) gridRef.value.scrollTop = 7 * 60
    }, 100)
  })
})
</script>

<style scoped>
.page-hero {
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 12px; margin-bottom: var(--space-4);
}
.week-nav { display: flex; align-items: center; gap: 4px; }
.week-range {
  font-size: 13px; font-weight: 600; color: var(--text-primary);
  min-width: 220px; text-align: center;
  letter-spacing: 0.02em;
}

.week-card { padding: 12px; }
.week-grid-wrapper { overflow-x: auto; }
.week-grid {
  display: grid; grid-template-columns: 56px repeat(7, 1fr);
  min-width: 960px; max-height: 640px; overflow-y: auto;
}

.grid-header { display: contents; }
.time-axis-header { background: var(--bg-elevated); position: sticky; top: 0; z-index: 2; }
.day-header {
  text-align: center; padding: 8px 4px; font-size: 12px; position: sticky; top: 0;
  background: var(--bg-elevated); z-index: 2; border-bottom: 1px solid var(--border-divider);
  min-width: 0; overflow: hidden;
}
.day-header.is-today { background: color-mix(in oklab, var(--neon-cyan) 12%, var(--bg-elevated)); }
.day-header.is-today .day-name { color: var(--neon-cyan); }
.col-today { background: color-mix(in oklab, var(--neon-cyan) 4%, transparent); }
.day-name { font-weight: 600; color: var(--text-primary); }
.day-date { color: var(--text-muted); font-size: 11px; }

.grid-row { display: contents; }
.grid-row.current-hour .time-label { color: var(--neon-cyan); font-weight: 700; }
.grid-row.current-hour .day-cell { background: color-mix(in oklab, var(--neon-cyan) 3%, transparent); }

.time-label {
  padding: 4px 8px; font-size: 11px; color: var(--text-muted); text-align: right;
  border-bottom: 1px solid var(--border-divider); height: 60px; display: flex;
  align-items: flex-start; justify-content: flex-end; padding-top: 2px;
  font-family: var(--font-mono);
}

.day-cell {
  border-bottom: 1px solid var(--border-divider); min-height: 60px;
  padding: 1px; position: relative; min-width: 0; overflow: hidden;
}
.cell-events { display: flex; flex-wrap: wrap; gap: 2px; padding: 2px; align-items: flex-start; }

.event-card {
  font-size: 11px; padding: 3px 5px; border-radius: 4px; cursor: pointer; overflow: hidden;
  white-space: nowrap; text-overflow: ellipsis; border-left: 3px solid; line-height: 1.5;
  background: color-mix(in oklab, var(--bg-deep) 60%, transparent);
  transition: background 0.15s;
  display: flex; align-items: center; gap: 3px; min-width: 0;
}
.event-card:hover { background: color-mix(in oklab, var(--neon-cyan) 12%, transparent); }
.event-card.consumed { opacity: 0.55; border-style: dashed; }
.card-time { font-weight: 600; color: var(--text-muted); font-size: 10px; flex-shrink: 0; font-family: var(--font-mono); }
.card-name { overflow: hidden; text-overflow: ellipsis; min-width: 0; }

.kind-routine { border-color: #3b82f6; color: #93c5fd; }
.kind-alarm { border-color: #f59e0b; color: #fbbf24; }
.kind-vital_threshold { border-color: var(--neon-red); color: var(--neon-red); }
.kind-task_reminder { border-color: #10b981; color: #6ee7b7; }
.kind-task_momentum { border-color: #8b5cf6; color: #c4b5fd; }
.kind-timer { border-color: #6b7280; color: #d1d5db; }
.kind-initiative { border-color: var(--neon-cyan); color: var(--neon-cyan); }
.kind-message { border-color: #ec4899; color: #f9a8d4; }
.kind-nurture_energy { border-color: #22c55e; color: #86efac; }
.kind-session { border-color: #6366f1; color: #a5b4fc; background: rgba(99, 102, 241, 0.08); }

.more-card {
  border-color: #9ca3af; color: var(--text-muted); font-weight: 600;
  justify-content: center; background: rgba(156, 163, 175, 0.1);
}

.group-title {
  font-family: var(--font-display);
  font-size: 14px;
  color: var(--neon-cyan);
  letter-spacing: 0.05em;
  margin: 0 0 var(--space-3);
}

.session-group {
  margin-bottom: 12px; padding: 8px;
  background: color-mix(in oklab, var(--bg-deep) 50%, transparent);
  border-radius: 6px; cursor: pointer;
  transition: background 0.15s;
}
.session-group:hover {
  background: color-mix(in oklab, var(--neon-cyan) 10%, transparent);
}
.session-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.session-name {
  font-family: var(--font-display);
  font-size: 13px;
  color: var(--neon-cyan);
  letter-spacing: 0.03em;
}
.session-link { color: var(--neon-cyan); cursor: pointer; font-size: 12px; }
.session-time { font-size: 11px; color: var(--text-muted); }

.session-info { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }

.more-item {
  padding: 8px; border-bottom: 1px solid var(--border-divider); cursor: pointer;
  border-radius: 4px; margin-bottom: 4px;
}
.more-item:hover { background: color-mix(in oklab, var(--neon-cyan) 8%, transparent); }
.more-item-head { display: flex; align-items: center; gap: 6px; }
</style>
