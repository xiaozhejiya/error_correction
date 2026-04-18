<script setup>
/**
 * QuestionItemSkeleton.vue
 * 题目条目骨架屏
 */
defineProps({
  count: { type: Number, default: 5 },
})
</script>

<template>
  <div class="space-y-4">
    <div
      v-for="i in count" :key="i"
      class="animate-pulse rounded-2xl border border-slate-200/60 bg-white/70 p-6 shadow-sm dark:border-white/10 dark:bg-white/[0.03]"
    >
      <div class="flex items-start gap-4">
        <!-- 内容区：精确复刻 QuestionItem 的 min-w-0 flex-1 -->
        <div class="min-w-0 flex-1">
          <!-- 标签行：status icon + subject + type + tag -->
          <div class="mb-3 flex flex-wrap items-center gap-2">
            <div class="h-4 w-4 rounded-full bg-slate-200/80 dark:bg-white/[0.07]"></div>
            <div class="h-5 w-14 rounded-full bg-slate-200/80 dark:bg-white/[0.07]"></div>
            <div class="h-5 w-10 rounded-full bg-slate-200/80 dark:bg-white/[0.07]"></div>
            <div class="h-5 w-16 rounded-full bg-slate-200/80 dark:bg-white/[0.07]"></div>
          </div>

          <!-- 摘要：line-clamp-2 text-sm -->
          <div class="space-y-2">
            <div class="h-4 w-full rounded-lg bg-slate-200/80 dark:bg-white/[0.07]"></div>
            <div class="h-4 rounded-lg bg-slate-200/80 dark:bg-white/[0.07]" :style="`width: ${60 + (i * 7) % 30}%`"></div>
          </div>
        </div>

        <!-- 右侧操作区：h-8 w-8 按钮 -->
        <div class="h-8 w-8 shrink-0 rounded-xl bg-slate-200/80 dark:bg-white/[0.07]"></div>
      </div>
    </div>
  </div>
</template>
