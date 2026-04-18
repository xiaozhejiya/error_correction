<script setup>
/**
 * ToastContainer.vue
 * Toast 通知容器（成功/错误/信息）
 */
defineProps({
  toasts: { type: Array, default: () => [] },
})

/**
 * 核心修复逻辑：在元素离开时通过 JS 获取其当前位置，并将其设为 absolute。
 * 这样既能脱离文档流让其他元素平滑移动，又能保持在原位不发生“瞬移”或重叠。
 */
const onLeave = (el) => {
  const { left, top, width, height } = el.getBoundingClientRect()
  // 保持原有宽度，并设为绝对定位，位置相对于 fixed 容器
  el.style.left = `${left}px`
  el.style.top = `${top}px`
  el.style.width = `${width}px`
  el.style.height = `${height}px`
  el.style.position = 'absolute'
}
</script>

<template>
  <div class="pointer-events-none fixed left-0 right-0 top-6 z-[200] flex flex-col items-center gap-3 px-4 md:left-64">
    <TransitionGroup
      enter-active-class="transition duration-500 cubic-bezier(0.34, 1.56, 0.64, 1)"
      enter-from-class="opacity-0 -translate-y-8 scale-90"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition duration-300 ease-in"
      leave-from-class="opacity-100 translate-y-0 scale-100"
      leave-to-class="opacity-0 -translate-y-12 scale-90"
      @leave="onLeave"
    >
      <div
        v-for="t in toasts"
        :key="t.id"
        class="pointer-events-auto relative flex min-w-[320px] max-w-md items-center gap-4 overflow-hidden rounded-[1.25rem] border px-5 py-4 shadow-[0_20px_50px_rgba(0,0,0,0.1)] dark:shadow-[0_20px_50px_rgba(0,0,0,0.3)]"
        :class="
          t.type === 'success'
            ? 'border-emerald-500/20 bg-emerald-50/90 text-emerald-900 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-300'
            : t.type === 'error'
              ? 'border-rose-500/20 bg-rose-50/90 text-rose-900 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-300'
              : t.type === 'warning'
                ? 'border-amber-500/20 bg-amber-50/90 text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300'
                : 'border-blue-500/20 bg-blue-50/90 text-blue-900 dark:border-indigo-500/20 dark:bg-indigo-500/10 dark:text-indigo-300'
        "
      >
        <!-- 背景流体装饰 -->
        <div 
          class="absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-10 blur-2xl"
          :class="
            t.type === 'success' ? 'bg-emerald-500' : 
            t.type === 'error' ? 'bg-rose-500' : 
            t.type === 'warning' ? 'bg-amber-500' : 'bg-blue-500'
          "
        ></div>

        <!-- 图标区 -->
        <div 
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl shadow-inner"
          :class="
            t.type === 'success' ? 'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400' : 
            t.type === 'error' ? 'bg-rose-500/10 text-rose-600 dark:bg-rose-500/20 dark:text-rose-400' : 
            t.type === 'warning' ? 'bg-amber-500/10 text-amber-600 dark:bg-amber-500/20 dark:text-amber-400' : 
            'bg-blue-500/10 text-blue-600 dark:bg-indigo-500/20 dark:text-indigo-400'
          "
        >
          <i 
            class="fa-solid text-lg"
            :class="
              t.type === 'success' ? 'fa-circle-check' : 
              t.type === 'error' ? 'fa-circle-xmark' : 
              t.type === 'warning' ? 'fa-triangle-exclamation' : 'fa-circle-info'
            "
          ></i>
        </div>

        <!-- 文本内容 -->
        <div class="flex flex-col gap-0.5">
          <span class="text-[10px] font-black uppercase tracking-[0.2em] opacity-50">
            {{ t.type === 'success' ? 'Success' : t.type === 'error' ? 'Error' : t.type === 'warning' ? 'Warning' : 'Information' }}
          </span>
          <p class="text-[13px] font-bold leading-tight tracking-tight">
            {{ t.message }}
          </p>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
/* 确保多个 Toast 同时存在时的布局平滑移动 */
.v-move {
  transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}
</style>
