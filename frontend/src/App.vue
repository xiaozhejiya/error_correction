<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, provide, reactive, ref, watch } from 'vue'
import { fileKey, typesetMath as _typesetMathEl } from './utils.js'
import * as api from './api.js'
// 注意：移除了 AppHeader，因为现在由左侧边栏接管了全局导航功能
import StatusBar from './components/StatusBar.vue'
import StepIndicator from './components/StepIndicator.vue'
import FileUploader from './components/FileUploader.vue'
import QuestionList from './components/QuestionList.vue'
import ActionBar from './components/ActionBar.vue'
import ImageModal from './components/ImageModal.vue'
import ToastContainer from './components/ToastContainer.vue'
import Dashboard from './components/Dashboard.vue'
import CatLoading from './components/CatLoading.vue'
import ErrorBank from './components/ErrorBank.vue'
import ChatView from './components/ChatView.vue'
import SplitHistory from './components/SplitHistory.vue'

// ---- 视图路由控制 ----
const currentView = ref('workspace') // 'workspace' | 'dashboard' | 'error-bank' | 'chat'

// ---- 主题 ----
const theme = ref('light')
const applyTheme = (nextTheme) => {
  theme.value = nextTheme === 'dark' ? 'dark' : 'light'
  const root = document.documentElement
  if (theme.value === 'dark') root.classList.add('dark')
  else root.classList.remove('dark')
}

const toggleTheme = async (btnEl) => {
  const nextTheme = theme.value === 'dark' ? 'light' : 'dark'
  localStorage.setItem('theme', nextTheme)

  const prefersReduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const canTransition = !prefersReduce && typeof document.startViewTransition === 'function'
  if (!canTransition || !btnEl) {
    applyTheme(nextTheme)
    return
  }

  const rect = btnEl.getBoundingClientRect()
  const x = rect.left + rect.width / 2
  const y = rect.top + rect.height / 2
  const endRadius = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y))

  const transition = document.startViewTransition(() => applyTheme(nextTheme))
  try {
    await transition.ready
    const duration = 1000
    const grow = [`circle(0px at ${x}px ${y}px)`, `circle(${endRadius}px at ${x}px ${y}px)`]
    document.documentElement.animate(
      { clipPath: grow },
      { duration, easing: 'cubic-bezier(0.2, 0, 0, 1)', pseudoElement: '::view-transition-new(root)' },
    )
    document.documentElement.animate(
      { opacity: [1, 0.98] },
      { duration, easing: 'linear', pseudoElement: '::view-transition-old(root)' },
    )
    await transition.finished
  } catch (_) {
    applyTheme(nextTheme)
  }
}
// ---- 系统状态 ----
const statusLoading = ref(true)
const systemStatus = ref(null)
const statusError = ref('')
const modelProvider = ref('deepseek')

const providerOptions = computed(() => {
  const s = systemStatus.value
  return s && s.available_models ? s.available_models : []
})

watch(systemStatus, (newVal) => {
  if (newVal && newVal.available_models) {
    const configured = newVal.available_models.find(m => m.configured)
    if (configured) modelProvider.value = configured.value
  }
})

const statusPills = computed(() => {
  const s = systemStatus.value
  if (!s) return []
  const pills = []
  pills.push({ key: 'paddle', ok: !!s.paddleocr_configured, label: s.paddleocr_configured ? 'PaddleOCR' : 'PaddleOCR未配置' })
  const activeProvider = providerOptions.value.find(p => p.value === modelProvider.value)
  if (activeProvider) {
    pills.push({ key: 'model', ok: activeProvider.configured, label: activeProvider.configured ? activeProvider.label : `${activeProvider.label}未配置` })
  }
  if (s.langsmith_enabled) pills.push({ key: 'langsmith', ok: true, label: 'LangSmith追踪' })
  return pills
})

const doFetchStatus = async () => {
  statusLoading.value = true
  statusError.value = ''
  try {
    systemStatus.value = await api.fetchStatus()
  } catch (e) {
    statusError.value = e instanceof Error ? e.message : String(e)
  } finally {
    statusLoading.value = false
  }
}

