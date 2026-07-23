<template>
  <div class="sessions-workbench">
    <aside class="sessions-sidebar">
      <div class="sessions-sidebar-head">
        <div>
          <div class="eyebrow">Wakes</div>
          <h2>Conversation runs</h2>
        </div>
        <el-tag size="small" effect="plain">{{ wakeTotal > 0 ? wakeTotal : auditWakes.length }}</el-tag>
      </div>

      <div class="wake-filter-bar">
        <el-radio-group v-model="wakeTypeFilter" size="small" @change="onWakeTypeFilterChange">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="group_message">群消息</el-radio-button>
          <el-radio-button label="message">私聊</el-radio-button>
          <el-radio-button label="timer">定时</el-radio-button>
          <el-radio-button label="task">任务</el-radio-button>
        </el-radio-group>
      </div>

      <div class="sessions-sidebar-list">
        <button
          v-for="w in pagedAuditWakes"
          :key="w.id"
          @click="selectWake(w.id)"
          class="session-list-item"
          :class="{ active: selectedWakeId === w.id }"
        >
          <span class="session-title">
            <span class="wake-num-small">#{{ w.wake_seq }}</span>
            【{{ wakeMetaLabel(w) }}】
            <span class="wake-snippet">{{ wakeFirstUserSnippet(w) }}</span>
          </span>
          <span class="session-meta">
            <span>{{ fmtWakeTime(w.started_at) }}</span>
            <el-tag v-if="wakeCallCount(w)" size="small" type="info" effect="plain" round>{{ wakeCallCount(w) }} calls</el-tag>
          </span>
        </button>

        <div v-if="!pagedAuditWakes.length && !wakeDetailLoading" class="no-more-hint" style="padding:24px 0">
          没有 wake 记录
        </div>
      </div>

      <div v-if="wakeTotal > 0" class="wake-pagination">
        <el-pagination
          v-model:current-page="wakeCurrentPage"
          :page-size="WAKE_PAGE_SIZE"
          :total="pagedWakeTotal"
          :pager-count="5"
          layout="prev, pager, next"
          small
          background
          @current-change="onWakePageChange"
        />
      </div>
    </aside>

    <main class="session-transcript">
      <div class="session-toolbar">
        <div class="toolbar-head">
          <div class="eyebrow">Transcript</div>
          <h2>{{ selectedSession ? sessionTitle(selectedSession) : 'Select a session' }}</h2>
        </div>
        <div class="session-metrics">
          <span class="metric"><el-icon><ChatLineRound /></el-icon>{{ messages.length }} messages</span>
          <span class="metric"><el-icon><Tools /></el-icon>{{ toolMessageCount }} tool events</span>
          <span v-if="auditWakes.length" class="metric"><el-icon><View /></el-icon>{{ auditWakes.length }} wakes</span>
          <a v-if="selectedSession && apiBase"
            :href="apiBase + '/sessions/' + selectedSession + '/raw'"
            target="_blank"
            class="raw-json-link"
            title="查看原始会话 JSON"
          >
            <el-icon><Document /></el-icon>原始 JSON
          </a>
        </div>

        <div v-if="consumedEvents && consumedEvents.length" class="consumed-events-bar">
          <div class="consumed-events-label">本轮消费事件</div>
          <div class="consumed-events-list">
            <el-tag
              v-for="ev in consumedEvents"
              :key="ev.event_id"
              size="small"
              :type="eventTagType(ev.kind)"
              effect="plain"
            >
              {{ ev.display_name || ev.kind }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- R3：基于新 audit DB 的 wake 视图 -->
      <div v-if="selectedWakeId" class="session-detail-view">
        <div v-if="wakeDetailLoading && !selectedWake" class="session-message-state">
          <el-icon class="rotating"><Loading /></el-icon>
          <span>加载中...</span>
        </div>
        <div v-else-if="error" class="session-message-state has-error">
          <el-icon><Warning /></el-icon>
          <span>{{ error }}</span>
        </div>
        <div v-else-if="!selectedWake" class="session-message-state">
          <span>未找到该 wake</span>
        </div>
        <template v-else>
          <div class="wake-card" :data-wake-id="selectedWake.id">
            <!-- wake 头部 -->
            <div class="wake-header">
              <div class="wake-header-left">
                <span class="wake-number">#{{ selectedWake.wake_seq }}</span>
                <el-tag size="small" :type="wakeMetaTagType(selectedWake)" effect="light">
                  {{ wakeMetaLabel(selectedWake) }}
                </el-tag>
                <span class="wake-ts">{{ fmtWakeTime(selectedWake.started_at) }}</span>
                <span class="wake-tail" v-if="selectedWake.ended_at">
                  · {{ durations(selectedWake.started_at, selectedWake.ended_at) }}
                </span>
                <span class="wake-tail" v-else> · 运行中</span>
              </div>
              <div class="wake-header-right" v-if="wakeCallCount(selectedWake)">
                <span class="metric-mini">{{ wakeCallCount(selectedWake) }} calls</span>
                <span class="metric-mini" v-if="countMsgs(selectedWake)"> · {{ countMsgs(selectedWake) }} turns</span>
              </div>
            </div>

            <!-- 系统说明 / Persona（每次 wake 一致，独立折叠展示） -->
            <div v-if="personaByWake[selectedWake.id]" class="wake-section">
              <div class="section-head" @click="toggleSection(selectedWake.id, 'persona')">
                <el-icon><component :is="expandedSections[`${selectedWake.id}:persona`] ? 'ArrowDown' : 'ArrowRight'" /></el-icon>
                <span class="section-title">🪪 系统说明（Persona）</span>
              </div>
              <div v-if="expandedSections[`${selectedWake.id}:persona`]" class="section-body">
                <ExpandableText :text="personaByWake[selectedWake.id]" :limit="200" :markdown="true" :render-fn="render" :external="toMsg({ role: 'system', content: personaByWake[selectedWake.id] })" />
              </div>
            </div>

            <!-- 系统注入的上下文（折叠/展开） -->
            <div v-if="injectionsByWake[selectedWake.id] && injectionsByWake[selectedWake.id].length" class="wake-section">
              <div class="section-head" @click="toggleSection(selectedWake.id, 'inj')">
                <el-icon><component :is="expandedSections[`${selectedWake.id}:inj`] ? 'ArrowDown' : 'ArrowRight'" /></el-icon>
                <span class="section-title">系统注入的上下文</span>
                <span class="section-count">{{ injectionsByWake[selectedWake.id].length }}</span>
              </div>
              <div v-if="expandedSections[`${selectedWake.id}:inj`]" class="section-body">
                <div v-for="inj in injectionsByWake[selectedWake.id]" :key="inj.id" class="inject-card">
                  <div class="inject-head">
                    <el-tag size="small" type="info" effect="plain" class="inject-kind">
                      {{ injectionSysToolLabel(inj.sys_tool) }}
                    </el-tag>
                    <span v-if="inj.scope_id && inj.scope_id !== '*'" class="inject-scope">@ {{ inj.scope_id.slice(0, 24) }}</span>
                  </div>
                  <ExpandableText :text="inj.content || ''" :limit="200" />
                </div>
              </div>
            </div>

            <!-- 真实回合流（user → assistant → tool → ...） -->
            <div v-if="turnsByWake[selectedWake.id]" class="wake-section">
              <div class="section-head" @click="toggleSection(selectedWake.id, 'flow')">
                <el-icon><component :is="expandedSections[`${selectedWake.id}:flow`] ? 'ArrowDown' : 'ArrowRight'" /></el-icon>
                <span class="section-title">对话流</span>
                <span class="section-count">{{ turnsByWake[selectedWake.id].length }}</span>
              </div>
              <div v-if="expandedSections[`${selectedWake.id}:flow`]" class="section-body flow-body">
                <template v-for="(t, idx) in turnsByWake[selectedWake.id]" :key="t.id || idx">
                  <!-- user action_prompt -->
                  <div v-if="t.role === 'user'" class="flow-block flow-event">
                    <div class="block-head">
                      <span class="block-label">💬 触发事件</span>
                      <span class="call-tag">call {{ t.llm_call_seq }}</span>
                      <el-button class="view-input-btn" size="small" text @click="openCallInput(selectedWake.id, t.llm_call_seq)">
                        <el-icon><Search /></el-icon>查看完整输入
                      </el-button>
                    </div>
                    <ExpandableText :text="t.content || ''" :limit="500" :markdown="true" :render-fn="render" :external="toMsg(t)" />
                  </div>
                  <!-- 普通工具调用 + 结果 可视化卡片 -->
                  <div
                    v-else-if="t.role === 'tool'"
                    class="flow-block flow-tool"
                    :class="{ 'flow-tool-special': isSpecialTool(t.tool_name) }"
                  >
                    <div class="block-head">
                      <span class="block-label">🔧 {{ toolPrettyName(t.tool_name) }}</span>
                      <span class="call-tag">call {{ t.llm_call_seq }}</span>
                      <span v-if="t.error" class="err-tag">⚠ 失败</span>
                    </div>
                    <!-- 特殊工具独立卡片 -->
                    <template v-if="t.tool_name === 'express_to_human'">
                      <ToolCardExpressToHuman :content="t.content || ''" :error="t.error" />
                    </template>
                    <template v-else-if="t.tool_name === 'terminal'">
                      <ToolCardTerminal :content="t.content || ''" :error="t.error" />
                    </template>
                    <template v-else-if="t.tool_name === 'record_thought'">
                      <ToolCardRecordThought :content="t.content || ''" :error="t.error" />
                    </template>
                    <template v-else>
                      <ExpandableText :text="t.content || ''" :limit="150" :mono="true" />
                      <div v-if="t.error" class="err-detail">⚠ {{ t.error }}</div>
                    </template>
                  </div>
                  <!-- 模型输出（带 tool_calls 占位 / 文本回复） -->
                  <div
                    v-else-if="t.role === 'assistant'"
                    class="flow-block flow-output"
                    :class="{ 'flow-output-thinking': !t.content }"
                  >
                    <div class="block-head">
                      <span class="block-label">{{ t.content ? '📤 输出' : '🤔 调用工具' }}</span>
                      <span class="call-tag">call {{ t.llm_call_seq }}</span>
                      <span class="tool-pills" v-if="parseTCNames(t.tool_calls).length">
                        <span v-for="n in parseTCNames(t.tool_calls)" :key="n" class="tool-pill">{{ n }}</span>
                      </span>
                      <el-button class="view-input-btn" size="small" text @click="openCallInput(selectedWake.id, t.llm_call_seq)">
                        <el-icon><Search /></el-icon>查看完整输入
                      </el-button>
                    </div>
                    <ExpandableText v-if="t.content" :text="t.content" :limit="400" :markdown="true" :render-fn="render" :external="toMsg(t)" />
                  </div>
                </template>
              </div>
            </div>
          </div>
        </template>
      </div>
      <div v-else class="empty-state">
        <el-icon><ChatDotRound /></el-icon>
        <div>请从左侧选择一个会话以查看详情</div>
      </div>
    </main>

    <!-- 右侧完整 input 抽屉 -->
    <aside class="input-drawer" :class="{ 'is-open': activeInputKey }">
      <div class="drawer-head">
        <div>
          <div class="eyebrow">LLM Call Input</div>
          <h3 v-if="activeInputMeta">
            Wake #{{ activeInputMeta.wakeSeq }} · Call {{ activeInputMeta.callSeq }}
            <span v-if="activeInputMeta.totalCalls" class="dim"> / {{ activeInputMeta.totalCalls }}</span>
          </h3>
        </div>
        <el-button text size="small" @click="closeCallInput" circle>
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
      <div v-if="callInputLoading" class="drawer-loading">
        <el-icon class="rotating"><Loading /></el-icon> 加载中...
      </div>
      <div v-else-if="activeInputMsgs && activeInputMsgs.length" class="drawer-list">
        <div
          v-for="(m, sIdx) in activeInputMsgs"
          :key="sIdx"
          class="drawer-row"
          :class="{ 'is-fake': m._is_fake, 'is-system': m.role === 'system' }"
        >
          <div class="drawer-role">
            <span class="role-pill" :class="roleClass(m)">{{ m.role }}{{ m.name ? '/' + m.name : '' }}{{ m._is_fake ? ' ¹' : '' }}</span>
          </div>
          <ExpandableText :text="m.content || ''" :limit="240" :mono="m.role === 'tool' || m._is_fake" :markdown="m.role === 'assistant' || m.role === 'system'" :render-fn="render" :external="toMsg({ ...m, role: 'assistant' })" />
        </div>
        <div class="drawer-legend">¹ = fake tool result（注入上下文，非真实模型调用）</div>
      </div>
      <div v-else class="drawer-empty">无可显示输入。</div>
    </aside>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ChatDotRound, ChatLineRound, Document, Loading, Tools, View, Warning, Search, Close, ArrowDown, ArrowRight } from '@element-plus/icons-vue'
