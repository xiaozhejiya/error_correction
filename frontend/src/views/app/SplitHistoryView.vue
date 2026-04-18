<script setup>
import { ref, watch, nextTick } from 'vue'
import * as api from '@/api.js'
import { isHtml, sanitizeHtml, typesetMath as _typesetMath } from '@/utils.js'

const props = defineProps({
  theme: { type: String, default: 'light' },
  visible: { type: Boolean, default: false },
})

const emit = defineEmits(['push-toast', 'open-image', 'load-record', 'go-workspace'])

// ---- 列表数据 ----
const records = ref([])
const loading = ref(false)
const detailLoading = ref(false)

// ---- 详情面板 ----
const activeRecord = ref(null)
const activeQuestions = ref([])
const selectedIds = ref(new Set())

const loadRecords = async () => {
  loading.value = true
  try {
    records.value = await api.fetchSplitRecords(20)
  } catch (e) {
    emit('push-toast', 'error', '加载分割历史失败: ' + (e instanceof Error ? e.message : String(e)))
  } finally {
    loading.value = false
  }
}

const openDetail = async (record) => {
  if (activeRecord.value?.id === record.id) {
    closeDetail()
    return
  }
  detailLoading.value = true
  activeRecord.value = record
  activeQuestions.value = []
  selectedIds.value = new Set()
  try {
    const detail = await api.fetchSplitRecordDetail(record.id)
    // 兼容旧历史记录（无 uid）：按索引补齐
    const qs = detail.questions || []
    qs.forEach((q, i) => { if (q.uid == null) q.uid = `hist_${i}` })
    activeQuestions.value = qs
  } catch (e) {
    emit('push-toast', 'error', '加载记录详情失败')
    activeRecord.value = null
  } finally {
    detailLoading.value = false
  }
  await nextTick()
  const el = document.querySelector('.split-history-questions')
  if (el) await _typesetMath(el)
}

const closeDetail = () => {
  activeRecord.value = null
  activeQuestions.value = []
  selectedIds.value = new Set()
}

const toggleSelect = (qid) => {
  const s = new Set(selectedIds.value)
  if (s.has(qid)) s.delete(qid)
  else s.add(qid)
  selectedIds.value = s
}

const selectAllQuestions = () => {
  selectedIds.value = new Set(activeQuestions.value.map(q => q.uid))
}

const deselectAllQuestions = () => {
  selectedIds.value = new Set()
}

const loadToWorkspace = () => {
  if (!activeQuestions.value.length) return
  const qs = selectedIds.value.size > 0
    ? activeQuestions.value.filter(q => selectedIds.value.has(q.uid))
    : activeQuestions.value
  emit('load-record', qs, activeRecord.value)
}

