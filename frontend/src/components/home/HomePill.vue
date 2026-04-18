<script setup>
/**
 * HomePill.vue
 * 落地页标签徽章
 */
</script>

<template>
  <div class="relative overflow-hidden inline-flex items-center rounded-full px-4 py-1 text-xs font-medium text-white/90 pill-fill">
    <span class="pill-grid absolute inset-0 pointer-events-none"></span>
    <slot>AI 驱动 · 专为学生设计</slot>
  </div>
</template>

<style scoped>
.pill-fill {
  background: linear-gradient(to bottom, rgba(129, 115, 223, 0.9), rgba(99, 87, 199, 0.9));
  box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.12);
}

.pill-grid {
  background-image:
    linear-gradient(to right, rgba(255, 255, 255, 0.06) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255, 255, 255, 0.06) 1px, transparent 1px);
  background-size: 8px 8px;
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
  -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
}
</style>
