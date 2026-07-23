<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import {
  Bell,
  Calendar,
  ChatDotRound,
  Clock,
  Collection,
  Connection,
  Cpu,
  DataAnalysis,
  Document,
  Finished,
  Folder,
  Grid,
  Memo,
  Operation,
  Plus,
  Setting,
  TrendCharts,
  User,
} from '@element-plus/icons-vue'
import '../assets/styles.css'

import StatusTab from '../components/StatusTab.vue'
import SessionsTab from '../components/SessionsTab.vue'
import MemoriesTab from '../components/MemoriesTab.vue'
import CalendarTab from '../components/CalendarTab.vue'
import EventLogTab from '../components/EventLogTab.vue'
import AssociationsTab from '../components/AssociationsTab.vue'
import ConfigTab from '../components/ConfigTab.vue'
import PromptsTab from '../components/PromptsTab.vue'
import ContactsTab from '../components/ContactsTab.vue'
import ProjectsTab from '../components/ProjectsTab.vue'
import TodosTab from '../components/TodosTab.vue'
import MemoryAdvisorTab from '../components/MemoryAdvisorTab.vue'
import CreateInstanceDialog from '../components/CreateInstanceDialog.vue'

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const runtimeConfig = window.__EMPLOYEE_CONSOLE__ || {}
const apiBase = String(
  runtimeConfig.apiBase || import.meta.env.VITE_EMPLOYEE_CONSOLE_API_BASE || '/api/employee'
).replace(/\/+$/, '')
const employeeName = runtimeConfig.employeeName || import.meta.env.VITE_EMPLOYEE_CONSOLE_NAME || 'Employee'
const currentInstanceId = ref(runtimeConfig.employeeId || '')
const instanceList = ref([])

const defaultLinkOpen = markdown.renderer.rules.link_open || function renderLink(tokens, idx, options, env, self) {
  return self.renderToken(tokens, idx, options)
}
markdown.renderer.rules.link_open = function renderSafeLink(tokens, idx, options, env, self) {
  const token = tokens[idx]
  token.attrSet('target', '_blank')
  token.attrSet('rel', 'noopener noreferrer')
  return defaultLinkOpen(tokens, idx, options, env, self)
}

const tab = ref('status');
const status = ref({ vitals: {}, vitals_detail: {}, runtime: {}, lq: 0, lq_segment: '', affair: null, wait_intent: null, last_heartbeat: null, now: '' });
const sessions = ref([]);
const messages = ref([]);
const selectedSession = ref(null);
const sessionLoading = ref(false);
const sessionError = ref('');
const memTab = ref('consciousness');
const memoryContent = ref('');
const memoryDates = ref([]);
const selectedDate = ref(null);
const assocData = ref({ chunks: 0, associations: 0, top_links: [], sources: [] });
const chunkQuery = ref('');
const chunkFilter = ref('');
const chunkResults = ref([]);
const chunkTotal = ref(0);
const chunkDetail = ref(null);
const sessionDigest = ref('');
const consumedEvents = ref([]);
const eventLog = ref(null);
const eventLogError = ref('');
const predictions = ref([]);
const wallet = ref({});
const configCenter = ref({ sections: [], schema: [], paths: {}, config: {} });
const promptList = ref([]);
const eventTypeList = ref([]);
const expandedPrompt = ref(null);
const editingPrompt = ref(null);
const editingContent = ref('');
const toast = ref(null);
const toastError = ref(false);
const showCreateDialog = ref(false);
let timer = null;
let toastTimer = null;

const affairStatus = computed(() => {
  const a = status.value.affair;
  if (!a) return 'UNKNOWN';
  return a.status === 'RUNNING' ? 'RUNNING' : 'BLOCKED';
});

const currentInstanceDisplayName = computed(() => {
  const inst = instanceList.value.find(i => i.id === currentInstanceId.value);
  return inst?.display_name || currentInstanceId.value;
});

const energyValue = computed(() => {
  const runtimeEnergy = status.value.runtime?.energy;
  const raw = runtimeEnergy ?? status.value.vitals?.energy ?? 0;
  return Math.round(Number(raw) || 0);
});

