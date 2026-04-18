/**
 * useChatSession.js
 * AI 辅导对话会话管理（题目绑定对话）— 单例 composable
 */
import { ref } from 'vue'
import * as api from '@/api.js'
import { useToast } from '@/composables/useToast.js'
import { useWorkspaceNav } from '@/composables/useWorkspaceNav.js'

// ── 模块级单例状态 ──────────────────────────────────────
const chatSessionId = ref(null)
const chatQuestion = ref(null)
const chatActive = ref(false)
const answerModalOpen = ref(false)
const answerModalTarget = ref(null)
const answerModalText = ref('')
const answerModalSaving = ref(false)

export function useChatSession() {
  const { pushToast } = useToast()
  const { currentView } = useWorkspaceNav()

  const doOpenChatSession = async (question) => {
    try {
      const sessions = await api.fetchChatSessions(question.id)
      chatSessionId.value = sessions.length ? sessions[0].id : (await api.createChat(question.id)).id
      chatActive.value = true
      currentView.value = 'chat'
    } catch (e) {
      pushToast('error', '打开对话失败: ' + (e instanceof Error ? e.message : String(e)))
    }
  }

  const openChat = async (question) => {
    chatQuestion.value = question
    if (!question.answer) {
      answerModalTarget.value = question
      answerModalText.value = ''
      answerModalOpen.value = true
      return
    }
    await doOpenChatSession(question)
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

  return {
    chatSessionId, chatQuestion, chatActive,
    answerModalOpen, answerModalTarget, answerModalText, answerModalSaving,
    openChat, saveAnswerAndChat, backToErrorBank,
  }
}
