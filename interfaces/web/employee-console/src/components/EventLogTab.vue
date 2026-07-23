<template>
  <div class="event-log-view">
    <div class="event-log-header">
      <div>
        <div class="eyebrow">Flow EventLog</div>
        <div class="card-title">最近运行轨迹</div>
        <div class="event-log-subtitle">{{ activeRunId || '选择一个 run 查看完整事件链' }}</div>
      </div>
      <div class="event-log-actions">
        <div class="event-stat">
          <span>Events</span>
          <strong>{{ eventStats.total }}</strong>
        </div>
        <div class="event-stat">
          <span>Errors</span>
          <strong>{{ eventStats.errors }}</strong>
        </div>
        <el-button size="small" :icon="InfoFilled" @click="legendOpen = true">事件说明</el-button>
        <el-button size="small" :icon="Refresh" :disabled="!activeRunId" @click="refreshActiveRun">刷新</el-button>
        <el-button size="small" :disabled="!activeRunId" @click="openSession(activeRunId)">查看会话</el-button>
      </div>
    </div>

    <div class="run-selector-card">
      <div class="run-selector-main">
        <el-input
          v-model="runQuery"
          clearable
          placeholder="搜索 run id / 标题 / 时间"
          :prefix-icon="Search"
        />
        <el-select
          v-model="activeRunId"
          filterable
          placeholder="选择 Run"
          @change="selectRun"
        >
          <el-option
            v-for="run in filteredRuns"
            :key="run.id"
            :label="run.label"
            :value="run.id"
          />
        </el-select>
      </div>
      <span>{{ filteredRuns.length }} / {{ runs.length }} runs</span>
    </div>

    <div class="event-log-workbench">
      <aside class="run-list-panel">
        <button
          v-for="run in filteredRuns"
          :key="run.id"
          class="run-list-item"
          :class="{ active: activeRunId === run.id }"
          @click="selectRun(run.id)"
        >
          <span class="run-title">{{ run.title }}</span>
          <span class="run-meta">
            <span>{{ fmtTime(run.time) }}</span>
            <el-tag size="small" effect="plain">{{ run.message_count }} msg</el-tag>
          </span>
          <code>{{ run.id }}</code>
        </button>
        <div v-if="!filteredRuns.length" class="empty-event-log">暂无可选 run</div>
      </aside>

      <main class="event-log-main">
        <div v-if="eventLogError" class="message-panel tool-result-panel">{{ eventLogError }}</div>
        <div v-else-if="!eventLog?.events?.length" class="empty-event-log">暂无事件轨迹</div>
        <template v-else>
          <div class="event-log-filter">
            <div class="event-filter-controls">
              <div class="event-filter-row">
                <span>阶段</span>
                <el-segmented v-model="selectedLayer" :options="layerOptions" size="small" />
              </div>
              <div class="event-filter-row">
                <span>类型</span>
                <el-segmented v-model="selectedKind" :options="kindOptions" size="small" />
              </div>
            </div>
            <div class="event-filter-meta">
              <span>{{ filteredEvents.length }} / {{ eventLog.events.length }}</span>
              <el-button size="small" text :icon="InfoFilled" @click="legendOpen = true">事件说明</el-button>
            </div>
          </div>

          <div class="event-log-split">
            <div class="event-timeline">
              <button
                v-for="event in filteredEvents"
                :key="event.id"
                class="event-node"
                :class="{ active: selectedEvent?.id === event.id, error: event.severity === 'error' }"
                @click="selectedEventId = event.id"
              >
                <span class="event-sequence">{{ event.sequence ?? '-' }}</span>
                <span class="event-node-body">
                  <span class="event-node-head">
                    <span class="event-node-title">
                      <span class="event-type">{{ eventKindLabel(event) }}</span>
                      <span class="event-type-detail">{{ eventTitle(event) }}</span>
                    </span>
                    <span class="event-time">{{ fmtTime(event.timestamp) }}</span>
                  </span>
                  <span class="event-node-summary">{{ event.summary || event.source || 'No summary' }}</span>
                  <span class="event-node-tags">
                    <el-tag size="small" :type="layerTagType(event.layer)" effect="plain">{{ layerLabel(event.layer) }}</el-tag>
                    <el-tag size="small" :type="kindTagType(eventKind(event))" effect="plain">{{ eventKindLabel(event) }}</el-tag>
                    <el-tag v-if="event.severity && event.severity !== 'info'" size="small" :type="severityTagType(event.severity)" effect="plain">{{ event.severity }}</el-tag>
                  </span>
                </span>
              </button>
            </div>

            <div class="event-detail-panel" v-if="selectedEvent">
              <div class="event-detail-header">
                <div>
                  <div class="eyebrow">Event {{ selectedEvent.sequence ?? selectedEventIndex + 1 }}</div>
                  <h2>{{ eventKindLabel(selectedEvent) }}</h2>
                  <div class="event-detail-subtitle">{{ eventTitle(selectedEvent) }}</div>
                </div>
                <div class="event-detail-tags">
                  <el-tag size="small" effect="dark">{{ layerLabel(selectedEvent.layer) }}</el-tag>
                  <el-tag size="small" :type="kindTagType(eventKind(selectedEvent))" effect="plain">{{ eventKindLabel(selectedEvent) }}</el-tag>
                </div>
              </div>

              <div class="event-detail-grid">
                <div class="detail-cell">
                  <span>Kind</span>
                  <strong>{{ eventKindLabel(selectedEvent) }}</strong>
                </div>
                <div class="detail-cell">
                  <span>Timestamp</span>
                  <strong>{{ fmtTime(selectedEvent.timestamp) }}</strong>
                </div>
                <div class="detail-cell">
                  <span>Severity</span>
                  <strong>{{ selectedEvent.severity || 'info' }}</strong>
                </div>
                <div class="detail-cell">
                  <span>Source</span>
                  <strong>{{ selectedEvent.source || '—' }}</strong>
                </div>
                <div class="detail-cell">
                  <span>Status</span>
                  <strong>{{ selectedEvent.status || '—' }}</strong>
                </div>
              </div>

              <div class="event-meaning-box">
                <div class="event-meaning-head">
                  <div>
                    <span>这是什么事件</span>
                    <strong>{{ selectedEventDefinition.label }}</strong>
                  </div>
                  <el-tag size="small" :type="layerTagType(selectedEventDefinition.layer)" effect="plain">
                    {{ layerLabel(selectedEventDefinition.layer) }}
                  </el-tag>
                </div>
                <p>{{ selectedEventDefinition.description }}</p>
                <div v-if="selectedEventFields.length" class="event-field-list">
                  <div v-for="field in selectedEventFields" :key="field.name" class="event-field-item">
                    <code>{{ field.name }}</code>
                    <span>{{ field.description }}</span>
                  </div>
                </div>
              </div>

              <div class="event-summary-box" v-if="selectedEvent.summary">
                {{ selectedEvent.summary }}
              </div>

              <div class="event-lineage" v-if="lineageFields.length">
                <div v-for="field in lineageFields" :key="field.label" class="lineage-row">
                  <span>{{ field.label }}</span>
                  <code>{{ field.value }}</code>
                </div>
              </div>

              <div class="panel-title">
                <span>Raw payload</span>
                <code>{{ selectedEvent.id }}</code>
              </div>
              <ContentActions
                :copy-text="formatToolPayload(selectedEvent)"
                :fullscreen-text="formatToolPayload(selectedEvent)"
                :fullscreen-title="`Event payload · ${selectedEvent.type}`"
              >
                <pre class="tool-payload">{{ formatToolPayload(selectedEvent) }}</pre>
              </ContentActions>
            </div>
          </div>
        </template>
      </main>
    </div>

    <el-drawer
      v-model="legendOpen"
      title="事件说明"
      size="460px"
      class="event-legend-drawer"
    >
      <div class="event-legend-intro">
        轨迹按入口、记忆、编排、执行、反馈五个阶段记录一次 run 的完整生命周期。
      </div>
      <div class="event-legend-groups">
        <section
          v-for="group in eventLegendGroups"
          :key="group.layer"
          class="event-legend-group"
        >
          <div class="event-legend-group-head">
            <div>
              <strong>{{ group.label }}</strong>
              <span>{{ group.description }}</span>
            </div>
            <el-tag size="small" :type="layerTagType(group.layer)" effect="plain">{{ group.events.length }}</el-tag>
          </div>
          <div class="event-legend-list">
            <div
              v-for="definition in group.events"
              :key="definition.type"
              class="event-legend-item"
            >
              <div>
                <strong>{{ definition.label }}</strong>
                <code>{{ definition.type }}</code>
              </div>
              <p>{{ definition.description }}</p>
              <span>{{ kindLabel(definition.kind) }}</span>
            </div>
          </div>
        </section>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { InfoFilled, Refresh, Search } from '@element-plus/icons-vue'