const runtimeStatus = computed(() => {
  const runtime = status.value.runtime || {};
  const energy = energyValue.value;
  const recoveryRate = runtime.recovery_rate ?? 12;
  return {
    energy,
    energy_segment: runtime.energy_segment || '',
    mode: runtime.mode || (affairStatus.value === 'RUNNING' ? 'working' : 'blocked'),
    mode_label: runtime.mode_label || (affairStatus.value === 'RUNNING' ? '工作中' : '阻塞'),
    last_rest_at: runtime.last_rest_at || status.value.last_heartbeat?.fired_at || '',
    recovery_rate: recoveryRate,
    estimated_full_at: runtime.estimated_full_at || estimateFullAt(energy, recoveryRate),
    recommendation: runtime.recommendation || runtimeRecommendation(energy),
    policy: runtime.policy || {
      auto_rest_below: 20,
      light_work_below: 35,
      deep_work_above: 70,
      current_band: energy >= 70 ? 'deep' : energy >= 35 ? 'normal' : energy >= 20 ? 'light' : 'rest',
    },
    workload: runtime.workload || {
      light: energy >= 20,
      medium: energy >= 45,
      deep: energy >= 70,
    },
    recent_energy_events: runtime.recent_energy_events || [],
    event_queue: runtime.event_queue || { total: 0, messages: 0, group_messages: 0, blocks_express: false, unread_items: [] },
  };
});

const vitalsDims = computed(() => {
  const d = status.value.vitals_detail || {};
  return [
    { key: 'energy', label: 'Energy', value: energyValue.value, segment: runtimeStatus.value.energy_segment || (d.energy || {}).segment || '' },
  ];
});

const menuItems = [
  { key: 'status', label: '概览', icon: DataAnalysis, group: 'Monitor' },
  { key: 'projects', label: '项目', icon: Folder, group: 'Workspace' },
  { key: 'todos', label: '待办', icon: Memo, group: 'Workspace' },
  { key: 'sessions', label: '会话', icon: ChatDotRound, group: 'Workspace' },
  { key: 'eventLog', label: '轨迹', icon: TrendCharts, group: 'Observability' },
  { key: 'calendar', label: '日程', icon: Calendar, group: 'Observability' },
  { key: 'memories', label: '记忆', icon: Collection, group: 'Knowledge' },
  { key: 'associations', label: '联想', icon: Connection, group: 'Knowledge' },
  { key: 'memoryAdvisor', label: '记忆顾问', icon: Collection, group: 'Knowledge' },
  { key: 'prompts', label: '提示词', icon: Document, group: 'System' },
  { key: 'contacts', label: '社交关系', icon: User, group: 'System' },
  { key: 'config', label: '配置', icon: Setting, group: 'System' },
];

const menuGroups = computed(() => {
  return menuItems.reduce((groups, item) => {
    const group = groups.find(entry => entry.name === item.group);
    if (group) group.items.push(item);
    else groups.push({ name: item.group, items: [item] });
    return groups;
  }, []);
});

const shellStats = computed(() => [
  { label: 'Energy', value: energyValue.value, suffix: '%', icon: Cpu },
  { label: 'Mode', value: runtimeStatus.value.mode_label, suffix: '', icon: Operation },
  { label: 'Sessions', value: sessions.value.length || '—', suffix: '', icon: ChatDotRound },
]);

