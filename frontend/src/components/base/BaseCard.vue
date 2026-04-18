<script setup>
/**
 * BaseCard.vue
 * 毛玻璃风格卡片容器
 */
defineProps({
  padding: { type: String, default: 'p-4' },
  rounded: { type: String, default: 'rounded-lg' },
})
</script>

<template>
  <div
    :class="[rounded, padding]"
    class="border border-white/[0.06] bg-white/[0.02] transition-all hover:bg-white/[0.04] hover:border-white/[0.1]"
  >
    <slot />
  </div>
</template>
