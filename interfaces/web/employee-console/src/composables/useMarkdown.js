// 集中渲染 markdown：复用 markdown-it，统一选项 + neon 主题 css class
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
  typographer: true,
})

export function renderMarkdown(text) {
  if (!text) return ''
  try {
    return md.render(String(text))
  } catch {
    return String(text)
  }
}

// inline markdown（用于短注）
export function renderMarkdownInline(text) {
  if (!text) return ''
  try {
    return md.renderInline(String(text))
  } catch {
    return String(text)
  }
}