function showToast(msg, err = false) {
  toast.value = msg; toastError.value = err;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.value = null }, 3000);
}
async function api(url, opts) {
  const path = url.startsWith('/') ? url : '/' + url;
  try {
    const r = await fetch(apiBase + path, opts);
    const text = await r.text();
    let payload = {};
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        payload = { error: text };
      }
    }
    if (!r.ok) return { error: payload.error || r.statusText || `HTTP ${r.status}` };
    return payload;
  }
  catch (e) { console.error(e); return { error: e.message } }
}
async function fetchStatus() {
  const d = await api('/status');
  if (!d.error) status.value = d;
}
async function loadInstances() {
  const d = await api('/instances');
  if (!d.error) {
    instanceList.value = (d.instances || []).map(i => typeof i === 'string' ? { id: i, active: true } : i);
    if (!currentInstanceId.value && d.current) {
      currentInstanceId.value = d.current;
    }
  }
}
function switchInstance(id) {
  window.location.href = `/employee/${id}/`;
}
async function toggleInstanceActive(inst) {
  const targetActive = !inst.active;
  const d = await api('/instances/' + inst.id + '/active', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ active: targetActive }),
  });
  if (d.error) {
    showToast(d.error, true);
    return;
  }
  inst.active = !!d.active;
  showToast(`实例 ${inst.id} ${inst.active ? '已启用，重启后生效' : '已停用，重启后生效'}`);
}
function onInstanceCreated(name) {
  showCreateDialog.value = false;
  loadInstances();
  showToast(`实例 ${name} 已创建，编辑人设后重启 gateway 即可生效`);
}
async function loadSessions() {
  const d = await api('/sessions?limit=15');
  if (!d.error) sessions.value = d.sessions || [];
}
async function loadMessages(sid) {
  selectedSession.value = sid;
  messages.value = [];
  sessionDigest.value = '';
  consumedEvents.value = [];
  sessionLoading.value = true;
  sessionError.value = '';
  eventLog.value = null;
  eventLogError.value = '';
  const d = await api('/sessions/' + sid + '/full');
  sessionLoading.value = false;
  if (!d.error) {
    messages.value = d.messages || [];
    sessionDigest.value = d.digest || '';
    consumedEvents.value = d.consumed_events || [];
  } else {
    sessionError.value = d.error || '会话详情加载失败';
  }
}
function selectSession(sid) {
  return loadMessages(sid);
}
async function openSession(sid) {
  if (!sid) return;
  tab.value = 'sessions';
  await loadSessions();
  await loadMessages(sid);
}
async function loadEventLog(runId) {
  if (!runId) return;
  eventLogError.value = '';
  const d = await api('/event-log/runs/' + runId);
  if (d.error) {
    eventLog.value = null;
    eventLogError.value = d.error;
  } else {
    eventLog.value = d;
  }
}
async function loadMemory(name, date) {
  memTab.value = name;
  let url = '/memories/' + name;
  if (date) url += '?date=' + date;
  const d = await api(url);
  if (!d.error) {
    memoryContent.value = d.content || '';
    memoryDates.value = d.dates || [];
    if (date) selectedDate.value = date;
    else if (memoryDates.value.length) selectedDate.value = memoryDates.value[0];
    else selectedDate.value = null;
  }
}
async function selectDate(d) {
  selectedDate.value = d;
  await loadMemory(memTab.value, d);
}
async function loadAssociations() {
  const d = await api('/associations');
  if (!d.error) assocData.value = d;
}
async function loadConfig() {
  const d = await api('/config');
  if (d.error) {
    showToast(d.error, true);
    return;
  }
  configCenter.value = {
    sections: d.sections || [],
    schema: d.schema || [],
    paths: d.paths || {},
    config: d.config || {},
  };
}
async function saveConfig(values) {
  const d = await api('/config', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ values }),
  });
  if (d.error) showToast(d.error, true);
  else {
    showToast('配置已保存，部分项需重启后生效');
    configCenter.value = {
      sections: d.sections || [],
      schema: d.schema || [],
      paths: d.paths || {},
      config: d.config || {},
    };
  }
}
async function recoverEnergy(amount) {
  const value = Number(amount);
  if (!Number.isFinite(value) || value <= 0) {
    showToast('恢复精力数值必须大于 0', true);
    return;
  }
  const d = await api('/deltas', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ energy: value }),
  });
  if (d.error) {
    showToast(d.error, true);
    return;
  }
  showToast(`已恢复精力 +${value}`);
  await fetchStatus();
}
async function nurtureEnergy(amount, label) {
  const d = await api('/nurture-energy', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ amount, label }),
  });
  if (d.error) {
    showToast(d.error, true);
    return;
  }
  showToast(`${label} +${d.added}，当前精力 ${d.energy}%`);
  await fetchStatus();
}
async function loadPrompts() {
  const d = await api('/prompts');
  if (!d.error) promptList.value = d.prompts || [];
}
async function loadEventTypes() {
  const d = await api('/event-types');
  if (!d.error) eventTypeList.value = d.events || [];
}
function editPrompt(p) {
  editingPrompt.value = p.key;
  editingContent.value = p.content;
}
function cancelEdit() {
  editingPrompt.value = null;
  editingContent.value = '';
}
async function savePrompt(key) {
  const d = await api('/prompts/' + key, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content: editingContent.value }) });
  if (d.error) showToast(d.error, true);
  else { showToast('Prompt 已保存'); editingPrompt.value = null; loadPrompts(); loadEventTypes(); }
}
function resetPrompt(p) {
  editingContent.value = p.original;
}

