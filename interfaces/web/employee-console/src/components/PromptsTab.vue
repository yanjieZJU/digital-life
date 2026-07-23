<template>
  <div class="prompts-workbench">
    <!-- Sub-tab switcher -->
    <div class="sub-tabs">
      <button
        class="sub-tab"
        :class="{ active: activeSubTab === 'system' }"
        @click="activeSubTab = 'system'"
      >
        系统提示词
      </button>
      <button
        class="sub-tab"
        :class="{ active: activeSubTab === 'events' }"
        @click="activeSubTab = 'events'"
      >
        事件管理
        <el-tag size="small" effect="plain">{{ eventTypeList.length }}</el-tag>
      </button>
    </div>

    <!-- ── System Prompts ── -->
    <template v-if="activeSubTab === 'system'">
      <aside class="prompt-list-panel">
        <div class="prompt-list-head">
          <div>
            <div class="eyebrow">System Prompts</div>
            <h2>系统提示词</h2>
          </div>
          <el-tag size="small" effect="plain">{{ promptList.length }}</el-tag>
        </div>

        <button
          v-for="(p, i) in promptList"
          :key="promptKey(p, i)"
          class="prompt-list-item"
          :class="{ active: activePrompt === promptKey(p, i) }"
          @click="activePrompt = promptKey(p, i)"
        >
          <span class="prompt-title">{{ p.name }}</span>
          <span class="prompt-meta">
            <el-tag size="small" type="info" effect="plain">{{ p.layer || 'layer' }}</el-tag>
            <el-tag v-if="p.overridden" type="warning" size="small" effect="plain">已覆盖</el-tag>
          </span>
          <span v-if="false" @click.stop="savePrompt(p.key)" />
        </button>
      </aside>

      <section class="prompt-detail-panel" v-if="selectedPrompt">
        <div class="prompt-detail-head">
          <div>
            <div class="eyebrow">Prompt Detail</div>
            <h2>{{ selectedPrompt.name }}</h2>
            <div class="prompt-file" v-if="selectedPrompt.file">
              <el-icon><Folder /></el-icon>
              <span>{{ selectedPrompt.file }}</span>
            </div>
          </div>
          <div class="prompt-detail-actions">
            <el-tag v-if="selectedPrompt.overridden" type="warning" effect="plain">Override</el-tag>
            <el-button
              v-if="selectedPrompt.key && editingPrompt !== selectedPrompt.key"
              type="primary"
              plain
              :icon="Edit"
              @click="editPrompt(selectedPrompt)"
            >
              编辑
            </el-button>
          </div>
        </div>

        <div class="prompt-kpis">
          <div>
            <span>Layer</span>
            <strong>{{ selectedPrompt.layer || '—' }}</strong>
          </div>
          <div>
            <span>Trigger</span>
            <strong>{{ selectedPrompt.trigger || '—' }}</strong>
          </div>
          <div>
            <span>Length</span>
            <strong>{{ selectedPrompt.content?.length || 0 }}</strong>
          </div>
        </div>

        <div v-if="editingPrompt !== selectedPrompt.key" class="prompt-preview-shell">
          <ContentActions
            :copy-text="selectedPrompt.content"
            :fullscreen-text="selectedPrompt.content"
            :fullscreen-title="selectedPrompt.name"
          >
            <pre class="prompt-preview">{{ selectedPrompt.content }}</pre>
          </ContentActions>
        </div>

        <div v-else class="prompt-editor-shell">
          <el-input
            v-model="editableContent"
            type="textarea"
            :rows="22"
            class="prompt-editor"
          />
          <div class="prompt-actions">
            <el-button type="primary" @click="savePrompt(selectedPrompt.key)">保存</el-button>
            <el-button @click="resetPrompt(selectedPrompt)">恢复默认</el-button>
            <el-button @click="cancelEdit()">取消</el-button>
          </div>
        </div>
      </section>

      <div v-else class="prompt-detail-panel prompt-empty">
        <div>暂无提示词</div>
      </div>
    </template>

    <!-- ── Event Management ── -->
    <template v-else>
      <aside class="prompt-list-panel">
        <div class="prompt-list-head">
          <div>
            <div class="eyebrow">Event Registry</div>
            <h2>事件类型</h2>
          </div>
          <el-tag size="small" effect="plain">{{ eventTypeList.length }}</el-tag>
        </div>

        <button
          v-for="et in eventTypeList"
          :key="et.type_id"
          class="prompt-list-item"
          :class="{ active: activeEvent === et.type_id }"
          @click="activeEvent = et.type_id"
        >
          <span class="prompt-title">{{ et.display_name }}</span>
          <span class="prompt-meta">
            <el-tag size="small" type="info" effect="plain">{{ triggerLabel(et.trigger_type) }}</el-tag>
            <el-tag v-if="et.prompt_overridden" type="warning" size="small" effect="plain">已覆盖</el-tag>
          </span>
        </button>
      </aside>

      <section class="prompt-detail-panel" v-if="selectedEvent">
        <div class="prompt-detail-head">
          <div>
            <div class="eyebrow">Event Detail</div>
            <h2>{{ selectedEvent.display_name }}</h2>
            <div class="prompt-file">
              <el-icon><Folder /></el-icon>
              <span>{{ selectedEvent.prompt_file || 'heartbeat.py' }}</span>
            </div>
          </div>
          <div class="prompt-detail-actions">
            <el-tag v-if="selectedEvent.prompt_overridden" type="warning" effect="plain">Override</el-tag>
            <el-button
              v-if="selectedEvent.prompt_key && editingPrompt !== selectedEvent.prompt_key"
              type="primary"
              plain
              :icon="Edit"
              @click="editEventPrompt(selectedEvent)"
            >
              编辑 Prompt
            </el-button>
          </div>
        </div>

        <!-- Event metadata -->
        <div class="prompt-kpis">
          <div>
            <span>Type ID</span>
            <strong>{{ selectedEvent.type_id }}</strong>
          </div>
          <div>
            <span>Trigger</span>
            <strong>{{ triggerLabel(selectedEvent.trigger_type) }}</strong>
          </div>
          <div>
            <span>Allowed Tools</span>
            <strong>{{ selectedEvent.allowed_tools?.length || 0 }}</strong>
          </div>
        </div>

        <!-- 触发描述 -->
        <div class="event-section" v-if="selectedEvent.trigger_description">
          <h3>触发条件</h3>
          <p class="trigger-desc">{{ selectedEvent.trigger_description }}</p>
        </div>

        <!-- Allowed tools -->
        <div class="event-section" v-if="selectedEvent.allowed_tools?.length">
          <h3>允许的工具</h3>
          <div class="tool-tags">
            <el-tag
              v-for="tool in selectedEvent.allowed_tools"
              :key="tool"
              size="small"
              effect="plain"
            >{{ tool }}</el-tag>
          </div>
        </div>

        <!-- Payload schema -->
        <div class="event-section" v-if="Object.keys(selectedEvent.payload_schema || {}).length">
          <h3>Payload Schema</h3>
          <ContentActions
            :copy-text="formatJson(selectedEvent.payload_schema)"
            :fullscreen-text="formatJson(selectedEvent.payload_schema)"
            fullscreen-title="Payload Schema"
          >
            <pre class="schema-preview">{{ formatJson(selectedEvent.payload_schema) }}</pre>
          </ContentActions>
        </div>

        <!-- Context policy -->
        <div class="event-section" v-if="Object.keys(selectedEvent.context_policy || {}).length">
          <h3>Context Policy</h3>
          <ContentActions
            :copy-text="formatJson(selectedEvent.context_policy)"
            :fullscreen-text="formatJson(selectedEvent.context_policy)"
            fullscreen-title="Context Policy"
          >
            <pre class="schema-preview">{{ formatJson(selectedEvent.context_policy) }}</pre>
          </ContentActions>
        </div>

        <!-- Prompt template -->
        <div class="event-section prompt-section">
          <h3>Prompt 模板</h3>
          <div v-if="editingPrompt !== selectedEvent.prompt_key" class="prompt-preview-shell">
            <ContentActions
              :copy-text="selectedEvent.prompt_content"
              :fullscreen-text="selectedEvent.prompt_content"
              :fullscreen-title="`${selectedEvent.display_name} Prompt`"
            >
              <pre class="prompt-preview">{{ selectedEvent.prompt_content }}</pre>
            </ContentActions>
          </div>
          <div v-else class="prompt-editor-shell">
            <el-input
              v-model="editableContent"
              type="textarea"
              :rows="22"
              class="prompt-editor"
            />
            <div class="prompt-actions">
              <el-button type="primary" @click="savePrompt(selectedEvent.prompt_key)">保存</el-button>
              <el-button @click="resetEventPrompt(selectedEvent)">恢复默认</el-button>
              <el-button @click="cancelEdit()">取消</el-button>
            </div>
          </div>
        </div>
      </section>

      <div v-else class="prompt-detail-panel prompt-empty">
        <div>暂无事件</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Edit, Folder } from '@element-plus/icons-vue'