import ContentActions from './ContentActions.vue'

const props = defineProps({
  eventLog: Object,
  eventLogError: String,
  sessions: Array,
  selectedSession: String,
  loadSessions: Function,
  loadEventLog: Function,
  selectSession: Function,
  openSession: Function,
  sessionTitle: Function,
  fmtTime: Function,
  formatToolPayload: Function,
})

const activeRunId = ref('')
const runQuery = ref('')
const selectedLayer = ref('all')
const selectedKind = ref('all')
const selectedEventId = ref(null)
const legendOpen = ref(false)
const layerOrder = ['all', 'ingress', 'memory', 'orchestration', 'execution', 'feedback', 'error']
const kindOrder = [
  'all',
  'tool_call',
  'tool_result',
  'agent_step',
  'task',
  'state',
  'message',
  'memory',
  'orchestration',
  'feedback',
  'system',
  'error',
]

const layerDefinitions = {
  ingress: {
    label: '入口',
    description: '记录外部消息进入系统、标准化和入口检查。',
  },
  memory: {
    label: '记忆',
    description: '记录 persona、技能上下文、记忆召回和上下文预算。',
  },
  orchestration: {
    label: '编排',
    description: '记录意图识别、槽位抽取、能力匹配和执行计划生成。',
  },
  execution: {
    label: '执行',
    description: '记录执行请求、工具调用、工具结果、状态变化和失败。',
  },
  feedback: {
    label: '反馈',
    description: '记录结果评估、对外回复和生命周期反馈事件。',
  },
}

