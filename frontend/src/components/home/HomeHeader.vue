<script setup>
/**
 * HomeHeader.vue
 * 落地页顶部导航栏
 */
import { useTheme } from '@/composables/useTheme.js'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseLogo from '@/components/base/BaseLogo.vue'

const { isDark, toggleTheme } = useTheme()

const props = defineProps({
  navScrolled: Boolean,
  activeSection: String,
  sections: Array,
})

const emit = defineEmits(['scrollToSection'])
</script>

<template>
  <nav
    id="top-nav"
    class="fixed top-0 left-0 w-full z-50 border-b transition-[border-color] duration-200"
    :class="navScrolled ? 'border-white/[0.06] bg-[#0A0A0F]/80' : 'border-transparent'"
  >
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-14">
        <!-- Logo -->
        <div class="flex items-center gap-2.5">
          <BaseLogo size="sm" />
          <span class="text-sm font-semibold text-white/90 tracking-wide">智卷错题本</span>
        </div>

        <!-- 中间导航 -->
        <div class="hidden md:flex items-center gap-1">
          <button
            v-for="s in sections"
            :key="s.id"
            @click="emit('scrollToSection', s.id)"
            class="px-3 py-1.5 text-[13px] font-medium rounded-md transition-colors"
            :class="activeSection === s.id ? 'text-white bg-white/[0.06]' : 'text-white/40 hover:text-white/70'"
          >{{ s.label }}</button>
        </div>

        <!-- 右侧操作 -->
        <div class="flex items-center gap-3">
          <a href="https://github.com/xiaozhejiya/error_correction" target="_blank" rel="noopener noreferrer" class="text-white/30 hover:text-white/60 transition-colors">
            <i class="fa-brands fa-github text-base"></i>
          </a>
          <BaseButton to="/auth" size="sm">
            进入工作台
          </BaseButton>
        </div>
      </div>
    </div>
  </nav>
</template>