import ContentActions from './ContentActions.vue'

const props = defineProps({
  promptList: Array,
  eventTypeList: Array,
  editingPrompt: String,
  editingContent: String,
  editPrompt: Function,
  cancelEdit: Function,
  savePrompt: Function,
  resetPrompt: Function
});

const emit = defineEmits(['update:editingContent']);

const activeSubTab = ref('system');
const activePrompt = ref(null);
const activeEvent = ref(null);
const editableContent = ref('');

// ── System prompts ──

const selectedPrompt = computed(() => {
  const list = props.promptList || [];
  return list.find((prompt, index) => promptKey(prompt, index) === activePrompt.value) || list[0] || null;
});

watch(() => props.promptList, list => {
  if (!list?.length) {
    activePrompt.value = null;
    return;
  }
  if (!list.some((prompt, index) => promptKey(prompt, index) === activePrompt.value)) {
    activePrompt.value = promptKey(list[0], 0);
  }
}, { immediate: true });

// ── Events ──

const selectedEvent = computed(() => {
  const list = props.eventTypeList || [];
  return list.find(et => et.type_id === activeEvent.value) || list[0] || null;
});

watch(() => props.eventTypeList, list => {
  if (!list?.length) {
    activeEvent.value = null;
    return;
  }
  if (!list.some(et => et.type_id === activeEvent.value)) {
    activeEvent.value = list[0].type_id;
  }
}, { immediate: true });

