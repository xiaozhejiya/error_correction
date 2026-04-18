/**
 * 纯函数单元测试
 * 对应后端 tests/test_utils.py 的测试风格
 */
import { describe, it, expect } from 'vitest'
import { fileKey, formatOption, isHtml, sanitizeHtml, clampScale } from '../utils.js'

describe('fileKey', () => {
  it('根据文件名、大小、修改时间生成唯一标识', () => {
    const file = { name: 'test.pdf', size: 1024, lastModified: 1700000000 }
    expect(fileKey(file)).toBe('test.pdf|1024|1700000000')
  })

  it('不同文件生成不同标识', () => {
    const a = { name: 'a.png', size: 100, lastModified: 1 }
    const b = { name: 'b.png', size: 100, lastModified: 1 }
    expect(fileKey(a)).not.toBe(fileKey(b))
  })

  it('同名但大小不同的文件标识不同', () => {
    const a = { name: 'test.pdf', size: 100, lastModified: 1 }
    const b = { name: 'test.pdf', size: 200, lastModified: 1 }
    expect(fileKey(a)).not.toBe(fileKey(b))
  })
})

describe('formatOption', () => {
  it('正常字符串原样返回', () => {
    expect(formatOption('A. 选项一')).toBe('A. 选项一')
  })

  it('null 返回空字符串', () => {
    expect(formatOption(null)).toBe('')
  })

  it('undefined 返回空字符串', () => {
    expect(formatOption(undefined)).toBe('')
  })

  it('数字转为字符串', () => {
    expect(formatOption(42)).toBe('42')
  })
})

describe('isHtml', () => {
  it('包含 <table> 标签返回 true', () => {
    expect(isHtml('<table><tr><td>内容</td></tr></table>')).toBe(true)
  })

  it('包含 <thead> 标签返回 true', () => {
    expect(isHtml('<thead><tr><th>标题</th></tr></thead>')).toBe(true)
  })

  it('包含闭合标签 </td> 返回 true', () => {
    expect(isHtml('文本</td></tr>')).toBe(true)
  })

  it('大小写不敏感', () => {
    expect(isHtml('<TABLE><TR><TD>x</TD></TR></TABLE>')).toBe(true)
  })

  it('纯文本返回 false', () => {
    expect(isHtml('这是一道数学题')).toBe(false)
  })

  it('包含非表格 HTML 返回 false', () => {
    expect(isHtml('<div>内容</div>')).toBe(false)
  })

  it('null/undefined 返回 false', () => {
    expect(isHtml(null)).toBe(false)
    expect(isHtml(undefined)).toBe(false)
  })

  it('空字符串返回 false', () => {
    expect(isHtml('')).toBe(false)
  })
})

describe('sanitizeHtml', () => {
  it('保留白名单中的表格标签', () => {
    const input = '<table><tr><td>数据</td></tr></table>'
    // DOMPurify 会自动插入 <tbody>（符合 HTML 规范）
    expect(sanitizeHtml(input)).toBe('<table><tbody><tr><td>数据</td></tr></tbody></table>')
  })

  it('保留排版标签 (p, br, span, b, em, strong)', () => {
    const input = '<p>段落 <b>加粗</b> <em>斜体</em></p>'
    expect(sanitizeHtml(input)).toBe(input)
  })

  it('保留上下标标签 (sub, sup)', () => {
    const input = 'H<sub>2</sub>O 和 x<sup>2</sup>'
    expect(sanitizeHtml(input)).toBe(input)
  })

  it('过滤 script 标签（XSS 防护）', () => {
    const input = '<p>正常内容</p><script>alert("xss")</script>'
    const result = sanitizeHtml(input)
    expect(result).not.toContain('<script>')
    expect(result).toContain('<p>正常内容</p>')
  })

  it('过滤 img 标签的 onerror 属性', () => {
    const input = '<img src=x onerror=alert(1)>'
    const result = sanitizeHtml(input)
    expect(result).not.toContain('onerror')
    expect(result).not.toContain('<img')
  })

  it('过滤 div 标签（不在白名单中）', () => {
    const input = '<div>内容</div>'
    expect(sanitizeHtml(input)).toBe('内容')
  })

  it('过滤 style 标签', () => {
    const input = '<style>body{display:none}</style><p>文本</p>'
    const result = sanitizeHtml(input)
    expect(result).not.toContain('<style>')
    expect(result).toContain('<p>文本</p>')
  })

  it('过滤 iframe 标签', () => {
    const input = '<iframe src="https://evil.com"></iframe>'
    expect(sanitizeHtml(input)).not.toContain('<iframe')
  })
})

describe('clampScale', () => {
  it('向上滚动（deltaY < 0）放大', () => {
    const result = clampScale(1.0, -100)
    expect(result).toBeCloseTo(1.1, 5)
  })

  it('向下滚动（deltaY > 0）缩小', () => {
    const result = clampScale(1.0, 100)
    expect(result).toBeCloseTo(0.9, 5)
  })

  it('不超过最大值', () => {
    const result = clampScale(5.0, -100, 0.25, 5)
    expect(result).toBe(5)
  })

  it('不低于最小值', () => {
    const result = clampScale(0.25, 100, 0.25, 5)
    expect(result).toBe(0.25)
  })

  it('接近边界时钳制到边界', () => {
    const result = clampScale(4.95, -100, 0.25, 5)
    expect(result).toBe(5)
  })

  it('支持自定义范围', () => {
    const result = clampScale(0.5, -100, 0.1, 2)
    expect(result).toBeCloseTo(0.6, 5)
  })
})
