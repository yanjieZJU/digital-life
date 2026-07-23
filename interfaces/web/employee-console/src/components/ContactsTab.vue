<script setup>
import { ref, onMounted, computed } from 'vue'
import { Plus, Edit, Delete, Refresh, User, Warning, Close, QuestionFilled } from '@element-plus/icons-vue'

const props = defineProps({
  apiBase: { type: String, required: true },
})

const loading = ref(false)
const contacts = ref([])
const error = ref('')
const successToast = ref('')

/**
 * 容错的 fetch：先把响应读成 text 再 JSON.parse。
 * 后端任一接口返回非 JSON（404 文本「404: Not Found」、HTML 错误页、空响应）
 * 时，裸 r.json() 会抛「Unexpected non-whitespace character after JSON...」
 * 这种对用户无意义的长报错串，并阻塞后续逻辑。这里降级为友好提示。
 */
async function safeFetch(url, opts) {
  const r = await fetch(url, opts)
  const text = await r.text()
  let payload = {}
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = { error: text.slice(0, 120) }
    }
  }
  // 不 ok 且后端没给 reason：拼一个可读的状态描述
  if (!r.ok && !payload.reason && !payload.error) {
    payload.reason = `HTTP ${r.status}`
  }
  return { ok: r.ok, status: r.status, payload }
}

// 主 dialog：新建/编辑 contact
const dialogVisible = ref(false)
const dialogMode = ref('create')
const form = ref({
  id: '',
  name: '',
  notes: '',
  kind: 'human',
  platform_ids: [{ platform: 'feishu', platform_id: '' }],
})
const submitting = ref(false)

const isCreate = computed(() => dialogMode.value === 'create')
const dialogTitle = computed(() => isCreate.value ? '新增联系人' : '编辑联系人')

// 黑名单原因 dialog
const blockDialogVisible = ref(false)
const blockTarget = ref(null) // contact object
const blockReasonInput = ref('')
const blockSubmitting = ref(false)

// 过滤
const search = ref('')
const filterMode = ref('all') // 'all' | 'normal' | 'blocked' | 'unnamed'

const filtered = computed(() => {
  const s = search.value.trim().toLowerCase()
  return contacts.value.filter(c => {
    if (filterMode.value === 'normal' && c.blocked) return false
    if (filterMode.value === 'blocked' && !c.blocked) return false
    if (filterMode.value === 'unnamed' && (c.name || '').trim()) return false
    if (!s) return true
    const nameMatch = (c.name || '').toLowerCase().includes(s)
    const notesMatch = (c.notes || '').toLowerCase().includes(s)
    const idMatch = (c.platform_ids || []).some(p =>
      p.platform_id.toLowerCase().includes(s) || p.platform.toLowerCase().includes(s)
    )
    return nameMatch || notesMatch || idMatch
  })
})

// ──────────── Load ────────────
async function load() {
  loading.value = true
  error.value = ''
  try {
    const { ok, payload } = await safeFetch(`${props.apiBase}/contacts`)
    if (ok) contacts.value = payload.contacts || []
    else error.value = payload.reason || payload.error || '加载失败'
  } catch (e) {
    error.value = e.message || '网络错误'
  } finally {
    loading.value = false
  }
}

// ──────────── CRUD ────────────
function openCreate() {
  dialogMode.value = 'create'
  form.value = {
    id: '',
    name: '',
    notes: '',
    kind: 'human',
    platform_ids: [{ platform: 'feishu', platform_id: '' }],
  }
  dialogVisible.value = true
}

function openEdit(row) {
  dialogMode.value = 'edit'
  const pids = (row.platform_ids && row.platform_ids.length)
    ? row.platform_ids.map(p => ({ platform: p.platform, platform_id: p.platform_id }))
    : [{ platform: 'feishu', platform_id: '' }]
  form.value = {
    id: row.id,
    name: row.name,
    notes: row.notes || '',
    kind: row.kind || 'human',
    platform_ids: pids,
  }
  dialogVisible.value = true
}

function addPlatformId() {
  form.value.platform_ids.push({ platform: 'feishu', platform_id: '' })
}

function removePlatformId(idx) {
  if (form.value.platform_ids.length <= 1) return
  form.value.platform_ids.splice(idx, 1)
}

async function submit() {
  if (!form.value.name.trim()) {
    error.value = 'name 不能为空'
    return
  }
  const pids = form.value.platform_ids
    .map(p => ({ platform: (p.platform || '').trim(), platform_id: (p.platform_id || '').trim() }))
    .filter(p => p.platform && p.platform_id)
  if (pids.length === 0) {
    error.value = '至少需要一个有效的 platform_id'
    return
  }
  submitting.value = true
  error.value = ''
  try {
    const url = isCreate.value
      ? `${props.apiBase}/contacts`
      : `${props.apiBase}/contacts/${encodeURIComponent(form.value.id)}`
    const method = isCreate.value ? 'POST' : 'PATCH'
    const body = {
      name: form.value.name.trim(),
      notes: form.value.notes.trim(),
      kind: form.value.kind || 'human',
      platform_ids: pids,
    }
    const { ok, payload } = await safeFetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (ok && payload.ok) {
      successToast.value = isCreate.value ? '已新增' : '已更新'
      dialogVisible.value = false
      await load()
      setTimeout(() => { successToast.value = '' }, 2000)
    } else {
      error.value = payload.reason || payload.error || `保存失败`
    }
  } catch (e) {
    error.value = e.message || '网络错误'
  } finally {
    submitting.value = false
  }
}

