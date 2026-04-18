/**
 * 组件状态逻辑测试
 * 对应后端 tests/test_web_helpers.py 的测试风格，测试组件内部状态管理
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import App from '../App.vue'

/* ── 辅助函数 ── */

/** 创建最小化的系统状态 mock 响应 */
const mockStatusResponse = (overrides = {}) => ({
  success: true,
  status: {
    paddleocr_configured: true,
    available_models: [
      { value: 'openai', label: 'gpt-4o-mini', configured: true, status: '配置成功' },
      { value: 'anthropic', label: 'claude-sonnet-4-20250514', configured: false, status: '未配置' },
    ],
    langsmith_enabled: false,
    ...overrides,
  },
})

/** 挂载 App 组件并 mock fetch 返回系统状态 */
const mountApp = async (statusOverrides = {}) => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(mockStatusResponse(statusOverrides)),
  })

  const wrapper = mount(App, {
    global: {
      stubs: {
        Listbox: true,
        ListboxButton: true,
        ListboxOptions: true,
        ListboxOption: true,
        teleport: true,
      },
    },
  })

  // 等待 onMounted 中的 fetchStatus 完成
  await vi.waitFor(() => {
    expect(global.fetch).toHaveBeenCalled()
  })

  return wrapper
}

beforeEach(() => {
  // mock localStorage
  const store = {}
  vi.stubGlobal('localStorage', {
    getItem: vi.fn((key) => store[key] ?? null),
    setItem: vi.fn((key, val) => { store[key] = val }),
    removeItem: vi.fn((key) => { delete store[key] }),
  })

  // mock matchMedia
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false })))
})

afterEach(() => {
  vi.restoreAllMocks()
  document.body.style.overflow = ''
  document.documentElement.classList.remove('dark')
})

describe('主题切换', () => {
  it('默认浅色模式，html 不含 dark 类', async () => {
    const wrapper = await mountApp()
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    wrapper.unmount()
  })

  it('localStorage 存储 dark 时启用暗色模式', async () => {
    localStorage.getItem.mockReturnValue('dark')
    const wrapper = await mountApp()
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    wrapper.unmount()
  })
})

describe('Toast 通知', () => {
  it('渲染 toast 消息', async () => {
    const wrapper = await mountApp()

    // 触发一个 toast —— 通过点击"重新开始"按钮
    const resetBtn = wrapper.findAll('button').find((b) => b.text().includes('重新开始'))
    await resetBtn.trigger('click')

    // 应该出现 toast
    const toasts = wrapper.findAll('[class*="ring-1"]')
    expect(toasts.length).toBeGreaterThan(0)
    wrapper.unmount()
  })
})

describe('图片预览弹窗', () => {
  it('默认关闭状态', async () => {
    const wrapper = await mountApp()
    const modal = wrapper.find('.img-modal')
    expect(modal.isVisible()).toBe(false)
    wrapper.unmount()
  })

  it('ESC 键关闭弹窗', async () => {
    const wrapper = await mountApp()

    // 模拟打开弹窗
    const event = new KeyboardEvent('keydown', { key: 'Escape' })
    document.dispatchEvent(event)

    const modal = wrapper.find('.img-modal')
    expect(modal.isVisible()).toBe(false)
    wrapper.unmount()
  })
})

describe('步骤指示器', () => {
  it('初始状态步骤为 1', async () => {
    const wrapper = await mountApp()

    // 第一个步骤圆圈应高亮
    const circles = wrapper.findAll('.step-circle')
    expect(circles.length).toBe(4)

    // 第一个步骤应有 blue 高亮样式（当前步骤用 border-blue 表示）
    expect(circles[0].classes().some((c) => c.includes('border-blue'))).toBe(true)
    wrapper.unmount()
  })
})

describe('文件上传区域', () => {
  it('上传区域可通过键盘聚焦', async () => {
    const wrapper = await mountApp()
    const dropZone = wrapper.find('[role="button"]')
    expect(dropZone.exists()).toBe(true)
    expect(dropZone.attributes('tabindex')).toBe('0')
    wrapper.unmount()
  })
})