import ContentActions from './ContentActions.vue'
import ExpandableText from './ExpandableText.vue'
import ToolCardExpressToHuman from './ToolCardExpressToHuman.vue'
import ToolCardTerminal from './ToolCardTerminal.vue'
import ToolCardRecordThought from './ToolCardRecordThought.vue'

const props = defineProps({
  sessions: Array,
  selectedSession: String,
  messages: Array,
  loading: Boolean,
  error: String,
  consumedEvents: Array,
  apiBase: String,
  loadMessages: Function,
  sessionTitle: Function,
  fmtTime: Function,
  roleLabel: Function,
  renderMarkdown: Function,
  toolCalls: Function,
  toolCallName: Function,
  toolCallArguments: Function,
  formatToolPayload: Function,
})

const selectedIdx = ref(-1)
const expandedSystem = ref(true)
const expandedTCs = reactive({})

const inspectorMsg = computed(() => {
  if (selectedIdx.value < 0 || !props.messages?.length) return null
  return props.messages[selectedIdx.value] || null
})

const toolMessageCount = computed(() => {
  try {
    return (props.messages || []).filter(m => m.role === 'tool' ||
      (typeof props.toolCalls === 'function' && props.toolCalls(m)?.length)).length
  } catch {
    return 0
  }
})

function eventTagType(kind) {
  if (kind === 'message') return 'primary'
  if (kind === 'group_message') return 'success'
  if (kind === 'timer') return 'warning'
  return ''
}

