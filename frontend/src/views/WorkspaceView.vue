<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, provide, reactive, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { fileKey, typesetMath as _typesetMathEl } from '../utils.js'
import * as api from '../api.js'
import { useAuth } from '../composables/useAuth.js'
import { usePageTransition } from '../composables/usePageTransition.js'
// 注意：移除了 AppHeader，因为现在由左侧边栏接管了全局导航功能
import StatusBar from '../components/StatusBar.vue'
import StepIndicator from '../components/StepIndicator.vue'
import FileList from '../components/FileList.vue'
import FileUploader from '../components/FileUploader.vue'
import QuestionList from '../components/QuestionList.vue'
import ActionBar from '../components/ActionBar.vue'
import SelectionPanel from '../components/SelectionPanel.vue'
import SplitLoading from '../components/SplitLoading.vue'
import ImageModal from '../components/ImageModal.vue'
import ToastContainer from '../components/ToastContainer.vue'
import Dashboard from '../components/Dashboard.vue'
import ReviewView from '../components/ReviewView.vue'
import ErrorBank from '../components/ErrorBank.vue'
import ChatView from '../components/ChatView.vue'
import SettingsView from '../components/SettingsView.vue'
import SplitHistory from '../components/SplitHistory.vue'
import NoteView from '../components/NoteView.vue'
import GlassButton from '../components/GlassButton.vue'

// ---- 认证状态 ----
const { currentUser } = useAuth()
const router = useRouter()
const route = useRoute()

const handleLogout = async () => {
  try {
    await fetch('/api/auth/logout', { method: 'POST' })
  } catch (_) {}
  currentUser.value = null
  router.push('/auth')
}

const navigateToHome = () => {
  document.body.style.transition = 'opacity 0.25s ease, transform 0.25s ease'
  document.body.style.opacity = '0'
  document.body.style.transform = 'translateY(-6px)'
  setTimeout(() => { window.location.href = '/' }, 260)
}

// ---- 视图路由控制 ----
const VIEW_TO_PATH = {
  workspace: '/app/workspace',
  workspace_review: '/app/workspace/review',
  dashboard: '/app/dashboard',
  review: '/app/review',
  'error-bank': '/app/error-bank',
  notes: '/app/notes',
  settings: '/app/settings',
  'split-history': '/app/split-history',
  chat: '/app/chat',
}

const WORKSPACE_VIEWS = new Set(['workspace', 'workspace_review', 'split-history'])

const lastWorkspaceView = ref('workspace')

const NAV_ITEMS = [
  { id: 'workspace', label: '录题工作台', icon: 'fa-wand-magic-sparkles', match: (v) => WORKSPACE_VIEWS.has(v) },
  { id: 'dashboard', label: '数据面板', icon: 'fa-chart-pie', match: (v) => v === 'dashboard' },
  { id: 'error-bank', label: '错题库', icon: 'fa-database', match: (v) => v === 'error-bank' },
  { id: 'notes', label: '笔记库', icon: 'fa-book-open', match: (v) => v === 'notes' },
]

const currentView = computed({
  get() {
    const view = route.params.view || 'workspace'
    const subview = route.params.subview
    if (view === 'workspace' && subview === 'review') return 'workspace_review'
    return view
  },
  set(view) {
    const path = VIEW_TO_PATH[view]
    if (path && route.path !== path) router.push(path)
  },
})

watch(currentView, (v) => {
  if (WORKSPACE_VIEWS.has(v)) lastWorkspaceView.value = v
})

const navIndicatorStyle = computed(() => {
  const idx = NAV_ITEMS.findIndex(item => item.match(currentView.value))
  if (idx === -1) return { opacity: 0, transform: 'translateY(0)' }
  
  // 精确计算：
  // 1. 核心功能标题：text-xs (16px) + mb-2 (8px) = 24px
  // 2. Flex Gap: gap-1.5 (6px)
  // 3. 按钮高度：py-3 (12px * 2) + text-lg 图标高度 (28px) = 52px
  const headerHeight = 24
  const gap = 6
  const itemHeight = 52
  
  const offset = headerHeight + gap
  return {
    opacity: 1,
    transform: `translateY(${idx * (itemHeight + gap) + offset}px)`,
    height: `${itemHeight}px`
  }
})