// ---- 步骤 & Toast ----
const step = ref(1)
const toasts = ref([])
let toastId = 0
const pushToast = (type, message, timeout = 2600) => {
  const id = ++toastId
  toasts.value = [{ id, type, message }, ...toasts.value].slice(0, 5)
  if (timeout > 0) window.setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id) }, timeout)
}
provide('pushToast', pushToast)

// ---- AI 辅导对话 ----
const chatSessionId = ref(null)
const chatQuestion = ref(null)
const chatActive = ref(false)

// 答案录入弹窗（AI 辅导前置）
const answerModalOpen = ref(false)
const answerModalTarget = ref(null)
const answerModalText = ref('')
const answerModalSaving = ref(false)

const openChat = async (question) => {
  chatQuestion.value = question
  // 如果没有答案，先弹出答案录入弹窗
  if (!question.answer) {
    answerModalTarget.value = question
    answerModalText.value = ''
    answerModalOpen.value = true
    return
  }
  await doOpenChatSession(question)
}

const doOpenChatSession = async (question) => {
  try {
    const sessions = await api.fetchChatSessions(question.id)
    if (sessions.length) {
      chatSessionId.value = sessions[0].id
    } else {
      const session = await api.createChat(question.id)
      chatSessionId.value = session.id
    }
    chatActive.value = true
    currentView.value = 'chat'
  } catch (e) {
    pushToast('error', '打开对话失败: ' + (e instanceof Error ? e.message : String(e)))
  }
}

const saveAnswerAndChat = async () => {
  if (!answerModalTarget.value || answerModalSaving.value) return
  const text = answerModalText.value.trim()
  if (!text) { pushToast('error', '请输入答案/解析内容'); return }
  answerModalSaving.value = true
  try {
    await api.saveQuestionAnswer(answerModalTarget.value.id, text)
    answerModalTarget.value.answer = text
    answerModalOpen.value = false
    pushToast('success', '答案已保存')
    // 继续打开对话
    await doOpenChatSession(answerModalTarget.value)
  } catch (e) {
    pushToast('error', '保存答案失败: ' + (e instanceof Error ? e.message : String(e)))
  } finally {
    answerModalSaving.value = false
  }
}

const backToErrorBank = () => {
  chatActive.value = false
  chatSessionId.value = null
  chatQuestion.value = null
  currentView.value = 'error-bank'
}

// ---- 图片弹窗 ----
const modalOpen = ref(false)
const modalSrc = ref('')
const modalScale = ref(1)
const openModal = (src) => {
  modalSrc.value = src || ''
  modalScale.value = 1
  modalOpen.value = !!src
  if (src) document.body.style.overflow = 'hidden'
}
const closeModal = () => {
  modalOpen.value = false
  modalSrc.value = ''
  modalScale.value = 1
  document.body.style.overflow = ''
}
const onKeydown = (e) => { if (e.key === 'Escape' && modalOpen.value) closeModal() }

// ---- 上传状态 ----
const uploadBusy = ref(false)
const uploadReady = ref(false)
const splitting = ref(false)
const splitCompleted = ref(false)

const pendingFiles = reactive([])
const fileProgress = reactive({})
const waitingKeys = reactive(new Set())
const uploadQueue = reactive([])
let activeXhr = null
let fakeProgressTimer = null
let fakeProgressKeys = []

const historyOpen = ref(false)
const splitEnabled = computed(() => !splitting.value && !splitCompleted.value && uploadReady.value && !uploadBusy.value)
const exportEnabled = computed(() => splitCompleted.value && selectedIds.size > 0)

const stopFakeProgress = () => {
  if (fakeProgressTimer) {
    window.clearInterval(fakeProgressTimer)
    fakeProgressTimer = null
  }
  fakeProgressKeys = []
}
const setProgress = (key, p) => { fileProgress[key] = Math.max(0, Math.min(100, Number(p) || 0)) }

const startFakeProgress = (keys) => {
  stopFakeProgress()
  fakeProgressKeys = Array.from(keys || [])
  const tick = () => {
    if (!uploadBusy.value) { stopFakeProgress(); return }
    for (const key of fakeProgressKeys) {
      const current = Number(fileProgress[key] || 0)
      const cap = 82
      if (current >= cap) continue
      let inc = current < 55 ? 1 + Math.random() * 3 : current < 75 ? 0.4 + Math.random() * 1.1 : 0.08 + Math.random() * 0.25
      setProgress(key, Math.min(cap, current + inc))
    }
  }
  tick()
  fakeProgressTimer = window.setInterval(tick, 360)
}