// Forward session click to App.vue's loadMessages (legacy path; new wake data
// is fetched separately via loadAuditWakesForSession below).
function selectSession(sid) {
  if (typeof props.loadMessages === 'function') {
    props.loadMessages(sid)
  }
}

// 用户点击左侧某一 wake → 高亮选中并确保 turns/injections 已拉取。
function selectWake(wakeId) {
  selectedWakeId.value = wakeId
  // 默认展开 sections
  if (!(expandedSections[`${wakeId}:inj`] === false)) expandedSections[`${wakeId}:inj`] = true
  if (!(expandedSections[`${wakeId}:flow`] === false)) expandedSections[`${wakeId}:flow`] = true
  // 拉详情（如果还没拉过）
  if (!turnsByWake[wakeId]) fetchWakeDetail(wakeId)
}

// 让左侧列表显示 wake 的内容摘要：找到该 wake 的第一条 user action_prompt，
// 抽 60 字符作为 snippet。
function wakeFirstUserSnippet(w) {
  // 优先从 wake prompt 第一行之外提取"真实摘要"，避免显示 markdown header 噪音。
  const turns = turnsByWake[w.id]
  if (!turns || !turns.length) {
    // turn 还没加载——退到 wake.meta_json 取 reason / text
    const meta = typeof w?.meta_json === 'string' ? safeJson(w?.meta_json) : (w?.meta_json || {})
    const payload = meta?.payload || {}
    const reason = payload.reason || payload.mental_context || payload.text || ''
    return reason ? truncate(stripMd(reason), 60) : ''
  }
  for (const t of turns) {
    if (t.role === 'user' && t.content) {
      // 1. 去 markdown：## 标题 / *粗体* / `-`-列表 / 引用块等
      const stripped = stripMd(t.content)
      // 2. 跳过 wake prompt 通用前缀（"当下事件 / 唤醒原因 / 你醒了 / 系统提示"等）
      const meaningful = stripPromptPrefix(stripped)
      // 3. 多空白压成一格 + 截断
      const s = meaningful.replace(/\s+/g, ' ').trim()
      if (!s) continue
      return s.length > 60 ? s.slice(0, 60) + '…' : s
    }
  }
  return ''
}

