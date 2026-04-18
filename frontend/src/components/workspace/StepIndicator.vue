<script setup>
/**
 * StepIndicator.vue
 * 步骤指示器
 */
import { computed } from 'vue'

const props = defineProps({
  step: { type: Number, default: 1 },
  mode: { type: String, default: 'exam' }, // exam | note
})

const examLabels = ['上传文件', 'OCR解析', '分割题目', '预览导出']
const examDescs = ['选择 PDF 或图片', '结构化提取题干', 'AI 识别并拆分', '勾选题目并导出']
const noteLabels = ['上传笔记', 'OCR解析', '整理归纳', '保存笔记']
const noteDescs = ['选择 PDF 或图片', '结构化提取内容', 'AI 智能整理', '存入笔记库']

const labels = computed(() => props.mode === 'note' ? noteLabels : examLabels)
const descs = computed(() => props.mode === 'note' ? noteDescs : examDescs)
</script>

<template>
  <div class="px-2 sm:px-0">
    <ol class="relative flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between sm:gap-0">
      <li
        v-for="n in 4"
        :key="n"
        class="group relative flex items-center gap-4 sm:flex-1 sm:flex-col sm:gap-2"
      >
        <!-- 桌面端连接线 (优化定位，避免穿过圆圈) -->
        <div
          v-if="n < 4"
          class="hidden sm:block absolute left-[calc(50%+1.25rem)] top-5 w-[calc(100%-2.5rem)] h-[2px] -translate-y-1/2"
          :class="n < step ? 'bg-[#62666d]' : 'bg-white/[0.08]'"
        ></div>

        <!-- 移动端连接线 -->
        <div
          v-if="n < 4"
          class="sm:hidden absolute left-5 top-12 bottom-[-1.5rem] w-[2px] -translate-x-1/2"
          :class="n < step ? 'bg-[#62666d]' : 'bg-white/[0.08]'"
        ></div>

        <!-- 步骤圆圈 -->
        <div
          class="step-circle relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border"
          :class="
            n < step
              ? 'border-transparent bg-gradient-to-br from-[rgb(129,115,223)] to-[rgb(145,132,235)] text-white/90'
              : n === step
                ? 'border-white/[0.12] bg-white/[0.08] text-[rgb(145,132,235)]'
                : 'border-white/[0.05] bg-white/[0.03] text-[#62666d]'
          "
        >
          <Transition name="scale" mode="out-in">
            <i v-if="n < step" :key="'check-'+n" class="fa-solid fa-check text-[10px] font-medium"></i>
            <span v-else :key="'num-'+n" class="text-xs font-medium tabular-nums">{{ n }}</span>
          </Transition>

          <!-- 当前步骤的光晕 -->
          <div v-if="n === step" class="absolute -inset-1 animate-pulse rounded-lg bg-[rgb(129,115,223)]/20 blur-md"></div>
        </div>

        <!-- 文本描述 -->
        <div class="flex flex-col sm:items-center sm:text-center">
          <h3
            class="text-xs font-medium tracking-tight"
            :class="n <= step ? 'text-[#f7f8f8]' : 'text-[#62666d]'"
          >
            {{ labels[n - 1] }}
          </h3>
          <p class="mt-0.5 text-xs font-medium leading-relaxed text-[#62666d] sm:max-w-[100px]">
            {{ descs[n - 1] }}
          </p>
        </div>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.scale-enter-active,
.scale-leave-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.scale-enter-from {
  opacity: 0;
  transform: scale(0.5);
}

.scale-leave-to {
  opacity: 0;
  transform: scale(1.5);
}
</style>
