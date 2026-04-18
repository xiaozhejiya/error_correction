<script setup>
/**
 * ContentPanel.vue
 * 右侧内容面板布局 — Linear 风格
 * 支持：顶部栏（标题 + 步骤 tab + 工具栏）+ 主内容区 + 可选右侧属性栏
 */
defineProps({
  title: { type: String, required: true },
  steps: { type: Array, default: () => [] },  // [{ label, active, done }]
  currentStep: { type: Number, default: -1 }, // -1 = 不显示步骤
})

const emit = defineEmits(['step-click'])
</script>

<template>
  <div class="h-full flex flex-col rounded-none md:rounded-lg brand-btn overflow-hidden" style="background: rgba(255,255,255,0.04);">
    <!-- 顶部栏 -->
    <header class="flex items-center h-14 px-4 border-b border-white/[0.08] shrink-0 gap-4">
      <!-- 标题 -->
      <h2 class="text-sm font-medium text-[#f7f8f8] shrink-0">{{ title }}</h2>

      <!-- 步骤 tab（可选） -->
      <div v-if="steps.length" class="flex items-center gap-1 ml-2">
        <button
          v-for="(s, i) in steps"
          :key="i"
          @click="emit('step-click', i)"
          class="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs transition-colors"
          :class="i === currentStep
            ? 'bg-white/[0.06] text-[#f7f8f8] font-medium'
            : s.done
              ? 'text-[#8a8f98] hover:bg-white/[0.04] hover:text-[#d0d6e0]'
              : 'text-[#62666d] cursor-default'"
        >
          <span
            class="flex h-4 w-4 items-center justify-center rounded text-[10px]"
            :class="s.done
              ? 'bg-[rgb(129,115,223)] text-white'
              : i === currentStep
                ? 'bg-white/[0.08] text-[#f7f8f8]'
                : 'bg-white/[0.04] text-[#62666d]'"
          >
            <i v-if="s.done" class="fa-solid fa-check text-[8px]"></i>
            <span v-else>{{ i + 1 }}</span>
          </span>
          <span>{{ s.label }}</span>
        </button>
      </div>

      <!-- 左侧附加操作 -->
      <div v-if="$slots.actions" class="flex items-center gap-1 text-[#62666d]">
        <slot name="actions"></slot>
      </div>

      <!-- 右侧工具栏 -->
      <div class="flex shrink-0 items-center gap-3 ml-auto">
        <!-- 子组件可通过 Teleport 注入内容 -->
        <div :id="'panel-toolbar-' + title" class="flex items-center gap-3"></div>
        <slot name="toolbar"></slot>
      </div>
    </header>

    <!-- 内容区：主体 + 可选右侧栏 -->
    <div class="flex-1 flex overflow-hidden">
      <!-- 主内容 -->
      <div class="flex-1 min-h-0 overflow-y-auto px-4 py-3 flex flex-col">
        <slot></slot>
      </div>

      <!-- 右侧属性栏（可选） -->
      <aside v-if="$slots.sidebar" class="hidden lg:flex w-80 shrink-0 flex-col border-l border-white/[0.05] overflow-y-auto">
        <slot name="sidebar"></slot>
      </aside>
    </div>
  </div>
</template>
