<script setup>
/**
 * BaseSelect.vue
 * 自定义下拉选择器
 */
import { ref } from 'vue'
import { useClickOutside } from '@/composables/useClickOutside.js'

const props = defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },
  label: { type: String, default: '' },
  placeholder: { type: String, default: '全部' },
  icon: { type: Function, default: null },
  widthClass: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])
const open = ref(false)

useClickOutside('.custom-select-wrapper', () => { open.value = false })

const toggle = () => { open.value = !open.value }
const select = (val) => { emit('update:modelValue', val); open.value = false }
</script>

<template>
  <div class="custom-select-wrapper relative" :class="widthClass">
    <label v-if="label" class="mb-1.5 block text-xs font-medium text-slate-500 dark:text-[#62666d]">{{ label }}</label>
    <button
      type="button"
      @click.stop="toggle"
      class="flex h-9 w-full items-center justify-between rounded-md border border-slate-200/70 bg-white/80 px-3 text-left text-sm font-medium text-slate-500 transition-colors hover:border-slate-300 dark:border-white/[0.08] dark:bg-white/[0.02] dark:hover:border-white/[0.12]"
      :class="[
        open ? 'border-slate-300 dark:border-white/[0.15]' : '',
        modelValue ? 'text-slate-800 dark:text-[#d0d6e0]' : 'text-slate-500 dark:text-[#62666d]',
      ]"
    >
      <span class="truncate">{{ modelValue || placeholder }}</span>
      <i class="fa-solid fa-chevron-down ml-2 text-[10px] text-slate-400 transition-transform duration-200 dark:text-[#62666d]" :class="open ? 'rotate-180' : ''"></i>
    </button>
    <Transition name="dropdown">
      <div v-if="open" class="absolute left-0 top-full z-50 mt-1 min-w-full overflow-hidden rounded-md border border-slate-200/70 bg-white/95 py-1 shadow-lg shadow-slate-200/60 dark:border-white/[0.08] dark:bg-[#1c1c20] dark:shadow-black/40">
        <div class="no-scrollbar max-h-56 overflow-y-auto">
          <button
            type="button"
            @click.stop="select('')"
            class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-slate-100/80 dark:hover:bg-white/[0.04]"
            :class="modelValue === '' ? 'text-slate-900 dark:text-[#f7f8f8]' : 'text-slate-600 dark:text-[#8a8f98]'"
          >
            <span class="min-w-0 flex-1 truncate">{{ placeholder }}</span>
            <i v-if="modelValue === ''" class="fa-solid fa-check shrink-0 text-[10px] text-[rgb(129,115,223)]"></i>
          </button>
          <button
            v-for="opt in options" :key="opt"
            type="button"
            @click.stop="select(opt)"
            class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-slate-100/80 dark:hover:bg-white/[0.04]"
            :class="modelValue === opt ? 'text-slate-900 dark:text-[#f7f8f8]' : 'text-slate-600 dark:text-[#8a8f98]'"
          >
            <span class="min-w-0 flex-1 truncate">{{ opt }}</span>
            <i v-if="modelValue === opt" class="fa-solid fa-check shrink-0 text-[10px] text-[rgb(129,115,223)]"></i>
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.15s ease-out;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