const eventDefinitions = {
  MessageReceivedEvent: {
    type: 'MessageReceivedEvent',
    layer: 'ingress',
    kind: 'message',
    label: '消息接收',
    description: '外部消息进入系统，形成一次 run 的入口。',
    fields: ['message_event_id', 'sender', 'content_preview'],
  },
  MessageNormalizedEvent: {
    type: 'MessageNormalizedEvent',
    layer: 'ingress',
    kind: 'message',
    label: '消息标准化',
    description: '入口消息被转换成内部可处理的 MessageEvent。',
    fields: ['message_event_id', 'role', 'activated_skills'],
  },
  IngressCheckPassedEvent: {
    type: 'IngressCheckPassedEvent',
    layer: 'ingress',
    kind: 'system',
    label: '入口检查通过',
    description: '消息通过入口校验，可以继续进入记忆和编排阶段。',
    fields: ['reason', 'source'],
  },
  IngressCheckRejectedEvent: {
    type: 'IngressCheckRejectedEvent',
    layer: 'ingress',
    kind: 'system',
    label: '入口检查拒绝',
    description: '消息在入口校验阶段被拒绝或降级处理。',
    fields: ['reason', 'source'],
  },
  MemoryContextRequestedEvent: {
    type: 'MemoryContextRequestedEvent',
    layer: 'memory',
    kind: 'memory',
    label: '请求记忆上下文',
    description: '系统开始为本次 run 收集 persona、记忆和技能上下文。',
    fields: ['request', 'budget'],
  },
  PersonaLoadedEvent: {
    type: 'PersonaLoadedEvent',
    layer: 'memory',
    kind: 'memory',
    label: 'Persona 加载',
    description: '数字员工的人格设定已被加载进当前上下文。',
    fields: ['persona_path', 'employee_id'],
  },
  SkillContextLoadedEvent: {
    type: 'SkillContextLoadedEvent',
    layer: 'memory',
    kind: 'memory',
    label: '技能上下文加载',
    description: '与当前任务相关的技能说明或工具上下文已加载。',
    fields: ['skill', 'source'],
  },
  MemoryRecallRequestedEvent: {
    type: 'MemoryRecallRequestedEvent',
    layer: 'memory',
    kind: 'memory',
    label: '请求记忆召回',
    description: '系统开始按当前消息或任务检索相关记忆。',
    fields: ['query', 'limit'],
  },
  MemoryRecallCompletedEvent: {
    type: 'MemoryRecallCompletedEvent',
    layer: 'memory',
    kind: 'memory',
    label: '记忆召回完成',
    description: '相关记忆已经返回，可用于编排和执行。',
    fields: ['count', 'sources'],
  },
  MemoryWriteCommittedEvent: {
    type: 'MemoryWriteCommittedEvent',
    layer: 'memory',
    kind: 'memory',
    label: '记忆写入',
    description: '新的记忆、笔记或长期信息已经落库。',
    fields: ['memory_type', 'path'],
  },
  MemoryCondensationCompletedEvent: {
    type: 'MemoryCondensationCompletedEvent',
    layer: 'memory',
    kind: 'memory',
    label: '记忆压缩完成',
    description: '长上下文或历史内容已被压缩成更短的可用摘要。',
    fields: ['source_count', 'summary'],
  },
  ContextBudgetAppliedEvent: {
    type: 'ContextBudgetAppliedEvent',
    layer: 'memory',
    kind: 'memory',
    label: '上下文预算应用',
    description: '系统根据上下文预算裁剪或选择本次 run 可使用的材料。',
    fields: ['budget', 'used', 'dropped'],
  },
  OrchestrationStartedEvent: {
    type: 'OrchestrationStartedEvent',
    layer: 'orchestration',
    kind: 'orchestration',
    label: '编排开始',
    description: '系统开始理解任务并规划后续执行路径。',
    fields: ['request'],
  },
  IntentClassifiedEvent: {
    type: 'IntentClassifiedEvent',
    layer: 'orchestration',
    kind: 'orchestration',
    label: '意图识别',
    description: '系统判断本次输入属于哪类任务或请求。',
    fields: ['intent', 'domain', 'confidence'],
  },
  SlotExtractedEvent: {
    type: 'SlotExtractedEvent',
    layer: 'orchestration',
    kind: 'orchestration',
    label: '槽位抽取',
    description: '系统从输入中抽取目标、时间、条件、动作等结构化参数。',
    fields: ['slots', 'missing_required'],
  },
  ClarificationRequiredEvent: {
    type: 'ClarificationRequiredEvent',
    layer: 'orchestration',
    kind: 'orchestration',
    label: '需要澄清',
    description: '编排发现关键信息缺失，需要先向用户确认。',
    fields: ['questions', 'missing_slots'],
  },
  CapabilityMatchedEvent: {
    type: 'CapabilityMatchedEvent',
    layer: 'orchestration',
    kind: 'orchestration',
    label: '能力匹配',
    description: '当前任务所需能力已在系统中找到。',
    fields: ['required_capabilities', 'available'],
  },
  CapabilityMissingEvent: {
    type: 'CapabilityMissingEvent',
    layer: 'orchestration',
    kind: 'orchestration',
    label: '能力缺失',
    description: '系统发现缺少完成任务所需的能力，可能进入能力建设或 Speckit 拆解。',
    fields: ['missing', 'partial'],
  },
  PlanCreatedEvent: {
    type: 'PlanCreatedEvent',
    layer: 'orchestration',
    kind: 'task',
    label: '计划生成',
    description: '编排阶段已经生成可执行计划或能力建设计划。',
    fields: ['plan_id', 'plan_type', 'tasks'],
  },
  ExecutionRequestCreatedEvent: {
    type: 'ExecutionRequestCreatedEvent',
    layer: 'orchestration',
    kind: 'task',
    label: '执行请求创建',
    description: '计划节点被转换成可交给执行引擎处理的请求。',
    fields: ['execution_id', 'runtime_capability', 'task_node_id'],
  },
  OrchestrationCompletedEvent: {
    type: 'OrchestrationCompletedEvent',
    layer: 'orchestration',
    kind: 'orchestration',
    label: '编排完成',
    description: '编排阶段完成，系统已决定继续执行、澄清、阻塞或结束。',
    fields: ['kind', 'plan_id'],
  },
  ExecutionStartedEvent: {
    type: 'ExecutionStartedEvent',
    layer: 'execution',
    kind: 'task',
    label: '执行开始',
    description: '运行时执行阶段开始处理编排产生的请求。',
    fields: ['orchestration_kind', 'plan_id'],
  },
  AgentStepStartedEvent: {
    type: 'AgentStepStartedEvent',
    layer: 'execution',
    kind: 'agent_step',
    label: 'Agent 步骤开始',
    description: 'Agent 内部的一个推理或行动步骤开始。',
    fields: ['step_id', 'engine'],
  },
  AgentStepCompletedEvent: {
    type: 'AgentStepCompletedEvent',
    layer: 'execution',
    kind: 'agent_step',
    label: 'Agent 步骤完成',
    description: 'Agent 内部的一个推理或行动步骤结束。',
    fields: ['step_id', 'status'],
  },
  ActionProposedEvent: {
    type: 'ActionProposedEvent',
    layer: 'execution',
    kind: 'tool_call',
    label: '动作提议',
    description: '系统准备调用工具或执行一个运行时动作。',
    fields: ['execution_request', 'task_node', 'tool_name'],
  },
  ActionDispatchedEvent: {
    type: 'ActionDispatchedEvent',
    layer: 'execution',
    kind: 'tool_call',
    label: '动作下发',
    description: '工具调用或运行时动作已经发送给执行引擎。',
    fields: ['execution_id', 'runtime_capability', 'tool_call_id'],
  },
  ObservationReceivedEvent: {
    type: 'ObservationReceivedEvent',
    layer: 'execution',
    kind: 'tool_result',
    label: '结果返回',
    description: '工具、Agent 或执行引擎返回了观察结果。',
    fields: ['status', 'tool_name', 'tool_call_id'],
  },
  ToolErrorEvent: {
    type: 'ToolErrorEvent',
    layer: 'execution',
    kind: 'error',
    label: '工具异常',
    description: '工具调用或执行动作发生错误。',
    fields: ['execution_id', 'runtime_capability', 'error'],
  },
  StateChangedEvent: {
    type: 'StateChangedEvent',
    layer: 'execution',
    kind: 'state',
    label: '状态变化',
    description: 'run 的执行状态发生变化，例如 running、finished、stuck。',
    fields: ['state', 'reason'],
  },
  ExecutionCompletedEvent: {
    type: 'ExecutionCompletedEvent',
    layer: 'execution',
    kind: 'task',
    label: '执行完成',
    description: '执行阶段正常结束，并产生执行结果。',
    fields: ['executed', 'status', 'results'],
  },
  ExecutionFailedEvent: {
    type: 'ExecutionFailedEvent',
    layer: 'execution',
    kind: 'error',
    label: '执行失败',
    description: '执行阶段失败，通常需要查看错误 payload 或工具返回。',
    fields: ['reason', 'error', 'results'],
  },
  FeedbackSignalReceivedEvent: {
    type: 'FeedbackSignalReceivedEvent',
    layer: 'feedback',
    kind: 'feedback',
    label: '反馈信号接收',
    description: '系统收到用户或外部渠道的反馈信号。',
    fields: ['signal', 'source'],
  },
  HumanReplyPlannedEvent: {
    type: 'HumanReplyPlannedEvent',
    layer: 'feedback',
    kind: 'feedback',
    label: '回复计划',
    description: '系统计划向用户发送任务结果或进度反馈。',
    fields: ['channel', 'preview'],
  },
  HumanReplySentEvent: {
    type: 'HumanReplySentEvent',
    layer: 'feedback',
    kind: 'feedback',
    label: '回复已发送',
    description: '系统已经向用户或渠道发送回复。',
    fields: ['channel', 'message_id', 'status'],
  },
  ProactiveReportEvaluatedEvent: {
    type: 'ProactiveReportEvaluatedEvent',
    layer: 'feedback',
    kind: 'feedback',
    label: '主动汇报评估',
    description: '系统评估当前结果是否值得主动汇报给用户。',
    fields: ['decision', 'reason'],
  },
  ProactiveReportSentEvent: {
    type: 'ProactiveReportSentEvent',
    layer: 'feedback',
    kind: 'feedback',
    label: '主动汇报发送',
    description: '系统已发送主动汇报。',
    fields: ['channel', 'message_id'],
  },
  VitalsUpdatedEvent: {
    type: 'VitalsUpdatedEvent',
    layer: 'feedback',
    kind: 'feedback',
    label: '运行状态更新',
    description: '精力或运行状态等 runtime 指标发生变化。',
    fields: ['energy', 'mode', 'delta'],
  },
  LifecycleEventScheduledEvent: {
    type: 'LifecycleEventScheduledEvent',
    layer: 'feedback',
    kind: 'feedback',
    label: '生命周期事件排期',
    description: '系统注册了后续唤醒、定时器或生命周期事件。',
    fields: ['kind', 'fire_at', 'payload'],
  },
  LifecycleEventConsumedEvent: {
    type: 'LifecycleEventConsumedEvent',
    layer: 'feedback',
    kind: 'feedback',
    label: '生命周期事件消费',
    description: '已到期的生命周期事件被消费并进入处理流程。',
    fields: ['kind', 'consumed_at', 'payload'],
  },
  RunResultEvaluatedEvent: {
    type: 'RunResultEvaluatedEvent',
    layer: 'feedback',
    kind: 'feedback',
    label: '运行结果评估',
    description: '系统对本次 run 的最终执行结果进行归档和评估。',
    fields: ['status', 'executed', 'results'],
  },
}

