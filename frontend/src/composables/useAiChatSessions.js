import { ref, nextTick, watch } from 'vue'
import * as api from '@/api.js'
import { useRoute, useRouter } from 'vue-router'

// 模块单例：确保 Sidebar / AppLayout / ChatPageView 共享同一份会话状态
const aiChatSessions = ref([])
const activeAiChatId = ref(null)
const chatMenuOpenId = ref(null)
const renamingChatId = ref(null)
const renameText = ref('')

let pushToastFn = null
let routerRef = null
let routeRef = null
let routeSyncInitialized = false

const toast = (type, message) => {
  if (typeof pushToastFn === 'function') pushToastFn(type, message)
}

export function useAiChatSessions(pushToast) {
  if (pushToast) pushToastFn = pushToast
  if (!routerRef) routerRef = useRouter()
  if (!routeRef) routeRef = useRoute()

  if (!routeSyncInitialized) {
    routeSyncInitialized = true

    // URL -> 状态：支持直接访问 /app/ai-chat/:sessionId
    watch(
      () => [routeRef.params.view, routeRef.params.subview],
      ([view, sub]) => {
        if (view !== 'ai-chat') return
        const id = sub ? String(sub) : null
        const cur = activeAiChatId.value != null ? String(activeAiChatId.value) : null
        if (id && id !== cur) activeAiChatId.value = id
        if (!id && cur) routerRef.replace(`/app/ai-chat/${cur}`)
      },
      { immediate: true }
    )

    // 状态 -> URL：侧边栏切换会话时更新地址
    watch(activeAiChatId, (id) => {
      if (routeRef.params.view !== 'ai-chat') return
      const next = id != null ? String(id) : null
      const cur = routeRef.params.subview ? String(routeRef.params.subview) : null
      if (!next && cur) routerRef.replace('/app/ai-chat')
      if (next && cur !== next) routerRef.replace(`/app/ai-chat/${next}`)
    })
  }

  async function loadAiChatSessions() {
    try {
      const data = await api.fetchMyChatSessions({ limit: 50 })
      aiChatSessions.value = data.sessions || []
    } catch (_) {}
  }

  async function createAiChat(currentView) {
    try {
      const session = await api.createIndependentChat('新对话')
      aiChatSessions.value.unshift(session)
      activeAiChatId.value = session.id
      if (currentView.value !== 'ai-chat') currentView.value = 'ai-chat'
    } catch (e) {
      toast('error', e.message)
    }
  }

  function selectAiChat(s, currentView) {
    activeAiChatId.value = s.id
    if (currentView.value !== 'ai-chat') currentView.value = 'ai-chat'
  }

  async function onAiChatTitleUpdated(sessionId, title) {
    const s = aiChatSessions.value.find(s => s.id === sessionId)
    if (s && s.title === '新对话') {
      s.title = title
      try { await api.updateChatTitle(sessionId, title) } catch (_) {}
    }
  }

  function toggleChatMenu(id) {
    chatMenuOpenId.value = chatMenuOpenId.value === id ? null : id
  }

  function closeChatMenu() {
    chatMenuOpenId.value = null
  }

  async function startRenameChat(s) {
    chatMenuOpenId.value = null
    renamingChatId.value = s.id
    renameText.value = s.title
    await nextTick()
    const input = document.querySelector('input[data-rename-input]')
    if (input) { input.focus(); input.selectionStart = input.selectionEnd = input.value.length }
  }

  async function confirmRenameChat(s) {
    const title = renameText.value.trim()
    if (title && title !== s.title) {
      try {
        await api.updateChatTitle(s.id, title)
        s.title = title
      } catch (e) {
        toast('error', e.message)
      }
    }
    renamingChatId.value = null
  }

  async function deleteAiChat(id) {
    try {
      await api.deleteChat(id)
      aiChatSessions.value = aiChatSessions.value.filter(s => s.id !== id)
      if (activeAiChatId.value === id) activeAiChatId.value = null
    } catch (e) {
      toast('error', e.message)
    }
  }

  return {
    aiChatSessions, activeAiChatId,
    chatMenuOpenId, renamingChatId, renameText,
    loadAiChatSessions, createAiChat, selectAiChat,
    onAiChatTitleUpdated, toggleChatMenu, closeChatMenu,
    startRenameChat, confirmRenameChat, deleteAiChat,
  }
}