function stripMd(s) {
  return (s || '')
    .replace(/^#{1,6}\s+/gm, '')   // ## 标题
    .replace(/\*\*(.+?)\*\*/g, '$1')  // **粗体**
    .replace(/__(.+?)__/g, '$1')      // __粗体__
    .replace(/[`*_-]/g, m => (m === '`' || m === '*' || m === '_' || m === '-') ? '' : m)
    .replace(/^\s*[-*+]\s+/gm, '')     // 列表项
    .replace(/^\s*>\s?/gm, '')          // 引用
}

function stripPromptPrefix(s) {
  const noisePrefixes = [
    /^[\s]*──[^─]+───?[\s]*/,        // "── ↓ 当下事件 ↓ ──"
    /^[\s]*当下事件[\s:]*/,
    /^[\s]*唤醒原因[\s:]*/,
    /^[\s]*###\s*唤醒原因[\s:]*/,
    /^[\s]*##\s*[^如果][^\n]{0,30}\n/m,
    /^[\s]*你醒了[。，]?/,
    /^[\s]*系统提示[\s:]*/,
  ]
  let out = s
  for (const re of noisePrefixes) {
    out = out.replace(re, '')
  }
  return out.trim()
}

function truncate(s, n) {
  return s.length > n ? s.slice(0, n) + '…' : s
}

// ─── 新 audit 数据：load wakes / turns / injections ───
const WAKE_PAGE_SIZE = 30
const auditWakes = ref([])
const wakeTotal = ref(0)
const wakeCurrentPage = ref(1)
const wakeHasMore = ref(false)   // 保留供向后兼容；现在用 total 计算分页
const wakeLoadingMore = ref(false)
const turnsByWake = reactive({})  // wake_id -> turns[]
const injectionsByWake = reactive({})  // wake_id -> injections[]
const personaByWake = reactive({})  // wake_id -> persona text
const wakeDetailLoading = ref(false)
const callInputCache = reactive({})  // "wake_id:call_seq" -> msgs[]
const callInputLoading = ref(false)
const expandedSections = reactive({})  // "wake_id:section_key" -> bool
// 右侧抽屉状态
const activeInputKey = ref(null)  // "wake_id:call_seq"
const activeInputMeta = ref(null)  // { wakeSeq, callSeq, totalCalls }
// 当前选中的 wake
const selectedWakeId = ref(null)

// wake 类型过滤（纯前端过滤 auditWakes，不动后端）
// ''=全部；'group_message' / 'message' / 'timer' / 'task' 前缀匹配 trigger_type
// 'task' 是合 Cluster task_reminder / task_todo_due / task_momentum 多种 task_* 前缀
const wakeTypeFilter = ref('')

const selectedWake = computed(() => auditWakes.value.find(w => w.id === selectedWakeId.value) || null)

// 过滤后的 wake（按 wake_type_filter 过 trigger_type）
const filteredAuditWakes = computed(() => {
  const f = wakeTypeFilter.value
  if (!f) return auditWakes.value
  return auditWakes.value.filter(w => {
    let meta = w.meta_json
    if (typeof meta === 'string') { try { meta = JSON.parse(meta || '{}') } catch { meta = {} } }
    const t = (meta && (meta.trigger_type || meta.kind || '')) || ''
    if (f === 'task') return t.startsWith('task')
    return t === f
  })
})

// 当前页要显示的 wake 列表（按 wake_seq 倒序后切片）
const pagedAuditWakes = computed(() => {
  const sorted = [...filteredAuditWakes.value].sort((a, b) => (b.wake_seq ?? 0) - (a.wake_seq ?? 0))
  // 过滤时分页仍然按总 length 算，但 slice 范围限制在内
  const total = sorted.length
  const start = (wakeCurrentPage.value - 1) * WAKE_PAGE_SIZE
  return sorted.slice(start, start + WAKE_PAGE_SIZE)
})

// 过滤模式下分页 total 用过滤后的数量
const pagedWakeTotal = computed(() => {
  if (!wakeTypeFilter.value) return wakeTotal.value
  return filteredAuditWakes.value.length
})

function onWakeTypeFilterChange() {
  // 切换过滤时重置到第 1 页，并自动选第一条可见的 wake
  wakeCurrentPage.value = 1
  if (pagedAuditWakes.value.length) {
    selectedWakeId.value = pagedAuditWakes.value[0].id
  }
}

// 拉取第一页（最新 N 条），自动刷新时调
async function loadAuditWakesForSession() {
  if (!props.apiBase) { auditWakes.value = []; return }
  if (wakeLoadingMore.value) return  // 正在加载更多时不刷新首页
  wakeDetailLoading.value = true
  try {
    // 只取第 1 页 + 1 个 buffer 页（最多 2 * WAKE_PAGE_SIZE 条），减少传输
    const r = await fetch(`${props.apiBase}/wakes?limit=${WAKE_PAGE_SIZE * 2}&offset=0`)
    const d = await r.json()
    const newWakes = d.wakes || []
    wakeTotal.value = d.total || 0
    wakeHasMore.value = d.has_more || false
    // 整体替换：原来是"首页 + 旧用户加载更多"的合并集合，现在改成统一缓存，
    // onWakePageChange 会按需补拉缺失的页。第一次加载就用 newWakes 全量替换。
    auditWakes.value = newWakes
    // eslint-disable-next-line no-console
    console.log('[SessionsTab] loaded wakes page 1:', newWakes.length, 'total:', wakeTotal.value)
    // 默认选中最新一条 wake（如果没选过/或选中的被清掉）。
    if (newWakes.length) {
      if (!selectedWakeId.value || !auditWakes.value.find(w => w.id === selectedWakeId.value)) {
        selectedWakeId.value = newWakes[0].id
      }
    } else {
      selectedWakeId.value = null
    }
    // 详细拉首页每个 wake 的 turns + injections（只为当前可见的拉）
    for (const w of pagedAuditWakes.value) {
      if (!turnsByWake[w.id]) fetchWakeDetail(w.id)
    }
  } catch (e) {
    // eslint-disable-next-line no-console
    console.error('[SessionsTab] loadAuditWakesForSession failed', e)
  } finally {
    wakeDetailLoading.value = false
  }
}

// 翻页：如果目标页的数据还没在 auditWakes 里（超出已加载 buffer），就拉一次
async function onWakePageChange(page) {
  const start = (page - 1) * WAKE_PAGE_SIZE
  if (start >= auditWakes.value.length) {
    // 需要补拉
    wakeLoadingMore.value = true
    try {
      const r = await fetch(`${props.apiBase}/wakes?limit=${WAKE_PAGE_SIZE}&offset=${start}`)
      const d = await r.json()
      const olderWakes = d.wakes || []
      wakeTotal.value = d.total || 0
      // 合并去重
      const existingIds = new Set(auditWakes.value.map(w => w.id))
      const merged = [...auditWakes.value]
      for (const w of olderWakes) {
        if (!existingIds.has(w.id)) merged.push(w), existingIds.add(w.id)
      }
      auditWakes.value = merged
    } catch (e) {
      console.error('[SessionsTab] onWakePageChange load failed', e)
    } finally {
      wakeLoadingMore.value = false
    }
  }
  // 当前页的详情如未拉则批量拉
  const sorted = [...auditWakes.value].sort((a, b) => (b.wake_seq ?? 0) - (a.wake_seq ?? 0))
  const pageWakes = sorted.slice(start, start + WAKE_PAGE_SIZE)
  for (const w of pageWakes) {
    if (!turnsByWake[w.id]) fetchWakeDetail(w.id)
  }
  // 翻页后回到列表顶部
  nextTick(() => {
    const scroller = document.querySelector('.sessions-sidebar-list')
    if (scroller) scroller.scrollTop = 0
  })
}

async function fetchWakeDetail(wakeId) {
  try {
    const r = await fetch(`${props.apiBase}/wakes/${wakeId}`)
    const d = await r.json()
    if (d.error) return
    turnsByWake[wakeId] = d.turns || []
    injectionsByWake[wakeId] = (d.injections || []).filter(i => i.injected_before_call === 0)
    // eslint-disable-next-line no-console
    console.log('[SessionsTab] fetched detail wake', wakeId, 'turns=', turnsByWake[wakeId].length, 'inj=', injectionsByWake[wakeId].length)
    // 拉一次 LLM call 0 的 input 拿 system prompt
    fetchWakePersona(wakeId)
    // 默认展开此 wake（首次拉到详情时）。
    const injKey = `${wakeId}:inj`
    const flowKey = `${wakeId}:flow`
    const personaKey = `${wakeId}:persona`
    if (!(injKey in expandedSections)) expandedSections[injKey] = true
    if (!(flowKey in expandedSections)) expandedSections[flowKey] = true
    if (!(personaKey in expandedSections)) expandedSections[personaKey] = false  // persona 默认收起
  } catch (e) {
    // eslint-disable-next-line no-console
    console.error('[SessionsTab] fetchWakeDetail failed', wakeId, e)
  }
}

async function fetchWakePersona(wakeId) {
  if (personaByWake[wakeId]) return  // cached
  try {
    const r = await fetch(`${props.apiBase}/wakes/${wakeId}/input/0`)
    const d = await r.json()
    const msgs = d.messages || []
    if (msgs.length && msgs[0].role === 'system') {
      personaByWake[wakeId] = msgs[0].content || ''
    }
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn('[SessionsTab] fetchWakePersona failed', wakeId, e)
  }
}

function wakeCallCount(wake) {
  if (!wake?.meta_json) return 0
  const meta = typeof selectedWake.meta_json === 'string' ? safeJson(selectedWake.meta_json) : selectedWake.meta_json
  return meta?.llm_call_count || 0
}

function countMsgs(wake) {
  return turnsByWake[selectedWake.id]?.length || 0
}

function toggleSection(wakeId, key) {
  const k = `${wakeId}:${key}`
  expandedSections[k] = !expandedSections[k]
}

async function openCallInput(wakeId, callSeq) {
  // 找到对应 wake 以填 meta
  const w = auditWakes.value.find(x => x.id === wakeId)
  const key = `${wakeId}:${callSeq}`
  activeInputKey.value = key
  activeInputMeta.value = {
    wakeSeq: w?.wake_seq ?? '?',
    callSeq,
    totalCalls: w ? wakeCallCount(w) : 0,
  }
  // 让被点击的 wake card 在「右侧 transcript 面板」内滚动到可见，
  // 而非触发整页滚动（避免拖得用户找不到列表入口）。
  nextTick(() => {
    const detail = document.querySelector('.session-detail-view')
    const el = document.querySelector(`.wake-card[data-wake-id="${wakeId}"]`)
    if (detail && el && el.scrollIntoView) {
      // 用 relative + block:nearest，让浏览器只在最近的可滚动祖先里滚动
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  })
  if (callInputCache[key]) return
  callInputLoading.value = true
  try {
    const r = await fetch(`${props.apiBase}/wakes/${wakeId}/input/${callSeq}`)
    const d = await r.json()
    callInputCache[key] = d.messages || []
  } catch (e) {
    callInputCache[key] = []
  } finally {
    callInputLoading.value = false
  }
}

function closeCallInput() {
  activeInputKey.value = null
  activeInputMeta.value = null
}

const activeInputMsgs = computed(() => {
  if (!activeInputKey.value) return null
  return callInputCache[activeInputKey.value] || null
})

// 切 session（实例） 时刷新 audit 数据
watch(() => props.selectedSession, () => {
  if (props.selectedSession) {
    selectedWakeId.value = null
    wakeCurrentPage.value = 1   // 切实例时重置到首页
    wakeTotal.value = 0
    wakeHasMore.value = false
    Object.keys(turnsByWake).forEach(k => delete turnsByWake[k])
    Object.keys(injectionsByWake).forEach(k => delete injectionsByWake[k])
    loadAuditWakesForSession()
  }
})
// 进入 sessions tab：mount 时立刻拉 wakes（无论 selectedSession 是否已设）。
let _refreshTimer = null
onMounted(() => {
  loadAuditWakesForSession()
  // 新 wake 会持续写入；每 12s 刷新一次。**只在第 1 页**刷新，
  // 否则用户翻到历史页时会被强制弹回第 1 页。
  _refreshTimer = setInterval(() => {
    if (wakeCurrentPage.value === 1) {
      loadAuditWakesForSession()
    }
  }, 12000)
})
onUnmounted(() => {
  if (_refreshTimer) clearInterval(_refreshTimer)
})

// ─── 格式化辅助 ───
function truncated(s, n=200) {
  const v = (s || '').toString()
  return v.length > n ? v.slice(0, n) + '…' : v
}
function safeJson(s) {
  try { return JSON.parse(s) } catch { return {} }
}
function fmtWakeTime(ts) {
  if (!ts) return ''
  return props.fmtTime ? props.fmtTime(ts) : String(ts)
}
function durations(start, end) {
  if (!start || !end) return ''
  const s = Math.round((end - start) * 10) / 10
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  return `${m}m${Math.round(s - m * 60)}s`
}
function wakeMetaLabel(wake) {
  // 用参数 wake 而不是 selectedWake——否则列表所有行都显示同一个 label。
  const w = wake || {}
  const meta = typeof w.meta_json === 'string' ? safeJson(w.meta_json) : (w.meta_json || {})
  const t = meta?.trigger_type || meta?.reason || meta?.prompt_reason || ''
  const kind = meta?.kind || ''
  if (t === 'group_message' || kind === 'group_message') return '群消息'
  if (t === 'message' || kind === 'message') return '私聊'
  if (t === 'initiative' || kind === 'initiative') return '主动探索'
  if (t === 'timer' || kind === 'timer') return '定时器'
  if (t === 'routine' || kind === 'routine') return '作息'
  if (t === 'task_todo_due' || kind === 'task_todo_due') return '任务到期'
  if (t === 'awaiting_reply' || kind === 'awaiting_reply') return '等回复'
  if (t === 'birth' || kind === 'birth') return '初次醒来'
  if (t === 'daily_item' || kind === 'daily_item') return '今日计划'
  if (t === 'vital_threshold' || kind === 'vital_threshold') return '精力预警'
  if (t === 'nurture_energy' || kind === 'nurture_energy') return '加鸡腿'
  return t || kind || '事件'
}
function wakeMetaTagType(wake) {
  const l = wakeMetaLabel(wake)
  if (l === '群消息') return 'success'
  if (l === '私聊') return 'primary'
  if (l === '主动探索') return 'warning'
  if (l === '定时器') return 'info'
  return ''
}
function injectionSysToolLabel(t) {
  return ({
    system_context: '系统上下文',
    session_digest: '最近经历',
    consciousness: '休息前思绪',
    social_context: '社交关系',
    task_skill: '任务方法论',
    my_context: '我的待办+项目',
    task_board: '任务看板',
    chat_stream: '对话流水',
    wake_signal: '唤醒信号',
    entity_recall: '记忆联想',
  })[t] || t
}
function parseTCNames(tcs) {
  if (!Array.isArray(tcs)) return []
  return tcs.map(tc => tc?.function?.name || tc?.name || '').filter(Boolean)
}
const SPECIAL_TOOLS = new Set(['express_to_human', 'terminal', 'record_thought'])
function isSpecialTool(name) {
  return name && SPECIAL_TOOLS.has(name)
}
const TOOL_PRETTY = {
  express_to_human: '面向人类发送',
  record_thought: '记录思绪',
  write_diary: '写日记',
  rest: '休息',
  search_history: '搜记忆',
  read_archive: '读归档',
  update_scratchpad: '记草稿',
  remember_him: '记住他',
  terminal: '执行命令',
  execute_code: '执行代码',
}
function toolPrettyName(n) {
  return TOOL_PRETTY[n] || n || '工具'
}
function roleClass(m) {
  if (m._is_fake) return 'fake'
  if (m.role === 'system') return 'system'
  if (m.role === 'user') return 'user'
  if (m.role === 'assistant') return 'assistant'
  return 'tool'
}
function toMsg(t) {
  const role = t.role === 'user' ? 'user' : (t.role === 'system' ? 'system' : 'assistant')
  return {
    role,
    content: t.content || '',
    tool_calls: t.tool_calls || undefined,
    tool_name: t.tool_name || t.name || undefined,
  }
}
// Markdown 渲染 wrapper —— 直接调 props.renderMessageMarkdown 不能在模板里裸用。
function render(t) {
  if (typeof props.renderMessageMarkdown !== 'function') return ''
  try {
    return props.renderMessageMarkdown(toMsg(t)) || ''
  } catch (e) {
    return ''
  }
}
</script>

<style scoped>
.sessions-workbench {
  display: grid;
  grid-template-columns: 260px 1fr auto;
  /* 父链上 .main-content { overflow-y: auto } + .content-view 无显式高度，
     导致 height:100% 失效、整体随 main 滚动。用 viewport-bound 高度绕开：
     给 sessions tab 一个稳定的内部滚动容器。
     160px ≈ 顶部 header + main padding 的估算，留点余量。 */
  height: calc(100vh - 160px);
  min-height: 360px;   /* 极小屏幕保底 */
  min-height: 0;       /* 让 grid 子项可以收缩；父级 el-main 高度约束生效关键 */
  gap: 16px;
  padding: 16px;
  background: var(--app-bg, #f5f7fa);
  overflow: hidden;  /* 整个工作台本身不滚 — 滚动只发生在 sidebar/transcript 内 */
}
.sessions-workbench:has(.input-drawer.is-open) {
  grid-template-columns: 240px 1fr 380px;
}.sessions-sidebar {
  background: var(--app-surface, #fff);
  border-radius: 10px;
  border: 1px solid var(--app-border, #e4e7ed);
  padding: 12px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
  min-height: 0;       /* flex 内部子元素才能 overflow:auto */
  overflow: hidden;
}
.sessions-sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-shrink: 0;     /* head 不缩，list 占用剩余高度 */
}
.wake-filter-bar {
  flex-shrink: 0;
  margin-bottom: 10px;
  display: flex;
  justify-content: center;
}
.wake-filter-bar :deep(.el-radio-button__inner) {
  padding: 4px 10px;
  font-size: 12px;
}
/* 新增：列表本身内部滚动，整个 sidebar 高度由父级约束 */
.sessions-sidebar-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
}
.wake-pagination {
  flex-shrink: 0;
  padding: 10px 4px 4px;
  border-top: 1px solid var(--app-border, #ebeef5);
  display: flex;
  justify-content: center;
  background: #fff;
}
.wake-pagination :deep(.el-pagination) {
  --el-pagination-button-width: 24px;
  --el-pagination-button-height: 24px;
}
.wake-pagination :deep(.el-pager li),
.wake-pagination :deep(.btn-prev),
.wake-pagination :deep(.btn-next) {
  min-width: 24px;
  height: 24px;
  line-height: 24px;
  font-size: 12px;
}
.sessions-sidebar-head h2 {
  margin: 4px 0 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2329;
}
.sessions-sidebar-head .eyebrow {
  font-size: 11px;
  letter-spacing: 0.8px;
  color: #909399;
  text-transform: uppercase;
}
.session-list-item {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  width: 100%;
  text-align: left;
  border: 1px solid transparent;
  background: transparent;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 4px;
  cursor: pointer;
  font: inherit;
  color: inherit;
  transition: all 0.15s;
}
.session-list-item:hover {
  background: #f5f7fa;
  transform: translateX(2px);
}
.session-list-item.active {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.08);
  box-shadow: 0 1px 4px rgba(64, 158, 255, 0.15);
}
.no-more-hint {
  font-size: 12px;
  color: #909399;
}
.session-title {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #1f2329;
}
.wake-num-small {
  display: inline-block;
  font-weight: 600;
  color: #409eff;
  margin-right: 2px;
}
.wake-snippet {
  color: #606266;
  font-size: 12px;
}
.session-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: #909399;
}

.session-transcript {
  background: var(--app-surface, #fff);
  border-radius: 10px;
  border: 1px solid var(--app-border, #e4e7ed);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}
.session-toolbar {
  padding: 14px 20px;
  border-bottom: 1px solid var(--app-border, #e4e7ed);
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: linear-gradient(to bottom, #fafbfc, #fff);
}
.toolbar-head {
  display: flex;
  flex-direction: column;
}
.session-toolbar h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2329;
}
.session-toolbar .eyebrow {
  font-size: 11px;
  color: #909399;
  letter-spacing: 0.8px;
  text-transform: uppercase;
}
.session-metrics {
  display: flex;
  gap: 16px;
  align-items: center;
  font-size: 12px;
  color: #606266;
}
.metric { display: inline-flex; align-items: center; gap: 4px; }
.raw-json-link {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  text-decoration: none;
  color: #409eff;
  font-size: 12px;
}
.consumed-events-bar {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 4px;
}
.consumed-events-label {
  font-size: 11px;
  color: #909399;
}
.consumed-events-list {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.session-detail-view {
  padding: 18px;
  overflow-y: auto;
  flex: 1;
}
.session-message-state {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 48px;
  color: #909399;
  justify-content: center;
  font-size: 13px;
}
.session-message-state.has-error { color: #f56c6c; }
.rotating { animation: rotate 1.4s linear infinite; }
@keyframes rotate {
  from { transform: rotate(0); }
  to { transform: rotate(360deg); }
}

/* Wake cards */
.wake-card {
  border: 1px solid var(--app-border, #e4e7ed);
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 14px;
  background: #fafbfc;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
  transition: box-shadow 0.15s;
}
.wake-card:hover { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); }

.wake-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  flex-wrap: wrap;
  gap: 8px;
}
.wake-header-left { display: flex; align-items: center; gap: 8px; }
.wake-header-right {
  display: flex;
  gap: 4px;
  align-items: center;
  font-size: 11px;
  color: #909399;
}
.wake-number {
  font-weight: 700;
  font-size: 15px;
  background: linear-gradient(135deg, #409eff, #67c23a);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.metric-mini { color: #909399; }
.wake-ts {
  font-size: 11px;
  color: #909399;
  font-family: 'Menlo', monospace;
}
.wake-tail { font-size: 11px; color: #c0c4cc; }

.wake-section { margin-top: 10px; }
.section-head {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: #606266;
  transition: background 0.12s;
  user-select: none;
}
.section-head:hover { background: rgba(0,0,0,0.03); }
.section-title { font-weight: 500; }
.section-count {
  background: rgba(0, 0, 0, 0.05);
  color: #606266;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 8px;
}
.section-body {
  padding: 10px 12px;
  margin-top: 6px;
  background: #fff;
  border-radius: 6px;
  border: 1px solid var(--app-border, #ebeef5);
}

/* Injection cards (slow_ctx) */
.inject-card {
  background: #fff;
  border-left: 3px solid #909399;
  border-radius: 0 4px 4px 0;
  padding: 6px 10px;
  margin-bottom: 6px;
  font-size: 12px;
  line-height: 1.55;
}
.inject-head {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 4px;
}
.inject-kind { font-weight: 500; }
.inject-scope {
  font-size: 10px;
  color: #909399;
  font-family: 'Menlo', monospace;
}

/* Flow blocks */
.flow-body {
  padding: 0;
  background: transparent;
  border: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: visible;
}
.flow-block {
  border: 1px solid var(--app-border, #ebeef5);
  border-radius: 8px;
  padding: 8px 12px;
  background: #fff;
  transition: background 0.12s;
}
.flow-event {
  background: linear-gradient(180deg, #f0f9ff, #fff);
  border-left: 3px solid #67c23a;
}
.flow-output {
  background: #fff;
  border-left: 3px solid #409eff;
}
.flow-output-thinking {
  background: #fafafa;
  border-left: 3px solid #c0c4cc;
}
.flow-tool {
  background: #fffaf3;
  border-left: 3px solid #e6a23c;
}
.flow-tool-special {
  background: linear-gradient(180deg, #fffbf0, #fff);
  border-left: 3px solid #f56c6c;
}
.block-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}
.block-label {
  font-size: 12px;
  font-weight: 500;
  color: #303133;
}
.call-tag {
  display: inline-block;
  padding: 1px 5px;
  font-size: 10px;
  border-radius: 3px;
  background: rgba(0,0,0,0.05);
  color: #909399;
  font-family: 'Menlo', monospace;
}
.tool-pills { display: inline-flex; gap: 3px; flex-wrap: wrap; }
.tool-pill {
  display: inline-block;
  padding: 1px 6px;
  font-size: 10px;
  font-family: 'Menlo', monospace;
  background: rgba(230, 162, 60, 0.12);
  color: #b88230;
  border-radius: 3px;
}
.view-input-btn {
  margin-left: auto;
  color: #409eff;
  font-size: 11px;
}
.err-tag {
  font-size: 11px;
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.1);
  padding: 1px 5px;
  border-radius: 3px;
}
.err-detail {
  margin-top: 4px;
  font-size: 12px;
  color: #f56c6c;
  font-family: 'Menlo', monospace;
  background: rgba(245, 108, 108, 0.06);
  padding: 4px 6px;
  border-radius: 4px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #909399;
}
.empty-state .el-icon { font-size: 32px; }

.debug-banner {
  background: #fff3cd;
  border: 1px solid #ffe08a;
  color: #8a6d3b;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-family: 'Menlo', monospace;
  margin-bottom: 8px;
  word-break: break-all;
}

/* Right drawer for call input — fixed overlay so main scroll stays intact. */
.input-drawer {
  position: fixed;
  top: 16px;
  right: 16px;
  bottom: 16px;
  width: 420px;
  max-width: calc(100vw - 32px);
  background: #fff;
  border-radius: 10px;
  border: 1px solid var(--app-border, #e4e7ed);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  z-index: 100;
  transform: translateX(calc(100% + 24px));
  opacity: 0;
  pointer-events: none;
  transition: transform 0.2s ease-out, opacity 0.2s;
}
.input-drawer.is-open {
  transform: translateX(0);
  opacity: 1;
  pointer-events: auto;
}
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 14px 14px 10px;
  margin-bottom: 0;
  border-bottom: 1px solid var(--app-border, #ebeef5);
}
.drawer-head h3 {
  margin: 4px 0 0;
  font-size: 14px;
  font-weight: 600;
  color: #1f2329;
}
.drawer-head .eyebrow {
  font-size: 10px;
  color: #909399;
  letter-spacing: 0.6px;
  text-transform: uppercase;
}
.drawer-loading, .drawer-empty {
  padding: 24px 14px;
  color: #909399;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.drawer-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  flex: 1;
  padding: 12px 14px;
}
.drawer-row {
  border: 1px solid var(--app-border, #ebeef5);
  border-radius: 6px;
  padding: 6px 8px;
  background: #fff;
}
.drawer-row.is-fake {
  background: #fafafa;
  border-style: dashed;
}
.drawer-row.is-system {
  border-left: 3px solid #909399;
  background: #fafafa;
}
.drawer-role { margin-bottom: 4px; }
.role-pill {
  display: inline-block;
  padding: 1px 6px;
  font-size: 10px;
  font-family: 'Menlo', monospace;
  border-radius: 3px;
  background: rgba(0, 0, 0, 0.05);
  color: #606266;
}
.role-pill.user { background: rgba(103, 194, 58, 0.12); color: #5faf35; }
.role-pill.assistant { background: rgba(64, 158, 255, 0.12); color: #2e80d8; }
.role-pill.tool { background: rgba(230, 162, 60, 0.12); color: #b88230; }
.role-pill.system { background: rgba(144, 147, 153, 0.18); color: #6e7177; }
.role-pill.fake {
  background: rgba(144, 147, 153, 0.1);
  color: #909399;
  font-style: italic;
}
.dim { color: #c0c4cc; }
.drawer-legend {
  margin-top: 8px;
  font-size: 10px;
  color: #c0c4cc;
  font-style: italic;
}
</style>