const eventFieldDescriptions = {
  activated_skills: '本次消息激活的技能或上下文能力。',
  available: '当前系统已经具备的能力列表。',
  budget: '上下文或执行预算。',
  channel: '发送或计划发送结果的渠道。',
  confidence: '分类或判断的置信度。',
  consumed_at: '事件被消费的时间。',
  content_preview: '消息正文的短预览。',
  count: '返回或处理的数量。',
  decision: '系统做出的判断结果。',
  dropped: '因预算限制被丢弃的上下文。',
  employee_id: '数字员工实例标识。',
  engine: '执行引擎名称。',
  error: '错误内容。',
  executed: '是否实际执行。',
  execution_id: '执行请求标识。',
  execution_request: '执行请求摘要。',
  fire_at: '计划触发时间。',
  kind: '事件类别。',
  limit: '召回或查询数量限制。',
  message_event_id: '入口消息事件标识。',
  message_id: '外部渠道消息标识。',
  missing: '缺失能力列表。',
  missing_required: '仍缺失的必填槽位。',
  missing_slots: '需要用户补充的信息项。',
  mode: '运行模式。',
  partial: '部分可用但不完整的能力。',
  payload: '事件原始业务负载。',
  persona_path: 'Persona 文件路径。',
  plan_id: '编排计划标识。',
  plan_type: '计划类型。',
  preview: '即将发送内容的预览。',
  query: '记忆检索查询。',
  reason: '状态变化、拒绝、失败或决策原因。',
  request: '编排或执行请求摘要。',
  required_capabilities: '完成任务所需能力列表。',
  results: '执行结果集合。',
  role: '消息角色。',
  runtime_capability: '执行请求需要的运行时能力。',
  sender: '消息发送者。',
  signal: '反馈信号。',
  skill: '技能名称。',
  slots: '抽取出的结构化任务参数。',
  source: '事件来源。',
  sources: '召回或加载的来源列表。',
  state: 'run 当前状态。',
  status: '执行或发送状态。',
  step_id: 'Agent 内部步骤标识。',
  summary: '摘要内容。',
  task_node: '编排计划中的任务节点。',
  task_node_id: '编排计划任务节点标识。',
  tasks: '计划中的任务节点列表。',
  tool_call_id: '工具调用标识。',
  tool_name: '工具名称。',
  used: '已使用预算。',
}