// ---- 状态定义 ----
const { loading: globalLoading } = usePageTransition()
const theme = ref('dark')
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
const selectedModel = ref('')  // 选中的具体模型名称（如 "gpt-4o-mini"）

const providerOptions = computed(() => {
  const s = systemStatus.value
  return s && s.available_models ? s.available_models : []
})

// 是否有可用模型
const hasConfiguredModel = computed(() => providerOptions.value.some(p => p.configured))

// 从 selectedModel 反查 provider
const selectedProvider = computed(() => {
  for (const p of providerOptions.value) {
    if (p.models && p.models.includes(selectedModel.value)) return p.value
  }
  // 找不到时回退到首个已配置的 provider，而非硬编码 'openai'
  const configured = providerOptions.value.find(p => p.configured)
  return configured ? configured.value : (providerOptions.value[0]?.value ?? 'openai')
})

watch(systemStatus, (newVal) => {
  if (newVal && newVal.available_models) {
    const configured = newVal.available_models.find(m => m.configured)
    if (configured) selectedModel.value = configured.default_model
  }
})

const statusPills = computed(() => {
  if (statusLoading.value) return [
    { key: 'paddle', loading: true, label: 'PaddleOCR' },
    { key: 'ensexam', loading: true, label: 'EnsExam' },
    { key: 'langsmith', loading: true, label: 'LangSmith (未接入)' },
  ]
  const s = systemStatus.value
  if (!s) return []
  const pills = []
  pills.push({ key: 'paddle', ok: !!s.paddleocr_configured, label: s.paddleocr_configured ? 'PaddleOCR' : 'PaddleOCR未配置' })
  if (s.ensexam_configured) {
    pills.push({ key: 'ensexam', ok: true, label: 'EnsExam已接入' })
  }
  pills.push(s.langsmith_enabled
    ? { key: 'langsmith', ok: true, label: 'LangSmith追踪' }
    : { key: 'langsmith', ok: false, label: 'LangSmith (未接入)', isPlaceholder: true }
  )
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
const uploadMode = ref('exam')  // 'exam'（试卷分割）或 'note'（笔记整理）
const uploadBusy = ref(false)
const uploadReady = ref(false)
const splitting = ref(false)
const splitCompleted = ref(false)
const eraseEnabled = ref(true)

const pendingFiles = reactive([])
const fileProgress = reactive({})
const waitingKeys = reactive(new Set())
const uploadQueue = reactive([])
let activeXhr = null
let fakeProgressTimer = null
let fakeProgressKeys = []

const splitEnabled = computed(() => !splitting.value && !splitCompleted.value && uploadReady.value && !uploadBusy.value && hasConfiguredModel.value)
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

  // 笔记模式：走笔记整理流程
  if (uploadMode.value === 'note') {
    await doNoteOrganize()
    return
  }

  // 试卷模式：走原有分割流程
  splitting.value = true
  step.value = 3
  pushToast('info', '正在调用AI分割题目，请稍候...', 1800)
  try {
    const data = await api.splitQuestions(selectedProvider.value, selectedModel.value, { erase: eraseEnabled.value })
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
      setTimeout(() => {
        if (currentView.value === 'workspace') {
          currentView.value = 'workspace_review'
        }
      }, 800)
    }
  } catch (e) {
    pushToast('error', '分割失败: ' + (e instanceof Error ? e.message : String(e)))
  } finally {
    splitting.value = false
  }
}

