<script setup>
/**
 * EditNoteDialog.vue
 * 题目/笔记编辑弹窗（Markdown 编辑）
 */
import { ref, watch, nextTick, computed } from 'vue'
import { typesetMath, sanitizeHtml } from '@/utils.js'

const props = defineProps({
  open: { type: Boolean, default: false },
  field: { type: String, default: 'answer' }, // 'answer' | 'user_answer' | 'question'
  question: { type: Object, default: null },
  value: { type: String, default: '' },
  valueAnswer: { type: String, default: '' },
  saving: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'save'])

const draft = ref('')
const draftAnswer = ref('')
const questionContentRef = ref(null)

// 处理题目内容，支持 HTML 渲染
const sanitizedContent = computed(() => {
  const content = props.question?.content_json?.filter(b => b.block_type === 'text').map(b => b.content).join(' ') || props.value || ''
  return sanitizeHtml(content)
})

watch(() => props.open, async (v) => {
  if (v) {
    draft.value = props.value || ''
    draftAnswer.value = props.valueAnswer || ''
    if (props.field === 'question') {
      await nextTick()
      typesetMath(questionContentRef.value)
    }
  }
})

const onSave = () => {
  if (props.field === 'question') {
    emit('save', { content: draft.value, answer: draftAnswer.value })
  } else {
    emit('save', draft.value)
  }
}

const config = () => {
  if (props.field === 'answer') {
    return {
      title: '正确答案',
      icon: 'fa-circle-check',
      iconBg: 'bg-emerald-50 dark:bg-emerald-500/10',
      iconCls: 'text-emerald-600 dark:text-emerald-400',
      btnCls: 'bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-500 dark:hover:bg-emerald-600',
    }
  }
  if (props.field === 'question') {
    return {
      title: '编辑题目',
      icon: 'fa-pen-to-square',
      iconBg: 'bg-indigo-50 dark:bg-indigo-500/10',
      iconCls: 'text-indigo-600 dark:text-indigo-400',
      btnCls: 'bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600',
    }
  }
  return {
    title: '我的笔记',
    icon: 'fa-pen-to-square',
    iconBg: 'bg-blue-50 dark:bg-blue-500/10',
    iconCls: 'text-blue-600 dark:text-blue-400',
    btnCls: 'bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600',
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="dialog-fade">
      <div v-if="open" class="fixed inset-0 z-[101] flex items-center justify-center p-4 md:left-64" @click.self="emit('close')">
        <div class="absolute inset-0 bg-black/40"></div>

        <div class="relative w-full rounded-2xl border border-slate-200/60 bg-white shadow-2xl dark:border-white/10 dark:bg-[#0f0f17]"
             :class="field === 'question' ? 'max-w-2xl' : 'max-w-xl'">
          <!-- 头部 -->
          <div class="flex items-center justify-between border-b border-slate-100 px-6 py-4 dark:border-white/5">
            <div class="flex items-center gap-3">
              <div class="flex h-9 w-9 items-center justify-center rounded-xl" :class="config().iconBg">
                <i class="fa-solid text-base" :class="[config().icon, config().iconCls]"></i>
              </div>
              <h3 class="text-base font-bold text-slate-800 dark:text-slate-200">{{ config().title }}</h3>
            </div>
            <button @click="emit('close')" class="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-white/5 dark:hover:text-slate-300">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>

          <!-- 编辑区：编辑题目 -->
          <div v-if="field === 'question'" class="max-h-[72vh] overflow-y-auto px-6 py-4 space-y-4">
            <!-- 题目内容只读渲染 -->
            <div>
              <p class="mb-2 text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">题目内容</p>
              <div ref="questionContentRef" class="rounded-xl border border-slate-200/60 bg-slate-50/60 p-4 dark:border-white/10 dark:bg-white/[0.03] prose prose-sm dark:prose-invert max-w-none">
                <div class="text-sm font-bold leading-relaxed whitespace-pre-wrap text-slate-700 dark:text-slate-200" v-html="sanitizedContent"></div>
                <div v-if="question?.content_json?.some(b => b.block_type === 'image' && b.content)" class="mt-3 flex flex-wrap gap-2">
                  <img v-for="(b, i) in question.content_json.filter(b => b.block_type === 'image' && b.content)"
                    :key="i" :src="b.content"
                    class="max-h-40 rounded-xl border border-slate-100 object-contain dark:border-white/5" />
                </div>
                <div v-if="question?.options_json?.length" class="mt-3 grid grid-cols-2 gap-1.5">
                  <div v-for="(opt, idx) in question.options_json" :key="idx"
                    class="flex items-start gap-2 rounded-lg border border-slate-100 bg-slate-50/50 px-3 py-1.5 text-xs font-bold text-slate-600 dark:border-white/5 dark:bg-white/[0.02] dark:text-slate-400">
                    <span class="shrink-0 text-slate-400">{{ String.fromCharCode(65 + idx) }}.</span>
                    <span>{{ String(opt).replace(/^[A-Da-d][.、．]\s*/, '') }}</span>
                  </div>
                </div>
              </div>
            </div>
            <!-- 答案编辑 -->
            <div>
              <p class="mb-2 text-xs font-bold uppercase tracking-widest text-emerald-600 dark:text-emerald-400">正确答案</p>
              <textarea
                v-model="draftAnswer"
                rows="5"
                class="w-full resize-none rounded-xl border border-slate-200/60 bg-slate-50/60 px-4 py-3 text-sm font-medium leading-relaxed text-slate-700 outline-none transition-all focus:border-slate-300 focus:ring-2 focus:ring-slate-200/60 dark:border-white/10 dark:bg-white/[0.03] dark:text-slate-200 dark:focus:border-white/20 dark:focus:ring-white/5"
                placeholder="输入正确答案..."
              ></textarea>
            </div>
          </div>

          <!-- 编辑区：答案 / 笔记 -->
          <div v-else class="px-6 py-4">
            <textarea
              v-model="draft"
              rows="7"
              class="w-full resize-none rounded-xl border border-slate-200/60 bg-slate-50/60 px-4 py-3 text-sm font-medium leading-relaxed text-slate-700 outline-none transition-all focus:border-slate-300 focus:ring-2 focus:ring-slate-200/60 dark:border-white/10 dark:bg-white/[0.03] dark:text-slate-200 dark:focus:border-white/20 dark:focus:ring-white/5"
              :placeholder="field === 'answer' ? '输入正确答案...' : '记录你的笔记...'"
            ></textarea>
          </div>

          <!-- 底部按钮 -->
          <div class="flex justify-end gap-2 border-t border-slate-100 px-6 py-4 dark:border-white/5">
            <button @click="emit('close')" class="inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-bold text-slate-500 transition-all hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300">
              取消
            </button>
            <button
              @click="onSave"
              :disabled="saving"
              class="inline-flex h-10 items-center justify-center gap-2 rounded-xl px-6 text-sm font-bold text-white transition-all disabled:cursor-not-allowed disabled:opacity-50"
              :class="config().btnCls"
            >
              <i v-if="saving" class="fa-solid fa-spinner animate-spin"></i>
              {{ saving ? '保存中…' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s ease;
}
.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}

/* 表格样式 */
:deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.5rem 0;
}
:deep(th),
:deep(td) {
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 0.5rem 0.75rem;
  text-align: center;
}
:deep(th) {
  background: rgba(255, 255, 255, 0.05);
  font-weight: 600;
}
:deep(tr:nth-child(even)) {
  background: rgba(255, 255, 255, 0.02);
}
</style>