async function removeRow(row) {
  error.value = ''
  try {
    const { ok, payload } = await safeFetch(`${props.apiBase}/contacts/${encodeURIComponent(row.id)}`, {
      method: 'DELETE',
    })
    if (ok && payload.ok) {
      successToast.value = '已删除'
      await load()
      setTimeout(() => { successToast.value = '' }, 2000)
    } else {
      error.value = payload.reason || payload.error || '删除失败'
    }
  } catch (e) {
    error.value = e.message || '网络错误'
  }
}

// ──────────── Block toggle ────────────
function openBlockDialog(row) {
  blockTarget.value = row
  blockReasonInput.value = row.block_reason || ''
  blockDialogVisible.value = true
}

async function submitBlock() {
  if (!blockTarget.value) return
  blockSubmitting.value = true
  error.value = ''
  try {
    const willBlock = !blockTarget.value.blocked
    const { ok, payload } = await safeFetch(
      `${props.apiBase}/contacts/${encodeURIComponent(blockTarget.value.id)}/block`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ blocked: willBlock, reason: blockReasonInput.value.trim() }),
      },
    )
    if (ok && payload.ok) {
      successToast.value = willBlock ? '已拉黑' : '已恢复'
      blockDialogVisible.value = false
      blockTarget.value = null
      await load()
      setTimeout(() => { successToast.value = '' }, 2000)
    } else {
      error.value = payload.reason || payload.error || '操作失败'
    }
  } catch (e) {
    error.value = e.message || '网络错误'
  } finally {
    blockSubmitting.value = false
  }
}

const stats = computed(() => ({
  total: contacts.value.length,
  blocked: contacts.value.filter(c => c.blocked).length,
  unnamed: contacts.value.filter(c => !(c.name || '').trim()).length,
}))

onMounted(() => {
  load()
})
</script>

