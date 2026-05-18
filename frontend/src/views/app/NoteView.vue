<script setup>
import { ref, reactive, watch, computed, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as api from '@/api.js'
import { renderMarkdown, typesetMath, getNotePreviewText } from '@/utils.js'
import ContentPanel from '@/components/workspace/ContentPanel.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseGhostButton from '@/components/base/BaseGhostButton.vue'
import BaseButton from '@/components/base/BaseButton.vue'
import SearchInput from '@/components/base/SearchInput.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import EmptyState from '@/components/base/EmptyState.vue'
import { useToast } from '@/composables/useToast.js'
import { useSystemStatus } from '@/composables/useSystemStatus.js'
import { useAuth } from '@/composables/useAuth.js'
import BaseViewSettingsPopover from '@/components/base/BaseViewSettingsPopover.vue'
import { useProjects } from '@/composables/useProjects.js'

const QUOTA_EXCEEDED_CODE = 'DAILY_FREE_QUOTA_EXCEEDED'

const route = useRoute()
const router = useRouter()
const { pushToast } = useToast()
const { selectedLlmOption } = useSystemStatus()
const { setQuotaSnapshot, refreshCurrentUser } = useAuth()
const { activeNoteProjectId, noteProjects } = useProjects()
const hasNoteProject = computed(() => noteProjects.value.length > 0)

const noteContentRef = ref(null)

// ---- 状态 ----
const notes = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
const loading = ref(false)
const creating = ref(false)
const createProgress = ref(0)
const isDeleting = ref(false)

// 筛选
const filters = reactive({
  subject: '',
  tag: '',
  keyword: '',
})
const subjects = ref([])
const tagNames = ref([])
const selectedTags = computed(() => {
  const s = new Set()
  if (filters.tag) s.add(filters.tag)
  return s
})

const filterPanelOpen = ref(false)
function toggleFilterPanel() { filterPanelOpen.value = !filterPanelOpen.value }

function toggleTagSelect(tag) {
  filters.tag = filters.tag === tag ? '' : tag
}

function resetFilters() {
  filters.subject = ''
  filters.tag = ''
  filters.keyword = ''
  page.value = 1
  loadNotes()
}
const selectedNote = ref(null)
const editing = ref(false)
const editTitle = ref('')
const editContent = ref('')

// ---- 加载笔记列表 ----
async function loadNotes() {
  if (!activeNoteProjectId.value) {
    notes.value = []
    total.value = 0
    loading.value = false
    return
  }
  loading.value = true
  try {
    const data = await api.fetchNotes({
      page: page.value,
      limit: pageSize.value,
      subject: filters.subject || undefined,
      knowledge_tag: filters.tag || undefined,
      keyword: filters.keyword || undefined,
      project_id: activeNoteProjectId.value || undefined,
    })
    notes.value = data.items
    total.value = data.total
  } catch (e) {
    pushToast('error', e.message)
  } finally {
    loading.value = false
  }
}

// 加载筛选选项
async function loadFilterOptions() {
  if (!activeNoteProjectId.value) {
    subjects.value = []
    return
  }
  try {
    subjects.value = await api.fetchNoteSubjects(activeNoteProjectId.value)
  } catch (_) { }
}

async function loadTags() {
  if (!activeNoteProjectId.value) {
    tagNames.value = []
    return
  }
  try {
    tagNames.value = await api.fetchNoteTagNames(filters.subject || undefined, activeNoteProjectId.value)
  } catch (_) { }
}

onMounted(() => {
  loadNotes()
  loadFilterOptions()
  loadTags()
})
watch([page, () => filters.subject, () => filters.tag], () => { page.value === 1 ? loadNotes() : (page.value = 1) })
watch(() => filters.subject, () => {
  filters.tag = ''
  loadTags()
})
watch(activeNoteProjectId, () => {
  filters.subject = ''
  filters.tag = ''
  page.value = 1
  selectedNote.value = null
  loadNotes()
  loadFilterOptions()
  loadTags()
})

let keywordTimer = null
watch(() => filters.keyword, () => {
  clearTimeout(keywordTimer)
  keywordTimer = setTimeout(() => { page.value = 1; loadNotes() }, 500)
})

// ---- 详情 ----
async function openNote(note) {
  router.push(`/app/notes/${note.id}`)
}

async function loadNoteDetail(id) {
  if (isDeleting.value) return // 正在删除时，不加载详情
  try {
    const full = await api.fetchNote(id)
    selectedNote.value = full
    // 等 DOM 完全更新后渲染 LaTeX 公式（nextTick + 延迟，确保过渡动画完成）
    await nextTick()
    setTimeout(() => {
      if (noteContentRef.value) typesetMath(noteContentRef.value)
    }, 100)
  } catch (e) {
    // 只有在非删除状态下才报错，且报错后也确保回到列表
    if (!isDeleting.value) {
      pushToast('error', '无法加载笔记数据，请检查网络或笔记是否存在')
      closeDetail()
    }
  }
}

watch(() => route.params.subview, (newId) => {
  if (route.params.view === 'notes') {
    if (newId) {
      loadNoteDetail(newId)
    } else {
      selectedNote.value = null
      editing.value = false
    }
  }
}, { immediate: true })

function closeDetail() {
  selectedNote.value = null
  editing.value = false
  router.push('/app/notes')
}

// ---- 编辑 ----
function startEdit() {
  editTitle.value = selectedNote.value.title
  editContent.value = selectedNote.value.content_markdown
  editing.value = true
}

async function cancelEdit() {
  editing.value = false
  await nextTick()
  setTimeout(() => {
    if (noteContentRef.value) typesetMath(noteContentRef.value)
  }, 100)
}

async function saveEdit() {
  try {
    const updated = await api.updateNote(selectedNote.value.id, {
      title: editTitle.value,
      content_markdown: editContent.value,
    })
    selectedNote.value = updated
    editing.value = false
    pushToast('success', '已保存')
    loadNotes()
    await nextTick()
    setTimeout(() => {
      if (noteContentRef.value) typesetMath(noteContentRef.value)
    }, 100)
  } catch (e) {
    pushToast('error', e.message)
  }
}

// ---- 删除 ----
async function doDelete(noteId) {
  if (!confirm('确认删除这条笔记？')) return
  isDeleting.value = true
  try {
    await api.deleteNote(noteId)
    pushToast('success', '笔记删除成功')
    // 成功后立即跳转并重置状态，防止触发重复加载
    closeDetail()
    loadNotes()
  } catch (e) {
    // 如果是 404，说明笔记已经不存在了，直接跳转回列表即可
    if (e.status === 404 || e.message?.includes('不存在')) {
      closeDetail()
      loadNotes()
    } else {
      pushToast('error', e.message)
    }
  } finally {
    isDeleting.value = false
  }
}

// ---- 跳转到工作台录入 ----
function goToWorkspace() {
  router.push('/app/workspace?mode=note')
}
</script>

<template>
  <ContentPanel title="笔记库">
    <template #toolbar>
      <button @click="goToWorkspace"
        class="flex h-7 items-center gap-1.5 rounded-md border border-gray-200 dark:border-white/[0.06] bg-white dark:bg-white/[0.03] px-2.5 text-xs font-medium text-gray-500 dark:text-[#8a8f98] hover:bg-gray-50 dark:hover:bg-white/[0.06] hover:text-gray-700 dark:hover:text-[#d0d6e0] transition-colors"
        title="录入新笔记">
        <i class="fa-solid fa-plus text-[10px]"></i> 录入
      </button>
    </template>
    <div class="relative h-full flex flex-col"
      :class="selectedNote ? 'overflow-hidden' : 'overflow-y-auto custom-scrollbar'">
      <div class="relative z-10 flex-1 flex flex-col">

        <!-- List View -->
        <div v-if="!selectedNote" class="relative flex-1 flex flex-col">
          <!-- 筛选栏（对齐错题库风格） -->
          <div class="relative z-20 mb-4 flex items-center gap-2 flex-wrap">
            <!-- 搜索框 -->
            <div class="relative">
              <i
                class="fa-solid fa-magnifying-glass pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 dark:text-[#62666d] transition-colors"></i>
              <input v-model="filters.keyword" type="text" placeholder="搜索笔记..."
                class="h-8 w-52 rounded-md border border-gray-200 dark:border-white/[0.08] bg-white dark:bg-white/[0.02] pl-8 pr-3 text-xs font-medium text-gray-900 dark:text-[#f7f8f8] placeholder-gray-400 dark:placeholder-[#62666d] outline-none transition-colors hover:border-gray-300 dark:hover:border-white/[0.12] focus:border-[rgb(var(--accent-rgb)/0.4)] dark:focus:border-[rgb(var(--accent-rgb)/0.4)]" />
            </div>

            <!-- 操作按钮 -->
            <div class="ml-auto flex items-center gap-1 relative">
              <button @click.stop="toggleFilterPanel"
                class="flex h-7 w-7 items-center justify-center rounded-md border transition-colors"
                :class="filterPanelOpen ? 'accent-bg-soft accent-text accent-border' : 'border-gray-200 dark:border-white/[0.06] bg-white dark:bg-white/[0.03] text-gray-500 dark:text-[#8a8f98] hover:bg-gray-50 dark:hover:bg-white/[0.06] hover:text-gray-700 dark:hover:text-[#d0d6e0]'"
                title="筛选设置">
                <i class="fa-solid fa-sliders text-xs"></i>
              </button>

              <BaseViewSettingsPopover v-model="filterPanelOpen" :filters="filters" :subjects="subjects"
                :tag-names="tagNames" :selected-tags="selectedTags" :show-review-status="false"
                :show-question-type="false" @toggle-tag="toggleTagSelect" @reset="resetFilters" />

              <div class="ml-2 flex items-center text-xs text-gray-500 dark:text-[#8a8f98]">
                共 {{ total }} 条笔记
              </div>
            </div>
          </div>
          <!-- 进度条 -->
          <div v-if="creating" class="mb-4">
            <div class="h-1 rounded-full bg-gray-200 dark:bg-white/[0.06]">
              <div class="h-full rounded-full accent-bg transition-all duration-300"
                :style="{ width: createProgress + '%' }"></div>
            </div>
            <p class="mt-1 text-xs text-gray-500 dark:text-[#62666d]">OCR 识别 + AI 整理中... {{ createProgress }}%</p>
          </div>

          <!-- Notes Grid -->
          <div class="relative flex-1 flex flex-col">
            <EmptyState v-if="!loading && notes.length === 0" icon="fa-solid fa-book-open"
              :title="hasNoteProject ? '还没有笔记' : '还没有笔记本'"
              :description="hasNoteProject ? '上传手写笔记或板书照片，AI 自动整理为结构化知识点' : '先在左侧创建一个笔记本，再录入笔记'">
              <BaseButton @click="goToWorkspace" variant="primary" size="sm">
                <i class="fa-solid fa-plus"></i> 录入新笔记
              </BaseButton>
            </EmptyState>

            <div v-else class="space-y-4">
              <BaseCard v-for="note in notes" :key="note.id" @click="openNote(note)" class="group cursor-pointer"
                padding="p-4">
                <div class="flex min-w-0 items-start gap-4">
                  <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg accent-bg-soft accent-text">
                    <i class="fa-solid fa-book-open text-sm"></i>
                  </div>
                  <div class="min-w-0 flex-1">
                    <div class="mb-2 flex min-w-0 items-start justify-between gap-4">
                      <h3 class="min-w-0 truncate text-sm font-semibold text-gray-900 dark:text-[#f7f8f8]">{{ note.title }}
                      </h3>
                      <span class="shrink-0 text-xs text-gray-400 dark:text-[#62666d]">{{ note.updated_at?.slice(0, 10)
                      }}</span>
                    </div>
                    <p class="text-sm leading-relaxed text-gray-600 dark:text-[#8a8f98] line-clamp-2">
                      {{ getNotePreviewText(note.content_markdown, 180) }}
                    </p>
                    <div class="mt-3 flex flex-wrap items-center gap-2">
                      <span v-if="note.subject"
                        class="rounded-md accent-bg-soft px-2 py-0.5 text-xs font-medium accent-text">{{
                          note.subject }}</span>
                      <span v-for="tag in (note.knowledge_tags || []).slice(0, 5)" :key="tag"
                        class="rounded-md border border-gray-200 px-2 py-0.5 text-xs text-gray-500 dark:border-white/[0.06] dark:text-[#8a8f98]">{{
                          tag }}</span>
                    </div>
                  </div>
                </div>
              </BaseCard>
            </div>

            <!-- 分页 -->
            <div v-if="totalPages > 1" class="mt-8 flex justify-center gap-2">
              <button v-for="p in totalPages" :key="p" @click="page = p"
                class="size-8 rounded-md text-xs font-medium transition-all"
                :class="p === page ? 'accent-bg text-white shadow-sm' : 'border border-gray-200 bg-white text-gray-500 hover:bg-gray-50 hover:text-gray-700 dark:border-white/[0.06] dark:bg-transparent dark:text-[#8a8f98] dark:hover:bg-white/[0.04]'">
                {{ p }}
              </button>
            </div>
          </div>
        </div>

        <!-- Detail View -->
        <div v-else class="relative flex-1 flex flex-col">
          <!-- 详情工具栏 -->
          <div class="mb-6 flex items-center justify-between">
            <h3 class="text-base font-medium text-gray-900 dark:text-[#f7f8f8]">{{ selectedNote.title }}</h3>
            <div class="flex items-center gap-2">
              <button @click="closeDetail"
                class="inline-flex items-center gap-2 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-800 dark:border-white/[0.08] dark:bg-white/[0.02] dark:text-[#d0d6e0] dark:hover:bg-white/[0.05] transition-colors">
                <i class="fa-solid fa-arrow-left text-[10px]"></i> 返回
              </button>
              <button v-if="!editing" @click="startEdit"
                class="inline-flex items-center gap-2 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-800 dark:border-white/[0.08] dark:bg-white/[0.02] dark:text-[#d0d6e0] dark:hover:bg-white/[0.05] transition-colors">
                <i class="fa-solid fa-pen text-[10px]"></i> 编辑
              </button>
              <button @click="doDelete(selectedNote.id)"
                class="inline-flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-100 hover:text-red-700 dark:border-white/[0.08] dark:bg-white/[0.02] dark:text-rose-400 dark:hover:bg-rose-500/10 transition-colors">
                <i class="fa-solid fa-trash text-[10px]"></i> 删除
              </button>
            </div>
          </div>

          <!-- Tags Row -->
          <div class="mb-6 flex flex-wrap items-center gap-2">
            <span v-if="selectedNote.subject"
              class="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300">{{
                selectedNote.subject }}</span>
            <span v-for="tag in selectedNote.knowledge_tags" :key="tag"
              class="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600 dark:bg-white/[0.06] dark:text-slate-300">{{
                tag }}</span>
          </div>

          <!-- Edit Mode -->
          <BaseCard v-if="editing" padding="p-8">
            <div class="space-y-4">
              <div>
                <label class="mb-2 block text-[11px] font-black uppercase tracking-widest text-slate-500">标题</label>
                <input v-model="editTitle"
                  class="w-full rounded-xl border border-slate-200/60 bg-white/60 px-4 h-12 text-lg font-bold outline-none focus:border-emerald-300 focus:ring-2 focus:ring-emerald-500/20 dark:border-white/10 dark:bg-white/[0.03] dark:text-white" />
              </div>
              <div>
                <label class="mb-2 block text-[11px] font-black uppercase tracking-widest text-slate-500">内容
                  (Markdown)</label>
                <textarea v-model="editContent" rows="15"
                  class="w-full rounded-xl border border-slate-200/60 bg-white/60 p-4 font-mono text-sm leading-relaxed outline-none focus:border-emerald-300 focus:ring-2 focus:ring-emerald-500/20 custom-scrollbar dark:border-white/10 dark:bg-white/[0.03] dark:text-slate-200"></textarea>
              </div>
              <div class="flex gap-3 pt-4">
                <button @click="saveEdit" class="btn-primary h-10 px-8 shadow-md shadow-emerald-500/20">
                  <i class="fa-solid fa-check mr-2"></i>保存修改
                </button>
                <BaseGhostButton @click="cancelEdit">取消</BaseGhostButton>
              </div>
            </div>
          </BaseCard>

          <!-- View Mode -->
          <div v-else class="grid min-h-0 flex-1 gap-4 overflow-hidden xl:grid-cols-[minmax(20rem,0.42fr)_minmax(0,1fr)]">
            <section class="flex min-h-0 flex-col overflow-hidden">
              <div class="mb-3 flex items-center justify-between">
                <h3 class="text-sm font-bold text-gray-900 dark:text-[#f7f8f8]">
                  <i class="fa-solid fa-image mr-2 text-xs text-gray-400 dark:text-[#62666d]"></i>原始笔记图片
                </h3>
                <span class="text-xs text-gray-400 dark:text-[#62666d]">{{ selectedNote.source_images?.length || 0 }} 张</span>
              </div>
              <div v-if="selectedNote.source_images?.length" class="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1 custom-scrollbar">
                <img v-for="(src, idx) in selectedNote.source_images" :key="idx"
                  :src="'/uploads/' + src.split(/[\\/]/).pop()"
                  class="w-full rounded-xl object-contain transition-opacity hover:opacity-90"
                  @error="$event.target.style.display = 'none'" />
              </div>
              <div v-else class="flex min-h-64 items-center justify-center rounded-xl border border-dashed border-gray-200 text-sm text-gray-400 dark:border-white/[0.08] dark:text-[#62666d]">
                暂无原始图片
              </div>
            </section>

            <section class="min-w-0 min-h-0 overflow-hidden">
              <div ref="noteContentRef" class="h-full overflow-y-auto pr-2 custom-scrollbar">
                <article
                  class="prose prose-slate max-w-none dark:prose-invert prose-headings:text-slate-900 dark:prose-headings:text-white prose-p:leading-relaxed prose-a:text-emerald-600 prose-pre:bg-slate-50 dark:prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-200/60 dark:prose-pre:border-white/10"
                  v-html="renderMarkdown(selectedNote.content_markdown || '')"></article>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  </ContentPanel>
</template>