function parseDateTime(value) {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value === 'number') return new Date(value * 1000);
  const raw = String(value).trim();
  if (!raw) return null;
  if (/^\d+(\.\d+)?$/.test(raw)) return new Date(Number(raw) * 1000);
  const normalized = raw.includes('T') ? raw : raw.replace(' ', 'T');
  const d = new Date(normalized);
  return Number.isNaN(d.getTime()) ? null : d;
}
function pad2(n) { return String(n).padStart(2, '0') }
function fmtDateTime(value) {
  const d = parseDateTime(value);
  if (!d) return String(value || '').replace('T', ' ').replace(/([+-]\d{2}:?\d{2}|Z)$/, '');
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}
function fmtDate(value) {
  if (!value) return '';
  return fmtDateTime(value).slice(0, 10);
}
function renderMarkdown(content) {
  return markdown.render(String(content || ''));
}
function renderMessageMarkdown(message) {
  if (message?.display_view?.blocks?.length) {
    const visible = conversationBlocks(message).map(block => String(block.content || '')).join('\n\n');
    return renderMarkdown(visible);
  }
  const content = message?.role === 'user'
    ? formatUserMessageMarkdown(message.content)
    : String(message?.content || '');
  return renderMarkdown(content);
}
function displayView(message) {
  return message?.display_view || {};
}
function displayBlocks(message) {
  const blocks = displayView(message).blocks;
  return Array.isArray(blocks) ? blocks : [];
}
function conversationBlocks(message) {
  return displayBlocks(message).filter(block => block.display_scope === 'conversation');
}
function debugBlocks(message) {
  return displayBlocks(message).filter(block => block.display_scope !== 'conversation');
}
function renderDisplayBlock(block) {
  if (block?.render_as === 'markdown') return renderMarkdown(block.content);
  if (block?.render_as === 'json' || block?.render_as === 'table') return renderMarkdown('```json\n' + formatToolPayload(block.content) + '\n```');
  if (block?.render_as === 'list') return renderMarkdown((block.content || []).map(item => '- ' + item).join('\n'));
  return renderMarkdown(String(block?.content || ''));
}
function roleAvatar(role) {
  if (role === 'assistant') return '🤖';
  if (role === 'user') return '📋';
  if (role === 'tool') return '🔧';
  return '⚙️';
}
function roleLabel(role) {
  return role;
}
function messagePanelClass(message) {
  return {
    'context-panel': message?.role === 'user' || message?.role === 'system',
    'assistant-panel': message?.role === 'assistant',
  };
}
function messageLayoutClass(message) {
  if (message.role === 'user' || message.role === 'system') {
    return 'user-row';
  }
  if (message.role === 'assistant') {
    return 'assistant-row';
  }
  return 'tool-row';
}
function toolCalls(message) {
  return Array.isArray(message?.tool_calls) ? message.tool_calls : [];
}
function toolCallName(call) {
  return call?.function?.name || call?.name || call?.tool_name || call?.type || 'tool_call';
}
function toolCallArguments(call) {
  return call?.function?.arguments ?? call?.arguments ?? call?.args ?? {};
}
function formatToolPayload(payload) {
  if (payload === null || payload === undefined || payload === '') return '';
  if (typeof payload === 'object') return JSON.stringify(payload, null, 2);
  const text = String(payload);
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch (_) {
    return text;
  }
}
function formatUserMessageMarkdown(content) {
  const message = parseUserMessageContent(content);
  if (!message.hasStructuredContent) return String(content || '');

  const sections = [];
  if (message.timestamp) sections.push(`## 时间\n\n\`${message.timestamp}\``);
  if (message.currentMessage.length) {
    sections.push(`## 当前消息\n\n${message.currentMessage.join('\n').trim()}`);
  }
  if (hasSystemPromptContent(message.systemPrompt)) {
    sections.push(`## 系统提示词\n\n\`\`\`json\n${JSON.stringify(message.systemPrompt, null, 2)}\n\`\`\``);
  }
  if (message.waitingStatus) sections.push(`## 当前等待状态\n\n\`${message.waitingStatus}\``);
  if (message.recentSent.length) {
    const rows = message.recentSent.map(item => {
      return `| \`${escapeMarkdownTable(item.time)}\` | ${escapeMarkdownTable(item.content)} |`;
    });
    sections.push(['## 最近发送的消息', '', '| 时间 | 内容 |', '| --- | --- |', ...rows].join('\n'));
  }
  if (message.recentExperiences.length) {
    sections.push(`## 最近经历\n\n\`\`\`text\n${message.recentExperiences.join('\n').trim()}\n\`\`\``);
  }
  if (message.associativeMemory.length) {
    sections.push(`## 联想记忆\n\n\`\`\`text\n${message.associativeMemory.join('\n').trim()}\n\`\`\``);
  }

  return sections.join('\n\n---\n\n');
}
function parseUserMessageContent(content) {
  const message = {
    timestamp: '',
    currentMessage: [],
    systemPrompt: {
      注意事项: [],
      后续动作: [],
      重复消息规则: [],
    },
    waitingStatus: '',
    recentSent: [],
    recentExperiences: [],
    associativeMemory: [],
    hasStructuredContent: false,
  };
  let section = 'current';
  const lines = String(content || '').replace(/\r\n/g, '\n').split('\n');

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line && section === 'current' && !message.currentMessage.length) continue;
    if (!line && ['recentSent'].includes(section)) continue;
    if (line.toLowerCase() === 'user') {
      message.hasStructuredContent = true;
      continue;
    }
    const timestamp = line.match(/^\[(\d{4}-\d{2}-\d{2}T.+)\]$/);
    if (timestamp) {
      message.timestamp = timestamp[1];
      message.hasStructuredContent = true;
      continue;
    }
    if (line.startsWith('## ')) {
      section = sectionForUserMessageHeading(line.replace(/^##\s+/, '').replace(/[：:]$/, '').trim());
      message.hasStructuredContent = true;
      continue;
    }
    if (line.startsWith('养育命令：')) {
      section = 'nurture';
      message.hasStructuredContent = true;
      continue;
    }
    if (line.startsWith('注意：')) {
      section = 'notice';
      message.hasStructuredContent = true;
      pushNonEmpty(message.systemPrompt.注意事项, line.replace('注意：', '').trim());
      continue;
    }
    if (line.startsWith('感知消息')) {
      section = 'workflow';
      pushNonEmpty(message.systemPrompt.后续动作, line);
      continue;
    }
    if (line.startsWith('waiting for reply')) {
      section = 'waiting';
      message.waitingStatus = line;
      message.hasStructuredContent = true;
      continue;
    }
    if (line.startsWith('最近发送的消息：')) {
      section = 'recentSent';
      message.hasStructuredContent = true;
      continue;
    }
    if (line.startsWith('你最近的经历：')) {
      section = 'recentExperiences';
      message.hasStructuredContent = true;
      continue;
    }
    if (line.startsWith('[联想记忆')) {
      section = 'associativeMemory';
      message.hasStructuredContent = true;
      pushNonEmpty(message.associativeMemory, line.replace(/^\[|\]$/g, ''));
      continue;
    }
    if (line.startsWith('[/联想记忆')) continue;

    appendUserMessageLine(message, section, rawLine);
  }

  trimMessageLines(message);
  cleanupSystemPrompt(message.systemPrompt);
  return message;
}
function sectionForUserMessageHeading(title) {
  if (['当前消息', '唤醒事件', '用户原话'].includes(title)) return 'current';
  if (['执行要求', '后续动作', '行动流程'].includes(title)) return 'workflow';
  if (['养育命令', '养育规则'].includes(title)) return 'nurture';
  if (['注意', '注意事项'].includes(title)) return 'notice';
  if (['当前等待状态', '等待状态'].includes(title)) return 'waiting';
  if (['最近发送的消息', '最近发送'].includes(title)) return 'recentSent';
  if (['最近经历', '你最近的经历'].includes(title)) return 'recentExperiences';
  if (['联想记忆', 'Associative Memory'].includes(title)) return 'associativeMemory';
  return 'current';
}
function appendUserMessageLine(message, section, rawLine) {
  const line = rawLine.trim();
  if (section === 'nurture') {
    return;
  }
  if (section === 'notice') {
    pushNonEmpty(message.systemPrompt.注意事项, line);
    return;
  }
  if (section === 'workflow') {
    pushNonEmpty(message.systemPrompt.后续动作, line);
    return;
  }
  if (section === 'recentSent') {
    const sent = line.match(/^(\d{4}-\d{2}-\d{2}T[^|]+)\s+\|\s+(.+)$/);
    if (sent) {
      message.recentSent.push({ time: sent[1].trim(), content: sent[2].trim() });
    } else {
      pushNonEmpty(message.systemPrompt.重复消息规则, line);
    }
    return;
  }
  if (section === 'recentExperiences') {
    message.recentExperiences.push(rawLine);
    return;
  }
  if (section === 'associativeMemory') {
    message.associativeMemory.push(rawLine);
    return;
  }
  if (section === 'waiting') return;
  message.currentMessage.push(rawLine);
}
function pushNonEmpty(target, value) {
  const text = String(value || '').trim();
  if (text) target.push(text);
}
function trimMessageLines(message) {
  message.currentMessage = trimOuterBlankLines(message.currentMessage);
  message.recentExperiences = trimOuterBlankLines(message.recentExperiences);
  message.associativeMemory = trimOuterBlankLines(message.associativeMemory);
}
function trimOuterBlankLines(lines) {
  const copy = [...lines];
  while (copy.length && !copy[0].trim()) copy.shift();
  while (copy.length && !copy[copy.length - 1].trim()) copy.pop();
  return copy;
}
function cleanupSystemPrompt(systemPrompt) {
  for (const key of Object.keys(systemPrompt)) {
    if (Array.isArray(systemPrompt[key]) && !systemPrompt[key].length) delete systemPrompt[key];
    if (typeof systemPrompt[key] === 'object' && !Array.isArray(systemPrompt[key]) && !Object.keys(systemPrompt[key]).length) {
      delete systemPrompt[key];
    }
  }
}
function hasSystemPromptContent(systemPrompt) {
  return Object.keys(systemPrompt).some(key => {
    const value = systemPrompt[key];
    if (Array.isArray(value)) return value.length > 0;
    if (value && typeof value === 'object') return Object.keys(value).length > 0;
    return Boolean(value);
  });
}
function escapeMarkdownTable(value) {
  return String(value || '').replace(/\\/g, '\\\\').replace(/\|/g, '\\|').replace(/\n/g, '<br>');
}
function sessionTitle(id) {
  if (!id) return '';
  const tx = id.match(/^tx_([a-z0-9_]+)_(\d{2})(\d{2})_(\d{2})(\d{2})_([0-9a-f]{6})$/i);
  if (tx) return `${tx[1]} ${tx[2]}-${tx[3]} ${tx[4]}:${tx[5]} #${tx[6]}`;
  return id.replace(/^l4_wake_/, '').replace(/^session_/, '');
}
const fmtTs = fmtDateTime;
const fmtTime = fmtDateTime;
const fmtFireAt = fmtDateTime;
function runtimeRecommendation(energy) {
  if (energy < 20) return '精力已进入耗尽区，建议优先休息，不启动新的长任务。';
  if (energy < 35) return '精力偏低，只适合轻量检查、短回复和状态整理。';
  if (energy < 55) return '精力有限，适合推进明确的小任务，避免连续工具调用。';
  if (energy >= 80) return '精力充足，可以处理深度任务或主动推进计划。';
  return '精力稳定，适合处理中等负载任务并保持节奏。';
}
function estimateFullAt(energy, recoveryRate) {
  const rate = Number(recoveryRate) || 0;
  if (energy >= 100 || rate <= 0) return '';
  const hours = (100 - energy) / rate;
  return new Date(Date.now() + hours * 60 * 60 * 1000).toISOString();
}

