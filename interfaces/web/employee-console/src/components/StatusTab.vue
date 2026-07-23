<template>
  <div class="runtime-overview">
    <section class="runtime-hero">
      <div class="runtime-hero-copy">
        <div class="eyebrow">Runtime State</div>
        <h2>{{ runtime.mode_label }}</h2>
        <p>{{ runtime.recommendation }}</p>
      </div>
      <div class="runtime-energy-gauge">
        <span>{{ runtime.energy }}%</span>
        <el-progress
          type="dashboard"
          :percentage="runtime.energy"
          :color="energyColor"
          :width="150"
          :stroke-width="12"
        />
        <div class="nurture-buttons">
          <el-button size="small" plain @click="$emit('nurture', 30, '加了鸡腿🍗')">🍗 +30</el-button>
          <el-button size="small" plain @click="$emit('nurture', 60, '投喂了能量包⚡')">⚡ +60</el-button>
          <el-button size="small" type="primary" @click="$emit('nurture', 100, '满血复活💯')">💯 满血</el-button>
        </div>
      </div>
    </section>

    <section class="runtime-grid">
      <div class="card" v-if="status.affair">
        <div class="card-title">当前工作状态</div>
        <div class="runtime-affair">
          <div>
            <span>Current Goal</span>
            <strong>{{ status.affair.goal }}</strong>
          </div>
          <el-tag :type="status.affair.status === 'RUNNING' ? 'success' : 'warning'" effect="plain">
            {{ status.affair.status }}
          </el-tag>
        </div>
      </div>

      <div class="card">
        <div class="card-title">恢复节律</div>
        <div class="runtime-facts">
          <div>
            <span>恢复速度</span>
            <strong>{{ runtime.recovery_rate }} / hour</strong>
          </div>
          <div>
            <span>预计满格</span>
            <strong>{{ runtime.estimated_full_at ? fmtTime(runtime.estimated_full_at) : '已充足' }}</strong>
          </div>
          <div>
            <span>上次恢复点</span>
            <strong>{{ runtime.last_rest_at ? fmtTime(runtime.last_rest_at) : '暂无记录' }}</strong>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">工作负载预算</div>
        <div class="workload-list">
          <div v-for="item in workloadItems" :key="item.key" class="workload-item" :class="{ disabled: !item.enabled }">
            <span>{{ item.label }}</span>
            <strong>{{ item.enabled ? '可执行' : '不建议' }}</strong>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">自动策略</div>
        <div class="runtime-policy">
          <div>
            <span>低于 {{ runtime.policy.auto_rest_below }}%</span>
            <strong>自动休息</strong>
          </div>
          <div>
            <span>低于 {{ runtime.policy.light_work_below }}%</span>
            <strong>只做轻任务</strong>
          </div>
          <div>
            <span>高于 {{ runtime.policy.deep_work_above }}%</span>
            <strong>允许深度任务</strong>
          </div>
        </div>
      </div>
    </section>

    <section class="card budget-card" v-if="budget">
      <div class="card-title">
        📊 Token 预算
        <el-tag v-if="budget.is_throttled" type="danger" size="small" effect="dark">已限制 wake</el-tag>
      </div>
      <div class="budget-row">
        <div class="budget-cell">
          <div class="budget-label">本小时</div>
          <el-progress
            :percentage="budgetPct('hour')"
            :color="budgetColor('hour')"
            :stroke-width="12"
            :format="() => `${budget.hour.used.toLocaleString()} / ${budget.hour.limit.toLocaleString()}`"
          />
          <div class="budget-foot" v-if="budget.hour.resets_at">重置于 {{ fmtShort(budget.hour.resets_at) }}</div>
        </div>
        <div class="budget-cell">
          <div class="budget-label">今日</div>
          <el-progress
            :percentage="budgetPct('day')"
            :color="budgetColor('day')"
            :stroke-width="12"
            :format="() => `${budget.day.used.toLocaleString()} / ${budget.day.limit.toLocaleString()}`"
          />
          <div class="budget-foot" v-if="budget.day.resets_at">重置于 {{ fmtShort(budget.day.resets_at) }}</div>
        </div>
      </div>
      <div class="budget-energy" v-if="budget.energy && budget.energy.current !== null">
        精力 <strong :style="{ color: energyColor }">{{ Math.round(budget.energy.current) }}</strong>/100（{{ budget.energy.segment }}）
      </div>
    </section>

    <section class="card" v-if="runtime.event_queue && runtime.event_queue.total > 0">
      <div class="card-title">
        事件队列
        <el-tag v-if="runtime.event_queue.blocks_express" type="danger" size="small" effect="dark">阻塞发消息</el-tag>
      </div>
      <div class="event-queue-stats">
        <div class="eq-stat">
          <span>总未消费</span>
          <strong>{{ runtime.event_queue.total }}</strong>
        </div>
        <div class="eq-stat" :class="{ warning: runtime.event_queue.messages > 0 }">
          <span>人类消息</span>
          <strong>{{ runtime.event_queue.messages }}</strong>
        </div>
        <div class="eq-stat" :class="{ warning: runtime.event_queue.group_messages > 0 }">
          <span>群聊消息</span>
          <strong>{{ runtime.event_queue.group_messages }}</strong>
        </div>
      </div>
      <div v-if="runtime.event_queue.unread_items.length" class="eq-previews">
        <div v-for="item in runtime.event_queue.unread_items" :key="item.event_id" class="eq-preview-item">
          <el-tag :type="item.kind === 'message' ? 'warning' : 'info'" size="small" effect="plain">
            {{ item.kind === 'message' ? '私聊' : '群聊' }}
          </el-tag>
          <span class="eq-preview-text">{{ item.preview || '(无文本)' }}</span>
          <span class="eq-preview-sender" v-if="item.sender">{{ item.sender }}</span>
        </div>
      </div>
      <div v-if="runtime.event_queue.blocks_express" class="eq-hint">
        <el-icon><WarningFilled /></el-icon>
        有未读人类消息时，模型调用 express_to_human 会被自动拦截，要求先查看消息上下文后再回复。
      </div>
    </section>

    <section class="card" v-if="runtime.recent_energy_events.length">
      <div class="card-title">最近精力变化</div>
      <div class="energy-event-list">
        <div v-for="event in runtime.recent_energy_events" :key="`${event.at}-${event.delta}`" class="energy-event">
          <div>
            <strong :class="{ positive: event.delta > 0, negative: event.delta < 0 }">
              {{ event.delta > 0 ? '+' : '' }}{{ event.delta }}
            </strong>
            <span>{{ event.summary }}</span>
          </div>
          <time>{{ fmtTs(event.at) }}</time>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'

