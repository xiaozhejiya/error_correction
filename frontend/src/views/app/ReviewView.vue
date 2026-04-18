<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount, computed } from 'vue'
import * as api from '@/api.js'
import { typesetMath as _typesetMath } from '@/utils.js'
import { useSelectableList } from '@/composables/useSelectableList.js'
import ContentPanel from '@/components/workspace/ContentPanel.vue'
import QuestionDetailModal from '@/components/question/QuestionDetailModal.vue'
import AiAnalysisModal from '@/components/review/AiAnalysisModal.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import QuestionItem from '@/components/question/QuestionItem.vue'
import { useToast } from '@/composables/useToast.js'
import { useImageModal } from '@/composables/useImageModal.js'
import { useWorkspaceNav } from '@/composables/useWorkspaceNav.js'
import { useChatSession } from '@/composables/useChatSession.js'
import { useTheme } from '@/composables/useTheme.js'

const { pushToast } = useToast()
const { openModal } = useImageModal()
const { currentView } = useWorkspaceNav()
const { openChat } = useChatSession()
const { isDark } = useTheme()
const theme = computed(() => isDark.value ? 'dark' : 'light')

const answerEditId = ref(null)
const answerEditField = ref('')
const answerEditDraft = ref('')
const answerEditSaving = ref(false)

// ---- 学科筛选 ----
const selectedSubject = ref('')
const subjects = ref([])

// ---- 待复习题目列表 ----
const reviewItems = ref([])
const reviewTotal = ref(0)
const reviewLoading = ref(false)

// ---- 详情弹窗 ----
const detailOpen = ref(false)
const detailQuestion = ref(null)

// ---- AI 分析 ----
const { selectMode, selectedIds, toggleSelectMode, toggleSelect, selectAllItems } = useSelectableList()
const aiModalOpen = ref(false)
const aiAnalysisResult = ref(null)
const aiAnalyzing = ref(false)

// ---- 数据加载 ----
const loadSubjects = async () => {
  try {
    const data = await api.fetchDashboardStats()
    subjects.value = data?.subjects || []
  } catch (_) {}
}

const loadReviewItems = async () => {
  reviewLoading.value = true
  try {
    const params = { review_status: '待复习', page: 1, page_size: 20 }
    if (selectedSubject.value) params.subject = selectedSubject.value
    const data = await api.fetchErrorBank(params)
    reviewItems.value = data.items || []
    reviewTotal.value = data.total || 0
  } catch (e) {
    pushToast('error', '加载待复习题目失败')
  } finally {
    reviewLoading.value = false
    typesetMath()
  }
}

const loadAll = () => { loadSubjects(); loadReviewItems() }

watch(selectedSubject, () => { loadReviewItems() })

// ---- 题目操作 ----
const typesetMath = async () => {
  await nextTick()
  await _typesetMath()
}

const openDetail = (q) => { detailQuestion.value = q; detailOpen.value = true }
const closeDetail = () => { detailOpen.value = false; detailQuestion.value = null }

const quickMarkStatus = async (q, status) => {
  try {
    const data = await api.updateReviewStatus(q.id, status)
    q.review_status = data.review_status
    pushToast('success', `已标记为「${status}」`)
    if (status !== '待复习') {
      reviewItems.value = reviewItems.value.filter(x => x.id !== q.id)
      reviewTotal.value = Math.max(0, reviewTotal.value - 1)
    }
  } catch (e) {
    pushToast('error', '更新状态失败')
  }
}

const onDeleted = (id) => {
  reviewItems.value = reviewItems.value.filter(q => q.id !== id)
  reviewTotal.value = Math.max(0, reviewTotal.value - 1)
  closeDetail()
}

const onAnswerSaved = (id, answer, updatedAt) => {
  const q = reviewItems.value.find(x => x.id === id)
  if (q) { q.user_answer = answer; q.updated_at = updatedAt }
}

const startInlineEdit = (q, field) => {
  answerEditId.value = q.id
  answerEditField.value = field
  answerEditDraft.value = q[field] || ''
}
const cancelInlineEdit = () => { answerEditId.value = null }
const saveInlineEdit = async () => {
  if (answerEditSaving.value) return
  const q = reviewItems.value.find(x => x.id === answerEditId.value)
  if (!q) return
  answerEditSaving.value = true
  try {
    if (answerEditField.value === 'answer') {
      await api.saveQuestionAnswer(q.id, answerEditDraft.value)
      q.answer = answerEditDraft.value
    } else {
      await api.saveAnswer(q.id, answerEditDraft.value)
      q.user_answer = answerEditDraft.value
    }
    answerEditId.value = null
    pushToast('success', '已保存')
  } catch (e) {
    pushToast('error', '保存失败')
  } finally {
    answerEditSaving.value = false
  }
}

