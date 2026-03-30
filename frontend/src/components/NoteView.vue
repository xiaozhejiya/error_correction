<script setup>
import { ref, watch, computed, nextTick } from 'vue'
import * as api from '../api.js'
import { renderMarkdown, typesetMath } from '../utils.js'

const noteContentRef = ref(null)

const props = defineProps({
  visible: Boolean,
  modelProvider: { type: String, default: 'openai' },
  modelName: { type: String, default: '' },
  theme: String,
})
const emit = defineEmits(['push-toast'])

// ---- 状态 ----
const notes = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)
const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
const loading = ref(false)
const creating = ref(false)
const createProgress = ref(0)

// 筛选
const filterSubject = ref('')
const filterKeyword = ref('')

// 详情/编辑
const selectedNote = ref(null)
const editing = ref(false)
const editTitle = ref('')
const editContent = ref('')

// ---- 加载笔记列表 ----
async function loadNotes() {
  loading.value = true
  try {
    const data = await api.fetchNotes({
      page: page.value,
      limit: pageSize.value,
      subject: filterSubject.value || undefined,
      keyword: filterKeyword.value || undefined,
    })
    notes.value = data.items
    total.value = data.total
  } catch (e) {
    emit('push-toast', 'error', e.message)
  } finally {
    loading.value = false
  }
}

watch(() => props.visible, (v) => { if (v) loadNotes() }, { immediate: true })
watch([page, filterSubject], () => loadNotes())

let keywordTimer = null
function onKeywordInput() {
  clearTimeout(keywordTimer)
  keywordTimer = setTimeout(() => { page.value = 1; loadNotes() }, 500)
}

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
  formData.append('model_provider', props.modelProvider)
  if (props.modelName) formData.append('model_name', props.modelName)

  api.createNote(formData, {
    onProgress: (ratio) => { createProgress.value = Math.round(ratio * 50) },
    onSuccess: (data) => {
      creating.value = false
      createProgress.value = 100
      emit('push-toast', 'success', '笔记整理完成')
      loadNotes()
      // 自动打开新创建的笔记
      if (data.note) selectedNote.value = data.note
    },
    onError: (msg) => {
      creating.value = false
      emit('push-toast', 'error', msg)
    },
  })

  // 模拟 OCR + LLM 处理进度
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
  try {
    const full = await api.fetchNote(note.id)
    selectedNote.value = full
    // 等 DOM 完全更新后渲染 LaTeX 公式（nextTick + 延迟，确保过渡动画完成）
    await nextTick()
    setTimeout(() => {
      if (noteContentRef.value) typesetMath(noteContentRef.value)
    }, 100)
  } catch (e) {
    emit('push-toast', 'error', e.message)
  }
}

function closeDetail() {
  selectedNote.value = null
  editing.value = false
}

// ---- 编辑 ----
function startEdit() {
  editTitle.value = selectedNote.value.title
  editContent.value = selectedNote.value.content_markdown
  editing.value = true
}

async function saveEdit() {
  try {
    const updated = await api.updateNote(selectedNote.value.id, {
      title: editTitle.value,
      content_markdown: editContent.value,
    })
    selectedNote.value = updated
    editing.value = false
    emit('push-toast', 'success', '已保存')
    loadNotes()
    await nextTick()
    setTimeout(() => {
      if (noteContentRef.value) typesetMath(noteContentRef.value)
    }, 100)
  } catch (e) {
    emit('push-toast', 'error', e.message)
  }
}

// ---- 删除 ----
async function doDelete(noteId) {
  if (!confirm('确认删除这条笔记？')) return
  try {
    await api.deleteNote(noteId)
    emit('push-toast', 'success', '已删除')
    if (selectedNote.value?.id === noteId) closeDetail()
    loadNotes()
  } catch (e) {
    emit('push-toast', 'error', e.message)
  }
}
</script>

