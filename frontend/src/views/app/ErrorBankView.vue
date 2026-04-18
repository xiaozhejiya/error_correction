<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import * as api from '@/api.js'
import { typesetMath as _typesetMath } from '@/utils.js'
import { useSelectableList } from '@/composables/useSelectableList.js'
import ContentPanel from '@/components/workspace/ContentPanel.vue'
import ErrorBankFilterPanel from '@/components/workspace/ErrorBankFilterPanel.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import SearchInput from '@/components/base/SearchInput.vue'
import QuestionItem from '@/components/question/QuestionItem.vue'
import EmptyState from '@/components/base/EmptyState.vue'
import QuestionItemSkeleton from '@/components/question/QuestionItemSkeleton.vue'
import EditNoteDialog from '@/components/question/EditNoteDialog.vue'
import SelectionPanel from '@/components/workspace/SelectionPanel.vue'
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

// ---- 筛选条件 ----
const openFilter = ref('')
const filterPanelOpen = ref(false)

function toggleFilterPanel() { filterPanelOpen.value = !filterPanelOpen.value }

// 点击外部关闭筛选下拉
function closeFilters(e) {
  if (!e.target.closest('.filter-pill') && !e.target.closest('.dropdown-item')) {
    openFilter.value = ''
  }
}
onMounted(() => document.addEventListener('click', closeFilters))
onBeforeUnmount(() => document.removeEventListener('click', closeFilters))

const filters = reactive({
  subject: '',
  knowledge_tag: '',
  question_type: '',
  keyword: '',
  review_status: '',
})
const page = ref(1)
const pageSize = ref(10)

const reviewStatusIcon = (status) => {
  if (status === '待复习') return 'fa-clock'
  if (status === '复习中') return 'fa-spinner'
  return 'fa-circle-check'
}

const reviewStatusClass = (status) => {
  if (status === '待复习') return 'bg-rose-500/10 text-rose-600 dark:bg-rose-500/20 dark:text-rose-400 border-rose-200/50 dark:border-rose-500/30'
  if (status === '复习中') return 'bg-amber-500/10 text-amber-600 dark:bg-amber-500/20 dark:text-amber-400 border-amber-200/50 dark:border-amber-500/30'
  return 'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400 border-emerald-200/50 dark:border-emerald-500/30'
}

// ---- 数据 ----
const items = ref([])
const total = ref(0)
const grandTotal = ref(0)
const totalPages = ref(0)
const loading = ref(false)
const subjects = ref([])
const questionTypes = ref([])
const tagNames = ref([])
const { selectMode, selectedIds, toggleSelectMode, toggleSelect, clearSelection } = useSelectableList()


// ---- 知识点多选标签 ----
const selectedTags = reactive(new Set())

const toggleTagSelect = (tag) => {
  if (selectedTags.has(tag)) {
    selectedTags.delete(tag)
  } else {
    selectedTags.add(tag)
  }
  // 多选标签同步到筛选（取第一个选中的标签给下拉框）
  const arr = Array.from(selectedTags)
  filters.knowledge_tag = arr.length === 1 ? arr[0] : arr.length > 1 ? arr.join(',') : ''
}

const clearTagSelection = () => {
  selectedTags.clear()
  filters.knowledge_tag = ''
}


const totalText = computed(() => `共收录 ${grandTotal.value} 道题目`)

// ---- 查询 ----
let debounceTimer = null
const doQuery = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filters.subject) params.subject = filters.subject
    if (filters.knowledge_tag) params.knowledge_tag = filters.knowledge_tag
    if (filters.question_type) params.question_type = filters.question_type
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.review_status) params.review_status = filters.review_status

    const data = await api.fetchErrorBank(params)
    items.value = data.items || []
    total.value = data.total || 0
    grandTotal.value = data.grand_total ?? data.total ?? 0
    totalPages.value = data.total_pages || 0
  } catch (e) {
    pushToast('error', e instanceof Error ? e.message : String(e))
  } finally {
    loading.value = false
    typesetMath()
  }
}