function triggerLabel(triggerType) {
  const labels = {
    time: '时间触发',
    condition: '条件触发',
    message: '消息触发',
    manual: '手动',
    system: '系统',
    external: '外部',
  };
  return labels[String(triggerType)] || String(triggerType);
}

function editEventPrompt(et) {
  // Reuse parent's editPrompt with the event's prompt key+content shape
  props.editPrompt({ key: et.prompt_key, content: et.prompt_content });
}

function resetEventPrompt(et) {
  props.resetPrompt({ original: et.prompt_original });
}

// ── Shared editing state ──

watch(() => props.editingPrompt, newVal => {
  if (newVal) editableContent.value = props.editingContent;
});

watch(() => props.editingContent, newVal => {
  if (props.editingPrompt && newVal !== editableContent.value) {
    editableContent.value = newVal || '';
  }
});

watch(editableContent, newVal => {
  emit('update:editingContent', newVal);
});

function promptKey(prompt, index) {
  return prompt?.key || prompt?.name || String(index);
}

function formatJson(value) {
  return JSON.stringify(value || {}, null, 2);
}
</script>

<style scoped>
.prompts-workbench {
  display: grid;
  gap: 16px;
  grid-template-columns: 340px minmax(0, 1fr);
  min-height: calc(100vh - 132px);
}

