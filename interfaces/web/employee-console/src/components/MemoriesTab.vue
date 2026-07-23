<template>
  <div class="memory-workspace">
    <section class="memory-toolbar">
      <div class="memory-title-block">
        <span class="section-kicker">Memory Workspace</span>
        <h2>{{ activeType.label }}</h2>
        <p>{{ activeType.description }}</p>
      </div>
      <div class="memory-actions">
        <el-input
          v-model="contentQuery"
          class="memory-search"
          :prefix-icon="Search"
          clearable
          placeholder="搜索当前记忆内容"
        />
        <el-button :icon="Refresh" @click="refreshCurrent">刷新</el-button>
        <el-button :icon="CopyDocument" :disabled="!memoryContent" @click="copyCurrent">复制</el-button>
      </div>
    </section>

    <section class="memory-type-strip">
      <button
        v-for="type in memoryTypes"
        :key="type.key"
        class="memory-type-button"
        :class="{ active: activeMemTab === type.key }"
        type="button"
        @click="switchMemory(type.key)"
      >
        <span>{{ type.label }}</span>
        <small>{{ type.short }}</small>
      </button>
    </section>

    <section class="memory-grid">
      <aside class="memory-date-panel">
        <div class="memory-panel-head">
          <div>
            <strong>记录索引</strong>
            <span>{{ filteredDates.length }} / {{ memoryDates.length }}</span>
          </div>
          <el-button v-if="memoryDates.length" text size="small" @click="selectLatest">最新</el-button>
        </div>
        <div class="memory-date-filter">
          <el-input
            v-model="dateQuery"
            :prefix-icon="Search"
            clearable
            size="small"
            placeholder="过滤日期"
          />
        </div>

        <div v-if="!memoryDates.length" class="memory-empty small">
          <strong>暂无日期记录</strong>
          <span>这个记忆类型当前没有可索引的日期。</span>
        </div>
        <div v-else-if="!filteredDates.length" class="memory-empty small">
          <strong>没有匹配日期</strong>
          <span>换一个关键词试试。</span>
        </div>
        <button
          v-for="date in filteredDates"
          :key="date"
          class="memory-date-item"
          :class="{ active: selectedDate === date }"
          type="button"
          @click="selectDate(date)"
        >
          <span>{{ date }}</span>
          <small>{{ dateHint(date) }}</small>
        </button>
      </aside>

      <main class="memory-reader-panel">
        <header class="memory-reader-head">
          <div>
            <span class="section-kicker">{{ activeMemTab }}</span>
            <h3>{{ readerTitle }}</h3>
          </div>
          <div class="memory-reader-stats">
            <span>{{ wordCount }} words</span>
            <span>{{ lineCount }} lines</span>
            <span>{{ headingCount }} headings</span>
          </div>
        </header>

        <div v-if="!memoryContent" class="memory-empty">
          <strong>暂无记忆内容</strong>
          <span>当前类型还没有写入内容，或该日期没有记录。</span>
        </div>
        <div
          v-else
          ref="readerBody"
          class="memory-markdown-shell"
        >
          <ContentActions
            :copy-text="memoryContent"
            :fullscreen-html="renderedContent"
            :fullscreen-text="memoryContent"
            :fullscreen-title="readerTitle"
          >
            <div
              v-if="contentQuery.trim()"
              class="memory-markdown markdown-body"
              v-html="renderedContent"
            />
            <div
              v-else
              class="memory-markdown markdown-body"
              v-html="renderMarkdown(memoryContent)"
            />
          </ContentActions>
        </div>
      </main>

      <aside class="memory-inspector">
        <div class="memory-inspector-section">
          <strong>当前上下文</strong>
          <dl>
            <div>
              <dt>类型</dt>
              <dd>{{ activeType.label }}</dd>
            </div>
            <div>
              <dt>日期</dt>
              <dd>{{ selectedDate || '全部 / 最新' }}</dd>
            </div>
            <div>
              <dt>字符数</dt>
              <dd>{{ charCount }}</dd>
            </div>
            <div>
              <dt>搜索命中</dt>
              <dd>{{ matchCount }}</dd>
            </div>
          </dl>
        </div>

        <div class="memory-inspector-section">
          <strong>阅读辅助</strong>
          <div class="memory-outline">
            <button
              v-for="heading in outline"
              :key="`${heading.index}-${heading.level}-${heading.text}`"
              type="button"
              @click="scrollToHeading(heading)"
            >
              <span :style="{ paddingLeft: `${(heading.level - 1) * 10}px` }">{{ heading.text }}</span>
            </button>
            <span v-if="!outline.length">当前内容没有标题结构。</span>
          </div>
        </div>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { CopyDocument, Refresh, Search } from '@element-plus/icons-vue'
import ContentActions from './ContentActions.vue'

const props = defineProps({
  memTab: String,
  memoryDates: Array,
  selectedDate: String,
  memoryContent: String,
  loadMemory: Function,
  selectDate: Function,
  renderMarkdown: Function
})

