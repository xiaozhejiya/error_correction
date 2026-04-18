<script setup>
/**
 * QuestionItem.vue
 * 题目条目（分割结果列表项）
 */
import { ref, watch, nextTick } from 'vue'
import { getQuestionSnippet, typesetMath } from '@/utils.js'

const props = defineProps({
  question: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  selectable: { type: Boolean, default: false },
  showStatus: { type: Boolean, default: false },
  maxTags: { type: Number, default: 0 },
})

const emit = defineEmits(['click', 'toggle-select'])

const optionsEl = ref(null)

const summary = () => getQuestionSnippet(props.question)

watch(() => props.question.options_json, async (val) => {
  if (val?.length && optionsEl.value) {
    await nextTick()
    typesetMath(optionsEl.value)
  }
}, { immediate: true, flush: 'post' })

const tags = () => {
  const all = props.question.knowledge_tags || []
  return props.maxTags ? all.slice(0, props.maxTags) : all
}

const statusClass = (status) => {
  if (status === '已掌握') return 'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400 border border-emerald-200/50 dark:border-emerald-500/30'
  if (status === '复习中') return 'bg-amber-500/10 text-amber-600 dark:bg-amber-500/20 dark:text-amber-400 border border-amber-200/50 dark:border-amber-500/30'
  return 'bg-rose-500/10 text-rose-600 dark:bg-rose-500/20 dark:text-rose-400 border border-rose-200/50 dark:border-rose-500/30'
}

const statusColor = (status) => {
  if (status === '已掌握') return 'text-emerald-500 dark:text-emerald-400'
  if (status === '复习中') return 'text-amber-500 dark:text-amber-400'
  return 'text-rose-500 dark:text-rose-400'
}

const statusIcon = (status) => {
  if (status === '已掌握') return 'fa-circle-check'
  if (status === '复习中') return 'fa-spinner'
  return 'fa-clock'
}
</script>

<template>
  <div
    @click="selectable ? emit('toggle-select', question.id) : emit('click', question)"
    class="group cursor-pointer rounded-lg border border-white/[0.06] bg-white/[0.02] p-4 transition-all hover:bg-white/[0.04] hover:border-white/[0.1]"
    :class="{ 'border-[rgb(129,115,223)]/40 bg-[rgb(129,115,223)]/[0.06]': selected }"
  >
    <div class="flex items-start gap-4">
      <!-- 选择复选框 -->
      <div v-if="selectable" class="flex shrink-0 items-center pt-1" @click.stop="emit('toggle-select', question.id)">
        <div class="flex h-5 w-5 items-center justify-center rounded-lg border-2 transition-all"
          :class="selected ? 'border-[rgb(129,115,223)] bg-[rgb(129,115,223)] text-white' : 'border-white/[0.15]'">
          <i v-if="selected" class="fa-solid fa-check text-xs"></i>
        </div>
      </div>

      <div class="min-w-0 flex-1">
        <!-- 标签行 -->
        <div class="mb-2 flex flex-wrap items-center gap-2">
          <!-- 复习状态图标 -->
          <i v-if="showStatus" class="fa-solid text-sm" :class="[statusIcon(question.review_status), statusColor(question.review_status)]"></i>
          <span class="rounded-full bg-white/[0.04] px-2 py-0.5 text-xs font-medium text-[#8a8f98]">{{ question.question_type }}</span>
          <span v-if="question.subject" class="rounded-full bg-[rgb(129,115,223)]/10 px-2 py-0.5 text-xs font-medium text-[rgb(145,132,235)]">{{ question.subject }}</span>
          <span v-for="tag in tags()" :key="tag" class="rounded-full border border-white/[0.06] px-2 py-0.5 text-xs font-medium text-[#8a8f98]">{{ tag }}</span>
        </div>

        <!-- 摘要 -->
        <p class="line-clamp-2 text-sm font-medium leading-relaxed text-[#d0d6e0] group-hover:text-[#f7f8f8]">{{ summary() }}</p>

        <!-- 题目图片 -->
        <div v-if="question.content_json?.some(b => b.block_type === 'image' && b.content)" class="mt-3 flex flex-wrap gap-2">
          <img
            v-for="(b, i) in question.content_json.filter(b => b.block_type === 'image' && b.content)"
            :key="i"
            :src="b.content"
            class="max-h-32 rounded-lg border border-white/[0.06] object-contain"
            @click.stop
          />
        </div>

        <!-- 选择题选项 -->
        <div v-if="question.options_json?.length" ref="optionsEl" class="mt-3 grid grid-cols-2 gap-1.5">
          <div
            v-for="(opt, idx) in question.options_json"
            :key="idx"
            class="flex items-start gap-2 rounded-md border border-white/[0.06] bg-white/[0.02] px-3 py-1.5 text-xs font-medium text-[#8a8f98]"
          >
            <span class="shrink-0 text-[#62666d]">{{ String.fromCharCode(65 + idx) }}.</span>
            <span class="line-clamp-1">{{ String(opt).replace(/^[A-Da-d][.、．]\s*/, '') }}</span>
          </div>
        </div>

        <!-- 扩展插槽（内联编辑等） -->
        <slot name="extra" :question="question" />
      </div>

      <!-- 右侧操作区插槽 -->
      <div v-if="$slots.actions" class="flex shrink-0 gap-2" @click.stop>
        <slot name="actions" :question="question" />
      </div>
    </div>
  </div>
</template>