const enqueueUpload = (files) => {
  const list = Array.from(files || [])
  if (!list.length) return
  if (splitCompleted.value || splitting.value) { pushToast('error', '已分割完成，请先重新开始'); return }
  for (const f of list) {
    const k = fileKey(f)
    if (pendingFiles.some(x => x.key === k)) continue
    pendingFiles.push({ key: k, file: f })
    setProgress(k, 0)
  }
  if (uploadBusy.value) {
    for (const f of list) waitingKeys.add(fileKey(f))
    uploadQueue.push(list)
    return
  }
  handleUpload(list)
}

const pumpUploadQueue = () => {
  if (uploadBusy.value || !uploadQueue.length) return
  const next = uploadQueue.shift()
  if (next && next.length) handleUpload(next)
}
const removePendingFile = async (key) => {
  if (!key || splitting.value || splitCompleted.value) return
  if (uploadBusy.value || uploadReady.value) { await doCancelFile(key); return }
  const idx = pendingFiles.findIndex(x => x.key === key)
  if (idx >= 0) pendingFiles.splice(idx, 1)
  delete fileProgress[key]
  waitingKeys.delete(key)
  for (let i = uploadQueue.length - 1; i >= 0; i--) {
    uploadQueue[i] = (uploadQueue[i] || []).filter(f => fileKey(f) !== key)
    if (!uploadQueue[i].length) uploadQueue.splice(i, 1)
  }
}

const doCancelFile = async (key) => {
  try {
    if (fakeProgressKeys.length) fakeProgressKeys = fakeProgressKeys.filter(k => k !== key)
    if (!fakeProgressKeys.length) stopFakeProgress()
    const data = await api.cancelFile(key)
    const idx = pendingFiles.findIndex(x => x.key === key)
    if (idx >= 0) pendingFiles.splice(idx, 1)
    delete fileProgress[key]
    waitingKeys.delete(key)
    questions.value = []
    selectedIds.clear()
    splitCompleted.value = false
    if (!pendingFiles.length) {
      uploadReady.value = false
      step.value = 1
    } else {
      step.value = 3
    }
    pushToast('success', data.message || '已撤销')
    if (!pendingFiles.length && activeXhr) {
      try { activeXhr.abort() } catch (_) {}
    }
  } catch (_) { pushToast('error', '撤销失败: 网络错误') }
}

const handleUpload = (files) => {
  const uploadFiles = Array.from(files || []).filter(f => pendingFiles.some(x => x.key === fileKey(f)))
  if (!uploadFiles.length) return
  uploadBusy.value = true
  step.value = 2
  const keys = uploadFiles.map(f => fileKey(f))
  for (const k of keys) waitingKeys.delete(k)
  startFakeProgress(keys)

  const formData = new FormData()
  for (const f of uploadFiles) {
    formData.append('files', f)
    formData.append('file_key', fileKey(f))
  }

  activeXhr = api.uploadFiles(formData, {
    onProgress: (ratio) => {
      const pct = Math.max(0, Math.min(95, ratio * 95))
      for (const k of keys) {
        if (pendingFiles.some(x => x.key === k)) setProgress(k, Math.max(fileProgress[k] || 0, pct))
      }
    },
    onSuccess: () => {
      stopFakeProgress()
      uploadBusy.value = false
      activeXhr = null
      for (const k of keys) {
        if (pendingFiles.some(x => x.key === k)) setProgress(k, 100)
      }
      uploadReady.value = pendingFiles.length > 0
      step.value = pendingFiles.length > 0 ? 3 : 1
      pushToast('success', `上传成功！本次新增 ${keys.length} 个文件，点击"开始分割题目"开始处理`)
      pumpUploadQueue()
    },
    onError: (msg) => {
      stopFakeProgress()
      uploadBusy.value = false
      activeXhr = null
      pushToast('error', msg)
      pumpUploadQueue()
    },
    onAbort: () => {
      stopFakeProgress()
      uploadBusy.value = false
      activeXhr = null
      pumpUploadQueue()
    },
  })
}