const debouncedQuery = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => { page.value = 1; doQuery() }, 300)
}

watch(() => [filters.subject, filters.knowledge_tag, filters.question_type, filters.review_status], debouncedQuery)
watch(() => filters.keyword, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => { page.value = 1; doQuery() }, 500)
})

const resetFilters = () => {
  Object.keys(filters).forEach(k => filters[k] = '')
  selectedTags.clear()
  page.value = 1
  doQuery()
}

const goPage = (p) => {
  if (p < 1 || p > totalPages.value) return
  page.value = p
  doQuery()
}


const doExport = async () => {
  if (!selectedIds.size) return
  try {
    const data = await api.exportFromDb(Array.from(selectedIds))
    pushToast('success', '错题本导出成功')
    let filename = 'wrongbook.md'
    if (data.output_path) {
      const parts = String(data.output_path).split(/[/\\]/)
      const last = parts[parts.length - 1]; if (last) filename = last
    }
    const a = document.createElement('a')
    a.href = `/download/${encodeURIComponent(filename)}?t=${Date.now()}`
    a.download = filename
    document.body.appendChild(a); a.click(); a.remove()
  } catch (e) {
    pushToast('error', '导出失败: ' + (e instanceof Error ? e.message : String(e)))
  }
}


// ---- 内联操作 ----
const dialogOpen = ref(false)
const dialogField = ref('answer')
const dialogQuestion = ref(null)
const dialogSaving = ref(false)

// hover dropdown
const hoverMenuId = ref(null)
const hoverMenuStyle = ref({})
let hoverCloseTimer = null

const onMenuEnter = (id, el) => {
  clearTimeout(hoverCloseTimer)
  const rect = el.getBoundingClientRect()
  const menuHeight = 280
  const spaceBelow = window.innerHeight - rect.bottom
  const style = {
    position: 'fixed',
    right: (window.innerWidth - rect.right) + 'px',
    zIndex: 9999,
  }
  if (spaceBelow < menuHeight) {
    style.bottom = (window.innerHeight - rect.top + 4) + 'px'
  } else {
    style.top = rect.bottom + 4 + 'px'
  }
  hoverMenuStyle.value = style
  hoverMenuId.value = id
}

const onMenuLeave = () => {
  hoverCloseTimer = setTimeout(() => { hoverMenuId.value = null }, 150)
}

const onMenuContentEnter = () => { clearTimeout(hoverCloseTimer) }
const onMenuContentLeave = () => { hoverCloseTimer = setTimeout(() => { hoverMenuId.value = null }, 150) }

const openEditDialog = (q, field) => {
  dialogQuestion.value = q
  dialogField.value = field
  dialogOpen.value = true
}

const onDialogSave = async (draft) => {
  if (dialogSaving.value || !dialogQuestion.value) return
  dialogSaving.value = true
  try {
    if (dialogField.value === 'question') {
      await api.updateQuestion(dialogQuestion.value.id, { content: draft.content, answer: draft.answer })
      dialogQuestion.value.content_json = [{ block_type: 'text', content: draft.content }]
      dialogQuestion.value.answer = draft.answer
    } else if (dialogField.value === 'answer') {
      await api.saveQuestionAnswer(dialogQuestion.value.id, draft)
      dialogQuestion.value.answer = draft
    } else {
      await api.saveAnswer(dialogQuestion.value.id, draft)
      dialogQuestion.value.user_answer = draft
    }
    dialogOpen.value = false
    pushToast('success', '已保存')
  } catch (e) {
    pushToast('error', '保存失败')
  } finally {
    dialogSaving.value = false
  }
}

const quickMarkStatus = async (q, status) => {
  try {
    const data = await api.updateReviewStatus(q.id, status)
    q.review_status = data.review_status
    pushToast('success', `已标记为「${status}」`)
  } catch (e) {
    pushToast('error', '更新状态失败')
  }
}

