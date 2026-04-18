<script setup>
/**
 * HomeSideNav.vue
 * 落地页右侧浮动导航（Section 圆点 + 回到顶部按钮）
 */
import { ArrowUp } from 'lucide-vue-next'

const props = defineProps({
  activeSection: String,
  sections: Array,
  showBackToTop: Boolean,
})

const emit = defineEmits(['scrollToSection', 'back-to-top'])
</script>

<template>
  <!-- 右侧 Section 导航 -->
  <nav id="section-nav" class="fixed right-4 md:right-6 top-1/2 -translate-y-1/2 z-40 flex flex-col items-center gap-3 py-4 px-1.5 rounded-lg brand-btn scale-90 md:scale-100">
    <button
      v-for="s in sections"
      :key="s.id"
      class="relative flex items-center justify-center w-6 h-6 focus:outline-none group"
      :title="s.label"
      @click="emit('scrollToSection', s.id)"
    >
      <div
        class="w-1 h-1 rounded-full transition-all duration-200"
        :class="activeSection === s.id
          ? 'bg-white scale-150'
          : 'bg-white/20 group-hover:bg-white/50'"
      ></div>
      <span class="absolute right-10 px-2 py-1 rounded-md bg-[#111118] border border-white/[0.06] text-[11px] font-medium text-white/70 whitespace-nowrap pointer-events-none opacity-0 translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200">
        {{ s.label }}
      </span>
    </button>
  </nav>

  <!-- 回到顶部按钮 -->
  <button
    id="back-to-top"
    class="fixed bottom-8 right-8 z-50 flex h-10 w-10 items-center justify-center rounded-full brand-btn text-[#8a8f98] transition-[opacity,transform] duration-300 hover:text-[#f7f8f8]"
    :style="{ opacity: showBackToTop ? '1' : '0', transform: showBackToTop ? 'translateY(0)' : 'translateY(12px)', pointerEvents: showBackToTop ? 'auto' : 'none' }"
    aria-label="回到顶部"
    @click="emit('back-to-top')"
  >
    <ArrowUp class="h-4 w-4" />
  </button>
</template>