// ---- 题目 ----
const questions = ref([])
const selectedIds = reactive(new Set())
const questionListRef = ref(null)
const errorBankRef = ref(null)

const toggleQuestion = (id) => { selectedIds.has(id) ? selectedIds.delete(id) : selectedIds.add(id) }
const selectAll = () => { for (const q of questions.value) selectedIds.add(q.question_id) }
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
const doSplit = async () => {
  if (!uploadReady.value || splitting.value || splitCompleted.value) return
  splitting.value = true
  step.value = 3
  pushToast('info', '正在调用AI分割题目，请稍候...', 1800)
  try {
    const data = await api.splitQuestions(modelProvider.value)
    questions.value = data.questions || []
    selectedIds.clear()
    if (data.warnings && data.warnings.length) {
      for (const w of data.warnings) pushToast('warning', w, 6000)
    }
    if (questions.value.length > 0) {
      splitCompleted.value = true
      step.value = 4
      if (!data.warnings || !data.warnings.length) {
        pushToast('success', `成功分割 ${questions.value.length} 道题目`)
      }
      await typesetMath()
    }
  } catch (e) {
    pushToast('error', '分割失败: ' + (e instanceof Error ? e.message : String(e)))
  } finally {
    splitting.value = false
  }
}

const doExport = async () => {
  if (!selectedIds.size) { pushToast('error', '请至少选择一道题目！'); return }
  try {
    const data = await api.exportQuestions(Array.from(selectedIds))
    step.value = 5
    pushToast('success', `错题本导出成功！已保存到: ${data.output_path}`)
    let filename = 'wrongbook.md'
    if (data.output_path) {
      const parts = String(data.output_path).split(/[/\\]/)
      const last = parts[parts.length - 1]
      if (last) filename = last
    }
    const a = document.createElement('a')
    a.href = `/download/${encodeURIComponent(filename)}?t=${Date.now()}`
    a.download = filename
    a.style.display = 'none'
    document.body.appendChild(a)
    a.click()
    a.remove()
  } catch (e) {
    pushToast('error', '导出失败: ' + (e instanceof Error ? e.message : String(e)))
  }
}

const doSaveToDb = async () => {
  if (!selectedIds.size) { pushToast('error', '请至少选择一道题目！'); return }
  try {
    // 收集已录入的答案数据一并传给后端
    const answers = questions.value
      .filter(q => selectedIds.has(q.question_id) && (q.answer || q.user_answer))
      .map(q => ({ question_id: q.question_id, answer: q.answer || '', user_answer: q.user_answer || '' }))
    const data = await api.saveToDb(Array.from(selectedIds), answers)
    pushToast('success', data.message || '已导入错题库')
    errorBankRef.value?.refresh()
  } catch (e) {
    pushToast('error', '导入失败: ' + (e instanceof Error ? e.message : String(e)))
  }
}

const clearWorkspaceState = () => {
  uploadBusy.value = false
  uploadReady.value = false
  splitting.value = false
  pendingFiles.splice(0, pendingFiles.length)
  for (const k of Object.keys(fileProgress)) delete fileProgress[k]
  waitingKeys.clear()
  uploadQueue.splice(0, uploadQueue.length)
  questions.value = []
  selectedIds.clear()
}

const doReset = () => {
  clearWorkspaceState()
  splitCompleted.value = false
  const configured = providerOptions.value.find(m => m.configured)
  modelProvider.value = configured ? configured.value : 'deepseek'
  step.value = 1
  pushToast('success', '已重置')
}

const loadFromHistory = (loadedQuestions) => {
  if (questions.value.length && !window.confirm('当前工作区已有题目，加载历史记录将替换现有内容。是否继续？')) return
  historyOpen.value = false
  clearWorkspaceState()
  splitCompleted.value = true
  questions.value = loadedQuestions
  step.value = 4
  pushToast('success', `已加载 ${loadedQuestions.length} 道历史题目`)
  typesetMath()
}

