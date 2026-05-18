<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions,
} from '@headlessui/vue'
import { useToast } from '@/composables/useToast.js'
import deepseekLogo from '@/assets/deepseek.svg'
import ernieLogo from '@/assets/ernie.svg'

const props = defineProps({
  modelValue: { type: String, default: '' },
  modelOptionsData: { type: Object, default: null },
  disabled: { type: Boolean, default: false },
  noModels: { type: Boolean, default: false },
  statusLoading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])
const { pushToast } = useToast()
const router = useRouter()

const modelLogos = { openai: deepseekLogo, anthropic: ernieLogo }
const checking = ref(false)

const options = computed(() => props.modelOptionsData?.options || [])
const sourceLabelMap = { system: '平台托管', personal: '自己设置' }

const sourceGroups = computed(() => {
  const groups = props.modelOptionsData?.groups || []
  return groups
    .map((group) => ({
      key: group.key,
      label: sourceLabelMap[group.key] || group.label,
      count: options.value.filter((option) => option.source === group.key).length,
    }))
    .filter((group) => group.count > 0)
})

const groupedOptions = computed(() => {
  const groups = sourceGroups.value
  const items = []

  for (const group of groups) {
    const groupOptions = options.value.filter((option) => option.source === group.key)
    if (!groupOptions.length) continue

    items.push({ type: 'group', key: group.key, label: group.label })
    for (const option of groupOptions) {
      items.push({
        type: 'model',
        optionId: option.option_id,
        source: option.source,
        provider: option.category,
        providerName: option.provider_name,
        modelName: option.model_name,
        label: option.label || option.model_name,
        available: option.available,
        isDefault: option.is_default,
        reason: option.reason,
      })
    }
  }

  return items
})

const currentOption = computed(() => {
  return options.value.find((option) => option.option_id === props.modelValue) || null
})

const currentSourceLabel = computed(() => {
  const source = currentOption.value?.source || ''
  const group = sourceGroups.value.find((item) => item.key === source)
  return group?.label || ''
})

const selectedLabel = computed(() => {
  if (props.noModels) return '暂无模型'
  return currentOption.value?.label || currentOption.value?.model_name || '选择模型'
})

const statusState = computed(() => {
  if (props.statusLoading || checking.value) return 'checking'
  if (!currentOption.value) return 'idle'
  if (!currentOption.value.available) return 'error'
  return 'ready'
})

const selectModel = (value) => {
  emit('update:modelValue', value)
}

const goToApiSettings = () => {
  router.push('/app/settings/api')
}

watch(() => props.modelValue, () => {
  if (!props.modelValue) return
  checking.value = true
  pushToast?.('info', '正在检查模型状态...', 1000)

  window.setTimeout(() => {
    checking.value = false
    const option = currentOption.value
    if (!option) return
    if (!option.available) {
      pushToast?.('error', option.reason || '模型不可用', 3000)
    } else {
      pushToast?.('success', `${option.provider_name} 状态验证成功`, 2000)
    }
  }, 700)
})

</script>