const runs = computed(() => {
  return (props.sessions || [])
    .filter(session => session?.id)
    .map(session => {
      const time = session.latest_message_at || session.ended_at || session.started_at
      const title = props.sessionTitle(session.id)
      return {
        id: session.id,
        title,
        label: `${title} · ${props.fmtTime(time)}`,
        time,
        message_count: session.message_count || 0,
      }
    })
})

const filteredRuns = computed(() => {
  const query = runQuery.value.trim().toLowerCase()
  if (!query) return runs.value
  return runs.value.filter(run => {
    return [run.id, run.title, run.label, props.fmtTime(run.time)]
      .join(' ')
      .toLowerCase()
      .includes(query)
  })
})

const layerOptions = computed(() => {
  const present = new Set((props.eventLog?.events || []).map(event => event.layer).filter(Boolean))
  if ((props.eventLog?.events || []).some(event => event.severity === 'error')) present.add('error')
  return layerOrder
    .filter(layer => layer === 'all' || present.has(layer))
    .map(layer => ({ label: layerLabel(layer), value: layer }))
})

const layerFilteredEvents = computed(() => {
  const events = props.eventLog?.events || []
  if (selectedLayer.value === 'all') return events
  if (selectedLayer.value === 'error') return events.filter(event => event.severity === 'error')
  return events.filter(event => event.layer === selectedLayer.value)
})

