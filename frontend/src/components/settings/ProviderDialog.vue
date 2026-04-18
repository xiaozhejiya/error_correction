<script setup>
/**
 * ProviderDialog.vue
 * API Provider 配置弹窗
 */
import { ref, computed, watch } from 'vue'
import { useToast } from '@/composables/useToast.js'

const { pushToast } = useToast()

const props = defineProps({
  open: { type: Boolean, default: false },
  type: { type: String, default: 'openai' }, // 'openai' | 'anthropic' | 'paddleocr'
  editData: { type: Object, default: null }, // null=新增, object=编辑
})

const emit = defineEmits(['close', 'confirm'])

const isEdit = computed(() => !!props.editData)

const typeConfig = computed(() => ({
  openai: {
    title: isEdit.value ? '编辑 OpenAI 兼容供应商' : '添加 OpenAI 兼容供应商',
    iconBg: 'bg-blue-50 dark:bg-blue-500/10',
    iconCls: 'fa-bolt text-blue-600 dark:text-blue-400',
    btnCls: 'bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600',
    namePlaceholder: '例如：DeepSeek / Qwen / Moonshot',
    urlPlaceholder: '留空使用 OpenAI 官方，或填入 https://api.deepseek.com 等',
    modelPlaceholder: 'gpt-4o-mini',
    defaultName: 'OpenAI Provider',
    secretLabel: 'API Key',
    secretPlaceholder: '输入 API Key',
    urlLabel: 'Base URL',
  },
  anthropic: {
    title: isEdit.value ? '编辑 Anthropic 供应商' : '添加 Anthropic 供应商',
    iconBg: 'bg-blue-50 dark:bg-blue-500/10',
    iconCls: 'fa-brain text-blue-600 dark:text-blue-400',
    btnCls: 'bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600',
    namePlaceholder: '例如：Claude Official',
    urlPlaceholder: '留空使用 Anthropic 官方',
    modelPlaceholder: 'claude-sonnet-4-20250514',
    defaultName: 'Anthropic Provider',
    secretLabel: 'API Key',
    secretPlaceholder: '输入 API Key',
    urlLabel: 'Base URL',
  },
  paddleocr: {
    title: isEdit.value ? '编辑 PaddleOCR 服务' : '添加 PaddleOCR 服务',
    iconBg: 'bg-blue-50 dark:bg-blue-500/10',
    iconCls: 'fa-eye text-blue-600 dark:text-blue-400',
    btnCls: 'bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600',
    namePlaceholder: '例如：PaddleOCR 官方',
    urlPlaceholder: 'https://paddleocr.aistudio-app.com/api/v2/ocr/jobs',
    modelPlaceholder: 'PaddleOCR-VL-1.5',
    defaultName: 'PaddleOCR',
    secretLabel: 'API Token',
    secretPlaceholder: '输入 API Token',
    urlLabel: 'API URL',
  },
}[props.type]))

const defaultForm = () => ({
  name: '',
  api_key: '',
  base_url: '',
  model_name: '',
  light_model_name: '',
  supports_function_calling: true,
  // PaddleOCR 专用
  use_doc_orientation: false,
  use_doc_unwarping: false,
  use_chart_recognition: false,
})

const form = ref(defaultForm())

// 模型列表相关
const modelList = ref([])
const fetchingModels = ref(false)
const fetchModelError = ref('')

const canFetchModels = computed(() => {
  if (props.type === 'paddleocr') return false
  // 需要有 API Key（新输入或已设置）
  const hasKey = form.value.api_key || (props.editData?.api_key_set)
  return !!hasKey
})

const fetchModels = async () => {
  if (fetchingModels.value) return
  fetchingModels.value = true
  fetchModelError.value = ''
  modelList.value = []
  try {
    const res = await fetch('/api/models/list', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: props.type,
        api_key: form.value.api_key || undefined,
        base_url: form.value.base_url || undefined,
        provider_id: props.editData?.id || undefined,
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || `HTTP ${res.status}`)
    }
    const data = await res.json()
    modelList.value = data.models || []
    if (modelList.value.length === 0) {
      pushToast('error', '未获取到可用模型')
    } else {
      pushToast('success', `获取到 ${modelList.value.length} 个可用模型`)
    }
  } catch (e) {
    pushToast('error', e.message || '获取模型列表失败')
  } finally {
    fetchingModels.value = false
  }
}