<template>
  <Listbox :model-value="modelValue" :disabled="disabled || noModels" @update:model-value="selectModel">
    <div class="relative w-56 min-w-0">
      <ListboxButton
        class="group flex h-10 w-full cursor-pointer items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white/80 px-3 text-left text-xs font-medium text-gray-900 shadow-sm shadow-black/[0.02] transition-all hover:border-gray-300 hover:bg-white disabled:cursor-not-allowed disabled:opacity-60 dark:border-white/[0.09] dark:bg-white/[0.035] dark:text-[#d0d6e0] dark:shadow-black/20 dark:hover:border-white/[0.14] dark:hover:bg-white/[0.06]"
      >
        <div class="flex min-w-0 flex-1 items-center gap-2.5">
          <div
            class="relative flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-gray-500 transition-colors dark:bg-white/[0.06] dark:text-[#8a8f98]"
          >
            <Transition name="model-fade" mode="out-in">
              <img
                v-if="currentOption && modelLogos[currentOption.category]"
                :key="currentOption.category"
                :src="modelLogos[currentOption.category]"
                class="h-3.5 w-3.5 object-contain"
                alt=""
              />
              <i v-else key="fallback" class="fa-solid fa-robot text-[10px]"></i>
            </Transition>
            <span
              class="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full border border-white dark:border-[#101114]"
              :class="{
                'animate-pulse bg-amber-400': statusState === 'checking',
                'bg-emerald-500': statusState === 'ready',
                'bg-rose-500': statusState === 'error',
                'bg-gray-400': statusState === 'idle',
              }"
            ></span>
          </div>

          <span class="min-w-0 flex-1 truncate text-[13px] font-semibold tracking-tight">
            {{ selectedLabel }}
          </span>
        </div>

        <div class="flex shrink-0 items-center gap-2">
          <span
            v-if="currentSourceLabel"
            class="hidden rounded-md bg-gray-100 px-1.5 py-0.5 text-[10px] font-semibold text-gray-500 dark:bg-white/[0.055] dark:text-[#777b84] sm:inline-flex"
          >
            {{ currentSourceLabel }}
          </span>
          <Transition name="model-pop" mode="out-in">
            <i
              v-if="statusState === 'checking'"
              key="checking"
              class="fa-solid fa-spinner animate-spin text-[10px] text-amber-500"
            ></i>
            <i
              v-else-if="statusState === 'error'"
              key="error"
              class="fa-solid fa-xmark text-[10px] text-rose-500"
            ></i>
            <i
              v-else-if="statusState === 'ready'"
              key="ready"
              class="fa-solid fa-check text-[10px] text-emerald-500"
            ></i>
          </Transition>
          <i
            class="fa-solid fa-chevron-down text-[10px] text-gray-400 transition-transform duration-200 group-aria-expanded:rotate-180 dark:text-[#62666d]"
          ></i>
        </div>
      </ListboxButton>

      <Transition
        enter-active-class="transition duration-160 ease-out"
        enter-from-class="-translate-y-1 scale-[0.98] opacity-0"
        enter-to-class="translate-y-0 scale-100 opacity-100"
        leave-active-class="transition duration-100 ease-in"
        leave-from-class="translate-y-0 scale-100 opacity-100"
        leave-to-class="-translate-y-1 scale-[0.98] opacity-0"
      >
        <ListboxOptions
          class="absolute right-0 z-50 mt-2 max-h-72 w-full overflow-hidden rounded-lg border border-gray-200 bg-white p-1 text-sm shadow-xl shadow-black/10 outline-none dark:border-white/[0.08] dark:bg-[#151617] dark:shadow-black/30"
        >
          <template v-for="(item, index) in groupedOptions" :key="item.type === 'group' ? item.key : item.optionId">
            <li
              v-if="item.type === 'group'"
              class="select-none px-3 py-2 text-[11px] font-semibold text-gray-500 dark:text-[#777b84]"
              :class="index > 0 ? 'mt-1 border-t border-gray-100 pt-2.5 dark:border-white/[0.06]' : ''"
            >
              {{ item.label }}
            </li>

            <ListboxOption
              v-else
              v-slot="{ active, selected, disabled: optionDisabled }"
              :value="item.optionId"
              :disabled="!item.available"
              as="template"
            >
              <li
                class="relative flex cursor-pointer select-none items-center gap-2 rounded-md px-3 py-2.5 transition-colors"
                :class="[
                  active ? 'bg-gray-100 dark:bg-white/[0.045]' : '',
                  selected ? 'text-gray-950 dark:text-[#f7f8f8]' : 'text-gray-700 dark:text-[#cbd5e1]',
                  optionDisabled ? 'cursor-not-allowed opacity-45' : '',
                ]"
                :title="item.reason || item.label"
              >
                <i
                  class="fa-solid fa-check w-3 shrink-0 text-[11px] transition-opacity"
                  :class="selected ? 'opacity-100 accent-text' : 'opacity-0'"
                ></i>
                <img
                  v-if="modelLogos[item.provider]"
                  :src="modelLogos[item.provider]"
                  class="h-3.5 w-3.5 shrink-0 object-contain opacity-75"
                  alt=""
                />
                <i v-else class="fa-solid fa-robot h-3.5 w-3.5 shrink-0 text-[11px] text-gray-400"></i>
                <span class="min-w-0 flex-1 truncate text-[13px] font-semibold">
                  {{ item.label }}
                </span>
                <span
                  v-if="item.isDefault"
                  class="shrink-0 rounded-md bg-gray-100 px-1.5 py-0.5 text-[10px] font-semibold text-gray-400 dark:bg-white/[0.06] dark:text-[#62666d]"
                >
                  默认
                </span>
              </li>
            </ListboxOption>
          </template>

          <div class="mt-1 border-t border-gray-100 p-1 pt-1.5 dark:border-white/[0.06]">
            <button
              type="button"
              class="flex w-full items-center justify-center gap-2 rounded-md px-3 py-2 text-xs font-semibold text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-900 dark:text-[#8a8f98] dark:hover:bg-white/[0.045] dark:hover:text-[#f7f8f8]"
              @click.stop="goToApiSettings"
            >
              <i class="fa-solid fa-plug-circle-bolt text-[11px]"></i>
              <span>API 设置</span>
            </button>
          </div>
        </ListboxOptions>
      </Transition>
    </div>
  </Listbox>
</template>

<style scoped>
.model-fade-enter-active,
.model-fade-leave-active {
  transition: opacity 160ms ease, transform 160ms ease;
}

.model-fade-enter-from,
.model-fade-leave-to {
  opacity: 0;
  transform: scale(0.9);
}

.model-pop-enter-active,
.model-pop-leave-active {
  transition: opacity 160ms ease, transform 160ms ease;
}

.model-pop-enter-from,
.model-pop-leave-to {
  opacity: 0;
  transform: scale(0.65);
}
</style>