const props = defineProps({
  status: Object,
  runtime: Object,
  apiBase: String,
  fmtTs: Function,
  fmtTime: Function
})

// ─── 预算状态：组件自取（独立 12s 轮询，与父级 status 解耦）───
const budget = ref(null)
let _budgetTimer = null

async function fetchBudget() {
  if (!props.apiBase) return
  try {
    const r = await fetch(`${props.apiBase}/budget`)
    if (r.ok) budget.value = await r.json()
  } catch {
    /* silent */
  }
}

function budgetPct(axis) {
  const b = budget.value
  if (!b || !b[axis] || !b[axis].limit) return 0
  return Math.min(100, Math.round((b[axis].used / b[axis].limit) * 100))
}

function budgetColor(axis) {
  const p = budgetPct(axis)
  if (p >= 90) return '#dc2626'
  if (p >= 70) return '#d97706'
  return '#10b981'
}

function fmtShort(iso) {
  if (!iso) return ''
  // 2026-06-14T13:00+08:00 → 13:00
  const m = iso.match(/T(\d{2}:\d{2})/)
  return m ? m[1] : iso
}

onMounted(() => {
  fetchBudget()
  _budgetTimer = setInterval(() => fetchBudget(), 12000)
})
onUnmounted(() => {
  if (_budgetTimer) clearInterval(_budgetTimer)
})

const energyColor = computed(() => {
  const energy = props.runtime?.energy || 0
  if (energy >= 70) return '#059669'
  if (energy >= 45) return '#2563eb'
  if (energy >= 25) return '#d97706'
  return '#dc2626'
})

const workloadItems = computed(() => {
  const workload = props.runtime?.workload || {}
  return [
    { key: 'light', label: '轻任务 / 状态整理', enabled: workload.light },
    { key: 'medium', label: '中等任务 / 单轮工具调用', enabled: workload.medium },
    { key: 'deep', label: '深度任务 / 连续推进', enabled: workload.deep },
  ]
})
</script>

<style scoped>
.event-queue-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 12px;
}
.eq-stat {
  text-align: center;
}
.eq-stat span {
  display: block;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.eq-stat strong {
  font-size: 22px;
}
.eq-stat.warning strong {
  color: var(--el-color-warning);
}
.eq-previews {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}
.eq-preview-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  font-size: 13px;
}
.eq-preview-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--el-text-color-regular);
}
.eq-preview-sender {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}
.eq-hint {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  font-size: 12px;
  color: var(--el-color-warning);
  line-height: 1.5;
}
.eq-hint .el-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

/* Token 预算面板 */
.budget-card { background: linear-gradient(180deg, #fafbfc, #fff); }
.budget-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 4px 2px 8px;
}
.budget-cell { display: flex; flex-direction: column; gap: 4px; }
.budget-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  letter-spacing: 0.4px;
}
.budget-foot {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}
.budget-energy {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--el-border-color-lighter);
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.budget-energy strong { font-size: 16px; margin: 0 2px; }
</style>
