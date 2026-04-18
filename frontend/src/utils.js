import DOMPurify from 'dompurify'

/** 生成文件唯一标识 */
export const fileKey = (file) => `${file.name}|${file.size}|${file.lastModified}`

/** 生成唯一 ID（兼容非 HTTPS 上下文，使用 getRandomValues 确保密码学安全） */
export const genId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('')
}

/** 格式化选项文本 */
export const formatOption = (s) => String(s || '')

/** 判断内容是否包含 HTML 表格标签 */
export const isHtml = (s) => /<\/?(?:table|tr|td|th|thead|tbody)\b/i.test(s || '')

/** 允许渲染的 HTML 标签白名单 */
export const ALLOWED_HTML_TAGS = [
  'table', 'tr', 'td', 'th', 'thead', 'tbody',
  'p', 'br', 'span', 'b', 'i', 'em', 'strong', 'sub', 'sup',
  'img',
]

/** 使用 DOMPurify 过滤 HTML，仅保留白名单标签 */
export const sanitizeHtml = (html) => {
  const fixed = html.replace(/src="imgs\//g, 'src="/images/')
  return DOMPurify.sanitize(fixed, { ALLOWED_TAGS: ALLOWED_HTML_TAGS, ALLOWED_ATTR: ['src', 'alt'] })
}

/** 从题目的 content_json 中提取纯文本摘要 */
export const getQuestionSnippet = (q, maxLen = 0, fallback = '') => {
  if (!q) return fallback
  const blocks = q.content_blocks || q.content_json || []
  const texts = blocks.filter(b => b.block_type === 'text').map(b => b.content || '')
  const raw = texts.join(' ').replace(/<[^>]+>/g, '').trim()
  if (!raw) return fallback
  if (maxLen > 0 && raw.length > maxLen) return raw.slice(0, maxLen) + '…'
  return raw
}

/** 将 Markdown 文本渲染为净化后的 HTML（用于聊天消息） */
export const renderMarkdown = (text) => {
  if (!text) return ''
  const parse = window.marked?.parse ?? ((s) => s)
  const html = parse(text, { breaks: true })
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      ...ALLOWED_HTML_TAGS,
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'ul', 'ol', 'li', 'code', 'pre', 'blockquote', 'hr',
      'a', 'img',
    ],
    ALLOWED_ATTR: ['href', 'target', 'rel', 'src', 'alt'],
  })
}

/** 等待 MathJax 加载就绪（最多等 10 秒） */
const waitForMathJax = () => new Promise((resolve) => {
  const mj = window.MathJax
  if (mj && typeof mj.typesetPromise === 'function') return resolve(mj)
  let tries = 0
  const timer = setInterval(() => {
    const mj = window.MathJax
    if (mj && typeof mj.typesetPromise === 'function') {
      clearInterval(timer)
      resolve(mj)
    } else if (++tries > 100) {
      clearInterval(timer)
      resolve(null)
    }
  }, 100)
})

/** 对指定元素触发 MathJax 公式渲染 */
export const typesetMath = async (el) => {
  const mj = await waitForMathJax()
  if (!mj) return
  try {
    if (el) {
      mj.typesetClear?.([el])
      await mj.typesetPromise([el])
    } else {
      await mj.typesetPromise()
    }
  } catch (_) {}
}

/** 计算滚轮缩放后的 scale 值 */
export const clampScale = (current, deltaY, min = 0.25, max = 5) => {
  const delta = deltaY > 0 ? -0.1 : 0.1
  return Math.min(max, Math.max(min, current + delta))
}
