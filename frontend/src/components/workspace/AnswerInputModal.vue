<script setup>
/**
 * AnswerInputModal.vue
 * AI 辅导前置 — 答案录入弹窗
 */
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  open: Boolean,
  text: String,
  saving: Boolean,
})
const emit = defineEmits(['update:open', 'update:text', 'confirm'])
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-[100] flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-black/60" @click="emit('update:open', false)"></div>
    <div class="relative w-full max-w-lg rounded-lg brand-btn p-6">
      <h3 class="mb-1 text-base font-medium text-[#f7f8f8]">录入答案</h3>
      <p class="mb-4 text-xs text-[#62666d]">
        AI 辅导需要正确答案作为参考。支持 Markdown 格式，数学公式使用 LaTeX（$..$ 行内，$$...$$ 独占行）
      </p>
      <textarea
        :value="text"
        @input="emit('update:text', $event.target.value)"
        rows="10"
        placeholder="在此粘贴或输入答案/解析..."
        class="w-full resize-none rounded-md border border-white/[0.08] bg-white/[0.02] px-4 py-3 font-mono text-sm text-[#d0d6e0] placeholder-[#62666d] focus:border-white/[0.12] focus:outline-none transition-colors"
      ></textarea>
      <div class="mt-4 flex justify-end gap-3">
        <button
          @click="emit('update:open', false)"
          class="rounded-md border border-white/[0.08] bg-white/[0.02] px-4 py-2 text-sm font-medium text-[#d0d6e0] transition-colors hover:bg-white/[0.05]"
        >
          取消
        </button>
        <button
          @click="emit('confirm')"
          :disabled="saving"
          class="rounded-md bg-[#5e6ad2] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#7170ff] disabled:opacity-50"
        >
          {{ saving ? '保存中...' : '保存并开始辅导' }}
        </button>
      </div>
    </div>
  </div>
</template>