<template>
  <div class="flex h-full flex-col overflow-hidden">
    <!-- 头部：标题 + 上传按钮 + 筛选 -->
    <div class="flex flex-wrap items-center gap-4 px-4 py-4 sm:px-8 sm:py-6">
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white">笔记</h1>

      <button
        @click="triggerUpload"
        :disabled="creating"
        class="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 h-10 text-sm font-bold text-white shadow-sm transition-all hover:bg-blue-700 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
      >
        <i class="fa-solid fa-plus size-4"></i>
        {{ creating ? '整理中...' : '上传笔记' }}
      </button>
      <input ref="fileInput" type="file" multiple accept="image/*" class="hidden" @change="handleFiles" />

      <!-- 进度条 -->
      <div v-if="creating" class="flex-1 min-w-[120px]">
        <div class="h-2 rounded-full bg-slate-200 dark:bg-slate-700">
          <div class="h-full rounded-full bg-blue-600 transition-all duration-300" :style="{ width: createProgress + '%' }"></div>
        </div>
        <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">OCR 识别 + AI 整理中... {{ createProgress }}%</p>
      </div>

      <div class="flex-1"></div>

      <!-- 搜索 -->
      <div class="relative">
        <i class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 size-4"></i>
        <input
          v-model="filterKeyword"
          @input="onKeywordInput"
          placeholder="搜索笔记..."
          class="h-10 w-48 rounded-xl border border-slate-200/60 bg-white/60 pl-10 pr-4 text-sm outline-none transition-all focus:border-blue-300 focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-white/[0.03] dark:text-white dark:focus:border-indigo-500/50"
        />
      </div>
    </div>

    <!-- 笔记详情（覆盖列表） -->
    <div v-if="selectedNote" class="flex-1 overflow-auto px-4 pb-6 sm:px-8">
      <div class="mx-auto max-w-4xl">
        <!-- 操作栏 -->
        <div class="mb-4 flex items-center gap-3">
          <button @click="closeDetail" class="inline-flex items-center gap-2 rounded-xl border border-slate-200/60 bg-white/60 px-4 h-10 text-sm font-bold text-slate-700 transition-all hover:bg-white dark:border-white/10 dark:bg-white/[0.03] dark:text-slate-200 dark:hover:bg-white/[0.06]">
            <i class="fa-solid fa-arrow-left size-4"></i> 返回列表
          </button>
          <div class="flex-1"></div>
          <button v-if="!editing" @click="startEdit" class="inline-flex items-center gap-2 rounded-xl border border-slate-200/60 bg-white/60 px-4 h-10 text-sm font-bold text-slate-700 transition-all hover:bg-white dark:border-white/10 dark:bg-white/[0.03] dark:text-slate-200">
            <i class="fa-solid fa-pen size-4"></i> 编辑
          </button>
          <button @click="doDelete(selectedNote.id)" class="inline-flex items-center gap-2 rounded-xl border border-rose-200/60 bg-rose-50/60 px-4 h-10 text-sm font-bold text-rose-600 transition-all hover:bg-rose-100 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-400">
            <i class="fa-solid fa-trash size-4"></i> 删除
          </button>
        </div>

        <!-- 编辑模式 -->
        <div v-if="editing" class="space-y-4">
          <input v-model="editTitle" class="w-full rounded-xl border border-slate-200/60 bg-white/60 px-4 h-12 text-xl font-bold outline-none dark:border-white/10 dark:bg-white/[0.03] dark:text-white" />
          <textarea v-model="editContent" rows="20" class="w-full rounded-xl border border-slate-200/60 bg-white/60 p-4 font-mono text-sm leading-relaxed outline-none dark:border-white/10 dark:bg-white/[0.03] dark:text-slate-200"></textarea>
          <div class="flex gap-3">
            <button @click="saveEdit" class="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-6 h-10 text-sm font-bold text-white hover:bg-blue-700">
              <i class="fa-solid fa-check size-4"></i> 保存
            </button>
            <button @click="editing = false" class="inline-flex items-center gap-2 rounded-xl border border-slate-200/60 bg-white/60 px-6 h-10 text-sm font-bold text-slate-700 dark:border-white/10 dark:bg-white/[0.03] dark:text-slate-200">
              取消
            </button>
          </div>
        </div>

        <!-- 查看模式 -->
        <div v-else ref="noteContentRef">
          <h2 class="mb-2 text-3xl font-bold text-slate-900 leading-tight dark:text-white">{{ selectedNote.title }}</h2>
          <div class="mb-6 flex flex-wrap items-center gap-2">
            <span v-if="selectedNote.subject" class="rounded-full bg-blue-100 px-3 py-1 text-xs font-bold text-blue-700 dark:bg-indigo-500/20 dark:text-indigo-300">{{ selectedNote.subject }}</span>
            <span v-for="tag in selectedNote.knowledge_tags" :key="tag" class="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600 dark:bg-white/[0.06] dark:text-slate-300">{{ tag }}</span>
            <span class="text-xs text-slate-400">{{ selectedNote.updated_at?.slice(0, 10) }}</span>
          </div>

          <!-- Markdown 渲染内容 + LaTeX 公式 -->
          <article class="prose prose-slate max-w-none dark:prose-invert prose-headings:text-slate-900 dark:prose-headings:text-white prose-p:leading-relaxed prose-a:text-blue-600" v-html="renderMarkdown(selectedNote.content_markdown || '')"></article>

          <!-- 原始上传图片 -->
          <div v-if="selectedNote.source_images?.length" class="mt-8 border-t border-slate-200/60 pt-6 dark:border-white/10">
            <h3 class="mb-4 text-base font-bold text-slate-700 dark:text-slate-300">
              <i class="fa-solid fa-image mr-2 text-slate-400"></i>原始笔记图片
            </h3>
            <div class="grid gap-4 sm:grid-cols-2">
              <img
                v-for="(src, idx) in selectedNote.source_images"
                :key="idx"
                :src="'/images/' + src.split('/imgs/').pop() || src"
                class="w-full rounded-xl border border-slate-200/60 dark:border-white/10"
                @error="$event.target.style.display='none'"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 笔记列表 -->
    <div v-else class="flex-1 overflow-auto px-4 pb-6 sm:px-8">
      <!-- 空状态 -->
      <div v-if="!loading && notes.length === 0" class="flex flex-col items-center justify-center py-20 text-center">
        <div class="mb-4 flex size-16 items-center justify-center rounded-2xl bg-slate-100 dark:bg-white/[0.04]">
          <i class="fa-solid fa-book-open text-2xl text-slate-400 dark:text-slate-500"></i>
        </div>
        <p class="text-base font-bold text-slate-600 dark:text-slate-300">还没有笔记</p>
        <p class="mt-1 text-sm text-slate-400 dark:text-slate-500">上传手写笔记或板书照片，AI 自动整理为结构化知识点</p>
        <button @click="triggerUpload" class="mt-6 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-6 h-10 text-sm font-bold text-white hover:bg-blue-700">
          <i class="fa-solid fa-plus size-4"></i> 上传笔记
        </button>
      </div>

      <!-- 笔记卡片网格 -->
      <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="note in notes"
          :key="note.id"
          @click="openNote(note)"
          class="group cursor-pointer rounded-2xl border border-slate-200/60 bg-white/70 p-6 backdrop-blur-xl transition-all hover:shadow-md hover:border-blue-200/60 dark:border-white/10 dark:bg-white/[0.03] dark:hover:border-indigo-500/30 dark:hover:shadow-[0_0_15px_rgba(99,102,241,0.1)]"
        >
          <h3 class="mb-2 text-base font-bold text-slate-900 line-clamp-2 dark:text-white">{{ note.title }}</h3>
          <p class="mb-3 text-sm text-slate-500 line-clamp-3 dark:text-slate-400">
            {{ note.content_markdown?.replace(/[#*`>\-]/g, '').slice(0, 120) }}...
          </p>
          <div class="flex flex-wrap items-center gap-2">
            <span v-if="note.subject" class="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-bold text-blue-600 dark:bg-indigo-500/15 dark:text-indigo-300">{{ note.subject }}</span>
            <span v-for="tag in (note.knowledge_tags || []).slice(0, 3)" :key="tag" class="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500 dark:bg-white/[0.06] dark:text-slate-400">{{ tag }}</span>
            <span class="ml-auto text-xs text-slate-400">{{ note.updated_at?.slice(0, 10) }}</span>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="mt-6 flex justify-center gap-2">
        <button
          v-for="p in totalPages"
          :key="p"
          @click="page = p"
          class="size-10 rounded-xl text-sm font-bold transition-all"
          :class="p === page ? 'bg-blue-600 text-white' : 'border border-slate-200/60 bg-white/60 text-slate-600 hover:bg-white dark:border-white/10 dark:bg-white/[0.03] dark:text-slate-300'"
        >
          {{ p }}
        </button>
      </div>
    </div>
  </div>
</template>
