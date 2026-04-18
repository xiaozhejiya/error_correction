import { ref, computed, watch } from 'vue'
import * as api from '@/api.js'

// ── 模块级单例状态 ──────────────────────────────────────
const statusLoading = ref(true)
const systemStatus = ref(null)
const statusError = ref('')
const selectedModel = ref('')
const selectedProviderId = ref(null)
const modelSwitching = ref(false)

const providerOptions = computed(() => {
  const s = systemStatus.value
  return s && s.available_models ? s.available_models : []
})

const hasConfiguredModel = computed(() => providerOptions.value.some(p => p.configured))

const selectedProvider = computed(() => {
  // 优先使用 selectedProviderId 匹配
  if (selectedProviderId.value) {
    const provider = providerOptions.value.find(p => p.provider_id === selectedProviderId.value)
    if (provider) return provider.value
  }
  // 回退到模型名称匹配
  for (const p of providerOptions.value) {
    if (p.models && p.models.includes(selectedModel.value)) return p.value
  }
  const configured = providerOptions.value.find(p => p.configured)
  return configured ? configured.value : (providerOptions.value[0]?.value ?? 'openai')
})

// 构建复合值
const buildCompositeValue = (providerId, modelName) => {
  return providerId ? `${providerId}:${modelName}` : modelName
}

watch(systemStatus, (newVal) => {
  if (newVal && newVal.available_models) {
    // 优先选择 is_active=true 且 configured=true 的 provider
    const activeConfigured = newVal.available_models.find(m => m.is_active && m.configured)

    if (!selectedModel.value) {
      // 初始状态：设置默认值
      if (activeConfigured) {
        selectedModel.value = activeConfigured.default_model || ''
        selectedProviderId.value = activeConfigured.provider_id || null
        return
      }
      // 否则选择任意一个 configured 的
      const configured = newVal.available_models.find(m => m.configured)
      if (configured) {
        selectedModel.value = configured.default_model || ''
        selectedProviderId.value = configured.provider_id || null
      }
    } else if (activeConfigured) {
      // 已有选中模型时：如果当前选中的 provider 不是激活状态的，则切换到激活的 provider
      const currentProviderId = selectedProviderId.value
      const isCurrentProviderActive = currentProviderId === activeConfigured.provider_id

      if (!isCurrentProviderActive) {
        // 切换到新激活的 provider 的默认模型
        selectedModel.value = activeConfigured.default_model || ''
        selectedProviderId.value = activeConfigured.provider_id || null
      }
    }
  }
})

const statusPills = computed(() => {
  if (statusLoading.value) return [
    { key: 'paddle', loading: true, label: 'PaddleOCR' },
    { key: 'ensexam', loading: true, label: 'EnsExam' },
    { key: 'langsmith', loading: true, label: 'LangSmith' },
  ]
  const s = systemStatus.value
  if (!s) return []
  const pills = []
  pills.push({ key: 'paddle', ok: !!s.paddleocr_configured, label: s.paddleocr_configured ? 'PaddleOCR' : 'PaddleOCR未配置' })
  if (s.ensexam_configured) {
    pills.push({ key: 'ensexam', ok: true, label: 'EnsExam' })
  }
  pills.push(s.langsmith_enabled
    ? { key: 'langsmith', ok: true, label: 'LangSmith追踪' }
    : { key: 'langsmith', ok: false, label: 'LangSmith', isPlaceholder: true }
  )
  return pills
})

const doFetchStatus = async () => {
  statusLoading.value = true
  statusError.value = ''
  try {
    systemStatus.value = await api.fetchStatus()
  } catch (e) {
    statusError.value = e instanceof Error ? e.message : String(e)
  } finally {
    statusLoading.value = false
  }
}

const switchModel = async (modelProvider, modelName, providerId = null) => {
  if (modelSwitching.value) {
    console.warn('[useSystemStatus] 切换正在进行中，忽略请求')
    return
  }
  modelSwitching.value = true
  try {
    console.log('[useSystemStatus] 开始切换模型:', { modelProvider, modelName, providerId })
    await api.switchModel(modelProvider, modelName, providerId)
    // 更新选中的模型和 provider ID
    selectedModel.value = modelName
    selectedProviderId.value = providerId
    // 立即刷新系统状态，确保获取最新的 default_model
    await doFetchStatus()
    console.log('[useSystemStatus] 模型切换成功，当前模型:', selectedModel.value, 'providerId:', selectedProviderId.value)
  } catch (e) {
    console.error('[useSystemStatus] 模型切换失败:', e)
    throw e
  } finally {
    modelSwitching.value = false
  }
}

/**
 * useSystemStatus — 系统状态单例 composable
 * 任何组件调用都返回同一份响应式状态
 */
export function useSystemStatus() {
  return {
    statusLoading, systemStatus, statusError, selectedModel, selectedProviderId, modelSwitching,
    providerOptions, hasConfiguredModel, selectedProvider, statusPills,
    doFetchStatus, switchModel,
  }
}