const doDelete = async (q) => {
  if (!window.confirm('确定要永久删除这道题吗？')) return
  try {
    await api.deleteQuestion(q.id)
    items.value = items.value.filter(x => x.id !== q.id)
    total.value = Math.max(0, total.value - 1)
    selectedIds.delete(q.id)
    pushToast('success', '题目已删除')
  } catch (e) {
    pushToast('error', '删除失败')
  }
}

const typesetMath = async () => {
  await nextTick()
  await _typesetMath()
}

const pageButtons = computed(() => {
  const tp = totalPages.value; const cp = page.value
  if (tp <= 7) return Array.from({ length: tp }, (_, i) => i + 1)
  const pages = [1]
  let start = Math.max(2, cp - 1); let end = Math.min(tp - 1, cp + 1)
  if (start > 2) pages.push('...')
  for (let i = start; i <= end; i++) pages.push(i)
  if (end < tp - 1) pages.push('...')
  pages.push(tp)
  return pages
})

const refreshTags = async () => {
  const raw = await api.fetchTagNames(filters.subject || undefined)
  tagNames.value = [...new Set(raw)]
}

const scrollContainerRef = ref(null)

const loadFilters = async () => {
  try {
    const [s, qt] = await Promise.all([
      api.fetchSubjects(),
      api.fetchQuestionTypes(),
    ])
    subjects.value = s
    questionTypes.value = qt
    await refreshTags()
  } catch (e) {
    pushToast('error', '加载筛选项失败')
  }
}

const reloadTags = async () => {
  try {
    await refreshTags()
    // 清除已选中但不再属于当前学科的标签
    const valid = new Set(tagNames.value)
    for (const t of Array.from(selectedTags)) {
      if (!valid.has(t)) selectedTags.delete(t)
    }
    filters.knowledge_tag = Array.from(selectedTags).join(',')
  } catch (e) { /* 静默失败，loadFilters 已加载过 */ }
}

watch(() => filters.subject, () => { reloadTags() })

onMounted(() => { loadFilters(); doQuery() })

defineExpose({
  refresh: doQuery,
  toggleSelectMode,
})

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
})
</script>

