// 时间格式化相关工具函数，统一抽到 composable
// 替代旧 App.vue 里散落的 fmtTs / fmtTime / pad2 / fmtDateTime

export function pad2(n) {
  return String(n).padStart(2, '0')
}

// ISO timestamp → 'YYYY-MM-DD HH:mm'
export function fmtTs(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

// 相对时间：'5 分钟前' / 'just now'
export function fmtRelative(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const diff = Date.now() - d.getTime()
  const sec = Math.floor(diff / 1000)
  if (sec < 60) return '刚刚'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min} 分钟前`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} 小时前`
  const day = Math.floor(hr / 24)
  if (day < 30) return `${day} 天前`
  return fmtTs(iso).slice(0, 10)
}

export function fmtTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

export function fmtDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return `${fmtTs(iso)}:${pad2(d.getSeconds())}`
}

// Safe slice helper —— 防止 .slice 被调用在非字符串/非数组上（防止 minified 报错
// "TypeError: l.slice is not a function"）。空值/数字/对象都被规整成 string 后再 slice。
export function safeSlice(value, start, end) {
  if (value == null) return ''
  if (Array.isArray(value)) return value.slice(start, end)
  const s = typeof value === 'string' ? value : String(value)
  return s.slice(start, end)
}

// Short id 取前 n 个字符，给 .slice(0, n) 用作 id 显示
export function shortId(value, n = 8) {
  const s = safeSlice(value, 0, n)
  return s || '—'
}

// Unix epoch（number/float）转 readable
export function fmtEpoch(ep) {
  if (ep == null) return '—'
  const n = Number(ep)
  if (!Number.isFinite(n)) return '—'
  return fmtTs(new Date(n * 1000).toISOString())
}

export function fmtEpochTime(ep) {
  if (ep == null) return '—'
  const n = Number(ep)
  if (!Number.isFinite(n)) return '—'
  return fmtTime(new Date(n * 1000).toISOString())
}

// 起止 epoch 之间相对时长（"3.2s" / "1分20秒"）
export function fmtDuration(startEp, endEp) {
  if (!startEp || !endEp) return '—'
  const sec = Number(endEp) - Number(startEp)
  if (!Number.isFinite(sec) || sec < 0) return '—'
  if (sec < 60) return sec.toFixed(1) + 's'
  const m = Math.floor(sec / 60), r = Math.round(sec % 60)
  return `${m}分${r}秒`
}

// 触发类型 → 中文短名
export function triggerLabel(type) {
  return {
    message: '💬 消息',
    awaiting_reply: '⏰ 等回复',
    routine: '🕐 例行',
    timer: '⏲️ 定时',
    condition: '⚙️ 条件',
    initiative: '✨ 主动',
    feedback: '↩️ 反馈',
    external: '📨 外部',
  }[String(type || '')] || String(type || '—')
}