const kindOptions = computed(() => {
  const present = new Set(layerFilteredEvents.value.map(event => eventKind(event)).filter(Boolean))
  return kindOrder
    .filter(kind => kind === 'all' || present.has(kind))
    .map(kind => ({ label: kindLabel(kind), value: kind }))
})

const filteredEvents = computed(() => {
  if (selectedKind.value === 'all') return layerFilteredEvents.value
  return layerFilteredEvents.value.filter(event => eventKind(event) === selectedKind.value)
})

const eventStats = computed(() => {
  const events = props.eventLog?.events || []
  return {
    total: events.length,
    errors: events.filter(event => event.severity === 'error').length,
  }
})

const selectedEvent = computed(() => {
  const events = filteredEvents.value
  return events.find(event => event.id === selectedEventId.value) || events[0] || null
})

const selectedEventIndex = computed(() => {
  if (!selectedEvent.value) return -1
  return filteredEvents.value.findIndex(event => event.id === selectedEvent.value.id)
})

const lineageFields = computed(() => {
  const event = selectedEvent.value || {}
  return [
    ['Run', event.run_id],
    ['Employee', event.employee_id],
    ['Message', event.message_event_id],
    ['Caused by', event.causation_event_id],
    ['Tool', event.tool_name],
    ['Engine', event.engine],
  ]
    .filter(([, value]) => value)
    .map(([label, value]) => ({ label, value }))
})

