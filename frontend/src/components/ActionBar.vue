<script setup>

const props = defineProps({
  splitEnabled: { type: Boolean, default: false },
  exportEnabled: { type: Boolean, default: false },
  splitting: { type: Boolean, default: false },
  splitCompleted: { type: Boolean, default: false },
  uploadMode: { type: String, default: 'exam' },
})

const emit = defineEmits(['split', 'export', 'save-to-db'])
</script>

<template>
  <div class="flex items-center justify-center gap-4">
    <!-- 主操作区 -->
    <div class="flex items-center gap-3">
    <!-- 主操作按钮：引入超级炫酷的炫彩发光效果 -->
    <button
      type="button"
      class="group relative inline-flex h-14 items-center justify-center sm:w-auto w-full disabled:cursor-not-allowed disabled:opacity-50"
      :disabled="!splitEnabled"
      @click="emit('split')"
    >
      <!-- 背景光晕 (悬浮时放大并提亮) -->
      <div
        class="absolute -inset-1 rounded-2xl bg-gradient-to-r from-blue-600 via-indigo-500 to-purple-600 blur-md transition-all duration-500 opacity-0 group-hover:opacity-60 group-hover:blur-xl"
        :class="!splitEnabled && 'hidden'"
      ></div>
      
      <!-- 按钮本体 -->
      <span class="relative inline-flex h-full w-full items-center justify-center gap-3 rounded-2xl bg-slate-900 px-10 text-[13px] font-black tracking-widest text-white shadow-2xl group-hover:-translate-y-0.5 group-active:translate-y-0 dark:bg-white dark:text-slate-900">
        <template v-if="splitting">
          <i class="fa-solid fa-spinner fa-spin" :class="uploadMode === 'note' ? 'text-emerald-400' : 'text-blue-400'"></i>
          <span>{{ uploadMode === 'note' ? '正在整理笔记...' : '正在智能分割...' }}</span>
        </template>
        <template v-else-if="splitCompleted">
          <i class="fa-solid fa-check-double text-emerald-400"></i>
          <span>{{ uploadMode === 'note' ? '整理已完成' : '解析已完成' }}</span>
        </template>
        <template v-else>
          <i class="fa-solid" :class="uploadMode === 'note' ? 'fa-book-open text-emerald-400 group-hover:animate-pulse' : 'fa-wand-magic-sparkles text-blue-400 group-hover:animate-pulse'"></i>
          <span>{{ uploadMode === 'note' ? '启动 AI 笔记整理' : '启动 AI 智能分割' }}</span>
        </template>
      </span>
    </button>

    <!-- 导出按钮：极简现代感 -->
    <Transition name="action-btn">
      <button
        v-if="exportEnabled"
        type="button"
        class="group relative inline-flex h-14 items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-white px-8 text-[13px] font-black tracking-widest text-slate-900 shadow-sm hover:border-slate-900 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-30 dark:border-white/10 dark:bg-slate-900 dark:text-white dark:hover:border-white dark:hover:bg-slate-800"
        @click="emit('export')"
      >
        <i class="fa-solid fa-file-export transition-transform group-hover:-translate-x-0.5"></i>
        导出错题本
      </button>
    </Transition>

    <!-- 导入错题库按钮：极简现代感 -->
    <Transition name="action-btn">
      <button
        v-if="exportEnabled"
        type="button"
        class="group relative inline-flex h-14 items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-white px-8 text-[13px] font-black tracking-widest text-slate-900 shadow-sm hover:border-slate-900 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-30 dark:border-white/10 dark:bg-slate-900 dark:text-white dark:hover:border-white dark:hover:bg-slate-800"
        @click="emit('save-to-db')"
      >
        <i class="fa-solid fa-database transition-transform group-hover:-translate-y-0.5"></i>
        导入错题库
      </button>
    </Transition>

    </div>
  </div>
</template>

<style scoped>
.action-btn-enter-active {
  transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.action-btn-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.action-btn-enter-from {
  opacity: 0;
  transform: translateY(8px) scale(0.95);
}
.action-btn-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.95);
}
</style>