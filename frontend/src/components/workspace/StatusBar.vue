<script setup>
/**
 * StatusBar.vue
 * 状态栏（引擎状态 + 模型选择）
 */
import { computed, ref, watch } from 'vue'
import { useToast } from '@/composables/useToast.js'
import {
  Listbox,
  ListboxButton,
  ListboxOptions,
  ListboxOption,
} from '@headlessui/vue'
import deepseekLogo from '@/assets/deepseek.svg'
import ernieLogo from '@/assets/ernie.svg'

// Tooltip 相关状态
const tooltipVisible = ref(false)
const tooltipText = ref('')
const tooltipPosition = ref({ x: 0, y: 0 })

// 显示 tooltip
const showTooltip = (event, text) => {
  if (!text || text.length <= 20) return // 短文本不需要 tooltip

  tooltipText.value = text
  const rect = event.currentTarget.getBoundingClientRect()
  tooltipPosition.value = {
    x: rect.left + rect.width / 2,
    y: rect.top - 8
  }
  tooltipVisible.value = true
}

// 隐藏 tooltip
const hideTooltip = () => {
  tooltipVisible.value = false
}

const emit = defineEmits(['update:selectedModel', 'model-switch'])
const { pushToast } = useToast()

const props = defineProps({
  statusLoading: { type: Boolean, default: true },
  statusError: { type: String, default: '' },
  statusPills: { type: Array, default: () => [] },
  providerOptions: { type: Array, default: () => [] },
  selectedModel: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  noModels: { type: Boolean, default: false },
  modelSwitching: { type: Boolean, default: false },
})

const modelLogos = { 'deepseek': deepseekLogo, 'ernie': ernieLogo, 'openai': deepseekLogo, 'anthropic': ernieLogo }
// 构建扁平模型列表，按 provider 分组
// 支持同一 category 下有多个 provider 实例（通过 provider_id 区分）
const modelOptions = computed(() => {
  const items = []

  for (const p of props.providerOptions) {
    if (!p.models || !p.models.length) continue

    const displayLabel = p.label || p.value
    const isActive = p.is_active === true

    // 添加分组标题
    items.push({
      type: 'group',
      label: displayLabel + (isActive ? '' : ' (非激活)'),
      provider: p.value,
      providerId: p.provider_id || null,
    })

    // 添加该分组下的模型
    for (const model of p.models) {
      // 复合值：包含 provider_id 和 model，确保唯一性
      const compositeValue = p.provider_id ? `${p.provider_id}:${model}` : model
      items.push({
        type: 'model',
        provider: p.value,
        providerId: p.provider_id || null,
        providerLabel: displayLabel,
        model,
        value: compositeValue,
        configured: p.configured,
        isDefault: model === p.default_model,
        isActive,
      })
    }
  }
  return items
})

const selectedLabel = computed(() => props.noModels ? '暂无模型' : (getSelectedModelName() || '选择模型'))

// 从复合值中提取模型名称
const getSelectedModelName = () => {
  if (!props.selectedModel) return ''
  if (typeof props.selectedModel === 'string' && props.selectedModel.includes(':')) {
    return props.selectedModel.split(':')[1]
  }
  return props.selectedModel
}

// 反查当前选中模型所属的 provider
const currentProvider = computed(() => {
  if (!props.selectedModel) return null

  const modelName = getSelectedModelName()

  for (const p of props.providerOptions) {
    if (p.models && p.models.includes(modelName)) {
      // 如果是复合值，还需要匹配 provider_id
      if (typeof props.selectedModel === 'string' && props.selectedModel.includes(':')) {
        const providerId = props.selectedModel.split(':')[0]
        if (p.provider_id === providerId) {
          return p
        }
      } else {
        return p
      }
    }
  }
  return null
})

// 模型切换处理函数
const handleModelSwitch = async (newValue) => {
  if (!newValue || newValue === props.selectedModel) return

  // 从复合值中提取信息
  let providerId = null
  let modelName = newValue
  if (typeof newValue === 'string' && newValue.includes(':')) {
    const parts = newValue.split(':')
    providerId = parts[0]
    modelName = parts[1]
  }

  const provider = modelOptions.value.find(item =>
    item.type === 'model' &&
    item.model === modelName &&
    item.providerId === providerId
  )

  if (!provider) {
    console.warn('[StatusBar] 未找到对应的 provider:', { providerId, modelName })
    return
  }

  console.log('[StatusBar] 切换模型:', { provider: provider.provider, providerId: provider.providerId, modelName: provider.model })

  emit('model-switch', {
    provider: provider.provider,
    providerId: provider.providerId,
    modelName: provider.model
  })
  emit('update:selectedModel', provider.value)
}