const doNoteOrganize = async () => {
  splitting.value = true
  step.value = 3
  pushToast('info', '正在调用AI整理笔记，请稍候...', 3000)
  try {
    // 收集已上传文件，构建 FormData 发给笔记 API
    const formData = new FormData()
    for (const pf of pendingFiles) {
      if (pf.file) formData.append('files', pf.file)
    }
    formData.append('model_provider', selectedProvider.value)
    if (selectedModel.value) formData.append('model_name', selectedModel.value)

    const result = await new Promise((resolve, reject) => {
      api.createNote(formData, {
        onSuccess: (data) => resolve(data),
        onError: (msg) => reject(new Error(msg)),
      })
    })

    splitCompleted.value = true
    step.value = 4
    pushToast('success', '笔记整理完成！')

    // 跳转到笔记页面查看
    setTimeout(() => {
      currentView.value = 'notes'
    }, 800)
  } catch (e) {
    pushToast('error', '笔记整理失败: ' + (e instanceof Error ? e.message : String(e)))
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

const handleLoadRecord = (qs, record) => {
  questions.value = qs || []
  selectedIds.clear()
  splitCompleted.value = true
  step.value = 4
  currentView.value = 'workspace_review'
  pushToast('success', `已加载「${record?.subject || '历史记录'}」的 ${qs.length} 道题目`)
  nextTick(() => typesetMath())
}

const doReset = () => {
  uploadBusy.value = false
  uploadReady.value = false
  splitting.value = false
  splitCompleted.value = false
  pendingFiles.splice(0, pendingFiles.length)
  for (const k of Object.keys(fileProgress)) delete fileProgress[k]
  waitingKeys.clear()
  uploadQueue.splice(0, uploadQueue.length)
  questions.value = []
  selectedIds.clear()
  const configured = providerOptions.value.find(m => m.configured)
  selectedModel.value = configured ? configured.default_model : ''
  step.value = 1
  pushToast('success', '已重置')
}

watch(currentView, async (newView) => {
  if (newView === 'workspace_review') {
    // 等待翻页动画结束
    await nextTick()
    setTimeout(() => {
      questionListRef.value?.triggerTypeset?.()
    }, 650)
  }
})

// ---- 页面加载动画 ----
const pageLoading = ref(true)

// ---- 生命周期 ----
onMounted(() => {
  applyTheme('dark')
  document.addEventListener('keydown', onKeydown)

  // 刷新时如果落在 /workspace/review 但没有数据，重定向回上传页
  if (currentView.value === 'workspace_review' && !splitCompleted.value) {
    router.replace('/app/workspace')
  }
  
  // 延迟系统状态检查，直到入场加载动画完全结束
  // 这能确保在动画过程中不会因为网络请求导致掉帧，且视觉上更连贯
  setTimeout(() => {
    pageLoading.value = false
    
    // 如果全局 loading 已经结束（说明动画已经淡出或不需要淡出），开始检查
    if (!globalLoading.value) {
      doFetchStatus()
    } else {
      // 否则，监听全局 loading 状态，待其变为 false（即 AppLoading 彻底消失）后触发
      const unwatch = watch(globalLoading, (val) => {
        if (!val) {
          doFetchStatus()
          unwatch()
        }
      })
    }
  }, 2000)
})

onBeforeUnmount(() => {
  stopFakeProgress()
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="flex h-screen w-full overflow-hidden bg-slate-50 font-sans text-slate-900 dark:bg-[#05050A] dark:text-slate-300">

    <Transition name="ws-loading-fade">
      <div v-if="pageLoading" class="fixed inset-0 z-[200] flex flex-col items-center justify-center gap-8 bg-[#05050A]">
        <div class="relative">
          <div class="absolute inset-0 rounded-2xl bg-indigo-500/40 blur-xl"></div>
          <div class="relative bg-gradient-to-br from-indigo-500 to-indigo-700 p-3.5 rounded-2xl shadow-lg border border-white/10">
            <img src="/logo.svg" class="w-9 h-9 brightness-0 invert" alt="logo" />
          </div>
        </div>
        <div class="w-48">
          <div class="h-0.5 w-full rounded-full bg-white/10 overflow-hidden">
            <div class="h-full rounded-full bg-gradient-to-r from-indigo-500 to-blue-400 ws-loading-bar"></div>
          </div>
        </div>
      </div>
    </Transition>
    <!-- ================== 全局固定背景光晕 (支持长页面滚动) ================== -->
    <div class="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <div class="animate-blob absolute -top-[10%] left-[-10%] h-[50vw] w-[50vw] rounded-full bg-blue-400/[0.12] mix-blend-multiply blur-[120px] dark:bg-indigo-500/[0.15] dark:mix-blend-screen"></div>
      <div class="animate-blob animation-delay-4000 absolute -bottom-[10%] right-[-10%] h-[45vw] w-[45vw] rounded-full bg-indigo-300/[0.15] mix-blend-multiply blur-[100px] dark:bg-fuchsia-500/[0.12] dark:mix-blend-screen"></div>
      <div class="animate-blob animation-delay-2000 absolute left-[15%] top-[25%] h-[35vw] w-[35vw] rounded-full bg-cyan-200/[0.12] mix-blend-multiply blur-[110px] dark:bg-blue-500/[0.10] dark:mix-blend-screen"></div>
    </div>

    <!-- ================== PC端：左侧边栏导航 ================== -->
    <aside class="hidden w-64 flex-col justify-between border-r border-slate-200 bg-white md:flex dark:border-white/5 dark:bg-[#0A0A0F]/80 z-20">
      <div>
        <!-- Logo 标题区 -->
        <div class="flex h-20 items-center gap-2 border-b border-slate-100 px-4 dark:border-white/5">
          <button @click="navigateToHome" class="flex flex-1 min-w-0 items-center gap-3 rounded-xl px-2 py-1.5 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors" title="返回介绍页">
            <div class="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/30 dark:shadow-indigo-500/20">
              <img src="/logo.svg" class="w-6 h-6 brightness-0 invert relative z-10" alt="logo" />
              <div class="absolute inset-0 animate-pulse rounded-xl bg-blue-400/20 blur-md"></div>
            </div>
            <span class="text-xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-blue-700 to-indigo-700 dark:from-white dark:to-indigo-200">
              智卷系统
            </span>
          </button>
          <button
            @click="(e) => toggleTheme(e.currentTarget)"
            class="hidden"
            title="切换主题"
          >
            <i class="fa-solid fa-sun text-[18px] hidden dark:block"></i>
            <i class="fa-solid fa-moon text-[18px] block dark:hidden"></i>
          </button>
        </div>

        <!-- 视图切换菜单 -->
        <nav class="mt-6 flex flex-col gap-1.5 px-4 relative">
          <div class="mb-2 px-3 text-xs font-bold uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500">核心功能</div>

          <!-- 悬浮指示器背景 -->
          <div
            class="absolute left-4 right-4 z-0 rounded-xl bg-blue-600 shadow-lg shadow-blue-600/20 transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] dark:bg-indigo-500 dark:shadow-indigo-500/20"
            :style="navIndicatorStyle"
          ></div>

          <!-- 激活指示小圆点 -->
          <div
            class="absolute right-6 z-20 h-1.5 w-1.5 rounded-full bg-white/80 transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] pointer-events-none"
            :style="{
              opacity: navIndicatorStyle.opacity,
              transform: `translateY(calc(${navIndicatorStyle.transform.match(/translateY\(([^)]+)\)/)[1]} + 25.25px))`,
            }"
          ></div>

          <button
            v-for="item in NAV_ITEMS"
            :key="item.id"
            @click="currentView = (item.id === 'workspace' ? lastWorkspaceView : item.id)"
            class="group relative z-10 flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold transition-all duration-200"
            :class="item.match(currentView)
              ? 'text-white'
              : 'text-slate-600 hover:bg-slate-100/50 hover:text-blue-600 dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-indigo-300'"
          >
            <i class="w-5 text-center text-lg transition-transform group-hover:scale-110" :class="[item.icon, 'fa-solid']"></i>
            <span>{{ item.label }}</span>
          </button>

          <button
            disabled
            class="group relative flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold cursor-not-allowed opacity-40 text-slate-400 dark:text-slate-600"
          >
            <i class="fa-solid fa-clock-rotate-left w-5 text-center text-lg"></i>
            <span>刷题</span>
          </button>
        </nav>
      </div>

      <!-- 底部控制与返回栏 -->
      <div class="space-y-1.5 border-t border-slate-100 p-4 dark:border-white/5">
        <!-- 用户信息 -->
        <div class="flex items-center gap-2 rounded-2xl px-3 py-2 mb-2 bg-white/70 backdrop-blur-xl border border-slate-200/60 dark:bg-white/[0.06] dark:backdrop-blur-xl dark:border-white/10">
          <div class="h-8 w-8 shrink-0 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 dark:from-indigo-400 dark:to-indigo-600 flex items-center justify-center text-white text-sm font-extrabold shadow-sm">
            {{ currentUser?.username?.[0]?.toUpperCase() ?? '?' }}
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-slate-700 dark:text-slate-200 truncate leading-tight">{{ currentUser?.username }}</p>
            <p class="text-xs text-slate-400 dark:text-slate-500 truncate leading-tight">{{ currentUser?.email }}</p>
          </div>
          <button
            @click="handleLogout"
            title="退出登录"
            class="shrink-0 h-7 w-7 flex items-center justify-center rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-50/80 dark:hover:bg-rose-500/10 transition-all"
          >
            <i class="fas fa-right-from-bracket text-sm"></i>
          </button>
        </div>

        <button
          @click="currentView = 'settings'"
          class="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-all duration-200"
          :class="currentView === 'settings' ? 'bg-white/70 backdrop-blur-xl border border-blue-200/60 text-blue-600 shadow-sm dark:bg-white/10 dark:backdrop-blur-xl dark:border-indigo-500/30 dark:text-indigo-300 dark:shadow-[0_0_15px_rgba(99,102,241,0.15)]' : 'text-slate-600 hover:bg-white/60 hover:backdrop-blur-xl hover:text-blue-600 dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-indigo-300'"
        >
          <i class="fa-solid fa-gear w-5 text-center text-lg"></i>
          系统设置
        </button>

      </div>
    </aside>

    <!-- ================== 移动端：底部 Tab 导航栏 ================== -->
    <nav class="fixed bottom-0 left-0 right-0 z-50 border-t border-slate-200 bg-white/90 pb-2 pt-2 backdrop-blur-xl md:hidden dark:border-white/10 dark:bg-[#0A0A0F]/90">
      <div class="flex justify-around">
        <button @click="currentView = lastWorkspaceView" class="flex flex-col items-center p-2" :class="WORKSPACE_VIEWS.has(currentView) ? 'text-blue-600 dark:text-indigo-400' : 'text-slate-500 dark:text-slate-400'">
          <i class="fa-solid fa-file-arrow-up text-lg"></i>
          <span class="mt-1 text-xs font-bold">录题</span>
        </button>
        <button @click="currentView = 'notes'" class="flex flex-col items-center p-2" :class="currentView === 'notes' ? 'text-blue-600 dark:text-indigo-400' : 'text-slate-500 dark:text-slate-400'">
          <i class="fa-solid fa-book-open text-lg"></i>
          <span class="mt-1 text-xs font-bold">笔记库</span>
        </button>
        <button @click="currentView = 'dashboard'" class="flex flex-col items-center p-2" :class="currentView === 'dashboard' ? 'text-blue-600 dark:text-indigo-400' : 'text-slate-500 dark:text-slate-400'">
          <i class="fa-solid fa-chart-pie text-lg"></i>
          <span class="mt-1 text-xs font-bold">数据面板</span>
        </button>
        <button @click="currentView = 'error-bank'" class="flex flex-col items-center p-2" :class="currentView === 'error-bank' ? 'text-blue-600 dark:text-indigo-400' : 'text-slate-500 dark:text-slate-400'">
          <i class="fa-solid fa-layer-group text-lg"></i>
          <span class="mt-1 text-xs font-bold">错题本</span>
        </button>
        <button @click="currentView = 'settings'" class="flex flex-col items-center p-2" :class="currentView === 'settings' ? 'text-blue-600 dark:text-indigo-400' : 'text-slate-500 dark:text-slate-400'">
          <i class="fa-solid fa-sliders text-lg"></i>
          <span class="mt-1 text-xs font-bold">设置</span>
        </button>
        <button @click="(e) => toggleTheme(e.currentTarget)" class="hidden">
          <i class="fa-solid mb-1 text-xl" :class="theme === 'dark' ? 'fa-sun text-indigo-400' : 'fa-moon'"></i>
          <span class="text-xs font-bold">主题</span>
        </button>
      </div>
    </nav>

    <!-- ================== 右侧主内容区 ================== -->
    <main class="relative z-10 flex-1 overflow-hidden pb-20 md:pb-0">

      <Transition name="view-fade" mode="out-in">
        <!-- 视图 1：录题工作台（分两页：上传解析页 / 题目核对页） -->
        <div v-if="currentView === 'workspace' || currentView === 'workspace_review'" key="workspace" class="relative h-full flex flex-col overflow-hidden">
          <div class="container relative z-10 mx-auto flex h-full min-h-0 max-w-6xl flex-col px-4 py-4 sm:px-8 sm:py-6">
            <Transition name="flip" mode="out-in">
              <!-- 第一页：录题与分析 -->
              <div v-if="currentView === 'workspace'" key="upload" class="flex flex-1 flex-col min-h-0">
                <div class="mb-4 flex flex-col items-start gap-2 pl-2 sm:pl-0 md:flex-row md:items-center md:justify-between shrink-0">
                  <div>
                    <h2 class="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl dark:text-white">
                      智能录入与分析
                    </h2>
                    <div class="mt-2 flex items-center">
                      <div class="relative flex items-center gap-2 py-1 text-xs font-black tracking-widest text-blue-600/80 dark:text-indigo-300/80">
                        <div class="relative flex h-4 w-4 items-center justify-center">
                          <i class="fa-solid fa-bolt-lightning absolute animate-pulse text-xs text-indigo-500 dark:text-indigo-400"></i>
                          <div class="absolute h-full w-full animate-ping rounded-full bg-indigo-400/10 dark:bg-indigo-400/10"></div>
                        </div>

                        <span class="relative z-10 uppercase pb-0.5">
                          新一代 AI 错题处理架构 <span class="ml-1 font-extrabold text-blue-600 dark:text-indigo-300">V2.0</span>
                        </span>
                      </div>
                    </div>
                  </div>
                  <GlassButton icon="fa-clock-rotate-left" @click="currentView = 'split-history'">
                    分割历史
                  </GlassButton>
                </div>

                <div class="main-content relative flex flex-1 flex-col min-h-0 bg-transparent">
                  <StatusBar
                    class="border-b border-slate-200/60 pb-6 dark:border-white/5"
                    :status-loading="statusLoading"
                    :status-error="statusError"
                    :status-pills="statusPills"
                    :provider-options="providerOptions"
                    :selected-model="selectedModel"
                    :disabled="splitting || splitCompleted"
                    :no-models="!hasConfiguredModel"
                    @update:selected-model="(v) => selectedModel = v"
                  />

                  <!-- 功能开关 -->
                  <div class="flex items-center gap-4 border-b border-slate-200/60 py-4 dark:border-white/5">
                    <label class="flex cursor-pointer items-center gap-2" @click="eraseEnabled = !eraseEnabled">
                      <div class="relative h-6 w-10 rounded-full transition-colors" :class="eraseEnabled ? 'bg-indigo-500' : 'bg-slate-300 dark:bg-slate-600'">
                        <div class="absolute top-1 h-4 w-4 rounded-full bg-white shadow-sm transition-transform" :class="eraseEnabled ? 'translate-x-5' : 'translate-x-1'"></div>
                      </div>
                      <span class="text-sm font-bold text-slate-700 dark:text-slate-300">擦除手写字迹</span>
                      <span class="text-xs text-slate-400 dark:text-slate-500">上传后自动擦除图片中的手写笔迹</span>
                    </label>
                  </div>

                  <div class="flex-1 overflow-y-auto pr-2 custom-scrollbar flex flex-col space-y-8 py-6">
                    <!-- 模式切换：试卷 / 笔记 -->
                    <div class="flex items-center gap-2 rounded-xl border border-slate-200/60 bg-white/60 p-1 backdrop-blur-xl dark:border-white/10 dark:bg-white/[0.03]">
                      <button
                        @click="uploadMode = 'exam'"
                        class="flex-1 h-9 rounded-lg text-sm font-bold transition-all"
                        :class="uploadMode === 'exam' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'"
                      >
                        <i class="fa-solid fa-file-lines mr-2"></i>试卷分割
                      </button>
                      <button
                        @click="uploadMode = 'note'"
                        class="flex-1 h-9 rounded-lg text-sm font-bold transition-all"
                        :class="uploadMode === 'note' ? 'bg-emerald-500 text-white shadow-sm' : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'"
                      >
                        <i class="fa-solid fa-book-open mr-2"></i>笔记整理
                      </button>
                    </div>

                    <StepIndicator :step="step" class="border-b border-slate-200/60 pb-8 dark:border-white/5" />

                    <FileList
                      :pending-files="pendingFiles"
                      :file-progress="fileProgress"
                      :waiting-keys="waitingKeys"
                      :upload-busy="uploadBusy"
                      :upload-ready="uploadReady"
                      :splitting="splitting"
                      :split-completed="splitCompleted"
                      @remove-file="removePendingFile"
                    />

                    <FileUploader
                      class="transition-all duration-500"
                      :class="questions.length === 0 ? 'flex-1' : 'border-b border-slate-200/60 pb-8 dark:border-white/5'"
                      :pending-files="pendingFiles"
                      :file-progress="fileProgress"
                      :waiting-keys="waitingKeys"
                      :upload-busy="uploadBusy"
                      :upload-ready="uploadReady"
                      :splitting="splitting"
                      :split-completed="splitCompleted"
                      :expand="questions.length === 0"
                      :disabled="!hasConfiguredModel"
                      @upload="enqueueUpload"
                      @remove-file="removePendingFile"
                    />
                  </div>

                  <ActionBar
                    class="shrink-0 border-t border-slate-200/60 pt-6 dark:border-white/5"
                    :split-enabled="splitEnabled"
                    :export-enabled="false"
                    :splitting="splitting"
                    :split-completed="splitCompleted"
                    :upload-mode="uploadMode"
                    @split="doSplit"
                  />

                </div>
              </div>

              <!-- 第二页：解析结果核对 -->
              <div v-else-if="currentView === 'workspace_review'" key="review" class="flex flex-1 flex-col overflow-hidden">
                <div class="mb-4 flex items-center justify-between pl-2 sm:pl-0 shrink-0">
                  <div class="flex items-center gap-4">
                    <button
                      @click="() => { doReset(); currentView = 'workspace' }"
                      class="group flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/60 bg-white/60 text-slate-500 backdrop-blur-md transition-all hover:border-blue-500/50 hover:bg-white hover:text-blue-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-400 dark:hover:border-indigo-500/50 dark:hover:text-indigo-300"
                    >
                      <i class="fa-solid fa-arrow-left-long transition-transform group-hover:-translate-x-1"></i>
                    </button>
                    <div>
                      <h2 class="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl dark:text-white">
                        题目数据核对
                      </h2>
                      <p class="text-xs font-bold text-slate-400 dark:text-slate-500 mt-1">请确认解析结果的准确性并进行导出或存档</p>
                    </div>
                  </div>
                </div>

                <div class="flex-1 overflow-y-auto pr-2 custom-scrollbar py-2 pb-24">
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
                </div>

              </div>
            </Transition>

          </div>
        </div>

        <!-- 视图 2：待复习 -->
        <div v-else-if="currentView === 'review'" key="review_view" class="h-full">
          <ReviewView
            :theme="theme"
            :visible="currentView === 'review'"
            @go-workspace="currentView = 'workspace'"
            @push-toast="pushToast"
            @open-image="openModal"
            @start-chat="openChat"
          />
        </div>

        <!-- 视图 3：数据面板 -->
        <div v-else-if="currentView === 'dashboard'" key="dashboard_view" class="h-full">
          <Dashboard
            :theme="theme"
            :visible="currentView === 'dashboard'"
            @go-workspace="currentView = 'workspace'"
            @push-toast="pushToast"
          />
        </div>

        <!-- 视图 4：错题库 -->
        <div v-else-if="currentView === 'error-bank'" key="error_bank_view" class="h-full">
          <ErrorBank
            ref="errorBankRef"
            :theme="theme"
            :visible="currentView === 'error-bank'"
            @go-workspace="currentView = 'workspace'"
            @push-toast="pushToast"
            @open-image="openModal"
            @start-chat="openChat"
          />
        </div>

        <!-- 视图 5：分割历史 -->
        <div v-else-if="currentView === 'split-history'" key="split_history_view" class="h-full">
          <SplitHistory
            :theme="theme"
            :visible="currentView === 'split-history'"
            @push-toast="pushToast"
            @open-image="openModal"
            @load-record="handleLoadRecord"
            @go-workspace="currentView = splitCompleted ? 'workspace_review' : 'workspace'"
          />
        </div>

        <!-- 视图 6：系统设置 -->
        <div v-else-if="currentView === 'settings'" key="settings_view" class="h-full">
          <SettingsView
            :visible="currentView === 'settings'"
            @saved="doFetchStatus"
          />
        </div>

        <!-- 视图 7：AI 辅导对话 -->
        <div v-else-if="currentView === 'chat'" key="chat_view" class="h-full">
          <ChatView
            v-if="chatActive"
            :session-id="chatSessionId"
            :question="chatQuestion"
            :model-provider="selectedProvider"
            :model-name="selectedModel"
            :username="currentUser?.username"
            @back="backToErrorBank"
          />
        </div>

        <!-- 视图 8：笔记 -->
        <div v-else-if="currentView === 'notes'" key="notes_view" class="h-full">
          <NoteView
            :visible="currentView === 'notes'"
            :model-provider="selectedProvider"
            :model-name="selectedModel"
            :theme="theme"
            @push-toast="pushToast"
          />
        </div>
      </Transition>

      <!-- workspace_review 浮动选择面板 -->
      <SelectionPanel
        :visible="currentView === 'workspace_review'"
        :count="selectedIds.size"
        export-label="导出错题本"
        :show-save="true"
        @export="doExport"
        @save="doSaveToDb"
        @clear="deselectAll"
      />

      <!-- AI 分割任务全局遮罩：置于 main 顶层，仅在录题视图且正在分割时显示 -->
      <SplitLoading v-if="splitting && (currentView === 'workspace' || currentView === 'workspace_review')" />
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

<style>
/* 自定义背景光晕动画 - 极致性能优化版 */
@keyframes blob {
  0% { transform: translate3d(0, 0, 0) scale(1); }
  33% { transform: translate3d(80px, -120px, 0) scale(1.15); }
  66% { transform: translate3d(-60px, 60px, 0) scale(0.9); }
  100% { transform: translate3d(0, 0, 0) scale(1); }
}

.animate-blob {
  animation: blob 30s infinite alternate ease-in-out;
  will-change: transform;
}

.animation-delay-2000 {
  animation-delay: 2s;
}

.animation-delay-4000 {
  animation-delay: 4s;
}

::view-transition-old(root),
::view-transition-new(root) {
  animation: none;
  mix-blend-mode: normal;
}


.ws-loading-fade-leave-active { transition: opacity 0.4s ease; }
.ws-loading-fade-leave-to { opacity: 0; }

.ws-loading-bar {
  animation: wsLoadProgress 2s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
@keyframes wsLoadProgress {
  from { width: 0%; }
  to   { width: 100%; }
}

/* 视图切换：极简淡入淡出 (Simple Fade) */
.view-fade-enter-active,
.view-fade-leave-active {
  transition: opacity 0.3s ease;
}

.view-fade-enter-from,
.view-fade-leave-to {
  opacity: 0;
}

/* 工作台内部页面切换：左右滑动淡入 (Flip) */
.flip-enter-active,
.flip-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.flip-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.flip-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

</style>