// 每次打开时重置或回填表单
watch(() => props.open, (v) => {
  if (!v) return
  modelList.value = []
  fetchModelError.value = ''
  openDropdown.value = null
  testResult.value = null
  if (props.editData) {
    form.value = {
      ...defaultForm(),
      name: props.editData.name || '',
      api_key: '',
      base_url: props.editData.base_url || '',
      model_name: props.editData.model_name || '',
      light_model_name: props.editData.light_model_name || '',
      supports_function_calling: props.editData.supports_function_calling ?? true,
      use_doc_orientation: props.editData.use_doc_orientation || false,
      use_doc_unwarping: props.editData.use_doc_unwarping || false,
      use_chart_recognition: props.editData.use_chart_recognition || false,
    }
  } else {
    form.value = defaultForm()
  }
})

// PaddleOCR 连接测试
const testingConnection = ref(false)
const testResult = ref(null) // { success: boolean, message: string } | null

const canTestConnection = computed(() => {
  const hasToken = form.value.api_key || (props.editData?.api_key_set)
  const hasUrl = form.value.base_url
  return !!hasToken && !!hasUrl
})

const testConnection = async () => {
  if (testingConnection.value) return
  testingConnection.value = true
  testResult.value = null
  try {
    const payload = {
      api_token: form.value.api_key || undefined,
      api_url: form.value.base_url || undefined,
      provider_id: props.editData?.id || undefined,
    }
    const res = await fetch('/api/paddleocr/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await res.json()
    testResult.value = {
      success: data.success,
      message: data.success ? data.message : data.error,
    }
  } catch (e) {
    testResult.value = { success: false, message: e.message || '请求失败' }
  } finally {
    testingConnection.value = false
  }
}

const confirm = () => {
  if (!form.value.name.trim()) {
    form.value.name = typeConfig.value.defaultName
  }
  emit('confirm', { ...form.value })
}

const inputCls = 'w-full rounded-xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-800 placeholder-slate-400 transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-slate-800/80 dark:text-slate-200 dark:placeholder-slate-500'

// 自定义下拉
const openDropdown = ref(null) // 'model_name' | 'light_model_name' | null
const toggleDropdown = (field) => {
  openDropdown.value = openDropdown.value === field ? null : field
}
const selectOption = (field, value) => {
  form.value[field] = value
  openDropdown.value = null
}
</script>

<template>
  <Teleport to="body">
    <!-- 背景遮罩 -->
    <div
      class="fixed inset-0 z-[100] transition-colors duration-200 md:left-64"
      :class="open ? 'bg-black/40 pointer-events-auto' : 'bg-transparent pointer-events-none'"
      @click="emit('close')"
    ></div>

    <Transition name="dialog-fade">
      <div v-if="open" class="fixed inset-0 z-[101] flex items-center justify-center p-4 md:left-64" @click.self="emit('close')">
        <!-- 弹窗主体 -->
        <div class="relative w-full max-w-lg sm:w-[32rem] rounded-2xl border border-slate-200/60 bg-white shadow-2xl dark:border-white/10 dark:bg-[#0f0f17]">
          <!-- 头部 -->
          <div class="flex items-center justify-between border-b border-slate-100 px-6 py-4 dark:border-white/5">
            <div class="flex items-center gap-3">
              <div class="flex h-9 w-9 items-center justify-center rounded-xl" :class="typeConfig.iconBg">
                <i class="fa-solid text-base" :class="typeConfig.iconCls"></i>
              </div>
              <h3 class="text-base font-bold text-slate-800 dark:text-slate-200">
                {{ typeConfig.title }}
              </h3>
            </div>
            <button
              @click="emit('close')"
              class="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-white/5 dark:hover:text-slate-300"
            >
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>

          <!-- 表单 -->
          <form autocomplete="off" class="space-y-4 px-6 py-5" @submit.prevent="confirm" @click="openDropdown = null">
            <div>
              <label class="mb-1.5 block text-xs font-bold text-slate-600 dark:text-slate-400">{{ type === 'paddleocr' ? '服务名称' : '供应商名称' }}</label>
              <input
                v-model="form.name"
                type="text"
                autocomplete="one-time-code"
                :placeholder="typeConfig.namePlaceholder"
                :class="inputCls"
                autofocus
              />
            </div>

            <div>
              <label class="mb-1.5 block text-xs font-bold text-slate-600 dark:text-slate-400">{{ typeConfig.secretLabel }}</label>
              <input
                v-model="form.api_key"
                type="password"
                autocomplete="new-password"
                :placeholder="isEdit && editData?.api_key_set ? `已设置 (${editData.api_key_hint})，留空则不修改` : typeConfig.secretPlaceholder"
                :class="inputCls"
              />
            </div>

            <div>
              <label class="mb-1.5 block text-xs font-bold text-slate-600 dark:text-slate-400">{{ typeConfig.urlLabel }}</label>
              <input
                v-model="form.base_url"
                type="text"
                autocomplete="one-time-code"
                :placeholder="typeConfig.urlPlaceholder"
                :class="inputCls"
              />
            </div>

            <!-- 获取模型列表按钮（仅 OpenAI / Anthropic） -->
            <div v-if="type !== 'paddleocr'" class="flex items-center gap-3">
              <button
                @click="fetchModels"
                :disabled="!canFetchModels || fetchingModels"
                class="inline-flex items-center gap-1.5 rounded-xl border border-slate-200/60 bg-white/60 px-3.5 py-2 text-xs font-bold text-slate-600 transition-all hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10"
              >
                <i class="fa-solid text-[10px]" :class="fetchingModels ? 'fa-circle-notch fa-spin' : 'fa-arrows-rotate'"></i>
                <span class="inline-block w-[4.5rem] text-center">{{ fetchingModels ? '获取中...' : '获取模型列表' }}</span>
              </button>
              <span v-if="!canFetchModels" class="text-xs text-slate-400 dark:text-slate-500">请先填写 API Key</span>
            </div>

            <div class="grid gap-4" :class="type === 'openai' ? 'sm:grid-cols-2' : ''">
              <div>
                <label class="mb-1.5 flex items-center gap-1.5 text-xs font-bold text-slate-600 dark:text-slate-400">
                  {{ type === 'paddleocr' ? 'OCR 模型' : '默认模型' }}
                  <span v-if="type !== 'paddleocr'" class="group relative">
                    <i class="fa-solid fa-circle-info cursor-help text-slate-400 transition-colors hover:text-blue-500 dark:text-slate-500"></i>
                    <span class="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 whitespace-nowrap rounded-lg border border-slate-200/60 bg-white/90 px-3 py-1.5 text-xs font-normal text-slate-600 opacity-0 shadow-lg transition-opacity group-hover:opacity-100 dark:border-white/10 dark:bg-[#0A0A0F]/90 dark:text-slate-300">
                      用于题目分割、纠错等核心任务
                    </span>
                  </span>
                </label>
                <!-- 有模型列表时用自定义下拉 -->
                <div v-if="modelList.length > 0 && type !== 'paddleocr'" class="relative">
                  <button
                    type="button"
                    @click.stop="toggleDropdown('model_name')"
                    class="flex w-full items-center justify-between rounded-xl border border-slate-200/80 bg-white/70 px-4 py-2.5 text-left text-sm transition-colors dark:border-white/10 dark:bg-slate-800/60"
                    :class="form.model_name ? 'text-slate-800 dark:text-slate-200' : 'text-slate-400 dark:text-slate-500'"
                  >
                    <span class="truncate">{{ form.model_name || '请选择模型' }}</span>
                    <i class="fa-solid fa-chevron-down ml-2 text-[10px] text-slate-400 transition-transform" :class="openDropdown === 'model_name' ? 'rotate-180' : ''"></i>
                  </button>
                  <Transition name="dropdown">
                    <div v-if="openDropdown === 'model_name'" class="absolute z-50 mt-1.5 max-h-48 w-full overflow-y-auto rounded-xl border border-slate-200/60 bg-white/80 py-1 shadow-xl dark:border-white/10 dark:bg-[#0A0A0F]/80">
                      <button
                        v-for="m in modelList" :key="m"
                        type="button"
                        @click.stop="selectOption('model_name', m)"
                        class="flex w-full items-center gap-2 px-4 py-2 text-left text-sm transition-colors hover:bg-blue-50/80 dark:hover:bg-blue-500/10"
                        :class="form.model_name === m ? 'font-bold text-blue-600 dark:text-blue-400' : 'text-slate-700 dark:text-slate-300'"
                      >
                        <i v-if="form.model_name === m" class="fa-solid fa-check text-[10px] text-blue-500"></i>
                        <span :class="form.model_name !== m ? 'pl-[18px]' : ''">{{ m }}</span>
                      </button>
                    </div>
                  </Transition>
                </div>
                <!-- 无模型列表时用 input -->
                <input
                  v-else
                  v-model="form.model_name"
                  type="text"
                  :placeholder="typeConfig.modelPlaceholder"
                  :class="inputCls"
                />
              </div>
              <div v-if="type === 'openai'">
                <label class="mb-1.5 flex items-center gap-1.5 text-xs font-bold text-slate-600 dark:text-slate-400">
                  辅助模型
                  <span class="font-normal text-slate-400">（可选）</span>
                  <span class="group relative">
                    <i class="fa-solid fa-circle-info cursor-help text-slate-400 transition-colors hover:text-blue-500 dark:text-slate-500"></i>
                    <span class="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 whitespace-nowrap rounded-lg border border-slate-200/60 bg-white/90 px-3 py-1.5 text-xs font-normal text-slate-600 opacity-0 shadow-lg transition-opacity group-hover:opacity-100 dark:border-white/10 dark:bg-[#0A0A0F]/90 dark:text-slate-300">
                      用于科目识别等简单任务，更快更省 Token
                    </span>
                  </span>
                </label>
                <div v-if="modelList.length > 0" class="relative">
                  <button
                    type="button"
                    @click.stop="toggleDropdown('light_model_name')"
                    class="flex w-full items-center justify-between rounded-xl border border-slate-200/80 bg-white/70 px-4 py-2.5 text-left text-sm transition-colors dark:border-white/10 dark:bg-slate-800/60"
                    :class="form.light_model_name ? 'text-slate-800 dark:text-slate-200' : 'text-slate-400 dark:text-slate-500'"
                  >
                    <span class="truncate">{{ form.light_model_name || '不使用' }}</span>
                    <i class="fa-solid fa-chevron-down ml-2 text-[10px] text-slate-400 transition-transform" :class="openDropdown === 'light_model_name' ? 'rotate-180' : ''"></i>
                  </button>
                  <Transition name="dropdown">
                    <div v-if="openDropdown === 'light_model_name'" class="absolute z-50 mt-1.5 max-h-48 w-full overflow-y-auto rounded-xl border border-slate-200/60 bg-white/80 py-1 shadow-xl dark:border-white/10 dark:bg-[#0A0A0F]/80">
                      <button
                        type="button"
                        @click.stop="selectOption('light_model_name', '')"
                        class="flex w-full items-center gap-2 px-4 py-2 text-left text-sm transition-colors hover:bg-blue-50/80 dark:hover:bg-blue-500/10"
                        :class="!form.light_model_name ? 'font-bold text-blue-600 dark:text-blue-400' : 'text-slate-700 dark:text-slate-300'"
                      >
                        <i v-if="!form.light_model_name" class="fa-solid fa-check text-[10px] text-blue-500"></i>
                        <span :class="form.light_model_name ? 'pl-[18px]' : ''">不使用</span>
                      </button>
                      <button
                        v-for="m in modelList" :key="m"
                        type="button"
                        @click.stop="selectOption('light_model_name', m)"
                        class="flex w-full items-center gap-2 px-4 py-2 text-left text-sm transition-colors hover:bg-blue-50/80 dark:hover:bg-blue-500/10"
                        :class="form.light_model_name === m ? 'font-bold text-blue-600 dark:text-blue-400' : 'text-slate-700 dark:text-slate-300'"
                      >
                        <i v-if="form.light_model_name === m" class="fa-solid fa-check text-[10px] text-blue-500"></i>
                        <span :class="form.light_model_name !== m ? 'pl-[18px]' : ''">{{ m }}</span>
                      </button>
                    </div>
                  </Transition>
                </div>
                <input
                  v-else
                  v-model="form.light_model_name"
                  type="text"
                  placeholder="科目识别等轻量任务使用"
                  :class="inputCls"
                />
              </div>
            </div>

            <!-- Function Calling 开关（仅 OpenAI） -->
            <div v-if="type === 'openai'" class="border-t border-slate-100 pt-4 dark:border-white/5">
              <label class="flex cursor-pointer items-center justify-between">
                <div>
                  <span class="text-sm font-medium text-slate-700 dark:text-slate-300">支持 Function Calling</span>
                  <p class="mt-0.5 text-xs text-slate-400 dark:text-slate-500">文心一言、通义千问等不支持时需关闭</p>
                </div>
                <button
                  type="button"
                  @click="form.supports_function_calling = !form.supports_function_calling"
                  class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                  :class="form.supports_function_calling ? 'bg-blue-600 dark:bg-indigo-500' : 'bg-slate-200 dark:bg-slate-700'"
                >
                  <span
                    class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out"
                    :class="form.supports_function_calling ? 'translate-x-5' : 'translate-x-0'"
                  ></span>
                </button>
              </label>
            </div>

            <!-- PaddleOCR 测试连接 -->
            <div v-if="type === 'paddleocr'" class="flex items-center gap-3">
              <button
                @click="testConnection"
                :disabled="!canTestConnection || testingConnection"
                class="inline-flex items-center gap-1.5 rounded-xl border border-slate-200/60 bg-white/60 px-3.5 py-2 text-xs font-bold text-slate-600 transition-all hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10"
              >
                <i class="fa-solid text-[10px]" :class="testingConnection ? 'fa-circle-notch fa-spin' : 'fa-plug-circle-check'"></i>
                {{ testingConnection ? '检测中...' : '测试连接' }}
              </button>
              <span v-if="testResult?.success" class="text-xs font-medium text-emerald-600 dark:text-emerald-400">
                <i class="fa-solid fa-circle-check mr-1"></i>{{ testResult.message }}
              </span>
              <span v-else-if="testResult && !testResult.success" class="text-xs font-medium text-rose-500 dark:text-rose-400">
                <i class="fa-solid fa-circle-xmark mr-1"></i>{{ testResult.message }}
              </span>
              <span v-else-if="!canTestConnection" class="text-xs text-slate-400 dark:text-slate-500">请先填写 API Token 和 URL</span>
            </div>

            <!-- PaddleOCR 功能开关 -->
            <div v-if="type === 'paddleocr'" class="border-t border-slate-100 pt-4 dark:border-white/5">
              <p class="mb-3 text-xs font-bold text-slate-600 dark:text-slate-400">功能开关</p>
              <div class="space-y-3">
                <label
                  v-for="toggle in [
                    { key: 'use_doc_orientation', label: '文档方向检测' },
                    { key: 'use_doc_unwarping', label: '文档去畸变' },
                    { key: 'use_chart_recognition', label: '图表识别' },
                  ]"
                  :key="toggle.key"
                  class="flex cursor-pointer items-center justify-between"
                >
                  <span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ toggle.label }}</span>
                  <button
                    type="button"
                    @click="form[toggle.key] = !form[toggle.key]"
                    class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    :class="form[toggle.key] ? 'bg-blue-600 dark:bg-indigo-500' : 'bg-slate-200 dark:bg-slate-700'"
                  >
                    <span
                      class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out"
                      :class="form[toggle.key] ? 'translate-x-5' : 'translate-x-0'"
                    ></span>
                  </button>
                </label>
              </div>
            </div>
          </form>

          <!-- 底部按钮 -->
          <div class="flex items-center justify-end gap-3 border-t border-slate-100 px-6 py-4 dark:border-white/5">
            <button
              @click="emit('close')"
              class="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200/60 bg-white/60 px-5 py-2.5 text-sm font-bold text-slate-700 transition-all hover:bg-slate-50 dark:border-white/10 dark:bg-slate-800/60 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              取消
            </button>
            <button
              @click="confirm"
              class="inline-flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-bold text-white shadow-md transition-all"
              :class="typeConfig.btnCls"
            >
              <i class="fa-solid text-xs" :class="isEdit ? 'fa-check' : 'fa-plus'"></i>
              {{ isEdit ? '保存修改' : '添加供应商' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.dialog-fade-enter-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.dialog-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
  transform: scale(0.96);
}
.dropdown-enter-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.dropdown-leave-active {
  transition: opacity 0.1s ease, transform 0.1s ease;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