const selectedEventDefinition = computed(() => eventDefinition(selectedEvent.value))

const selectedEventFields = computed(() => {
  return (selectedEventDefinition.value.fields || []).map(name => ({
    name,
    description: eventFieldDescriptions[name] || '该字段来自事件 payload，用于定位和解释事件上下文。',
  }))
})

const eventLegendGroups = computed(() => {
  return Object.entries(layerDefinitions).map(([layer, meta]) => ({
    layer,
    ...meta,
    events: Object.values(eventDefinitions).filter(definition => definition.layer === layer),
  }))
})

onMounted(() => {
  props.loadSessions()
})

watch(() => props.selectedSession, sessionId => {
  if (sessionId && !activeRunId.value) activeRunId.value = sessionId
}, { immediate: true })

watch(runs, nextRuns => {
  if (!nextRuns.length) return
  if (!activeRunId.value || !nextRuns.some(run => run.id === activeRunId.value)) {
    selectRun(nextRuns[0].id)
  } else if (!props.eventLog?.run_id && activeRunId.value) {
    props.loadEventLog(activeRunId.value)
  }
}, { immediate: true })

watch(() => props.eventLog?.run_id, () => {
  selectedLayer.value = 'all'
  selectedKind.value = 'all'
  selectedEventId.value = props.eventLog?.events?.[0]?.id || null
})

watch(selectedLayer, () => {
  selectedKind.value = 'all'
})

watch(kindOptions, options => {
  if (!options.some(option => option.value === selectedKind.value)) selectedKind.value = 'all'
})

watch(filteredEvents, events => {
  if (!events.length) {
    selectedEventId.value = null
  } else if (!events.some(event => event.id === selectedEventId.value)) {
    selectedEventId.value = events[0].id
  }
})

function selectRun(runId) {
  if (!runId) return
  activeRunId.value = runId
  props.selectSession(runId)
  props.loadEventLog(runId)
}