onMounted(() => {
  fetchStatus(); loadMemory('consciousness'); loadInstances();
  timer = setInterval(() => { fetchStatus() }, 10000);
});
onUnmounted(() => { if (timer) clearInterval(timer) });
watch(tab, v => {
  if (v === 'sessions') loadSessions();
  else if (v === 'eventLog') loadSessions();
  else if (v === 'associations') loadAssociations();
  else if (v === 'config') loadConfig();
  else if (v === 'prompts') { loadPrompts(); loadEventTypes(); }
});

const tabLabel = computed(() => {
  const labels = {
    status: '概览 / Overview',
    projects: '项目 / Projects',
    todos: '待办 / Todos',
    sessions: '会话 / Sessions',
    eventLog: '轨迹 / EventLog',
    calendar: '日程 / Calendar',
    memories: '记忆 / Memories',
    associations: '联想 / Associations',
    config: '配置 / Configuration',
    prompts: '提示词 / Prompts',
    contacts: '社交关系 / Contacts',
  };
  return labels[tab.value] || tab.value;
});

function getVitalColor(key) {
  const colors = {
    energy: '#3b82f6',
  };
  return colors[key] || '#94a3b8';
}
</script>

<template>
  <el-container class="admin-shell">
    <el-aside width="268px" class="sidebar">
      <div class="sidebar-header">
        <div class="logo-icon"><el-icon><Grid /></el-icon></div>
        <div>
          <div class="brand-name">Life System</div>
          <div class="brand-subtitle">Employee Console</div>
        </div>
      </div>

      <div class="employee-profile">
        <div class="employee-avatar"><el-icon><Operation /></el-icon></div>
        <div class="employee-copy">
          <div class="employee-name">{{ employeeName }}</div>
          <div class="employee-status" :class="{ blocked: affairStatus === 'BLOCKED' }">{{ affairStatus }}</div>
          <div class="instance-switch" v-if="instanceList.length > 1">
            <el-select v-model="currentInstanceId" @change="switchInstance" size="small" class="instance-dropdown" placeholder="切换实例">
              <el-option v-for="inst in instanceList" :key="inst.id" :label="inst.display_name || inst.id" :value="inst.id" />
            </el-select>
            <el-button :icon="Plus" size="small" circle class="create-instance-btn" @click="showCreateDialog = true" />
          </div>
          <div class="instance-tag" v-else-if="currentInstanceId">
            <el-tag size="small" type="info" effect="plain">{{ currentInstanceDisplayName }}</el-tag>
            <el-button :icon="Plus" size="small" circle class="create-instance-btn" @click="showCreateDialog = true" />
          </div>
          <div class="instance-active-list" v-if="instanceList.length > 1">
            <div v-for="inst in instanceList" :key="inst.id" class="instance-active-row">
              <span class="instance-active-name" :class="{ inactive: !inst.active }">{{ inst.display_name || inst.id }}</span>
              <el-switch
                :model-value="inst.active"
                size="small"
                @update:model-value="() => toggleInstanceActive(inst)"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="vitals-container">
        <div class="vitals-title">Energy Budget</div>
        <div class="vital-row" v-for="d in vitalsDims" :key="d.key">
          <div class="vital-info">
            <span class="vital-label">{{ d.label }}</span>
            <span class="vital-value">{{ d.value }}%</span>
          </div>
          <el-progress :percentage="d.value" :color="getVitalColor(d.key)" :show-text="false" />
        </div>
      </div>

      <el-scrollbar class="sidebar-scroll">
        <div v-for="group in menuGroups" :key="group.name" class="menu-section">
          <div class="menu-section-title">{{ group.name }}</div>
          <el-menu :default-active="tab" @select="key => tab = key">
            <el-menu-item v-for="item in group.items" :key="item.key" :index="item.key">
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.label }}</span>
            </el-menu-item>
          </el-menu>
        </div>
      </el-scrollbar>
    </el-aside>

    <el-container class="workspace-shell">
      <el-header class="header">
        <div>
          <div class="breadcrumb">Console / {{ tabLabel.split(' / ')[0] }}</div>
          <h1>{{ tabLabel }}</h1>
        </div>
        <div class="shell-stats">
          <div v-for="stat in shellStats" :key="stat.label" class="shell-stat">
            <el-icon><component :is="stat.icon" /></el-icon>
            <span>{{ stat.label }}</span>
            <strong>{{ stat.value }}{{ stat.suffix }}</strong>
          </div>
        </div>
      </el-header>
      <el-main class="main-content">
        <div class="content-view">
          <StatusTab v-if="tab === 'status'"
            :status="status"
            :runtime="runtimeStatus"
            :apiBase="apiBase"
            :fmtTs="fmtTs"
             :fmtTime="fmtTime"
             @nurture="nurtureEnergy"
           />
          <SessionsTab v-if="tab === 'sessions'"
            :sessions="sessions"
            :selectedSession="selectedSession"
            :messages="messages"
            :loading="sessionLoading"
            :error="sessionError"
            :consumedEvents="consumedEvents"
            :apiBase="apiBase"
            :loadMessages="loadMessages"
            :sessionTitle="sessionTitle"
            :fmtTime="fmtTime"
            :roleLabel="roleLabel"
            :renderMarkdown="renderMarkdown"
            :toolCalls="toolCalls"
            :toolCallName="toolCallName"
            :toolCallArguments="toolCallArguments"
            :formatToolPayload="formatToolPayload"
          />
          <EventLogTab v-if="tab === 'eventLog'"
            :eventLog="eventLog"
            :eventLogError="eventLogError"
            :sessions="sessions"
            :selectedSession="selectedSession"
            :loadSessions="loadSessions"
            :loadEventLog="loadEventLog"
            :selectSession="selectSession"
            :openSession="openSession"
            :sessionTitle="sessionTitle"
            :fmtTime="fmtTime"
            :formatToolPayload="formatToolPayload"
          />
          <MemoriesTab v-if="tab === 'memories'"
            :memTab="memTab"
            :memoryDates="memoryDates"
            :selectedDate="selectedDate"
            :memoryContent="memoryContent"
            :loadMemory="loadMemory"
            :selectDate="selectDate"
            :renderMarkdown="renderMarkdown"
          />
          <AssociationsTab v-if="tab === 'associations'"
            :assocData="assocData"
          />
          <MemoryAdvisorTab v-if="tab === 'memoryAdvisor'"
            :apiBase="apiBase"
          />
          <CalendarTab v-if="tab === 'calendar'"
            :apiBase="apiBase"
            :pad2="pad2"
            :fmtDateTime="fmtDateTime"
            @selectSession="(sid) => { tab = 'sessions'; selectSession(sid); }"
          />
          <ConfigTab v-if="tab === 'config'"
            :configCenter="configCenter"
            :saveConfig="saveConfig"
            :recoverEnergy="recoverEnergy"
          />
          <PromptsTab v-if="tab === 'prompts'"
            :promptList="promptList"
            :eventTypeList="eventTypeList"
            :expandedPrompt="expandedPrompt"
            :editingPrompt="editingPrompt"
            v-model:editingContent="editingContent"
            :editPrompt="editPrompt"
            :cancelEdit="cancelEdit"
            :savePrompt="savePrompt"
            :resetPrompt="resetPrompt"
          />
          <ProjectsTab v-if="tab === 'projects'"
            :apiBase="apiBase"
          />
          <TodosTab v-if="tab === 'todos'"
            :apiBase="apiBase"
          />
          <ContactsTab v-if="tab === 'contacts'"
            :apiBase="apiBase"
          />
        </div>
      </el-main>
    </el-container>
  </el-container>
  <div v-if="toast" class="toast-msg">{{ toast }}</div>
  <CreateInstanceDialog v-model="showCreateDialog" :apiBase="apiBase" @created="onInstanceCreated" />
</template>

<style scoped>
.instance-switch {
  margin-top: 6px;
}
.instance-dropdown {
  width: 120px;
}
.instance-tag {
  margin-top: 4px;
}
.create-instance-btn {
  margin-left: 6px;
  vertical-align: middle;
}
.instance-switch {
  display: flex;
  align-items: center;
  gap: 4px;
}
.instance-active-list {
  margin-top: 8px;
  padding: 8px 0;
  border-top: 1px solid var(--el-border-color-light);
}
.instance-active-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
}
.instance-active-name {
  font-size: 12px;
  color: var(--el-text-color-regular);
}
.instance-active-name.inactive {
  color: var(--el-text-color-placeholder);
}
</style>