// ---- 格式化 ----
const formatDate = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now - d
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr} 小时前`
  const diffDay = Math.floor(diffHr / 24)
  if (diffDay < 7) return `${diffDay} 天前`
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hr = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return y === now.getFullYear() ? `${m}-${day} ${hr}:${min}` : `${y}-${m}-${day}`
}

const formatFullDate = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

const providerLabel = (p) => {
  const map = { deepseek: 'DeepSeek', ernie: '文心一言', openai: 'OpenAI' }
  return map[p] || p || '未知'
}

const providerColor = (p) => {
  if (p === 'deepseek') return 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300'
  if (p === 'ernie') return 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300'
  return 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300'
}

const questionTypeIcon = (t) => {
  if (t === '选择题') return 'fa-list-check'
  if (t === '填空题') return 'fa-pen-to-square'
  if (t === '判断题') return 'fa-circle-check'
  if (t === '解答题' || t === '计算题') return 'fa-calculator'
  return 'fa-question'
}

const questionTypeBadge = (t) => {
  if (t === '选择题') return 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300'
  if (t === '填空题') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300'
  if (t === '判断题') return 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300'
  return 'bg-slate-100 text-slate-600 dark:bg-slate-500/15 dark:text-slate-300'
}

// ---- 初始化 ----
watch(() => props.visible, (v) => {
  if (v) loadRecords()
}, { immediate: true })

defineExpose({ refresh: loadRecords })
</script>

<template>
  <div v-show="visible" class="flex h-full flex-col overflow-hidden">
    <div class="relative flex h-full flex-col">
      <!-- 页头 -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-white/[0.05] shrink-0">
        <span class="text-xs font-medium text-[#f7f8f8]">分割历史</span>
        <button
          @click="loadRecords"
          :disabled="loading"
          class="text-xs text-[#8a8f98] hover:text-[#d0d6e0] transition-colors disabled:opacity-50"
        >
          <i class="fa-solid fa-arrows-rotate text-[10px]" :class="{ 'animate-spin': loading }"></i>
        </button>
      </div>

      <!-- 主体 -->
      <div class="flex-1 overflow-y-auto custom-scrollbar">

        <!-- 加载状态 -->
        <div v-if="loading && !records.length" class="flex items-center justify-center py-10">
          <div class="h-5 w-5 animate-spin rounded-full border-2 border-white/10 border-t-[rgb(129,115,223)]"></div>
        </div>

        <!-- 空状态 -->
        <div v-else-if="!loading && !records.length" class="px-4 py-10 text-center">
          <i class="fa-solid fa-clock-rotate-left text-lg text-[#62666d] mb-2"></i>
          <p class="text-xs text-[#62666d]">暂无记录</p>
        </div>

        <!-- 记录列表 -->
        <div v-else>
          <div
            v-for="(r, idx) in records"
            :key="r.id"
            class="group cursor-pointer border-b border-white/[0.05] px-4 py-3 transition-colors hover:bg-white/[0.03]"
            :class="activeRecord?.id === r.id ? 'bg-white/[0.04]' : ''"
            @click="openDetail(r)"
          >
            <!-- 一行：科目 + 时间 + 题数 -->
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-medium text-[#f7f8f8] truncate">{{ r.subject || '未识别' }}</span>
              <span class="text-xs tabular-nums text-[rgb(129,115,223)]">{{ r.question_count }} 题</span>
            </div>
            <!-- 二行：文件数 + 时间 -->
            <div class="flex items-center gap-2 text-xs text-[#62666d]">
              <span>{{ (r.file_names || []).length }} 个文件</span>
              <span>·</span>
              <span :title="formatFullDate(r.created_at)">{{ formatDate(r.created_at) }}</span>
            </div>

            <!-- 展开详情面板 -->
            <Transition
              enter-active-class="transition-all duration-400 ease-out"
              enter-from-class="max-h-0 opacity-0"
              enter-to-class="max-h-[2000px] opacity-100"
              leave-active-class="transition-all duration-300 ease-in"
              leave-from-class="max-h-[2000px] opacity-100"
              leave-to-class="max-h-0 opacity-0"
            >
              <div v-if="activeRecord?.id === r.id" class="overflow-hidden border-t border-slate-200/40 dark:border-white/5">
                <!-- 加载中 -->
                <div v-if="detailLoading" class="flex items-center justify-center py-10">
                  <div class="h-7 w-7 animate-spin rounded-full border-[3px] border-slate-200 border-t-violet-500 dark:border-slate-700 dark:border-t-violet-400"></div>
                </div>

                <!-- 题目列表 -->
                <div v-else class="split-history-questions px-5 py-4">
                  <!-- 工具栏 -->
                  <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
                    <div class="flex items-center gap-2">
                      <button
                        @click.stop="selectAllQuestions"
                        class="rounded-lg border border-slate-200/60 bg-white/60 px-3 py-1.5 text-xs font-bold text-slate-600 transition-all hover:bg-white dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10"
                      >全选</button>
                      <button
                        v-if="selectedIds.size > 0"
                        @click.stop="deselectAllQuestions"
                        class="rounded-lg border border-slate-200/60 bg-white/60 px-3 py-1.5 text-xs font-bold text-slate-500 transition-all hover:bg-white dark:border-white/10 dark:bg-white/5 dark:text-slate-400 dark:hover:bg-white/10"
                      >取消选择</button>
                      <span v-if="selectedIds.size > 0" class="ml-1 text-xs font-semibold text-violet-600 dark:text-violet-400">
                        已选 {{ selectedIds.size }} / {{ activeQuestions.length }}
                      </span>
                    </div>
                    <button
                      @click.stop="loadToWorkspace"
                      class="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-xs font-bold text-white shadow-sm transition-all hover:bg-violet-700 hover:shadow-md dark:bg-violet-500 dark:hover:bg-violet-600"
                    >
                      <i class="fa-solid fa-arrow-right-to-bracket"></i>
                      {{ selectedIds.size > 0 ? `加载选中 (${selectedIds.size})` : '全部加载到工作台' }}
                    </button>
                  </div>

                  <!-- 题目网格 -->
                  <div class="grid grid-cols-1 gap-2.5 lg:grid-cols-2">
                    <div
                      v-for="q in activeQuestions"
                      :key="q.uid"
                      @click.stop="toggleSelect(q.uid)"
                      class="cursor-pointer rounded-xl border p-3.5 transition-all duration-200"
                      :class="selectedIds.has(q.uid)
                        ? 'border-violet-400/60 bg-violet-50/60 ring-1 ring-violet-400/30 dark:border-violet-500/40 dark:bg-violet-500/[0.08] dark:ring-violet-500/20'
                        : 'border-slate-200/50 bg-white/50 hover:border-violet-300/40 hover:bg-white/80 dark:border-white/[0.05] dark:bg-white/[0.02] dark:hover:border-violet-500/20'"
                    >
                      <div class="mb-2 flex items-center gap-2">
                        <!-- 选中指示 -->
                        <div
                          class="flex h-5 w-5 shrink-0 items-center justify-center rounded-md border text-[10px] transition-colors"
                          :class="selectedIds.has(q.uid)
                            ? 'border-violet-500 bg-violet-500 text-white dark:border-violet-400 dark:bg-violet-500'
                            : 'border-slate-300 dark:border-white/15'"
                        >
                          <i v-if="selectedIds.has(q.uid)" class="fa-solid fa-check"></i>
                        </div>
                        <span class="text-xs font-black text-slate-700 dark:text-slate-200">
                          {{ q.question_id || '?' }}
                        </span>
                        <span v-if="q.question_type" class="rounded-md px-1.5 py-0.5 text-[10px] font-bold" :class="questionTypeBadge(q.question_type)">
                          <i class="fa-solid mr-0.5 text-[8px]" :class="questionTypeIcon(q.question_type)"></i>
                          {{ q.question_type }}
                        </span>
                        <span v-if="q.has_formula" class="rounded-md bg-purple-100/80 px-1.5 py-0.5 text-[10px] font-bold text-purple-600 dark:bg-purple-500/15 dark:text-purple-300">
                          <i class="fa-solid fa-square-root-variable text-[8px]"></i>
                        </span>
                        <span v-if="q.has_image" class="rounded-md bg-cyan-100/80 px-1.5 py-0.5 text-[10px] font-bold text-cyan-600 dark:bg-cyan-500/15 dark:text-cyan-300">
                          <i class="fa-solid fa-image text-[8px]"></i>
                        </span>
                      </div>
                      <!-- 题目内容 -->
                      <div class="line-clamp-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                        <template v-if="(q.content_blocks || q.content_json)?.length">
                          <template v-for="(b, i) in (q.content_blocks || q.content_json)" :key="i">
                            <span v-if="b.block_type === 'text'" v-html="isHtml(b.content) ? sanitizeHtml(b.content) : b.content"></span>
                          </template>
                        </template>
                        <span v-else class="italic text-slate-400 dark:text-slate-500">（无文本内容）</span>
                      </div>
                      <!-- 知识点标签 -->
                      <div v-if="q.knowledge_tags?.length" class="mt-2 flex flex-wrap gap-1">
                        <span
                          v-for="tag in q.knowledge_tags.slice(0, 3)"
                          :key="tag"
                          class="rounded-md bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-500 dark:bg-white/[0.05] dark:text-slate-400"
                        >{{ tag }}</span>
                        <span v-if="q.knowledge_tags.length > 3" class="text-[10px] text-slate-400 dark:text-slate-500">+{{ q.knowledge_tags.length - 3 }}</span>
                      </div>
                    </div>
                  </div>

                  <!-- 空题目提示 -->
                  <div v-if="!activeQuestions.length && !detailLoading" class="py-8 text-center text-sm text-slate-400 dark:text-slate-500">
                    此记录无题目数据
                  </div>
                </div>
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