const memoryTypes = [
  { key: 'consciousness', label: 'Consciousness', short: '意识流', description: '长期状态、近期感受和自我叙事。' },
  { key: 'diary', label: 'Diary', short: '日记', description: '按日期沉淀的运行记录和每日回顾。' },
  { key: 'scratchpad', label: 'Scratchpad', short: '草稿', description: '临时思考、任务拆解和工作草稿。' },
  { key: 'sent_log', label: 'Sent Log', short: '发送', description: '已经对外发送过的消息记录。' },
  { key: 'him', label: 'HIM', short: '用户画像', description: '关于主要协作者的长期画像和偏好。' },
  { key: 'goals', label: 'Goals', short: '目标', description: '当前目标、长期目标和推进线索。' },
  { key: 'daily', label: 'Daily', short: '日报', description: '每日状态、任务和节律摘要。' },
  { key: 'rules', label: 'Rules', short: '行为规则', description: '长期行为规则和自我约束。每次唤醒自动注入。' },
  { key: 'context', label: 'Context', short: '交接文', description: '晚间复盘留下的上下交接备忘。' },
  { key: 'lessons', label: 'Lessons', short: '教训', description: '可迁移的经验教训，长期积累。' },
]

const activeMemTab = ref(props.memTab || 'consciousness')
const contentQuery = ref('')
const dateQuery = ref('')
const readerBody = ref(null)

const activeType = computed(() => {
  return memoryTypes.find(type => type.key === activeMemTab.value) || memoryTypes[0]
})
const memoryDates = computed(() => props.memoryDates || [])
const selectedDate = computed(() => props.selectedDate || '')
const memoryContent = computed(() => props.memoryContent || '')
const normalizedContentQuery = computed(() => contentQuery.value.trim().toLowerCase())
const normalizedDateQuery = computed(() => dateQuery.value.trim().toLowerCase())
const filteredDates = computed(() => {
  if (!normalizedDateQuery.value) return memoryDates.value
  return memoryDates.value.filter(date => String(date).toLowerCase().includes(normalizedDateQuery.value))
})
const charCount = computed(() => memoryContent.value.length)
const wordCount = computed(() => {
  const words = memoryContent.value.match(/[\p{L}\p{N}_-]+/gu)
  return words ? words.length : 0
})
const lineCount = computed(() => memoryContent.value ? memoryContent.value.split(/\r?\n/).length : 0)
const headingCount = computed(() => outline.value.length)
const matchCount = computed(() => {
  if (!normalizedContentQuery.value || !memoryContent.value) return 0
  return memoryContent.value.toLowerCase().split(normalizedContentQuery.value).length - 1
})
const readerTitle = computed(() => {
  if (selectedDate.value) return `${activeType.value.label} · ${selectedDate.value}`
  return `${activeType.value.label} · 当前内容`
})
const outline = computed(() => {
  const headings = []
  for (const line of memoryContent.value.split(/\r?\n/)) {
    const match = line.match(/^(#{1,3})\s+(.+)$/)
    if (match) headings.push({ index: headings.length, level: match[1].length, text: match[2].trim() })
  }
  return headings.slice(0, 12)
})
const renderedContent = computed(() => {
  const html = props.renderMarkdown(memoryContent.value)
  if (!contentQuery.value.trim()) return html
  return highlightHtmlText(html, contentQuery.value.trim())
})

watch(() => props.memTab, newVal => {
  activeMemTab.value = newVal || 'consciousness'
})

function switchMemory(name) {
  activeMemTab.value = name
  contentQuery.value = ''
  dateQuery.value = ''
  props.loadMemory(name)
}

function refreshCurrent() {
  props.loadMemory(activeMemTab.value, selectedDate.value || undefined)
}

function selectLatest() {
  const latest = memoryDates.value[0]
  if (latest) props.selectDate(latest)
}

function selectDate(date) {
  props.selectDate(date)
}

function dateHint(date) {
  if (selectedDate.value === date) return '正在查看'
  return '点击查看'
}

async function copyCurrent() {
  if (!memoryContent.value) return
  try {
    await navigator.clipboard.writeText(memoryContent.value)
  } catch (_) {
    const textarea = document.createElement('textarea')
    textarea.value = memoryContent.value
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    textarea.remove()
  }
}

async function scrollToHeading(heading) {
  await nextTick()
  const container = readerBody.value
  if (!container) return
  const headings = [...container.querySelectorAll('h1, h2, h3')]
  const target = headings[heading.index] || headings.find(node => normalizeText(node.textContent) === normalizeText(heading.text))
  if (!target) return
  container.scrollTo({
    top: Math.max(0, target.offsetTop - container.offsetTop - 12),
    behavior: 'smooth',
  })
}

function highlightHtmlText(html, rawQuery) {
  if (!rawQuery) return html
  const template = document.createElement('template')
  template.innerHTML = html
  const regex = new RegExp(escapeRegExp(rawQuery), 'gi')
  const walker = document.createTreeWalker(template.content, NodeFilter.SHOW_TEXT)
  const nodes = []
  while (walker.nextNode()) nodes.push(walker.currentNode)
  for (const node of nodes) {
    const value = node.nodeValue || ''
    if (!regex.test(value)) continue
    regex.lastIndex = 0
    const fragment = document.createDocumentFragment()
    let lastIndex = 0
    for (const match of value.matchAll(regex)) {
      const index = match.index || 0
      fragment.append(document.createTextNode(value.slice(lastIndex, index)))
      const mark = document.createElement('mark')
      mark.textContent = match[0]
      fragment.append(mark)
      lastIndex = index + match[0].length
    }
    fragment.append(document.createTextNode(value.slice(lastIndex)))
    node.parentNode?.replaceChild(fragment, node)
  }
  return template.innerHTML
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function normalizeText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim()
}
</script>