<template>
  <ContentPanel title="错题库">
    <template #toolbar>
      <button @click="currentView = 'workspace'" class="flex h-7 items-center gap-1.5 rounded-md border border-white/[0.06] bg-white/[0.03] px-2.5 text-xs font-medium text-[#8a8f98] hover:bg-white/[0.06] hover:text-[#d0d6e0] transition-colors" title="录入新题目">
        <i class="fa-solid fa-plus text-[10px]"></i> 录入
      </button>
    </template>
    <template v-if="filterPanelOpen" #sidebar>
      <ErrorBankFilterPanel
        :filters="filters"
        :subjects="subjects"
        :question-types="questionTypes"
        :tag-names="tagNames"
        :selected-tags="selectedTags"
        @close="filterPanelOpen = false"
        @toggle-tag="toggleTagSelect"
      />
    </template>
  <div ref="scrollContainerRef" @scroll="handleScroll" class="relative h-full overflow-y-auto custom-scrollbar flex flex-col">
    <div class="relative z-10 flex-1 flex flex-col">
      <!-- 搜索 + 操作按钮 + 已激活筛选 pills -->
      <div class="relative z-20 mb-4 flex items-center gap-2 flex-wrap">
        <!-- 搜索框 -->
        <div class="relative">
          <i class="fa-solid fa-magnifying-glass pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs text-[#62666d]"></i>
          <input
            v-model="filters.keyword"
            type="text"
            placeholder="搜索题目..."
            class="h-8 w-52 rounded-md border border-white/[0.08] bg-white/[0.02] pl-8 pr-3 text-xs font-medium text-[#f7f8f8] placeholder-[#62666d] outline-none transition-colors hover:border-white/[0.12] focus:border-white/[0.15]"
          />
        </div>

        <!-- 操作按钮（推到右侧） -->
        <div class="ml-auto flex items-center gap-1">
          <button @click="toggleFilterPanel" class="flex h-7 w-7 items-center justify-center rounded-md border border-white/[0.06] bg-white/[0.03] transition-colors" :class="filterPanelOpen ? 'bg-white/[0.08] text-[#f7f8f8] border-white/[0.12]' : 'text-[#8a8f98] hover:bg-white/[0.06] hover:text-[#d0d6e0]'" title="筛选设置">
            <i class="fa-solid fa-sliders text-xs"></i>
          </button>
          <button @click="toggleSelectMode" class="flex h-7 w-7 items-center justify-center rounded-md border border-white/[0.06] bg-white/[0.03] transition-colors" :class="selectMode ? 'bg-white/[0.08] text-[#f7f8f8] border-white/[0.12]' : 'text-[#8a8f98] hover:bg-white/[0.06] hover:text-[#d0d6e0]'" title="导出题目">
            <i class="fa-solid fa-file-export text-xs"></i>
          </button>
        </div>

        <!-- 已激活的筛选 pills（换行显示） -->
        <button v-if="filters.subject" @click="filters.subject = ''" class="filter-pill filter-pill--active">
          {{ filters.subject }} <i class="fa-solid fa-xmark text-[8px] ml-1"></i>
        </button>
        <button v-if="filters.question_type" @click="filters.question_type = ''" class="filter-pill filter-pill--active">
          {{ filters.question_type }} <i class="fa-solid fa-xmark text-[8px] ml-1"></i>
        </button>
        <button v-if="filters.review_status" @click="filters.review_status = ''" class="filter-pill filter-pill--active">
          {{ filters.review_status }} <i class="fa-solid fa-xmark text-[8px] ml-1"></i>
        </button>
        <template v-for="tag in selectedTags" :key="tag">
          <button @click="toggleTagSelect(tag)" class="filter-pill filter-pill--active">
            {{ tag }} <i class="fa-solid fa-xmark text-[8px] ml-1"></i>
          </button>
        </template>
        <button
          v-if="filters.subject || filters.question_type || filters.review_status || selectedTags.size"
          @click="filters.subject = ''; filters.question_type = ''; filters.review_status = ''; clearTagSelection()"
          class="text-xs text-[#62666d] hover:text-rose-400 transition-colors"
        >清除筛选</button>
      </div>


      <!-- 列表区 -->
      <div class="relative flex-1 flex flex-col">
        <!-- 首次加载：无旧数据时显示骨架 -->
        <QuestionItemSkeleton v-if="loading && !items.length" />

        <!-- 空状态 -->
        <EmptyState
          v-else-if="!loading && !items.length"
          icon="fa-solid fa-layer-group"
          title="暂无匹配记录"
          description="调整筛选条件，或者开始新的录入"
        >
          <button @click="currentView = 'workspace'" class="inline-flex items-center gap-2 rounded-md brand-btn px-4 py-2 text-sm font-medium text-[#f7f8f8]">
            <i class="fa-solid fa-plus"></i> 录入新题目
          </button>
        </EmptyState>

        <!-- 列表（有旧数据时保留，遮罩覆盖） -->
        <div v-else class="space-y-4">
        <QuestionItem
          v-for="q in items" :key="q.id"
          :question="q"
          :selectable="selectMode"
          :selected="selectedIds.has(q.id)"
          :show-status="true"
          @toggle-select="toggleSelect"
        >
          <template #actions="{ question }">
            <button
              @mouseenter="onMenuEnter(question.id, $event.currentTarget)"
              @mouseleave="onMenuLeave"
              class="flex h-8 w-8 items-center justify-center rounded-xl text-slate-400 transition-all hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-white/5 dark:hover:text-slate-300">
              <i class="fa-solid fa-ellipsis text-sm"></i>
            </button>
            <Teleport to="body">
              <Transition
                enter-active-class="transition duration-150 ease-out"
                enter-from-class="opacity-0 scale-95 -translate-y-1"
                enter-to-class="opacity-100 scale-100 translate-y-0"
                leave-active-class="transition duration-100 ease-in"
                leave-from-class="opacity-100 scale-100 translate-y-0"
                leave-to-class="opacity-0 scale-95 -translate-y-1"
              >
                <div v-if="hoverMenuId === question.id" :style="hoverMenuStyle"
                  @mouseenter="onMenuContentEnter" @mouseleave="onMenuContentLeave"
                  class="w-44 overflow-hidden rounded-2xl border border-slate-200/60 bg-white/95 p-1.5 shadow-xl dark:border-white/10 dark:bg-[#12121A]/90 dark:bg-gradient-to-b dark:from-white/[0.08] dark:to-transparent dark:shadow-[0_20px_50px_rgba(0,0,0,0.6)]">
                  <div class="px-3 pb-1 pt-2 text-[11px] font-black uppercase tracking-widest text-slate-400 dark:text-slate-500">复习状态</div>
                  <button @click.stop="quickMarkStatus(question, '待复习')"
                    class="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-bold transition-all"
                    :class="!question.review_status || question.review_status === '待复习' ? 'bg-rose-500/10 text-rose-600 dark:bg-rose-500/20 dark:text-rose-400' : 'text-slate-600 hover:bg-rose-500/10 hover:text-rose-600 dark:text-slate-300 dark:hover:bg-rose-500/20 dark:hover:text-rose-400'">
                    <i class="fa-solid fa-clock text-xs"></i>待复习
                    <i v-if="!question.review_status || question.review_status === '待复习'" class="fa-solid fa-check ml-auto text-[10px]"></i>
                  </button>
                  <button @click.stop="quickMarkStatus(question, '复习中')"
                    class="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-bold transition-all"
                    :class="question.review_status === '复习中' ? 'bg-amber-500/10 text-amber-600 dark:bg-amber-500/20 dark:text-amber-400' : 'text-slate-600 hover:bg-amber-500/10 hover:text-amber-600 dark:text-slate-300 dark:hover:bg-amber-500/20 dark:hover:text-amber-400'">
                    <i class="fa-solid fa-spinner text-xs"></i>复习中
                    <i v-if="question.review_status === '复习中'" class="fa-solid fa-check ml-auto text-[10px]"></i>
                  </button>
                  <button @click.stop="quickMarkStatus(question, '已掌握')"
                    class="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-bold transition-all"
                    :class="question.review_status === '已掌握' ? 'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400' : 'text-slate-600 hover:bg-emerald-500/10 hover:text-emerald-600 dark:text-slate-300 dark:hover:bg-emerald-500/20 dark:hover:text-emerald-400'">
                    <i class="fa-solid fa-circle-check text-xs"></i>已掌握
                    <i v-if="question.review_status === '已掌握'" class="fa-solid fa-check ml-auto text-[10px]"></i>
                  </button>
                  <div class="mx-2 my-1.5 border-t border-slate-100 dark:border-white/5"></div>
                  <div class="px-3 pb-1 text-[11px] font-black uppercase tracking-widest text-slate-400 dark:text-slate-500">操作</div>
                  <button @click.stop="openEditDialog(question, 'question'); hoverMenuId = null"
                    class="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-bold text-slate-600 transition-all hover:bg-blue-500/10 hover:text-blue-600 dark:text-slate-300 dark:hover:bg-blue-500/20 dark:hover:text-blue-400">
                    <i class="fa-solid fa-pen-to-square text-xs"></i>编辑
                  </button>
                  <button @click.stop="openEditDialog(question, 'user_answer'); hoverMenuId = null"
                    class="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-bold text-slate-600 transition-all hover:bg-blue-500/10 hover:text-blue-600 dark:text-slate-300 dark:hover:bg-blue-500/20 dark:hover:text-blue-400">
                    <i class="fa-solid fa-note-sticky text-xs"></i>记笔记
                  </button>
                  <button @click.stop="openChat(question); hoverMenuId = null"
                    class="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-bold text-slate-600 transition-all hover:bg-indigo-500/10 hover:text-indigo-600 dark:text-slate-300 dark:hover:bg-indigo-500/20 dark:hover:text-indigo-400">
                    <i class="fa-solid fa-wand-magic-sparkles text-xs"></i>AI 辅导
                  </button>
                  <div class="mx-2 my-1.5 border-t border-slate-100 dark:border-white/5"></div>
                  <button @click.stop="doDelete(question); hoverMenuId = null"
                    class="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-bold text-rose-500 transition-all hover:bg-rose-500/10 dark:text-rose-400 dark:hover:bg-rose-500/20">
                    <i class="fa-solid fa-trash-can text-xs"></i>删除题目
                  </button>
                </div>
              </Transition>
            </Teleport>
          </template>

        </QuestionItem>
        </div>

        <!-- 遮罩：筛选/翻页时覆盖旧列表，布局不跳动 -->
        <Transition enter-active-class="transition-opacity duration-150" leave-active-class="transition-opacity duration-150" enter-from-class="opacity-0" leave-to-class="opacity-0">
          <div v-if="loading && items.length"
            class="absolute inset-0 z-10 flex items-center justify-center rounded-2xl bg-white/60 dark:bg-black/30">
            <div class="h-6 w-6 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600 dark:border-white/20 dark:border-t-white/60"></div>
          </div>
        </Transition>
      </div>

      <!-- 分页控制：浮动微拟物风格 -->
      <div v-if="totalPages > 1" class="mt-12 flex items-center justify-center gap-4">
        <button @click="goPage(page - 1)" :disabled="page <= 1" class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/60 bg-white/60 text-slate-700 shadow-sm transition-all hover:bg-white disabled:cursor-not-allowed disabled:opacity-30 dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
          <i class="fa-solid fa-chevron-left text-sm"></i>
        </button>
        <div class="flex items-center gap-2 rounded-2xl bg-white/50 p-1.5 shadow-sm dark:bg-white/5">
          <template v-for="(p, i) in pageButtons" :key="i">
            <span v-if="p === '...'" class="flex w-8 justify-center font-bold text-slate-400">...</span>
            <button v-else @click="goPage(p)" 
              class="h-9 min-w-[36px] rounded-xl text-sm font-bold transition-all"
              :class="p === page ? 'bg-blue-600 text-white shadow-sm dark:bg-indigo-600' : 'text-slate-500 hover:bg-white dark:text-slate-400 dark:hover:bg-white/10'">
              {{ p }}
            </button>
          </template>
        </div>
        <button @click="goPage(page + 1)" :disabled="page >= totalPages" class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/60 bg-white/60 text-slate-700 shadow-sm transition-all hover:bg-white disabled:cursor-not-allowed disabled:opacity-30 dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
          <i class="fa-solid fa-chevron-right text-sm"></i>
        </button>
      </div>
    </div>

    <!-- 选择模式浮动面板 -->
    <SelectionPanel
      :visible="selectMode"
      :count="selectedIds.size"
      @export="doExport"
      @clear="clearSelection"
    />

    <EditNoteDialog
      :open="dialogOpen"
      :field="dialogField"
      :question="dialogQuestion"
      :value="dialogField === 'question'
        ? (dialogQuestion?.content_json?.filter(b => b.block_type === 'text').map(b => b.content).join('\n') || '')
        : (dialogQuestion?.[dialogField] || '')"
      :value-answer="dialogField === 'question' ? (dialogQuestion?.answer || '') : ''"
      :saving="dialogSaving"
      @close="dialogOpen = false"
      @save="onDialogSave"
    />
  </div>
  </ContentPanel>
</template>

<style scoped>
@keyframes tagFadeIn {
  from { opacity: 0; transform: translateY(4px) scale(0.95); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
.tag-fade-in {
  animation: tagFadeIn 0.2s ease-out both;
}
</style>