// ---- 生命周期 ----
onMounted(() => {
  const saved = localStorage.getItem('theme')
  const initial = saved || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  applyTheme(initial)
  doFetchStatus()
  document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  stopFakeProgress()
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="flex h-screen w-full overflow-hidden bg-slate-50 font-sans text-slate-900 transition-colors duration-500 dark:bg-[#05050A] dark:text-slate-300">
    
    <!-- ================== PC端：左侧边栏导航 ================== -->
    <aside class="hidden w-64 flex-col justify-between border-r border-slate-200/80 bg-white/60 backdrop-blur-xl transition-colors md:flex dark:border-white/5 dark:bg-[#0A0A0F]/80 z-20">
      <div>
        <!-- Logo 标题区 -->
        <div class="flex h-20 items-center gap-3 border-b border-slate-100 px-6 dark:border-white/5">
          <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-lg shadow-blue-500/30 dark:shadow-indigo-900/40">
            <i class="fa-solid fa-file-circle-check text-xl"></i>
          </div>
          <span class="text-xl font-extrabold tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-blue-700 to-indigo-700 dark:from-white dark:to-indigo-200">
            智卷系统
          </span>
        </div>

        <!-- 视图切换菜单 -->
        <nav class="mt-6 flex flex-col gap-2 px-4">
          <div class="mb-2 px-2 text-xs font-bold uppercase tracking-wider text-slate-400">核心功能</div>
          
          <button
            @click="currentView = 'workspace'"
            class="group flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold transition-all"
            :class="currentView === 'workspace' ? 'bg-blue-600 text-white shadow-md dark:bg-indigo-500 dark:shadow-[0_0_15px_rgba(99,102,241,0.3)]' : 'text-slate-600 hover:bg-slate-100 hover:text-blue-600 dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-indigo-300'"
          >
            <i class="fa-solid fa-wand-magic-sparkles w-5 text-center text-lg transition-transform group-hover:scale-110"></i>
            录题工作台
          </button>

          <button
            @click="currentView = 'dashboard'"
            class="group flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold transition-all"
            :class="currentView === 'dashboard' ? 'bg-blue-600 text-white shadow-md dark:bg-indigo-500 dark:shadow-[0_0_15px_rgba(99,102,241,0.3)]' : 'text-slate-600 hover:bg-slate-100 hover:text-blue-600 dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-indigo-300'"
          >
            <i class="fa-solid fa-chart-pie w-5 text-center text-lg transition-transform group-hover:scale-110"></i>
            我的错题本
          </button>

          <button
            @click="currentView = 'error-bank'"
            class="group flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold transition-all"
            :class="currentView === 'error-bank' ? 'bg-blue-600 text-white shadow-md dark:bg-indigo-500 dark:shadow-[0_0_15px_rgba(99,102,241,0.3)]' : 'text-slate-600 hover:bg-slate-100 hover:text-blue-600 dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-indigo-300'"
          >
            <i class="fa-solid fa-database w-5 text-center text-lg transition-transform group-hover:scale-110"></i>
            错题库
          </button>
        </nav>
      </div>

      <!-- 底部控制与返回栏 -->
      <div class="space-y-2 border-t border-slate-100 p-4 dark:border-white/5">
        <button
          @click="(e) => toggleTheme(e.currentTarget)"
          class="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold text-slate-600 transition-all hover:bg-slate-100 hover:text-blue-600 dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-indigo-300"
        >
          <i class="fa-solid w-5 text-center text-lg transition-transform" :class="theme === 'dark' ? 'fa-sun text-amber-400 rotate-12' : 'fa-moon'"></i>
          <span>{{ theme === 'dark' ? '浅色模式' : '深色模式' }}</span>
        </button>

        <!-- 替换为带有左箭头的返回介绍页面按钮 -->
        <a
          href="/"
          class="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold text-slate-600 transition-all hover:bg-slate-100 hover:text-blue-600 dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-indigo-300"
        >
          <i class="fa-solid fa-arrow-left-long w-5 text-center text-lg"></i>
          返回介绍页面
        </a>
      </div>
    </aside>

    <!-- ================== 移动端：底部 Tab 导航栏 ================== -->
    <nav class="fixed bottom-0 left-0 right-0 z-50 border-t border-slate-200 bg-white/90 pb-2 pt-2 backdrop-blur-xl md:hidden dark:border-white/10 dark:bg-[#0A0A0F]/90">
      <div class="flex justify-around">
        <button @click="currentView = 'workspace'" class="flex flex-col items-center p-2 transition-colors" :class="currentView === 'workspace' ? 'text-blue-600 dark:text-indigo-400' : 'text-slate-500 dark:text-slate-400'">
          <i class="fa-solid fa-wand-magic-sparkles mb-1 text-xl"></i>
          <span class="text-[10px] font-bold">工作台</span>
        </button>
        <button @click="currentView = 'dashboard'" class="flex flex-col items-center p-2 transition-colors" :class="currentView === 'dashboard' ? 'text-blue-600 dark:text-indigo-400' : 'text-slate-500 dark:text-slate-400'">
          <i class="fa-solid fa-chart-pie mb-1 text-xl"></i>
          <span class="text-[10px] font-bold">错题本</span>
        </button>
        <button @click="currentView = 'error-bank'" class="flex flex-col items-center p-2 transition-colors" :class="currentView === 'error-bank' ? 'text-blue-600 dark:text-indigo-400' : 'text-slate-500 dark:text-slate-400'">
          <i class="fa-solid fa-database mb-1 text-xl"></i>
          <span class="text-[10px] font-bold">错题库</span>
        </button>
        <button @click="(e) => toggleTheme(e.currentTarget)" class="flex flex-col items-center p-2 text-slate-500 transition-colors dark:text-slate-400">
          <i class="fa-solid mb-1 text-xl" :class="theme === 'dark' ? 'fa-sun text-amber-400' : 'fa-moon'"></i>
          <span class="text-[10px] font-bold">主题</span>
        </button>
        <!-- 移动端同步替换 -->
        <a href="/" class="flex flex-col items-center p-2 text-slate-500 transition-colors dark:text-slate-400">
          <i class="fa-solid fa-arrow-left-long mb-1 text-xl"></i>
          <span class="text-[10px] font-bold">返回介绍</span>
        </a>
      </div>
    </nav>

    <!-- ================== 右侧主内容区 ================== -->
    <main class="relative z-10 flex-1 overflow-y-auto pb-20 md:pb-0">
      
      <!-- 视图 1：录题工作台 -->
      <div v-show="currentView === 'workspace'" class="relative min-h-full">
        <!-- 专属背景光晕 -->
        <div class="pointer-events-none absolute inset-0 z-0 overflow-hidden">
          <div class="absolute -top-[10%] left-[-10%] h-[40vw] w-[40vw] rounded-full bg-blue-300/10 mix-blend-multiply blur-[100px] transition-colors duration-1000 dark:bg-indigo-600/10 dark:mix-blend-screen"></div>
          <div class="absolute -bottom-[10%] right-[-10%] h-[30vw] w-[30vw] rounded-full bg-cyan-200/20 mix-blend-multiply blur-[80px] transition-colors duration-1000 dark:bg-fuchsia-600/10 dark:mix-blend-screen"></div>
        </div>

        <div class="container relative z-10 mx-auto max-w-5xl px-4 py-8 sm:px-8">
          <!-- 工作台页面标题 -->
          <div class="mb-8 flex items-end justify-between pl-2 sm:pl-0">
            <div>
              <h2 class="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl dark:text-white">
                智能录入与分析
              </h2>
              <p class="mt-2 text-sm font-medium text-slate-500 dark:text-slate-400">驱动 AI 引擎，快速将试卷转化为结构化数据。</p>
            </div>
            <button
              @click="historyOpen = true"
              class="inline-flex shrink-0 items-center gap-2 rounded-xl border border-slate-200/60 bg-white/60 px-4 py-2.5 text-sm font-bold text-slate-600 shadow-sm backdrop-blur-md transition-all hover:bg-white hover:text-blue-600 hover:shadow-md dark:border-white/10 dark:bg-white/5 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-indigo-300"
            >
              <i class="fa-solid fa-clock-rotate-left"></i>
              分割历史
            </button>
          </div>

          <!-- 原工作区主卡片 -->
          <div class="main-content relative rounded-3xl border border-slate-200/60 bg-white/70 p-5 shadow-xl backdrop-blur-xl sm:p-8 dark:border-white/10 dark:bg-[#0A0A0F]/60">
            <StatusBar
              :status-loading="statusLoading"
              :status-error="statusError"
              :status-pills="statusPills"
              :provider-options="providerOptions"
              :model-provider="modelProvider"
              :disabled="splitting || splitCompleted"
              @update:model-provider="(v) => modelProvider = v"
            />

            <StepIndicator :step="step" />

            <FileUploader
              :pending-files="pendingFiles"
              :file-progress="fileProgress"
              :waiting-keys="waitingKeys"
              :upload-busy="uploadBusy"
              :upload-ready="uploadReady"
              :splitting="splitting"
              :split-completed="splitCompleted"
              @upload="enqueueUpload"
              @remove-file="removePendingFile"
            />

            <QuestionList
              ref="questionListRef"
              :questions="questions"
              :selected-ids="selectedIds"
              @toggle-select="toggleQuestion"
              @select-all="selectAll"
              @deselect-all="deselectAll"
              @open-image="openModal"
              @reorder="reorderQuestions"
            />

            <ActionBar
              :split-enabled="splitEnabled"
              :export-enabled="exportEnabled"
              :splitting="splitting"
              :split-completed="splitCompleted"
              @split="doSplit"
              @export="doExport"
              @save-to-db="doSaveToDb"
              @reset="doReset"
            />

            <!-- 像素猫 loading 遮罩 (AI 分割中) -->
            <CatLoading v-if="splitting" />
          </div>
        </div>
      </div>

      <!-- 视图 2：我的错题本数据看板 (完全独立组件) -->
      <Dashboard
        v-show="currentView === 'dashboard'"
        :theme="theme"
        :visible="currentView === 'dashboard'"
        @go-workspace="currentView = 'workspace'"
        @push-toast="pushToast"
        @open-image="openModal"
        @start-chat="openChat"
      />

      <!-- 视图 3：错题库 -->
      <ErrorBank
        ref="errorBankRef"
        v-show="currentView === 'error-bank'"
        :theme="theme"
        :visible="currentView === 'error-bank'"
        @go-workspace="currentView = 'workspace'"
        @push-toast="pushToast"
        @open-image="openModal"
        @start-chat="openChat"
      />

      <!-- 视图 4：AI 辅导对话 -->
      <div v-show="currentView === 'chat'" class="h-full">
        <ChatView
          v-if="chatActive"
          :session-id="chatSessionId"
          :question="chatQuestion"
          :model-provider="modelProvider"
          @back="backToErrorBank"
        />
      </div>
    </main>

    <!-- 全局弹窗与通知 -->
    <Teleport to="body">
      <ImageModal
        :open="modalOpen"
        :src="modalSrc"
        :scale="modalScale"
        @close="closeModal"
        @update:scale="(s) => modalScale = s"
      />
      <ToastContainer :toasts="toasts" />
      <SplitHistory :open="historyOpen" @close="historyOpen = false" @load-record="loadFromHistory" />

      <!-- 答案录入弹窗（AI 辅导前置） -->
      <div v-if="answerModalOpen" class="fixed inset-0 z-[100] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm dark:bg-black/60" @click="answerModalOpen = false"></div>
        <div class="relative w-full max-w-lg rounded-2xl border border-slate-200/60 bg-white p-6 shadow-2xl dark:border-white/10 dark:bg-slate-900">
          <h3 class="mb-1 text-lg font-bold text-slate-900 dark:text-white">录入答案</h3>
          <p class="mb-4 text-xs text-slate-500 dark:text-slate-400">
            AI 辅导需要正确答案作为参考。支持 Markdown 格式，数学公式使用 LaTeX（$..$ 行内，$$...$$ 独占行）
          </p>
          <textarea
            v-model="answerModalText"
            rows="10"
            placeholder="在此粘贴或输入答案/解析..."
            class="w-full resize-none rounded-xl border border-slate-200/80 bg-slate-50 px-4 py-3 font-mono text-sm text-slate-800 placeholder-slate-400 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-slate-800 dark:text-slate-200"
          ></textarea>
          <div class="mt-4 flex justify-end gap-3">
            <button
              @click="answerModalOpen = false"
              class="rounded-xl border border-slate-200/60 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50 dark:border-white/10 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              取消
            </button>
            <button
              @click="saveAnswerAndChat"
              :disabled="answerModalSaving"
              class="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-bold text-white shadow-sm transition-all hover:bg-blue-700 disabled:opacity-50 dark:bg-indigo-500 dark:hover:bg-indigo-600"
            >
              {{ answerModalSaving ? '保存中...' : '保存并开始辅导' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>