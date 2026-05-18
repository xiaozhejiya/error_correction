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

/** 判断内容是否包含 HTML 表格或列表等富文本标签 */
export const isHtml = (s) => /<\/?(?:table|tr|td|th|thead|tbody|ul|ol|li|img|a|strong|em)\b/i.test(s || '')

/** 允许渲染的 HTML 标签白名单 */
export const ALLOWED_HTML_TAGS = [
  'table', 'tr', 'td', 'th', 'thead', 'tbody',
  'ul', 'ol', 'li',
  'p', 'br', 'span', 'b', 'i', 'em', 'strong', 'sub', 'sup',
  'img', 'a',
]

/** 使用 DOMPurify 过滤 HTML，仅保留白名单标签和属性，防止 XSS */
export const sanitizeHtml = (html) => {
  if (!html) return ''
  // 兼容旧数据的图片路径，修复转义
  let fixed = html.replace(/src="imgs\//g, 'src="/images/')
  fixed = fixed.replace(/\\n/g, '\n').replace(/\\"/g, '"')
  return DOMPurify.sanitize(fixed, {
    ALLOWED_TAGS: ALLOWED_HTML_TAGS,
    ALLOWED_ATTR: ['src', 'alt', 'href', 'target', 'rel', 'title', 'class', 'style'],
    ALLOW_DATA_ATTR: false
  })
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

const protectMathMarkdown = (text) => {
  const placeholders = []
  if (!text) return { text: '', restore: (html) => html }
  const codePlaceholders = []
  const stashCode = (match) => {
    const key = `@@CODE_${codePlaceholders.length}@@`
    codePlaceholders.push(match)
    return key
  }

  let s = String(text)
  s = s
    .replace(/```[\s\S]*?```/g, stashCode)
    .replace(/`[^`\n]+`/g, stashCode)

  s = s
    .replace(/\\\[((?:.|\n)*?)\\\]/g, (_, content) => `$$${content}$$`)
    .replace(/\\\(((?:.|\n)*?)\\\)/g, (_, content) => `$${content}$`)

  const stash = (match) => {
    const key = `@@MATH_${placeholders.length}@@`
    placeholders.push(match)
    return key
  }

  s = s
    .replace(/\$\$[\s\S]*?\$\$/g, stash)
    .replace(/\$(?!\$)[\s\S]*?(?<!\$)\$/g, stash)

  // Some LLM replies contain bare LaTeX commands, for example "\overline{z}".
  // Wrap those small math fragments so MathJax can process them while streaming.
  s = s.replace(/(?<![A-Za-z0-9:\\\\/])\\(?:frac|sqrt|overline|bar|hat|vec|angle|triangle|pi|cdot|times|leq|geq|neq|approx|sum|int|Delta|alpha|beta|gamma|theta|lambda|mu|sigma|omega)(?:\s*\{[^{}\n]*\}){0,2}(?:\s*[_^]\s*\{?[\w+\-=]+\}?){0,2}/g, (match) => `$${match}$`)

  s = s
    .replace(/\$\$[\s\S]*?\$\$/g, stash)
    .replace(/\$(?!\$)[\s\S]*?(?<!\$)\$/g, stash)

  s = s.replace(/@@CODE_(\d+)@@/g, (_, index) => codePlaceholders[Number(index)] || '')

  return {
    text: s,
    restore: (html) => html.replace(/@@MATH_(\d+)@@/g, (_, index) => placeholders[Number(index)] || ''),
  }
}

/** 将 Markdown 文本渲染为净化后的 HTML（用于聊天消息） */
export const renderMarkdown = (text) => {
  if (!text) return ''
  const parse = window.marked?.parse ?? ((s) => s)
  const math = protectMathMarkdown(text)
  const html = math.restore(parse(math.text, { breaks: true }))
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

/** 简化 LaTeX 公式并生成纯文本预览 */
export const getNotePreviewText = (text, maxLen = 120) => {
  if (!text) return ''

  const simplifyLatex = (math) => {
    if (!math) return ''
    math = math.trim()

    // 常见符号映射表
    const symbols = {
      'frac\\s*\\{([^{}]*)\\}\\s*\\{([^{}]*)\\}': '($1/$2)',
      'sqrt\\s*\\{([^{}]*)\\}': '√($1)',
      'cdot': '·', 'times': '×', 'div': '÷', 'pm': '±', 'neq': '≠', 'approx': '≈', 'leq': '≤', 'geq': '≥',
      'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ', 'epsilon': 'ε', 'zeta': 'ζ', 'eta': 'η', 'theta': 'θ',
      'iota': 'ι', 'kappa': 'κ', 'lambda': 'λ', 'mu': 'μ', 'nu': 'ν', 'xi': 'ξ', 'omicron': 'ο', 'pi': 'π',
      'rho': 'ρ', 'sigma': 'σ', 'tau': 'τ', 'upsilon': 'υ', 'phi': 'φ', 'chi': 'χ', 'psi': 'ψ', 'omega': 'ω',
      'Delta': 'Δ', 'Gamma': 'Γ', 'Theta': 'Θ', 'Lambda': 'Λ', 'Xi': 'Ξ', 'Pi': 'Π', 'Sigma': 'Σ', 'Upsilon': 'Υ',
      'Phi': 'Φ', 'Psi': 'Ψ', 'Omega': 'Ω',
      'sum': '∑', 'int': '∫', 'infty': '∞', 'to': '→', 'Rightarrow': '⇒', 'Leftrightarrow': '⇔',
      'parallel': '//', 'perp': '⊥',
      'text\\s*\\{([^{}]*)\\}': '$1', 'mathbf\\s*\\{([^{}]*)\\}': '$1', 'mathrm\\s*\\{([^{}]*)\\}': '$1'
    }

    Object.entries(symbols).forEach(([key, val]) => {
      math = math.replace(new RegExp(`\\\\${key}`, 'g'), val)
    })

    // 处理矩阵/方程组环境
    math = math.replace(/\\begin\s*\{([bpvBpv]?matrix|cases|aligned|array)\}([\s\S]*?)\\end\s*\{\1\}/g, (match, env, content) => {
      let matrix = content.replace(/\\\\/g, '; ') // 换行替换为分号
      matrix = matrix.replace(/&/g, ', ') // 列分隔符替换为逗号
      return `[${matrix.trim()}]`
    })

    // 清理多余指令和格式
    math = math.replace(/\\left|\\right/g, '')
    math = math.replace(/\\[a-zA-Z]+/g, '')
    return ` ${math.replace(/\s+/g, ' ')} `
  }

  let s = text

  // 完全移除图片路径（包括描述文字）
  s = s.replace(/!\[[^\]]*\]\([^)]+\)/g, '')

  // 提取和简化 LaTeX 公式（先处理公式，避免破坏 _ 和 -）
  // 块级 $$...$$
  s = s.replace(/\$\$([\s\S]*?)\$\$/g, (match, content) => simplifyLatex(content))
  // 行内 $...$
  s = s.replace(/\$([^$]+)\$/g, (match, content) => simplifyLatex(content))
  // 行内 \(...\)
  s = s.replace(/\\\(([\s\S]*?)\\\)/g, (match, content) => simplifyLatex(content))
  // 块级 \[...\]
  s = s.replace(/\\\[([\s\S]*?)\\\]/g, (match, content) => simplifyLatex(content))

  // 简化链接：保留文本，移除 URL
  s = s.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')

  // 移除 Markdown 标题符号
  s = s.replace(/^#{1,6}\s+/gm, '')

  // 移除 Markdown 格式符号
  s = s.replace(/[*`>\-_]/g, '')

  // 清理多余空格和换行
  s = s.replace(/\s+/g, ' ').trim()
  if (s.length > maxLen) return s.slice(0, maxLen) + '...'
  return s
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
  } catch (_) { }
}

/** 计算滚轮缩放后的 scale 值 */
export const clampScale = (current, deltaY, min = 0.25, max = 5) => {
  const delta = deltaY > 0 ? -0.1 : 0.1
  return Math.min(max, Math.max(min, current + delta))
}
