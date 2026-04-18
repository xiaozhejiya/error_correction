<script setup>
/**
 * ReviewStage.vue
 * 工作台第二页：分割结果核对（擦除预览 / OCR 预览 / 分割中 / 题目列表）
 */
import { ref } from 'vue'
import ErasePreview from '@/components/workspace/ErasePreview.vue'
import OcrPreview from '@/components/workspace/OcrPreview.vue'
import SplitLoading from '@/components/workspace/SplitLoading.vue'
import QuestionList from '@/components/question/QuestionList.vue'

const props = defineProps({
  eraseLoading: Boolean,
  eraseDone: Boolean,
  eraseImages: Array,
  ocrLoading: Boolean,
  ocrDone: Boolean,
  ocrPages: Array,
  splitting: Boolean,
  splitCompleted: Boolean,
  questions: Array,
  selectedIds: Set,
  previewUrl: String,
})

const emit = defineEmits([
  'toggle-select', 'select-all', 'deselect-all', 'open-image', 'reorder',
])

const questionListRef = ref(null)

defineExpose({
  triggerTypeset: () => questionListRef.value?.triggerTypeset?.(),
})
</script>

<template>
  <!-- 擦除加载中 / 擦除对比预览 -->
  <ErasePreview
    v-if="eraseLoading || (eraseDone && !ocrLoading && !ocrDone)"
    :images="eraseImages"
    :loading="eraseLoading"
    :preview-url="previewUrl"
  />

  <!-- OCR 加载中 / OCR 预览 -->
  <OcrPreview
    v-else-if="ocrLoading || (ocrDone && !splitCompleted && !splitting)"
    :pages="ocrPages"
    :loading="ocrLoading"
    :preview-url="previewUrl"
  />

  <!-- 分割进行中 -->
  <div v-else-if="splitting" class="flex-1 min-h-0 relative">
    <img v-if="previewUrl" :src="previewUrl" class="absolute inset-0 w-full h-full object-contain opacity-10 blur-sm" alt="" />
    <SplitLoading />
  </div>

  <!-- 题目列表 -->
  <div v-if="splitCompleted && questions.length" class="flex-1 overflow-y-auto pr-2 custom-scrollbar py-2 pb-24">
    <QuestionList
      ref="questionListRef"
      :questions="questions"
      :selected-ids="selectedIds"
      @toggle-select="(id) => emit('toggle-select', id)"
      @select-all="emit('select-all')"
      @deselect-all="emit('deselect-all')"
      @open-image="(src) => emit('open-image', src)"
      @reorder="(qs) => emit('reorder', qs)"
    />
  </div>
</template>