.sub-tabs {
  grid-column: 1 / -1;
  display: flex;
  gap: 8px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
}

.sub-tab {
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  padding: 8px 16px;
  transition: all 0.15s;
}

.sub-tab:hover {
  border-color: var(--primary);
  color: var(--text-main);
}

.sub-tab.active {
  background: var(--primary-glow);
  border-color: var(--primary);
  color: var(--primary);
  font-weight: 700;
}

.prompt-list-panel,
.prompt-detail-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: var(--shadow-card);
}

.prompt-list-panel {
  max-height: calc(100vh - 180px);
  overflow: auto;
  padding: 12px;
}

.prompt-list-head,
.prompt-detail-head {
  align-items: start;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 8px 8px 14px;
}

.prompt-list-head h2,
.prompt-detail-head h2 {
  font-size: 16px;
  line-height: 1.3;
  margin: 0;
}

.prompt-list-item {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  color: inherit;
  cursor: pointer;
  display: grid;
  gap: 8px;
  margin-bottom: 4px;
  padding: 12px;
  text-align: left;
  width: 100%;
}

.prompt-list-item:hover {
  background: var(--bg-soft);
  border-color: var(--border-color);
}

.prompt-list-item.active {
  background: var(--primary-glow);
  border-color: var(--primary);
}

.prompt-title {
  color: var(--text-main);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.4;
}

.prompt-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.prompt-detail-panel {
  min-width: 0;
  overflow: hidden;
  padding: 18px;
}

.prompt-detail-head {
  margin: -2px 0 16px;
  padding: 0 0 14px;
}

.prompt-file {
  align-items: center;
  color: var(--text-dim);
  display: flex;
  font-family: var(--font-mono);
  font-size: 11px;
  gap: 6px;
  margin-top: 8px;
  max-width: 860px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prompt-detail-actions {
  align-items: center;
  display: flex;
  gap: 8px;
}

.prompt-kpis {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 14px;
}

.prompt-kpis div {
  background: var(--bg-soft);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  display: grid;
  gap: 4px;
  padding: 10px;
}

.prompt-kpis span {
  color: var(--text-muted);
  font-size: 11px;
}

.prompt-kpis strong {
  color: var(--text-main);
  font-family: var(--font-mono);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prompt-preview-shell,
.prompt-editor-shell {
  min-width: 0;
}

.prompt-preview {
  background: #111827;
  border-radius: 8px;
  color: #d1d5db;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.7;
  margin: 0;
  max-height: calc(100vh - 328px);
  overflow: auto;
  padding: 16px;
  white-space: pre-wrap;
}

.prompt-editor {
  margin-bottom: 14px;
}

.prompt-actions {
  display: flex;
  gap: 10px;
}

.prompt-empty {
  align-items: center;
  color: var(--text-dim);
  display: flex;
  justify-content: center;
}

/* Event section */
.event-section {
  margin-bottom: 16px;
}

.event-section h3 {
  color: var(--text-main);
  font-size: 13px;
  font-weight: 700;
  margin: 0 0 8px;
}

.trigger-desc {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
  background: var(--bg-canvas);
  padding: 10px 14px;
  border-radius: 8px;
  border-left: 3px solid var(--color-primary);
}

.tool-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.schema-preview {
  background: var(--bg-soft);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-main);
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1.6;
  margin: 0;
  padding: 12px;
  white-space: pre-wrap;
}

.prompt-section .prompt-preview {
  max-height: 300px;
}

@media (max-width: 1180px) {
  .prompts-workbench {
    grid-template-columns: 1fr;
  }

  .prompt-list-panel {
    max-height: none;
  }
}

@media (max-width: 760px) {
  .prompt-detail-head,
  .prompt-list-head {
    display: grid;
    gap: 10px;
  }

  .prompt-kpis {
    grid-template-columns: 1fr;
  }
}
</style>
