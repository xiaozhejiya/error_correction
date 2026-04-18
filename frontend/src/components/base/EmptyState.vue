<script setup>
/**
 * EmptyState.vue
 * Linear 风格空状态组件 — 居中图标 + 标题 + 描述 + 操作按钮
 */
defineProps({
  icon: { type: String, default: '' },
  title: { type: String, required: true },
  description: { type: String, default: '' },
})
</script>

<template>
  <div class="flex flex-1 flex-col items-center justify-center">
    <!-- 图标 -->
    <div v-if="icon" class="mb-6 flex h-16 w-16 items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.02]">
      <i :class="icon" class="text-2xl text-[#62666d]"></i>
    </div>

    <!-- 标题 -->
    <h3 class="text-base font-medium text-[#f7f8f8]">{{ title }}</h3>

    <!-- 描述 -->
    <p v-if="description" class="mt-2 max-w-sm text-center text-sm text-[#62666d] leading-relaxed">{{ description }}</p>

    <!-- 操作按钮区 -->
    <div v-if="$slots.default" class="mt-6 flex items-center gap-3">
      <slot></slot>
    </div>
  </div>
</template>