<template>
  <div class="contacts-workbench">
    <header class="contacts-head">
      <div>
        <div class="eyebrow">Social Relations</div>
        <h2>社交关系</h2>
        <p class="hint">
          以<strong>用户</strong>为单位管理社交关系：每个用户可绑定多个平台的 ID（飞书 open_id、union_id、钉钉、微信…），
          并可标记为拉黑（消息会被立即丢弃，不进入事件队列、不唤醒实例）。
          未知发送者 fallback 显示 ID 本身。模型<strong>只读</strong>此通讯录。
        </p>
      </div>
      <div class="actions">
        <el-button :icon="Refresh" @click="load" :loading="loading">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
      </div>
    </header>

    <div class="stats-row">
      <el-tag size="default" effect="plain">共 {{ stats.total }}</el-tag>
      <el-tag v-if="stats.unnamed" size="default" type="warning" effect="plain">未命名 {{ stats.unnamed }}</el-tag>
      <el-tag v-if="stats.blocked" size="default" type="danger" effect="plain">黑名单 {{ stats.blocked }}</el-tag>
    </div>

    <div v-if="error" class="error-msg">⚠ {{ error }}</div>
    <div v-if="successToast" class="success-toast">{{ successToast }}</div>

    <div class="filter-row">
      <el-input
        v-model="search"
        placeholder="搜索姓名 / 备注 / platform_id"
        clearable
        class="search-input"
      />
      <el-radio-group v-model="filterMode" size="small">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="normal">正常</el-radio-button>
        <el-radio-button value="unnamed">
          <el-icon><QuestionFilled /></el-icon>
          未命名
        </el-radio-button>
        <el-radio-button value="blocked">
          <el-icon><Warning /></el-icon>
          黑名单
        </el-radio-button>
      </el-radio-group>
    </div>

    <el-table
      :data="filtered"
      v-loading="loading"
      empty-text="暂无联系人，点击右上角「新增」开始维护"
      row-key="id"
    >
      <el-table-column label="姓名" width="220">
        <template #default="{ row }">
          <div class="cell-name">
            <el-icon><User /></el-icon>
            <span v-if="(row.name || '').trim()">{{ row.name }}</span>
            <span v-else class="unnamed-label">未命名</span>
            <el-tag v-if="row.kind === 'bot'" size="small" type="warning" effect="plain">机器人</el-tag>
            <el-tag v-else-if="row.kind === 'system'" size="small" type="info" effect="plain">系统</el-tag>
            <el-tag v-if="row.blocked" size="small" type="danger" effect="dark">已拉黑</el-tag>
            <el-tag v-if="!(row.name || '').trim()" size="small" type="info" effect="plain">stub</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="平台 ID" min-width="320">
        <template #default="{ row }">
          <div v-if="row.platform_ids && row.platform_ids.length" class="id-stack">
            <div v-for="(p, i) in row.platform_ids" :key="i" class="id-pill">
              <el-tag size="small" effect="plain">{{ p.platform }}</el-tag>
              <code class="cell-openid" :title="p.platform_id">{{ p.platform_id }}</code>
            </div>
          </div>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="备注" min-width="180">
        <template #default="{ row }">
          <span class="cell-notes">{{ row.notes || (row.blocked ? row.block_reason : '—') }}</span>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="170">
        <template #default="{ row }">
          <span class="cell-time">{{ row.updated_at || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button size="small" link :type="row.blocked ? 'success' : 'danger'" @click="openBlockDialog(row)">
            {{ row.blocked ? '恢复' : '拉黑' }}
          </el-button>
          <el-button :icon="Edit" size="small" link @click="openEdit(row)">编辑</el-button>
          <el-popconfirm
            title="确定删除该联系人？"
            @confirm="removeRow(row)"
            confirm-button-text="删除"
            cancel-button-text="取消"
          >
            <template #reference>
              <el-button :icon="Delete" size="small" link type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- Contact dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="620px"
      :close-on-click-modal="false"
    >
      <el-form label-width="88px" @submit.prevent="submit">
        <el-form-item label="姓名">
          <el-input v-model="form.name" placeholder="例：张三 / Zero" />
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="form.kind" size="small">
            <el-radio-button value="human">人类</el-radio-button>
            <el-radio-button value="bot">机器人</el-radio-button>
            <el-radio-button value="system">系统</el-radio-button>
          </el-radio-group>
          <div class="form-hint">机器人：把多个实例 bot 当作社交对象登记（display_name + open_id），其他实例在群里写 "@BotName" 会自动 @ 对方。</div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="form.notes"
            type="textarea"
            :rows="2"
            placeholder="可选，对模型有帮助的身份说明"
          />
        </el-form-item>
        <el-form-item label="平台 ID">
          <div class="platform-ids-editor">
            <div
              v-for="(p, idx) in form.platform_ids"
              :key="idx"
              class="platform-id-row"
            >
              <el-select
                v-model="p.platform"
                placeholder="平台"
                class="platform-select"
                :disabled="!isCreate && false"
                filterable
                allow-create
              >
                <el-option label="feishu" value="feishu" />
                <el-option label="dingtalk" value="dingtalk" />
                <el-option label="wechat" value="wechat" />
              </el-select>
              <el-input
                v-model="p.platform_id"
                placeholder="平台 user ID（如 ou_xxx）"
                class="platform-id-input"
              />
              <el-button
                v-if="form.platform_ids.length > 1"
                :icon="Close"
                circle
                size="small"
                @click="removePlatformId(idx)"
              />
            </div>
            <el-button :icon="Plus" size="small" plain @click="addPlatformId">
              增加一个 ID
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">
          {{ isCreate ? '新增' : '保存' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Block reason dialog -->
    <el-dialog
      v-model="blockDialogVisible"
      :title="blockTarget && blockTarget.blocked ? '恢复联系人' : '拉黑联系人'"
      width="460px"
      :close-on-click-modal="false"
    >
      <p v-if="blockTarget">
        即将{{ blockTarget.blocked ? '恢复' : '拉黑' }}：<strong>{{ blockTarget.name }}</strong>
      </p>
      <el-form-item :label="blockTarget && blockTarget.blocked ? '恢复说明' : '拉黑原因'" label-width="88px">
        <el-input
          v-model="blockReasonInput"
          type="textarea"
          :rows="2"
          :placeholder="blockTarget && blockTarget.blocked ? '可选' : '可选，仅自己看'"
        />
      </el-form-item>
      <template #footer>
        <el-button @click="blockDialogVisible = false">取消</el-button>
        <el-button
          :type="blockTarget && blockTarget.blocked ? 'success' : 'danger'"
          :loading="blockSubmitting"
          @click="submitBlock"
        >
          {{ blockTarget && blockTarget.blocked ? '恢复' : '确认拉黑' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.contacts-workbench {
  padding: 8px 0;
}
.contacts-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}
.contacts-head h2 {
  margin: 4px 0;
}
.contacts-head .hint {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  max-width: 720px;
  margin: 0;
  line-height: 1.6;
}
.contacts-head .actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.stats-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.filter-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}
.search-input {
  max-width: 360px;
}
.cell-name {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.id-stack {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.id-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.cell-openid {
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.cell-notes {
  font-size: 13px;
}
.cell-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.muted {
  color: var(--el-text-color-placeholder);
}
.unnamed-label {
  color: var(--el-text-color-placeholder);
  font-style: italic;
}
.platform-ids-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.platform-id-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.platform-select {
  width: 130px;
  flex-shrink: 0;
}
.platform-id-input {
  flex: 1;
}
.error-msg {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 13px;
}
.success-toast {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 13px;
}
.eyebrow {
  font-size: 11px;
  letter-spacing: 1.5px;
  color: var(--el-text-color-placeholder);
  text-transform: uppercase;
  font-weight: 500;
}
</style>
