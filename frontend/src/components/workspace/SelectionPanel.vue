<script setup>
/**
 * SelectionPanel.vue
 * 题目选择面板
 */
defineProps({
  count: { type: Number, default: 0 },
  visible: { type: Boolean, default: false },
  exportLabel: { type: String, default: '生成复习卷' },
  showSave: { type: Boolean, default: false },
})

const emit = defineEmits(['export', 'save', 'clear'])
</script>

<template>
  <Transition
    enter-active-class="transition-transform duration-300 ease-out"
    enter-from-class="translate-y-12"
    enter-to-class="translate-y-0"
    leave-active-class="transition-transform duration-200 ease-in"
    leave-from-class="translate-y-0"
    leave-to-class="translate-y-12"
  >
    <div v-if="visible && count" class="fixed bottom-24 left-1/2 z-50 -translate-x-1/2 md:bottom-10">
      <div class="flex items-center gap-6 rounded-full border border-slate-200/60 bg-white/70 px-6 py-3 shadow-md dark:border-white/10 dark:bg-white/[0.03]">
        <div class="flex items-center gap-3 border-r border-slate-200/60 pr-6 dark:border-white/10">
          <div class="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 font-mono text-xs font-bold text-white shadow-sm dark:bg-indigo-500">
            {{ count }}
          </div>
          <span class="text-sm font-bold tracking-wider text-slate-700 dark:text-slate-200">已选中题目</span>
        </div>

        <div class="flex items-center gap-3">
          <button
            @click="emit('export')"
            class="group inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-6 text-[13px] font-black tracking-widest text-slate-900 shadow-sm transition-all hover:border-slate-900 hover:bg-slate-50 dark:border-white/10 dark:bg-slate-900 dark:text-white dark:hover:border-white dark:hover:bg-slate-800"
          >
            <i class="fa-solid fa-file-export transition-transform group-hover:-translate-x-0.5"></i>
            {{ exportLabel }}
          </button>

          <button
            v-if="showSave"
            @click="emit('save')"
            class="group inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-6 text-[13px] font-black tracking-widest text-slate-900 shadow-sm transition-all hover:border-slate-900 hover:bg-slate-50 dark:border-white/10 dark:bg-slate-900 dark:text-white dark:hover:border-white dark:hover:bg-slate-800"
          >
            <i class="fa-solid fa-database transition-transform group-hover:-translate-y-0.5"></i>
            导入错题库
          </button>

          <button
            @click="emit('clear')"
            class="group inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-6 text-[13px] font-black tracking-widest text-slate-900 shadow-sm transition-all hover:border-slate-900 hover:bg-slate-50 dark:border-white/10 dark:bg-slate-900 dark:text-white dark:hover:border-white dark:hover:bg-slate-800"
          >
            清除
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>
