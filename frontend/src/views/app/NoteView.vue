<script setup>
import { ref, watch, computed, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as api from '@/api.js'
import { renderMarkdown, typesetMath } from '@/utils.js'
import ContentPanel from '@/components/workspace/ContentPanel.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseGhostButton from '@/components/base/BaseGhostButton.vue'
import SearchInput from '@/components/base/SearchInput.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import EmptyState from '@/components/base/EmptyState.vue'
import { useToast } from '@/composables/useToast.js'
import { useSystemStatus } from '@/composables/useSystemStatus.js'
import { useAuth } from '@/composables/useAuth.js'

const QUOTA_EXCEEDED_CODE = 'DAILY_FREE_QUOTA_EXCEEDED'

const { pushToast } = useToast()
const { selectedProvider, selectedModel } = useSystemStatus()
const { setQuotaSnapshot, refreshCurrentUser } = useAuth()

const route = useRoute()
const router = useRouter()

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

// 筛选
const filterSubject = ref('')
const filterTag = ref('')
const filterKeyword = ref('')

// 所有可用的筛选选项（不随筛选条件变化）
const allSubjects = ref([])
const allTags = ref([])

// 从所有笔记中收集筛选选项
function collectFilterOptions(items) {
  const subjectSet = new Set(allSubjects.value)
  const tagSet = new Set(allTags.value)
  for (const note of items) {
    if (note.subject) subjectSet.add(note.subject)
    if (note.knowledge_tags) {
      for (const tag of note.knowledge_tags) {
        tagSet.add(tag)
      }
    }
  }
  allSubjects.value = Array.from(subjectSet).sort()
  allTags.value = Array.from(tagSet).sort()
}

// 详情/编辑
const selectedNote = ref(null)
const editing = ref(false)
const editTitle = ref('')
const editContent = ref('')

// 获取笔记预览文本（清理 Markdown，简化 LaTeX，移除图片）
function getNoteSnippet(note, maxLen = 120) {
  if (!note?.content_markdown) return ''
  let text = note.content_markdown
    // 完全移除图片路径（包括描述文字）
    .replace(/!\[[^\]]*\]\([^)]+\)/g, '')
    // 处理 LaTeX 公式：在清理 Markdown 之前提取公式内容并简化，避免破坏 `_`、`-` 等语法
    .replace(/\$\$[\s\S]*?\$\$/g, (match) => simplifyLatex(match.slice(2, -2)))
    .replace(/\$([^$]+)\$/g, (match, content) => simplifyLatex(content))
    // 简化链接：保留文本，移除 URL
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // 移除 Markdown 标题符号
    .replace(/^#{1,6}\s+/gm, '')
    // 移除 Markdown 格式符号
    .replace(/[*`>\-_]/g, '')
    // 移除多余空白
    .replace(/\s+/g, ' ')
    .trim()
  return text.slice(0, maxLen) + (text.length > maxLen ? '...' : '')
}

// 简化 LaTeX 公式为可读文本
function simplifyLatex(latex) {
  return latex
    // 希腊字母
    .replace(/\\rho/g, 'ρ')
    .replace(/\\pi/g, 'π')
    .replace(/\\alpha/g, 'α')
    .replace(/\\beta/g, 'β')
    .replace(/\\gamma/g, 'γ')
    .replace(/\\delta/g, 'δ')
    .replace(/\\Delta/g, 'Δ')
    .replace(/\\theta/g, 'θ')
    .replace(/\\lambda/g, 'λ')
    .replace(/\\mu/g, 'μ')
    .replace(/\\sigma/g, 'σ')
    .replace(/\\Sigma/g, 'Σ')
    .replace(/\\omega/g, 'ω')
    .replace(/\\phi/g, 'φ')
    .replace(/\\Phi/g, 'Φ')
    // 常用数学符号
    .replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, '$1/$2')
    .replace(/\\sqrt\{([^}]+)\}/g, '√$1')
    .replace(/\\sqrt/g, '√')
    .replace(/\\cdot/g, '·')
    .replace(/\\times/g, '×')
    .replace(/\\div/g, '÷')
    .replace(/\\pm/g, '±')
    .replace(/\\leq/g, '≤')
    .replace(/\\geq/g, '≥')
    .replace(/\\neq/g, '≠')
    .replace(/\\approx/g, '≈')
    .replace(/\\infty/g, '∞')
    .replace(/\\sum/g, '∑')
    .replace(/\\prod/g, '∏')
    .replace(/\\int/g, '∫')
    .replace(/\\partial/g, '∂')
    .replace(/\\nabla/g, '∇')
    .replace(/\\rightarrow/g, '→')
    .replace(/\\leftarrow/g, '←')
    .replace(/\\Rightarrow/g, '⇒')
    .replace(/\\Leftarrow/g, '⇐')
    // 上下标
    .replace(/\^\{([^}]+)\}/g, '^$1')
    .replace(/_\{([^}]+)\}/g, '_$1')
    .replace(/\^(.)/g, '^$1')
    .replace(/_(.)/g, '_$1')
    // 移除命令符号
    .replace(/\\[a-zA-Z]+/g, '')
    .replace(/[{}]/g, '')
    .trim()
}

// ---- 加载笔记列表 ----
async function loadNotes() {
  loading.value = true
  try {
    const data = await api.fetchNotes({
      page: page.value,
      limit: pageSize.value,
      subject: filterSubject.value || undefined,
      knowledge_tag: filterTag.value || undefined,
      keyword: filterKeyword.value || undefined,
    })
    notes.value = data.items
    total.value = data.total
    // 收集筛选选项（累积所有见过的选项）
    collectFilterOptions(data.items)
  } catch (e) {
    pushToast('error', e.message)
  } finally {
    loading.value = false
  }
}

// 监听路由变化，处理笔记详情页
watch(() => route.params.id, async (noteId) => {
  if (noteId) {
    // 有笔记ID，加载详情
    // 加载失败时由 loadNoteById() 内部负责回退到列表页，避免重复导航
    await loadNoteById(noteId)
  } else {
    // 无笔记ID，显示列表
    selectedNote.value = null
    editing.value = false
    await loadNotes()
  }
}, { immediate: true })

watch([page, filterSubject, filterTag], () => { page.value === 1 ? loadNotes() : (page.value = 1) })

let keywordTimer = null
watch(filterKeyword, () => {
  clearTimeout(keywordTimer)
  keywordTimer = setTimeout(() => { page.value = 1; loadNotes() }, 500)
})

// ---- 上传笔记 ----
const fileInput = ref(null)

function triggerUpload() {
  fileInput.value?.click()
}

function handleFiles(e) {
  const files = e.target.files
  if (!files?.length) return

  creating.value = true
  createProgress.value = 0

  const formData = new FormData()
  for (const f of files) formData.append('files', f)
  formData.append('model_provider', selectedProvider.value)
  if (selectedModel.value) formData.append('model_name', selectedModel.value)

  api.createNote(formData, {
    onProgress: (ratio) => { createProgress.value = Math.round(ratio * 50) },
    onSuccess: async (data) => {
      creating.value = false
      createProgress.value = 100
      await refreshCurrentUser().catch(() => {})
      pushToast('success', '笔记整理完成')
      loadNotes()
      if (data.note) selectedNote.value = data.note
    },
    onError: (error) => {
      creating.value = false
      createProgress.value = 0
      if (error?.quota) setQuotaSnapshot(error.quota)
      if (error?.code === QUOTA_EXCEEDED_CODE) {
        pushToast('error', error.message || '今日免费体验次数已用完')
        return
      }
      pushToast('error', error instanceof Error ? error.message : String(error))
    },
  })

  let fakeProgress = 50
  const timer = setInterval(() => {
    if (!creating.value) { clearInterval(timer); return }
    fakeProgress = Math.min(fakeProgress + 2, 95)
    createProgress.value = fakeProgress
  }, 500)

  e.target.value = ''
}


// ---- 详情 ----
async function openNote(note) {
  // 使用路由导航到笔记详情页
  router.push(`/app/notes/${note.id}`)
}

// 根据路由参数加载笔记详情
async function loadNoteById(noteId) {
  if (!noteId) return
  try {
    const full = await api.fetchNote(noteId)
    selectedNote.value = full
    // 等 DOM 完全更新后渲染 LaTeX 公式
    await nextTick()
    setTimeout(() => {
      if (noteContentRef.value) typesetMath(noteContentRef.value)
    }, 100)
  } catch (e) {
    pushToast('error', e.message)
    // 笔记不存在或加载失败，返回列表页
    router.push('/app/notes')
  }
}

function closeDetail() {
  selectedNote.value = null
  editing.value = false
  // 返回笔记列表页
  router.push('/app/notes')
}

// 处理图片路径，提取文件名
function getImageUrl(src) {
  if (!src) return ''
  // 如果已经是 /uploads/ 或 /images/ 开头，直接返回
  if (src.startsWith('/uploads/') || src.startsWith('/images/')) return src
  // 提取文件名（处理 /imgs/ 或完整路径）
  const parts = src.split(/[/\\]/)
  const filename = parts.pop() || src
  // 原始上传图片使用 /uploads/ 路径
  return '/uploads/' + filename
}

// ---- 编辑 ----
function startEdit() {
  editTitle.value = selectedNote.value.title
  editContent.value = selectedNote.value.content_markdown
  editing.value = true
}

// 重新渲染 LaTeX 公式
async function renderMath() {
  await nextTick()
  setTimeout(() => {
    if (noteContentRef.value) typesetMath(noteContentRef.value)
  }, 100)
}

async function cancelEdit() {
  editing.value = false
  await renderMath()
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
    await renderMath()
  } catch (e) {
    pushToast('error', e.message)
  }
}

// ---- 删除 ----
async function doDelete(noteId) {
  if (!confirm('确认删除这条笔记？')) return
  try {
    await api.deleteNote(noteId)
    pushToast('success', '已删除')
    if (selectedNote.value?.id === noteId) closeDetail()
    loadNotes()
  } catch (e) {
    pushToast('error', e.message)
  }
}
</script>

<template>
  <ContentPanel title="笔记库">
    <template #toolbar>
      <button @click="triggerUpload" class="flex h-7 items-center gap-1.5 rounded-md border border-white/[0.06] bg-white/[0.03] px-2.5 text-xs font-medium text-[#8a8f98] hover:bg-white/[0.06] hover:text-[#d0d6e0] transition-colors" title="上传笔记">
        <i class="fa-solid fa-upload text-[10px]"></i> 上传笔记
      </button>
    </template>
  <div class="relative flex min-h-0 flex-1 flex-col overflow-y-auto custom-scrollbar">
    <div class="container relative z-10 mx-auto flex min-h-0 flex-1 flex-col">
      
      <!-- List View -->
      <div v-if="!selectedNote" class="flex min-h-0 flex-1 flex-col">
        <input ref="fileInput" type="file" multiple accept="image/*" class="hidden" @change="handleFiles" />

        <!-- 筛选栏（对齐错题库风格） -->
        <div class="relative z-20 mb-8">
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-4">
            <SearchInput v-model="filterKeyword" label="内容检索" placeholder="搜索笔记关键词..." />
            <BaseSelect v-model="filterSubject" :options="allSubjects" label="学科" placeholder="全部学科" />
            <BaseSelect v-model="filterTag" :options="allTags" label="知识点" placeholder="全部知识点" />
            <div>
              <label class="mb-1.5 block text-xs font-medium text-[#62666d]">统计</label>
              <div class="flex h-9 items-center rounded-md border border-white/[0.08] bg-white/[0.02] px-3 text-sm text-[#8a8f98]">
                共 {{ total }} 条笔记
              </div>
            </div>
          </div>

          <!-- 进度条 -->
          <div v-if="creating" class="mt-4">
            <div class="h-1 rounded-full bg-white/[0.06]">
              <div class="h-full rounded-full bg-[rgb(129,115,223)] transition-all duration-300" :style="{ width: createProgress + '%' }"></div>
            </div>
            <p class="mt-1 text-xs text-[#62666d]">OCR 识别 + AI 整理中... {{ createProgress }}%</p>
          </div>
        </div>

        <!-- Notes Grid -->
        <div class="relative flex-1 flex flex-col">
          <EmptyState
            v-if="!loading && notes.length === 0"
            icon="fa-solid fa-book-open"
            title="还没有笔记"
            description="上传手写笔记或板书照片，AI 自动整理为结构化知识点"
          >
            <button @click="triggerUpload" class="inline-flex items-center gap-2 rounded-md brand-btn px-4 py-2 text-sm font-medium text-[#f7f8f8]">
              <i class="fa-solid fa-plus"></i> 上传笔记
            </button>
          </EmptyState>

          <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div
              v-for="note in notes"
              :key="note.id"
              @click="openNote(note)"
              class="group cursor-pointer rounded-lg border border-white/[0.06] bg-white/[0.02] p-4 transition-all hover:bg-white/[0.04] hover:border-white/[0.1]"
            >
              <h3 class="mb-2 text-sm font-medium text-[#f7f8f8] line-clamp-2">{{ note.title }}</h3>
              <p class="mb-3 text-xs text-[#8a8f98] line-clamp-3">
                {{ getNoteSnippet(note) }}
              </p>
              <div class="flex flex-wrap items-center gap-2">
                <span v-if="note.subject" class="rounded-md bg-[rgb(129,115,223)]/10 px-2 py-0.5 text-xs font-medium text-[rgb(145,132,235)]">{{ note.subject }}</span>
                <span v-for="tag in (note.knowledge_tags || []).slice(0, 3)" :key="tag" class="rounded-md border border-white/[0.06] px-2 py-0.5 text-xs text-[#8a8f98]">{{ tag }}</span>
                <span class="ml-auto text-xs text-[#62666d]">{{ note.updated_at?.slice(0, 10) }}</span>
              </div>
            </div>
          </div>

          <!-- 分页 -->
          <div v-if="totalPages > 1" class="mt-8 flex justify-center gap-2">
            <button
              v-for="p in totalPages"
              :key="p"
              @click="page = p"
              class="size-8 rounded-md text-xs font-medium transition-all"
              :class="p === page ? 'brand-btn text-[#f7f8f8]' : 'border border-white/[0.06] text-[#8a8f98] hover:bg-white/[0.04]'"
            >
              {{ p }}
            </button>
          </div>
        </div>
      </div>

      <!-- Detail View -->
      <div v-else>
        <!-- 详情工具栏 -->
        <div class="mb-6 flex items-center justify-between">
          <h3 class="text-base font-medium text-[#f7f8f8]">{{ selectedNote.title }}</h3>
          <div class="flex items-center gap-2">
            <button @click="closeDetail" class="inline-flex items-center gap-2 rounded-md border border-white/[0.08] bg-white/[0.02] px-3 py-1.5 text-xs font-medium text-[#d0d6e0] hover:bg-white/[0.05] transition-colors">
              <i class="fa-solid fa-arrow-left text-[10px]"></i> 返回
            </button>
            <button v-if="!editing" @click="startEdit" class="inline-flex items-center gap-2 rounded-md border border-white/[0.08] bg-white/[0.02] px-3 py-1.5 text-xs font-medium text-[#d0d6e0] hover:bg-white/[0.05] transition-colors">
              <i class="fa-solid fa-pen text-[10px]"></i> 编辑
            </button>
            <button @click="doDelete(selectedNote.id)" class="inline-flex items-center gap-2 rounded-md border border-white/[0.08] bg-white/[0.02] px-3 py-1.5 text-xs font-medium text-rose-400 hover:bg-rose-500/10 transition-colors">
              <i class="fa-solid fa-trash text-[10px]"></i> 删除
            </button>
          </div>
        </div>

        <!-- Tags Row -->
        <div class="mb-6 flex flex-wrap items-center gap-2">
          <span v-if="selectedNote.subject" class="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300">{{ selectedNote.subject }}</span>
          <span v-for="tag in selectedNote.knowledge_tags" :key="tag" class="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600 dark:bg-white/[0.06] dark:text-slate-300">{{ tag }}</span>
        </div>

        <BaseCard padding="p-8">
          <!-- Edit Mode -->
          <div v-if="editing" class="space-y-4">
            <div>
              <label class="mb-2 block text-[11px] font-black uppercase tracking-widest text-slate-500">标题</label>
              <input v-model="editTitle" class="w-full rounded-xl border border-slate-200/60 bg-white/60 px-4 h-12 text-lg font-bold outline-none focus:border-emerald-300 focus:ring-2 focus:ring-emerald-500/20 dark:border-white/10 dark:bg-white/[0.03] dark:text-white" />
            </div>
            <div>
              <label class="mb-2 block text-[11px] font-black uppercase tracking-widest text-slate-500">内容 (Markdown)</label>
              <textarea v-model="editContent" rows="15" class="w-full rounded-xl border border-slate-200/60 bg-white/60 p-4 font-mono text-sm leading-relaxed outline-none focus:border-emerald-300 focus:ring-2 focus:ring-emerald-500/20 custom-scrollbar dark:border-white/10 dark:bg-white/[0.03] dark:text-slate-200"></textarea>
            </div>
            <div class="flex gap-3 pt-4">
              <button @click="saveEdit" class="btn-primary h-10 px-8 shadow-md shadow-emerald-500/20">
                <i class="fa-solid fa-check mr-2"></i>保存修改
              </button>
              <BaseGhostButton @click="cancelEdit">取消</BaseGhostButton>
            </div>
          </div>

          <!-- View Mode -->
          <div v-else ref="noteContentRef">
            <article class="prose prose-slate max-w-none dark:prose-invert prose-headings:text-slate-900 dark:prose-headings:text-white prose-p:leading-relaxed prose-a:text-emerald-600 prose-pre:bg-slate-50 dark:prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-200/60 dark:prose-pre:border-white/10" v-html="renderMarkdown(selectedNote.content_markdown || '')"></article>
          </div>
        </BaseCard>

        <!-- Original Images -->
        <div v-if="selectedNote.source_images?.length && !editing" class="mt-8">
          <h3 class="mb-4 text-sm font-black uppercase tracking-widest text-slate-500">
            <i class="fa-solid fa-image mr-2"></i>原始笔记图片
          </h3>
          <div class="grid gap-4 sm:grid-cols-2">
            <BaseCard v-for="(src, idx) in selectedNote.source_images" :key="idx" padding="p-2" class="overflow-hidden">
              <img
                :src="getImageUrl(src)"
                class="w-full rounded-xl cursor-pointer hover:opacity-90 transition-opacity"
                @error="$event.target.style.display='none'"
              />
            </BaseCard>
          </div>
        </div>
      </div>
    </div>
  </div>
  </ContentPanel>
</template>
