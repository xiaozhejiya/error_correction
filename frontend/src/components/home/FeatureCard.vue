<script setup>
import { computed } from 'vue'

const props = defineProps({
  icon: {
    type: [Object, Function],
    required: true
  },
  title: {
    type: String,
    required: true
  },
  desc: {
    type: String,
    required: true
  },
  spanClass: {
    type: String,
    default: ''
  },
  delay: {
    type: String,
    default: '0ms'
  }
})
</script>

<template>
  <div
    class="reveal feature-card group relative flex flex-col rounded-[20px] p-[1px] overflow-hidden"
    :class="spanClass"
    :style="{ transitionDelay: delay }"
  >
    <!-- 默认状态：灰色 Linear 渐变边框层 -->
    <div class="absolute inset-0 bg-gradient-to-br from-white/[0.12] via-white/[0.04] to-transparent"></div>

    <!-- 卡片主体背景层 — brand-btn 风格白玻璃 -->
    <div class="relative h-full w-full rounded-[19px] p-6 flex flex-col items-start text-left transition-all duration-500 overflow-hidden" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); border-top-color: rgba(255,255,255,0.15); border-bottom-color: rgba(255,255,255,0.03);">

      <!-- 图标容器（BaseLogo 风格） -->
      <div class="feature-icon relative z-10 mb-4 flex h-10 w-10 items-center justify-center rounded-xl overflow-hidden">
        <span class="feature-icon__grid absolute inset-0 pointer-events-none"></span>
        <component :is="icon" class="relative h-5 w-5 text-white" />
      </div>
      
      <!-- 文字内容 -->
      <h3 class="relative z-10 mb-2 text-base font-semibold text-white/90 group-hover:text-white transition-colors duration-300">{{ title }}</h3>
      <p class="relative z-10 text-sm leading-relaxed text-white/40 group-hover:text-white/60 transition-colors duration-300">{{ desc }}</p>
    </div>
  </div>
</template>

<style scoped>
.feature-icon {
  background: linear-gradient(to bottom, rgba(129, 115, 223, 0.9), rgba(99, 87, 199, 0.9));
  box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.12);
}

.feature-icon__grid {
  background-image:
    linear-gradient(to right, rgba(255, 255, 255, 0.06) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255, 255, 255, 0.06) 1px, transparent 1px);
  background-size: 8px 8px;
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
  -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
}
</style>
