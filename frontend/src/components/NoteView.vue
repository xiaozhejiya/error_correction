<script setup>
import { ref, watch, computed, nextTick } from 'vue'
import * as api from '../api.js'
import { renderMarkdown, typesetMath } from '../utils.js'
import PageHeader from './PageHeader.vue'
import GlassCard from './GlassCard.vue'
import GlassButton from './GlassButton.vue'
import SearchInput from './SearchInput.vue'

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
  <div class="relative h-full overflow-y-auto custom-scrollbar">
    <div class="container relative z-10 mx-auto max-w-6xl px-4 py-8 sm:px-8">
      
      <!-- List View -->
      <div v-if="!selectedNote">
        <PageHeader
          title="学习笔记"
          subtitle="AI 自动提取手写笔记/板书中的核心知识点，支持跨模态检索"
          badge="NOTES"
          badgeIcon="fa-solid fa-book-open"
          badgeColor="emerald"
        >
          <template #extra>
            <div class="flex items-center gap-4">
              <button
                @click="triggerUpload"
                :disabled="creating"
                class="btn-primary group h-10 px-6 shadow-md shadow-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <i class="fa-solid fa-plus transition-transform group-hover:rotate-90 mr-1"></i>
                {{ creating ? '整理中...' : '上传笔记' }}
              </button>
              <input ref="fileInput" type="file" multiple accept="image/*" class="hidden" @change="handleFiles" />
            </div>
          </template>
        </PageHeader>

        <!-- Search and filters -->
        <div class="relative z-20 mb-8 space-y-6">
          <div class="flex flex-col sm:flex-row gap-6 items-center">
            <div class="w-full sm:w-1/3">
              <SearchInput v-model="filterKeyword" label="笔记检索" placeholder="搜索笔记内容..." />
            </div>
            
            <!-- Progress Bar -->
            <div v-if="creating" class="flex-1 w-full">
              <div class="h-2 rounded-full bg-slate-200 dark:bg-slate-700">
                <div class="h-full rounded-full bg-emerald-500 transition-all duration-300" :style="{ width: createProgress + '%' }"></div>
              </div>
              <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">OCR 识别 + AI 整理中... {{ createProgress }}%</p>
            </div>
          </div>
        </div>

        <!-- Notes Grid -->
        <div class="relative">
          <div v-if="!loading && notes.length === 0" class="flex flex-col items-center justify-center rounded-[2.5rem] border-2 border-dashed border-slate-200 bg-slate-50/50 py-32 dark:border-white/5 dark:bg-white/5">
            <div class="mb-8 flex h-24 w-24 items-center justify-center rounded-3xl bg-white shadow-md dark:bg-slate-900">
              <i class="fa-solid fa-book-open text-4xl text-slate-300 dark:text-slate-700"></i>
            </div>
            <p class="text-xl font-black text-slate-900 dark:text-white">还没有笔记</p>
            <p class="mt-2 text-sm font-medium text-slate-500">上传手写笔记或板书照片，AI 自动整理为结构化知识点</p>
            <button @click="triggerUpload" class="mt-6 btn-primary h-10 px-8">
              <i class="fa-solid fa-plus mr-2"></i>上传笔记
            </button>
          </div>

          <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <GlassCard
              v-for="note in notes"
              :key="note.id"
              @click="openNote(note)"
              padding="p-6"
              class="group cursor-pointer hover:border-emerald-300/50 hover:shadow-[0_0_20px_rgba(16,185,129,0.1)] dark:hover:border-emerald-500/30"
            >
              <h3 class="mb-2 text-base font-bold text-slate-900 line-clamp-2 dark:text-white">{{ note.title }}</h3>
              <p class="mb-3 text-sm text-slate-500 line-clamp-3 dark:text-slate-400">
                {{ note.content_markdown?.replace(/[#*`>\-]/g, '').slice(0, 120) }}...
              </p>
              <div class="flex flex-wrap items-center gap-2">
                <span v-if="note.subject" class="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-300">{{ note.subject }}</span>
                <span v-for="tag in (note.knowledge_tags || []).slice(0, 3)" :key="tag" class="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500 dark:bg-white/[0.06] dark:text-slate-400">{{ tag }}</span>
                <span class="ml-auto text-xs text-slate-400">{{ note.updated_at?.slice(0, 10) }}</span>
              </div>
            </GlassCard>
          </div>

          <!-- 分页 -->
          <div v-if="totalPages > 1" class="mt-8 flex justify-center gap-2">
            <button
              v-for="p in totalPages"
              :key="p"
              @click="page = p"
              class="size-10 rounded-xl text-sm font-bold transition-all"
              :class="p === page ? 'bg-emerald-500 text-white shadow-md shadow-emerald-500/20' : 'border border-slate-200/60 bg-white/60 text-slate-600 hover:bg-white dark:border-white/10 dark:bg-white/[0.03] dark:text-slate-300'"
            >
              {{ p }}
            </button>
          </div>
        </div>
      </div>

      <!-- Detail View -->
      <div v-else>
        <PageHeader
          :title="selectedNote.title"
          :subtitle="`最后更新: ${selectedNote.updated_at?.slice(0, 10)}`"
          badge="DETAIL"
          badgeColor="slate"
        >
          <template #extra>
            <div class="flex items-center gap-3">
              <GlassButton icon="fa-arrow-left" @click="closeDetail">返回</GlassButton>
              <div class="w-px h-6 bg-slate-200 dark:bg-white/10 mx-1"></div>
              <GlassButton v-if="!editing" icon="fa-pen" @click="startEdit">编辑</GlassButton>
              <GlassButton icon="fa-trash" class="text-rose-600 hover:text-rose-700 dark:text-rose-400 hover:border-rose-300 dark:hover:border-rose-500/30" @click="doDelete(selectedNote.id)">删除</GlassButton>
            </div>
          </template>
        </PageHeader>

        <!-- Tags Row -->
        <div class="mb-6 flex flex-wrap items-center gap-2">
          <span v-if="selectedNote.subject" class="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300">{{ selectedNote.subject }}</span>
          <span v-for="tag in selectedNote.knowledge_tags" :key="tag" class="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600 dark:bg-white/[0.06] dark:text-slate-300">{{ tag }}</span>
        </div>

        <GlassCard padding="p-8">
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
              <GlassButton @click="editing = false">取消</GlassButton>
            </div>
          </div>

          <!-- View Mode -->
          <div v-else ref="noteContentRef">
            <article class="prose prose-slate max-w-none dark:prose-invert prose-headings:text-slate-900 dark:prose-headings:text-white prose-p:leading-relaxed prose-a:text-emerald-600 prose-pre:bg-slate-50 dark:prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-200/60 dark:prose-pre:border-white/10" v-html="renderMarkdown(selectedNote.content_markdown || '')"></article>
          </div>
        </GlassCard>

        <!-- Original Images -->
        <div v-if="selectedNote.source_images?.length && !editing" class="mt-8">
          <h3 class="mb-4 text-sm font-black uppercase tracking-widest text-slate-500">
            <i class="fa-solid fa-image mr-2"></i>原始笔记图片
          </h3>
          <div class="grid gap-4 sm:grid-cols-2">
            <GlassCard v-for="(src, idx) in selectedNote.source_images" :key="idx" padding="p-2" class="overflow-hidden">
              <img
                :src="'/images/' + src.split('/imgs/').pop() || src"
                class="w-full rounded-xl cursor-pointer hover:opacity-90 transition-opacity"
                @error="$event.target.style.display='none'"
              />
            </GlassCard>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