function refreshActiveRun() {
  if (activeRunId.value) props.loadEventLog(activeRunId.value)
  props.loadSessions()
}

function eventDefinition(event) {
  if (!event) {
    return {
      type: 'UnknownEvent',
      layer: 'execution',
      kind: 'system',
      label: '未知事件',
      description: '当前没有选中事件，或事件类型尚未被登记到说明字典中。',
      fields: [],
    }
  }
  const type = event.type || event.payload?.type || 'UnknownEvent'
  const definition = eventDefinitions[type]
  if (definition) return definition
  const kind = eventKind(event)
  const layer = event.layer || (kind === 'memory' ? 'memory' : kind === 'feedback' ? 'feedback' : 'execution')
  return {
    type,
    layer,
    kind,
    label: eventKindLabel(event),
    description: '该事件还没有专门说明。可以查看 Raw payload 理解它在本次 run 中携带的上下文。',
    fields: Object.keys(event.payload || {}).slice(0, 6),
  }
}

function layerLabel(layer) {
  return {
    all: '全部',
    ingress: '入口',
    memory: '记忆',
    orchestration: '编排',
    execution: '执行',
    feedback: '反馈',
    error: '错误',
  }[layer] || layer || '未知'
}

function layerTagType(layer) {
  return {
    ingress: 'info',
    memory: 'success',
    orchestration: 'warning',
    execution: 'primary',
    feedback: '',
  }[layer] || 'info'
}

function severityTagType(severity) {
  return severity === 'error' ? 'danger' : severity === 'warning' ? 'warning' : 'info'
}

function eventKind(event) {
  if (!event) return 'system'
  if (event.kind) return event.kind
  const eventType = event.type || ''
  const payloadType = event.payload?.type || ''
  const typeKey = payloadType || eventType
  if (event.severity === 'error' || ['ToolErrorEvent', 'ExecutionFailedEvent'].includes(eventType)) return 'error'
  if (['ActionProposedEvent', 'ActionDispatchedEvent'].includes(eventType) || payloadType === 'ActionEvent') return 'tool_call'
  if (
    eventType === 'ObservationReceivedEvent' &&
    (payloadType === 'ObservationEvent' || event.payload?.tool_name || event.payload?.tool_call_id)
  ) return 'tool_result'
  if (eventType === 'StateChangedEvent' || ['StateUpdateEvent', 'RejectionEvent'].includes(payloadType)) return 'state'
  if (['AgentStepStartedEvent', 'AgentStepCompletedEvent'].includes(eventType)) return 'agent_step'
  if (['ExecutionStartedEvent', 'ExecutionCompletedEvent', 'ExecutionRequestCreatedEvent', 'PlanCreatedEvent'].includes(eventType)) return 'task'
  if (typeKey.includes('Message')) return 'message'
  if (typeKey.includes('Memory') || ['PersonaLoadedEvent', 'SkillContextLoadedEvent', 'ContextBudgetAppliedEvent'].includes(eventType)) return 'memory'
  if (event.layer === 'orchestration') return 'orchestration'
  if (event.layer === 'feedback') return 'feedback'
  return 'system'
}

function kindLabel(kind) {
  return {
    all: '全部类型',
    agent_step: 'Agent Step',
    error: '异常',
    feedback: '反馈',
    memory: '记忆',
    message: '消息',
    orchestration: '编排',
    state: '状态',
    system: '系统',
    task: '任务',
    tool_call: '工具调用',
    tool_result: '工具结果',
  }[kind] || kind || '未知'
}

function eventKindLabel(event) {
  return event?.kind_label || kindLabel(eventKind(event))
}

function kindTagType(kind) {
  return {
    agent_step: 'warning',
    error: 'danger',
    feedback: '',
    memory: 'success',
    message: 'info',
    orchestration: 'warning',
    state: 'info',
    task: 'primary',
    tool_call: 'primary',
    tool_result: 'success',
  }[kind] || 'info'
}

function eventTitle(event) {
  if (!event) return ''
  const toolName = event.tool_name || event.payload?.tool_name || event.payload?.runtime_capability
  if (toolName) return `${toolName} · ${event.type}`
  return event.type || event.source || 'Event'
}
</script>
