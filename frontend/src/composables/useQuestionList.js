import { ref, reactive, nextTick } from 'vue'
import { typesetMath as _typesetMathEl } from '@/utils.js'

export function useQuestionList() {
  const questions = ref([])
  const selectedIds = reactive(new Set())
  const questionListRef = ref(null)

  const toggleQuestion = (id) => { selectedIds.has(id) ? selectedIds.delete(id) : selectedIds.add(id) }
  const selectAll = () => { for (const q of questions.value) selectedIds.add(q.uid) }
  const deselectAll = () => { selectedIds.clear() }

  const reorderQuestions = (oldIndex, newIndex) => {
    const arr = questions.value.slice()
    const [moved] = arr.splice(oldIndex, 1)
    arr.splice(newIndex, 0, moved)
    questions.value = arr
  }

  const typesetMath = async () => {
    await nextTick()
    const el = questionListRef.value?.questionsBoxEl
    await _typesetMathEl(el || undefined)
  }

  return {
    questions, selectedIds, questionListRef,
    toggleQuestion, selectAll, deselectAll, reorderQuestions, typesetMath,
  }
}