const onReviewStatusChanged = (id, status, updatedAt) => {
  const q = reviewItems.value.find(x => x.id === id)
  if (q) { q.review_status = status; q.updated_at = updatedAt }
  if (status !== '待复习') {
    reviewItems.value = reviewItems.value.filter(x => x.id !== id)
    reviewTotal.value = Math.max(0, reviewTotal.value - 1)
  }
}

const selectAllReview = () => selectAllItems(reviewItems.value)

const startAiAnalysis = async () => {
  if (!selectedIds.size) {
    pushToast('error', '请先选择要分析的题目')
    return
  }
  aiAnalyzing.value = true
  aiModalOpen.value = true
  aiAnalysisResult.value = null
  try {
    const data = await api.requestAiAnalysis(Array.from(selectedIds))
    aiAnalysisResult.value = data.analysis
  } catch (e) {
    pushToast('error', 'AI 分析失败: ' + (e instanceof Error ? e.message : String(e)))
    aiModalOpen.value = false
  } finally {
    aiAnalyzing.value = false
  }
}

const closeAiModal = () => {
  aiModalOpen.value = false
  aiAnalysisResult.value = null
}

// ---- 生命周期 ----
onMounted(() => { loadAll() })
</script>

<template>
  <ContentPanel title="待复习">
    <template #toolbar>
      <BaseSelect v-if="subjects.length" v-model="selectedSubject" :options="subjects" placeholder="全部学科" width-class="min-w-[140px]" />
      <button @click="currentView = 'workspace'" class="btn-primary group h-10 px-8 shadow-md shadow-blue-500/20">
        <i class="fa-solid fa-plus-circle transition-transform group-hover:rotate-90"></i> 录入新题目
      </button>
    </template>
  <div class="relative h-full overflow-y-auto custom-scrollbar">
    <div class="container relative z-10 mx-auto">

      <!-- 操作栏 -->
      <div class="mb-6 flex flex-wrap items-center justify-between gap-4">
        <h3 class="flex items-center gap-2 text-base font-black text-slate-900 dark:text-white">
          <i class="fa-solid fa-list-check text-indigo-500"></i> 题目列表
          <span v-if="reviewTotal" class="ml-2 rounded-full bg-indigo-100 px-2 py-1 text-xs font-bold text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">{{ reviewTotal }}</span>
        </h3>
        <div v-if="reviewItems.length" class="flex items-center gap-2">
          <button @click="toggleSelectMode"
            class="rounded-xl border px-4 py-2 text-xs font-bold transition-all"
            :class="selectMode ? 'border-blue-500 bg-blue-50 text-blue-600 dark:border-blue-400/30 dark:bg-blue-500/10 dark:text-blue-400' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-white/10 dark:bg-white/5 dark:text-slate-400'">
            <i class="fa-solid mr-1" :class="selectMode ? 'fa-xmark' : 'fa-list-check'"></i>
            {{ selectMode ? '取消选择' : '选择题目' }}
          </button>
          <template v-if="selectMode">
            <button @click="selectAllReview" class="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50 transition-all dark:border-white/10 dark:bg-white/5 dark:text-slate-400">
              全选
            </button>
            <button @click="startAiAnalysis" :disabled="!selectedIds.size || aiAnalyzing"
              class="rounded-xl bg-gradient-to-r from-indigo-500 to-blue-600 px-4 py-2 text-xs font-bold text-white shadow-sm shadow-indigo-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed">
              <i class="fa-solid fa-wand-magic-sparkles mr-1" :class="{ 'animate-spin': aiAnalyzing }"></i>
              AI 错题分析 <span v-if="selectedIds.size">({{ selectedIds.size }})</span>
            </button>
          </template>
        </div>
      </div>

      <!-- 加载中 -->
      <div v-if="reviewLoading" class="flex justify-center py-16">
        <div class="h-12 w-12 animate-spin rounded-full border-4 border-blue-500/20 border-t-blue-500"></div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="!reviewItems.length" class="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50/50 py-20 dark:border-white/5 dark:bg-white/5">
        <i class="fa-solid fa-circle-check mb-4 text-4xl text-emerald-400"></i>
        <p class="text-base font-black text-slate-900 dark:text-white">全部搞定了</p>
        <p class="mt-1 text-sm text-slate-500">没有待复习的题目，继续保持</p>
      </div>

      <!-- 题目列表 -->
      <div v-else class="space-y-4">
        <QuestionItem
          v-for="q in reviewItems" :key="q.id"
          :question="q"
          :selectable="selectMode"
          :selected="selectedIds.has(q.id)"
          :max-tags="3"
          @click="selectMode ? toggleSelect(q.id) : openDetail(q)"
          @toggle-select="toggleSelect"
        >
          <template #extra="{ question }">
            <!-- 录入答案/笔记按钮 -->
            <div class="mt-3 flex flex-wrap items-center gap-2 text-xs" @click.stop>
              <button v-if="!question.answer" @click="startInlineEdit(question, 'answer')" class="inline-flex items-center gap-1 rounded-md border border-dashed border-emerald-300 px-2 py-0.5 font-bold text-emerald-500 hover:bg-emerald-50 dark:border-emerald-500/30 dark:hover:bg-emerald-500/10">
                <i class="fa-solid fa-plus"></i>录入答案
              </button>
              <button v-if="!question.user_answer" @click="startInlineEdit(question, 'user_answer')" class="inline-flex items-center gap-1 rounded-md border border-dashed border-blue-300 px-2 py-0.5 font-bold text-blue-500 hover:bg-blue-50 dark:border-blue-500/30 dark:hover:bg-blue-500/10">
                <i class="fa-solid fa-plus"></i>记笔记
              </button>
            </div>
            <!-- 内联编辑区 -->
            <div v-if="answerEditId === question.id" class="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-slate-800" @click.stop>
              <div class="mb-2 text-xs font-black uppercase tracking-widest" :class="answerEditField === 'answer' ? 'text-emerald-600 dark:text-emerald-400' : 'text-blue-600 dark:text-blue-400'">
                {{ answerEditField === 'answer' ? '正确答案' : '我的笔记' }}
              </div>
              <textarea v-model="answerEditDraft" rows="3" :placeholder="answerEditField === 'answer' ? '输入正确答案/解析…' : '记录错因或心得…'"
                class="w-full resize-none rounded-lg border border-slate-200/80 bg-slate-50 px-3 py-2 font-mono text-xs text-slate-800 placeholder-slate-400 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-slate-900 dark:text-slate-200"></textarea>
              <div class="mt-2 flex justify-end gap-2">
                <button @click="cancelInlineEdit" class="rounded-lg px-3 py-1 text-xs font-bold text-slate-500 hover:text-slate-700 dark:text-slate-400">取消</button>
                <button @click="saveInlineEdit" :disabled="answerEditSaving"
                  class="rounded-lg px-3 py-1 text-xs font-bold text-white disabled:opacity-50"
                  :class="answerEditField === 'answer' ? 'bg-emerald-500 hover:bg-emerald-600' : 'bg-blue-500 hover:bg-blue-600'">
                  {{ answerEditSaving ? '保存中…' : '保存' }}
                </button>
              </div>
            </div>
          </template>
          <template #actions>
            <div class="group/tip relative">
              <button @click="quickMarkStatus(q, '复习中')" class="rounded-xl border border-indigo-200 bg-indigo-50 px-4 py-2 text-xs font-bold text-indigo-600 transition-all hover:bg-indigo-100 dark:border-indigo-500/20 dark:bg-indigo-500/10 dark:text-indigo-400">
                <i class="fa-solid fa-spinner mr-1"></i>复习中
              </button>
              <span class="pointer-events-none absolute -top-7 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-600/90 px-2 py-0.5 text-xs font-semibold text-white opacity-0 shadow-sm transition-opacity group-hover/tip:opacity-100 dark:bg-slate-700/90">
                标记为复习中
                <span class="absolute -bottom-1 left-1/2 -translate-x-1/2 border-[3px] border-transparent border-t-slate-600/90 dark:border-t-slate-700/90"></span>
              </span>
            </div>
            <div class="group/tip relative">
              <button @click="quickMarkStatus(q, '已掌握')" class="rounded-xl border border-emerald-500/30 bg-emerald-50/80 px-4 py-2 text-xs font-bold text-emerald-700 transition-all hover:bg-emerald-100 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-400">
                <i class="fa-solid fa-circle-check mr-1"></i>已掌握
              </button>
              <span class="pointer-events-none absolute -top-7 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-600/90 px-2 py-0.5 text-xs font-semibold text-white opacity-0 shadow-sm transition-opacity group-hover/tip:opacity-100 dark:bg-slate-700/90">
                标记为已掌握
                <span class="absolute -bottom-1 left-1/2 -translate-x-1/2 border-[3px] border-transparent border-t-slate-600/90 dark:border-t-slate-700/90"></span>
              </span>
            </div>
          </template>
        </QuestionItem>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <QuestionDetailModal
      :open="detailOpen"
      :question="detailQuestion"
      @close="closeDetail"
      @open-image="(src) => openModal(src)"
      @deleted="onDeleted"
      @answer-saved="onAnswerSaved"
      @review-status-changed="onReviewStatusChanged"
      @push-toast="(type, msg) => pushToast(type, msg)"
      @start-chat="(q) => openChat(q)"
    />

    <!-- AI 分析弹窗 -->
    <AiAnalysisModal
      :open="aiModalOpen"
      :loading="aiAnalyzing"
      :analysis="aiAnalysisResult"
      @close="closeAiModal"
    />
  </div>
  </ContentPanel>
</template>

