<script setup>
/**
 * QuestionList.vue
 * 题目列表容器（选择 + 批量操作）
 */
import { ref, nextTick, watch, onMounted } from 'vue'
import QuestionCard from './QuestionCard.vue'
import { typesetMath } from '@/utils.js'

const props = defineProps({
  questions: { type: Array, default: () => [] },
  selectedIds: { type: Object, default: () => new Set() },
})

const emit = defineEmits(['toggle-select', 'select-all', 'deselect-all', 'open-image', 'reorder'])

const questionListEl = ref(null)
const questionsBoxEl = ref(null)
let sortable = null

const triggerTypeset = async () => {
  await nextTick()
  if (questionsBoxEl.value) {
    await typesetMath(questionsBoxEl.value)
  }
}

const initSortable = async () => {
  await nextTick()
  const el = questionListEl.value
  if (!el) return
  const Sortable = window.Sortable
  if (!Sortable) return
  if (sortable) sortable.destroy()
  sortable = Sortable.create(el, {
    animation: 250,
    easing: "cubic-bezier(0.2, 0, 0, 1)",
    handle: '[data-drag-handle="1"]',
    ghostClass: 'opacity-50',
    onEnd: (evt) => {
      const { oldIndex, newIndex } = evt
      if (oldIndex == null || newIndex == null || oldIndex === newIndex) return
      emit('reorder', oldIndex, newIndex)
    },
  })
}

watch(() => props.questions, (val) => {
  if (val && val.length) {
    initSortable()
    triggerTypeset()
  }
}, { flush: 'post', deep: true })

onMounted(() => {
  if (props.questions.length) {
    initSortable()
    triggerTypeset()
  }
})

defineExpose({ initSortable, questionsBoxEl, triggerTypeset })
</script>

<template>
  <div v-if="questions.length" ref="questionsBoxEl" class="relative z-10">
      <!-- 题目列表 -->
      <div ref="questionListEl" class="relative z-10 mt-6 grid gap-5" id="questionList">
        <QuestionCard
          v-for="q in questions"
          :key="q.uid"
          :question="q"
          :selected="selectedIds.has(q.uid)"
          @toggle="(id) => emit('toggle-select', id)"
          @open-image="(src) => emit('open-image', src)"
        />
      </div>
    </div>
</template>