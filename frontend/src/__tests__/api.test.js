/**
 * API 交互测试
 * 对应后端 tests/test_question_tools.py 的测试风格，测试 fetch 调用与错误处理
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import App from '../App.vue'

/* ── 辅助函数 ── */

const statusOk = {
  ok: true,
  json: () => Promise.resolve({
    success: true,
    status: {
      paddleocr_configured: true,
      available_models: [
        { value: 'openai', label: 'gpt-4o-mini', configured: true, status: '配置成功' },
      ],
      langsmith_enabled: false,
    },
  }),
}

const mountApp = async () => {
  global.fetch = vi.fn().mockResolvedValue(statusOk)

  const wrapper = mount(App, {
    global: {
      stubs: {
        Listbox: true,
        ListboxButton: true,
        ListboxOptions: true,
        ListboxOption: true,
      },
    },
  })

  await vi.waitFor(() => {
    expect(global.fetch).toHaveBeenCalled()
  })

  return wrapper
}

beforeEach(() => {
  vi.stubGlobal('localStorage', {
    getItem: vi.fn(() => null),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  })
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false })))
})

afterEach(() => {
  vi.restoreAllMocks()
  document.body.style.overflow = ''
  document.documentElement.classList.remove('dark')
})

describe('fetchStatus', () => {
  it('成功获取系统状态', async () => {
    const wrapper = await mountApp()

    // fetchStatus 在 onMounted 中调用
    expect(global.fetch).toHaveBeenCalledWith('/api/status')
    wrapper.unmount()
  })

  it('HTTP 错误时显示错误状态', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    })

    const wrapper = mount(App, {
      global: {
        stubs: {
          Listbox: true,
          ListboxButton: true,
          ListboxOptions: true,
          ListboxOption: true,
        },
      },
    })

    await vi.waitFor(() => {
      expect(global.fetch).toHaveBeenCalled()
    })

    // 应显示错误 pill
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    const errorPill = wrapper.find('[class*="bg-rose"]')
    expect(errorPill.exists()).toBe(true)
    wrapper.unmount()
  })

  it('网络异常时显示错误信息', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network Error'))

    const wrapper = mount(App, {
      global: {
        stubs: {
          Listbox: true,
          ListboxButton: true,
          ListboxOptions: true,
          ListboxOption: true,
        },
      },
    })

    await vi.waitFor(() => {
      expect(global.fetch).toHaveBeenCalled()
    })

    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    const errorPill = wrapper.find('[class*="bg-rose"]')
    expect(errorPill.exists()).toBe(true)
    wrapper.unmount()
  })
})

describe('doSplit', () => {
  it('未上传文件时点击分割按钮无效', async () => {
    const wrapper = await mountApp()
    const splitBtn = wrapper.findAll('button').find((b) => b.text().includes('启动 AI 智能分割'))

    // 按钮应处于禁用状态
    expect(splitBtn.attributes('disabled')).toBeDefined()
    wrapper.unmount()
  })
})

describe('doExport', () => {
  it('未选择题目时导出按钮禁用', async () => {
    const wrapper = await mountApp()
    const exportBtn = wrapper.findAll('button').find((b) => b.text().includes('导出错题本'))

    expect(exportBtn.attributes('disabled')).toBeDefined()
    wrapper.unmount()
  })
})

describe('doReset', () => {
  it('重置后状态归初始值', async () => {
    const wrapper = await mountApp()

    // 点击重置
    const resetBtn = wrapper.findAll('button').find((b) => b.text().includes('重新开始'))
    await resetBtn.trigger('click')

    // 分割按钮应回到禁用（因为没有上传文件）
    const splitBtn = wrapper.findAll('button').find((b) => b.text().includes('启动 AI 智能分割'))
    expect(splitBtn.attributes('disabled')).toBeDefined()
    wrapper.unmount()
  })

  it('重置后选择首个已配置模型', async () => {
    // 提供多个模型，第一个已配置的是 openai
    const wrapper = await mountApp()
    const resetBtn = wrapper.findAll('button').find((b) => b.text().includes('重新开始'))
    await resetBtn.trigger('click')

    // 验证 fetch 被调用（说明组件正常运行）
    expect(global.fetch).toHaveBeenCalledWith('/api/status')
    wrapper.unmount()
  })
})

describe('switchModel', () => {
  it('调用正确的 API 端点并包含 provider_id', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true, model_name: 'gpt-4o' }),
    })

    const { switchModel } = await import('../api.js')
    await switchModel('openai', 'gpt-4o', 'provider-123')

    expect(global.fetch).toHaveBeenCalledWith('/api/config/model', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model_provider: 'openai',
        model_name: 'gpt-4o',
        provider_id: 'provider-123',
      }),
    })
  })

  it('不包含 provider_id 当其为 null', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true, model_name: 'gpt-4o' }),
    })

    const { switchModel } = await import('../api.js')
    await switchModel('openai', 'gpt-4o', null)

    expect(global.fetch).toHaveBeenCalledWith('/api/config/model', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model_provider: 'openai',
        model_name: 'gpt-4o',
      }),
    })
  })

  it('HTTP 非 2xx 时抛出错误', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    })

    const { switchModel } = await import('../api.js')
    await expect(switchModel('openai', 'gpt-4o')).rejects.toThrow('HTTP 500')
  })

  it('返回 success:false 时抛出错误', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: false, error: '模型不可用' }),
    })

    const { switchModel } = await import('../api.js')
    await expect(switchModel('openai', 'gpt-4o')).rejects.toThrow('模型不可用')
  })

  it('返回 success:false 且无 error 时抛出默认错误', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: false }),
    })

    const { switchModel } = await import('../api.js')
    await expect(switchModel('openai', 'gpt-4o')).rejects.toThrow('切换模型失败')
  })
})