// ---- 模型检查状态 ----
const isChecking = ref(false)
const showResult = ref(true)

watch(() => props.selectedModel, () => {
  isChecking.value = true
  showResult.value = false
  setTimeout(() => {
    isChecking.value = false
    showResult.value = true
  }, 800)
})

const modelStatusError = computed(() => {
  if (!showResult.value || !currentProvider.value) return ''
  if (!currentProvider.value.configured) return `${currentProvider.value.label} 未配置 API Key`
  if (currentProvider.value.key_valid === false) return `${currentProvider.value.label} API Key 验证失败`
  return ''
})
</script>

<template>
  <div class="relative z-20 flex flex-wrap items-center gap-4 py-2 text-sm shrink-0">
    <div class="flex items-center gap-2.5">
      <span class="text-xs font-medium uppercase tracking-[0.15em] text-[#62666d]">
        引擎状态
      </span>
    </div>

    <!-- 分隔符 -->
    <div class="h-4 w-px bg-white/[0.08]"></div>

    <!-- 全局系统错误 -->
    <span v-if="statusError"
      class="inline-flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs font-medium text-rose-400">
      <i class="fa-solid fa-circle-exclamation animate-pulse"></i>
      {{ statusError }}
    </span>

    <!-- Pills -->
    <div v-if="!statusError" class="flex flex-wrap items-center gap-2.5">
      <span v-for="p in statusPills" :key="p.key"
        class="inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium" :class="p.loading
          ? 'border-amber-500/20 bg-amber-500/10 text-amber-400'
          : p.isPlaceholder
            ? 'border-white/[0.05] bg-white/[0.03] text-[#62666d]'
            : p.ok
              ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400'
              : 'border-rose-500/20 bg-rose-500/10 text-rose-400'
          ">
        <div class="relative h-2.5 w-2.5 shrink-0">
          <Transition name="icon-pop">
            <i :key="p.loading ? 'loading' : p.isPlaceholder ? 'placeholder' : p.ok ? 'ok' : 'error'"
              class="fa-solid absolute inset-0 flex items-center justify-center text-[10px]"
              :class="p.loading ? 'fa-spinner animate-spin' : p.isPlaceholder ? 'fa-hourglass-start' : p.ok ? 'fa-check' : 'fa-xmark'"></i>
          </Transition>
        </div>
        {{ p.label }}
      </span>
    </div>

    <!-- 模型下拉选择器 (按 provider 分组) -->
    <div v-if="!statusError" class="ml-auto flex items-center gap-2">
      <Listbox :model-value="selectedModel" @update:model-value="handleModelSwitch" :disabled="disabled || noModels">
        <div class="relative w-56 min-w-0">
          <ListboxButton
            class="group relative flex w-full cursor-pointer items-center justify-between gap-4 rounded-md border border-white/[0.08] bg-white/[0.02] px-3 py-1.5 text-left text-xs font-medium text-[#d0d6e0] transition-colors hover:bg-white/[0.05] hover:border-white/[0.12]"
            :disabled="disabled">
            <div class="flex items-center gap-2.5 min-w-0 flex-1">
              <div
                class="relative flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-white/[0.05] text-[rgb(145,132,235)]">
                <Transition name="fade" mode="out-in">
                  <img v-if="currentProvider" :key="currentProvider.provider_id || currentProvider.label"
                    :src="modelLogos[currentProvider.provider_id || currentProvider.label] || modelLogos[currentProvider.value]"
                    class="h-3.5 w-3.5 object-contain" alt="" />
                  <i v-else key="default-bot" class="fa-solid fa-robot text-[10px]"></i>
                </Transition>
                <!-- 状态指示点 -->
                <div v-if="currentProvider || statusLoading || modelSwitching"
                  class="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full border border-[#0f1011]"
                  :class="(statusLoading || isChecking || modelSwitching) ? 'bg-amber-400 animate-pulse' : (!currentProvider.configured || currentProvider.key_valid === false) ? 'bg-rose-500' : 'bg-emerald-500'">
                </div>
              </div>
              <span class="block min-w-0 flex-1 truncate text-xs font-medium tracking-tight text-[#d0d6e0]"
                @mouseenter="showTooltip($event, selectedLabel)" @mouseleave="hideTooltip">
                {{ selectedLabel }}
              </span>
            </div>
            <div class="flex items-center gap-2">
              <div class="relative h-2.5 w-2.5 shrink-0">
                <Transition name="icon-pop">
                  <i v-if="isChecking || statusLoading || modelSwitching" key="checking"
                    class="fa-solid fa-spinner animate-spin absolute inset-0 flex items-center justify-center text-[10px] text-amber-500"></i>
                  <i v-else-if="currentProvider && (!currentProvider.configured || currentProvider.key_valid === false)"
                    key="error"
                    class="fa-solid fa-xmark absolute inset-0 flex items-center justify-center text-[10px] text-rose-500"></i>
                  <i v-else-if="currentProvider" key="ok"
                    class="fa-solid fa-check absolute inset-0 flex items-center justify-center text-[10px] text-emerald-500"></i>
                </Transition>
              </div>
              <i
                class="fa-solid fa-chevron-down shrink-0 text-[10px] text-[#62666d] transition-transform duration-300 group-aria-expanded:rotate-180"></i>
            </div>
          </ListboxButton>

          <Transition enter-active-class="transition duration-200 ease-out"
            enter-from-class="transform scale-95 opacity-0 -translate-y-2"
            enter-to-class="transform scale-100 opacity-100 translate-y-0"
            leave-active-class="transition duration-100 ease-in"
            leave-from-class="transform scale-100 opacity-100 translate-y-0"
            leave-to-class="transform scale-95 opacity-0 -translate-y-2">
            <ListboxOptions
              class="absolute right-0 z-50 mt-2 max-h-72 w-full overflow-auto rounded-md border border-white/[0.08] bg-white/[0.02] text-base focus:outline-none sm:text-sm">
              <template v-for="(item, idx) in modelOptions" :key="idx">
                <!-- 分组标题 -->
                <li v-if="item.type === 'group'"
                  class="select-none px-4 text-[10px] font-medium uppercase tracking-widest text-[#62666d]"
                  :class="idx > 0 ? 'mt-1 border-t border-white/[0.05] pt-2' : ''">
                  <div class="flex items-center gap-2">
                    <img v-if="modelLogos[item.providerId] ?? modelLogos[item.provider]"
                      :src="modelLogos[item.providerId] ?? modelLogos[item.provider]"
                      class="h-3 w-3 object-contain opacity-60" alt="" />
                    {{ item.label }}
                  </div>
                </li>
                <!-- 模型选项 -->
                <ListboxOption v-else :value="item.value" :disabled="!item.configured" as="template"
                  v-slot="{ active, selected, disabled: optDisabled }">
                  <li class="relative cursor-pointer select-none py-2.5 pl-10 pr-4 transition-colors" :class="[
                    active ? 'bg-white/[0.05]' : '',
                    optDisabled ? 'opacity-40 cursor-not-allowed' : ''
                  ]">
                    <span class="block truncate text-sm transition-colors min-w-0"
                      :class="[selected ? 'font-medium text-white' : 'font-medium text-[#d0d6e0]']"
                      @mouseenter="showTooltip($event, item.model)" @mouseleave="hideTooltip">
                      {{ item.model }}
                      <span v-if="item.isDefault" class="ml-1 text-[10px] text-[#62666d]">默认</span>
                    </span>
                    <span v-if="selected" class="absolute inset-y-0 left-0 flex items-center pl-3 text-white">
                      <i class="fa-solid fa-check text-sm"></i>
                    </span>
                  </li>
                </ListboxOption>
              </template>
            </ListboxOptions>
          </Transition>
        </div>
      </Listbox>
    </div>
  </div>

  <!-- Tooltip 组件 -->
  <Teleport to="body">
    <Transition enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 scale-95 translate-y-1" enter-to-class="opacity-100 scale-100 translate-y-0"
      leave-active-class="transition duration-150 ease-in" leave-from-class="opacity-100 scale-100 translate-y-0"
      leave-to-class="opacity-0 scale-95 translate-y-1">
      <div v-if="tooltipVisible && tooltipText" class="fixed z-[9999] pointer-events-none" :style="{
        left: `${tooltipPosition.x}px`,
        top: `${tooltipPosition.y}px`,
        transform: 'translateX(-50%) translateY(-100%)'
      }">
        <div class="relative">
          <!-- 箭头 -->
          <div class="absolute left-1/2 top-full -translate-x-1/2 w-2 h-2">
            <div class="w-2 h-2 bg-[#191a1b] rotate-45"></div>
          </div>

          <!-- 内容 -->
          <div class="bg-[#191a1b] text-[#d0d6e0] px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap">
            {{ tooltipText }}
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.icon-pop-enter-active {
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.icon-pop-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.icon-pop-enter-from {
  opacity: 0;
  transform: scale(0.3) rotate(-180deg);
}

.icon-pop-leave-to {
  opacity: 0;
  transform: scale(0.3) rotate(180deg);
}
</style>
