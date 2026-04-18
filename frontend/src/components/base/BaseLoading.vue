<script setup>
/**
 * BaseLoading.vue
 * 全局加载遮罩（BaseLogo + 进度条动画）
 */
import BaseLogo from '@/components/base/BaseLogo.vue'

defineProps({
  visible: { type: Boolean, default: true },
})
const emit = defineEmits(['after-enter'])
</script>

<template>
  <Transition name="loading-fade" @after-enter="emit('after-enter')">
    <div v-if="visible" class="fixed inset-0 z-[200] flex flex-col items-center justify-center gap-8 bg-[#0A0A0F]">
      <BaseLogo size="lg" breathe />
      <div class="w-48">
        <div class="h-0.5 w-full rounded-full bg-white/10 overflow-hidden">
          <div class="h-full rounded-full bg-gradient-to-r from-[rgba(129,115,223,0.8)] to-[rgba(99,87,199,0.8)] loading-bar"></div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.loading-fade-enter-active {
  transition: opacity 0.25s ease;
}
.loading-fade-leave-active {
  transition: opacity 0.4s ease;
}
.loading-fade-enter-from,
.loading-fade-leave-to {
  opacity: 0;
}

.loading-bar {
  animation: loadProgress 1.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
@keyframes loadProgress {
  from { width: 0%; }
  to   { width: 100%; }
}
</style>
