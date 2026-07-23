<template>
  <div>
    <!-- 日历主体 -->
    <div class="card">
      <div class="calendar-header">
        <div class="week-nav">
          <el-button size="small" circle @click="prevWeek">&#9664;</el-button>
          <span class="week-range">{{ weekRangeText }}</span>
          <el-button size="small" circle @click="nextWeek">&#9654;</el-button>
          <el-button size="small" @click="goToday" style="margin-left: 8px;">今天</el-button>
        </div>
        <el-button type="primary" size="small" @click="openCreate">+ 新建</el-button>
      </div>

      <!-- 周网格 -->
      <div class="week-grid-wrapper">
        <div class="week-grid" ref="gridRef">
          <div class="grid-header">
            <div class="time-axis-header"></div>
            <div
              v-for="(day, di) in days"
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
            :class="{ 'current-hour': h === currentHour && isCurrentWeek }"
          >
            <div class="time-label">{{ pad2(h - 1) }}:00</div>
            <div
              v-for="(day, di) in days"
              :key="day.date"
              class="day-cell"
              :class="{ 'col-today': day.is_today }"
            >
              <div class="cell-events" v-if="day.hourGroups[h - 1]">
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
    <div class="card" v-if="consumedSessions.length">
      <div class="card-title">最近已消费 ({{ consumedSessions.length }})</div>
      <div v-for="sess in consumedSessions" :key="sess.session_id" class="session-group" style="cursor:pointer" @click="$emit('selectSession', sess.session_id)">
        <div class="session-head">
          <strong class="session-name">{{ sess.name || sess.session_id }}</strong>
          <span class="session-time">{{ sess.ended_at_display }}</span>
        </div>
        <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">
          <code>{{ sess.session_id }}</code> · {{ sess.source }} · {{ sess.message_count }}条 · {{ sess.tool_call_count }}次工具 · {{ sess.end_reason }}
        </div>
        <div v-if="sess.title" style="font-size:12px;color:var(--text-secondary);margin-top:2px;">{{ sess.title }}</div>
      </div>
    </div>

    <!-- 详情 Dialog -->
    <el-dialog v-model="detailVisible" :title="detailTitle" width="560px">
      <!-- 会话视图 -->
      <template v-if="detailSession">
        <div class="session-info">
          <code class="session-link" @click="detailVisible = false; $emit('selectSession', detailSession.session_id)">{{ detailSession.session_id }}</code>
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
      <!-- 普通事件视图 -->
      <template v-else-if="detailEvent">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="类型">{{ kindLabel(detailEvent.kind) }}</el-descriptions-item>
          <el-descriptions-item label="名称">{{ detailEvent.name }}</el-descriptions-item>
          <el-descriptions-item label="时间">{{ fmtDateTime(detailEvent.fire_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="detailEvent.description" label="说明">{{ detailEvent.description }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <template #footer>
        <el-button v-if="detailSession" type="primary" @click="detailVisible = false; $emit('selectSession', detailSession.session_id)">查看会话</el-button>
        <el-button v-else-if="detailEvent && !detailEvent.consumed && isEditableSource(detailEvent)" type="primary" @click="detailVisible = false; openEdit(detailEvent)">编辑</el-button>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 已消费事件列表（按 kind 展开） -->
    <el-dialog v-model="kindEventsVisible" :title="'已消费事件 - ' + kindLabel(kindEventsKind)" width="500px">
      <div v-for="(ev, i) in kindEvents" :key="i" class="more-item" @click="showConsumedEvent(ev)">
        <div class="more-item-head">
          <span>{{ kindLabel(ev.kind) }}</span>
          <span style="font-size: 11px; color: var(--text-muted); margin-left: auto;">{{ fmtDateTime(ev.consumed_at) }}</span>
        </div>
      </div>
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
          <el-select v-model="form.recurrence">
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
        <el-button type="primary" @click="save">保存</el-button>
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
import { ElMessage, ElMessageBox } from 'element-plus'

const emit = defineEmits(['selectSession', 'toast'])

const props = defineProps({
  apiBase: String,
  pad2: Function,
  fmtDateTime: Function,
})

const pad2 = props.pad2 || ((n) => String(n).padStart(2, '0'))
const fmtDateTime = props.fmtDateTime || ((v) => v || '')

const apiBase = computed(() => props.apiBase || window.__EMPLOYEE_CONSOLE__?.apiBase || '/api/employee')

const weekStart = ref(getMonday(new Date()))
const days = ref([])
const consumedSessions = ref([])
const currentHour = ref(new Date().getHours())
const gridRef = ref(null)

const dialogVisible = ref(false)
const isNew = ref(true)
const editingId = ref('')
const form = ref(makeForm())

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

const kindEventsVisible = ref(false)
const kindEventsKind = ref('')
const kindEvents = ref([])

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
  const parts = dateStr.split('-')
  return `${parseInt(parts[1])}/${parseInt(parts[2])}`
}

async function api(path, opts = {}) {
  const r = await fetch(apiBase.value + path, opts)
  const t = await r.text()
  try { return JSON.parse(t) } catch { return {} }
}

function cardClass(ev) {
  return 'kind-' + (ev.kind || 'other')
}

function cardStyle(group, index) {
  const total = Math.min(group.total, 3)
  const width = total > 0 ? (100 / total) : 100
  return {
    width: `calc(${width}% - 4px)`,
    flexShrink: 0,
  }
}

function formatDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

async function loadCalendar() {
  const ws = formatDate(weekStart.value)
  const d = await api('/calendar?week_start=' + ws)
  if (d.error) { ElMessage.error(d.error); return }

  for (const day of (d.days || [])) {
    day.hourGroups = {}
    for (const item of (day.items || [])) {
      const h = parseInt(item.time.split(':')[0])
      if (!day.hourGroups[h]) day.hourGroups[h] = []
      day.hourGroups[h].push(item)
    }
    for (const h of Object.keys(day.hourGroups)) {
      const group = day.hourGroups[h]
      group.sort((a, b) => a.time.localeCompare(b.time))
      const total = group.length
      group.total = total
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
    date: payload.date || item.fire_at?.slice(0, 10) || '',
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
  const recurrence = form.value.isAlarm ? 'once' : form.value.recurrence
  const body = {
    id: form.value.id, name: form.value.name, time: form.value.timeObj,
    description: form.value.description, prompt_template: form.value.prompt_template,
    recurrence, priority: form.value.priority, enabled: form.value.enabled,
  }
  if (form.value.isAlarm) body.date = form.value.date
  if (isNew.value) {
    const r = await api('/schedules', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    if (r.error) { ElMessage.error(r.error); return }
    ElMessage.success('创建成功')
  } else {
    const r = await api('/schedules/' + body.id, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    if (r.error) { ElMessage.error(r.error); return }
    ElMessage.success('更新成功')
  }
  dialogVisible.value = false
  await loadCalendar()
}

async function confirmDelete() {
  try {
    await ElMessageBox.confirm(`确定删除「${form.value.name}」？`, '确认删除', { type: 'warning' })
  } catch { return }
  await api('/schedules/' + form.value.id, { method: 'DELETE' })
  ElMessage.success('已删除')
  dialogVisible.value = false
  await loadCalendar()
}

function openItem(ev) {
  if (ev.kind === 'session') {
    detailSession.value = ev.payload || ev.session
    detailEvent.value = null
  } else {
    detailEvent.value = ev
    detailSession.value = null
  }
  detailVisible.value = true
}

function openEvent(ev) {
  openItem(ev)
}

function showMore(day, hour) {
  const group = day.hourGroups[hour]
  if (!group) return
  moreEvents.value = group.hidden
  moreVisible.value = true
}

function showConsumedEvent(ev) {
  detailEvent.value = {
    id: ev.event_id,
    kind: ev.kind,
    name: kindLabel(ev.kind),
    fire_at: ev.consumed_at,
    consumed: true,
    consumed_at: ev.consumed_at,
    payload: ev.payload,
  }
  detailSession.value = null
  detailVisible.value = true
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

function consumedKindTag(k) {
  if (k === 'message') return 'primary'
  if (k === 'nurture_energy') return 'success'
  if (k === 'vital_threshold') return 'danger'
  return 'info'
}

let hourTimer = null
onMounted(() => {
  loadCalendar()
  hourTimer = setInterval(() => { currentHour.value = new Date().getHours() }, 60000)
})

import { onUnmounted } from 'vue'
onUnmounted(() => { if (hourTimer) clearInterval(hourTimer) })

watch(weekStart, () => {
  loadCalendar()
})

watch(days, () => {
  nextTick(() => {
    setTimeout(() => {
      if (gridRef.value) gridRef.value.scrollTop = 7 * 60
    }, 100)
  })
})
</script>

<style scoped>
.card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.card-title { color: var(--text-primary); font-weight: 600; font-size: 14px; margin-bottom: 12px; }

.calendar-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
}
.week-nav { display: flex; align-items: center; gap: 4px; }
.week-range { font-size: 14px; font-weight: 600; color: var(--text-primary); min-width: 240px; text-align: center; }

.week-grid-wrapper { overflow-x: auto; }
.week-grid { display: grid; grid-template-columns: 56px repeat(7, 1fr); min-width: 960px; max-height: 650px; overflow-y: auto; }

.grid-header { display: contents; }
.time-axis-header { background: var(--bg-card); position: sticky; top: 0; z-index: 2; }
.day-header {
  text-align: center; padding: 8px 4px; font-size: 12px; position: sticky; top: 0;
  background: var(--bg-card); z-index: 2; border-bottom: 1px solid var(--border-color);
  min-width: 0; overflow: hidden;
}
.day-header.is-today { background: rgba(59, 130, 246, 0.12); }
.day-header.is-today .day-name { color: var(--primary); }
.col-today { background: rgba(59, 130, 246, 0.04); }
.day-name { font-weight: 600; color: var(--text-primary); }
.day-date { color: var(--text-muted); font-size: 11px; }

.grid-row { display: contents; }
.grid-row.current-hour .time-label { color: var(--primary); font-weight: 700; }
.grid-row.current-hour .day-cell { background: rgba(59, 130, 246, 0.03); }

.time-label {
  padding: 4px 8px; font-size: 11px; color: var(--text-muted); text-align: right;
  border-bottom: 1px solid var(--border-light, #eee); height: 60px; display: flex;
  align-items: flex-start; justify-content: flex-end; padding-top: 2px;
}

.day-cell {
  border-bottom: 1px solid var(--border-light, #eee); min-height: 60px;
  padding: 1px; position: relative; min-width: 0; overflow: hidden;
}
.cell-events { display: flex; flex-wrap: wrap; gap: 2px; padding: 2px; align-items: flex-start; }

.event-card {
  font-size: 11px; padding: 3px 5px; border-radius: 4px; cursor: pointer; overflow: hidden;
  white-space: nowrap; text-overflow: ellipsis; border-left: 3px solid; line-height: 1.5;
  background: rgba(255,255,255,0.7); transition: background 0.15s;
  display: flex; align-items: center; gap: 3px; min-width: 0;
}
.event-card:hover { background: rgba(59, 130, 246, 0.08); }
.event-card.consumed { opacity: 0.6; border-style: dashed; }
.card-time { font-weight: 600; color: var(--text-muted); font-size: 10px; flex-shrink: 0; }
.card-name { overflow: hidden; text-overflow: ellipsis; min-width: 0; }

.kind-routine { border-color: #3b82f6; color: #1d4ed8; }
.kind-alarm { border-color: #f59e0b; color: #b45309; }
.kind-vital_threshold { border-color: #ef4444; color: #b91c1c; }
.kind-task_reminder { border-color: #10b981; color: #047857; }
.kind-task_momentum { border-color: #8b5cf6; color: #6d28d9; }
.kind-timer { border-color: #6b7280; color: #374151; }
.kind-initiative { border-color: #06b6d4; color: #0e7490; }
.kind-message { border-color: #ec4899; color: #be185d; }
.kind-nurture_energy { border-color: #22c55e; color: #15803d; }
.kind-session { border-color: #6366f1; color: #4338ca; background: rgba(99, 102, 241, 0.06); }

.more-card {
  border-color: #9ca3af; color: var(--text-muted); font-weight: 600;
  justify-content: center; background: rgba(156, 163, 175, 0.1);
}

/* History */
.session-group { margin-bottom: 12px; padding: 8px; background: rgba(0,0,0,0.02); border-radius: 6px; }
.session-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.session-link { color: var(--primary); cursor: pointer; font-size: 12px; }
.session-link:hover { text-decoration: underline; }
.session-unknown { font-size: 11px; color: var(--text-muted); font-style: italic; }
.session-time { font-size: 11px; color: var(--text-muted); }
.session-kinds { display: flex; flex-wrap: wrap; gap: 2px; margin-top: 2px; }

.payload-pre {
  background: rgba(0,0,0,0.04); padding: 8px; border-radius: 4px;
  font-size: 11px; max-height: 200px; overflow-y: auto; margin: 0;
  white-space: pre-wrap; word-break: break-all;
}

.more-item {
  padding: 8px; border-bottom: 1px solid var(--border-color); cursor: pointer;
  border-radius: 4px; margin-bottom: 4px;
}
.more-item:hover { background: rgba(59, 130, 246, 0.06); }
.more-item-head { display: flex; align-items: center; gap: 6px; }

/* Session peers */
.section-label { font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
.session-info { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.peer-list { display: flex; flex-direction: column; gap: 6px; }
.peer-item {
  display: flex; align-items: center; gap: 6px; padding: 4px 8px;
  border-radius: 4px; background: rgba(0,0,0,0.03);
}
.peer-item:hover { background: rgba(59, 130, 246, 0.08); }
.peer-name { font-size: 12px; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.peer-time { font-size: 11px; color: var(--text-muted); flex-shrink: 0; margin-left: auto; }
</style>
