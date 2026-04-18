<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount, watch } from 'vue'
import { fetchMessages, streamChat } from '@/api.js'
import { getQuestionSnippet, renderMarkdown, typesetMath } from '@/utils.js'
import { useToast } from '@/composables/useToast.js'
import { useSystemStatus } from '@/composables/useSystemStatus.js'
import { useAuth } from '@/composables/useAuth.js'
import { useChatSession } from '@/composables/useChatSession.js'
import ContentPanel from '@/components/workspace/ContentPanel.vue'

const PAGE_SIZE = 30

const QUOTA_EXCEEDED_CODE = 'DAILY_FREE_QUOTA_EXCEEDED'

const { pushToast } = useToast()
const { selectedProvider, selectedModel } = useSystemStatus()
const { currentUser, setQuotaSnapshot, refreshCurrentUser } = useAuth()
const { chatSessionId, chatQuestion, backToErrorBank } = useChatSession()

const sessionId = computed(() => chatSessionId.value)
const question = computed(() => chatQuestion.value)
const modelProvider = computed(() => selectedProvider.value)
const modelName = computed(() => selectedModel.value)
const username = computed(() => currentUser.value?.username || '')

const toMsg = (m) => ({ id: m.id, role: m.role, content: m.content })

const messages = ref([])
const inputText = ref('')
const streaming = ref(false)
const listEl = ref(null)
const snippetEl = ref(null)
const hasMore = ref(false)
const loadingMore = ref(false)

const snippet = computed(() => getQuestionSnippet(question.value, 0, '未知题目'))

let abortCtrl = null
let scrollRafId = null
const mdCache = new Map()
const cachedRenderMarkdown = (text) => {
  if (!mdCache.has(text)) mdCache.set(text, renderMarkdown(text))
  return mdCache.get(text)
}
const scrollToBottom = async () => {
  await nextTick()
  if (scrollRafId) return
  scrollRafId = requestAnimationFrame(() => {
    scrollRafId = null
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
  })
}

const loadHistory = async () => {
  if (!sessionId.value) return
  try {
    const data = await fetchMessages(sessionId.value, { limit: PAGE_SIZE })
    messages.value = data.messages.map(toMsg)
    hasMore.value = data.hasMore
    scrollToBottom()
    await nextTick()
    await typesetMath(listEl.value)
  } catch (e) {
    pushToast('error', '加载对话历史失败')
  }
}

const loadOlder = async () => {
  if (!hasMore.value || loadingMore.value || !sessionId.value) return
  const firstMsg = messages.value[0]
  if (!firstMsg || !firstMsg.id) return

  loadingMore.value = true
  try {
    // 记录加载前滚动位置以保持视觉锚点
    const el = listEl.value
    const prevHeight = el ? el.scrollHeight : 0

    const data = await fetchMessages(sessionId.value, {
      limit: PAGE_SIZE,
      beforeId: firstMsg.id,
    })

    const older = data.messages.map(toMsg)
    messages.value = [...older, ...messages.value]
    hasMore.value = data.hasMore

    // 恢复滚动位置：新内容插入顶部后，保持用户视野不跳动
    await nextTick()
    if (el) {
      el.scrollTop = el.scrollHeight - prevHeight
    }
    await typesetMath(listEl.value)
  } catch (e) {
    pushToast('error', '加载更早消息失败')
  }
  loadingMore.value = false
}

let scrollCheckRaf = null
const onScroll = () => {
  if (scrollCheckRaf) return
  scrollCheckRaf = requestAnimationFrame(() => {
    scrollCheckRaf = null
    const el = listEl.value
    if (!el || loadingMore.value || !hasMore.value) return
    if (el.scrollTop < 80) loadOlder()
  })
}

const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text || streaming.value || !sessionId.value) return

  inputText.value = ''
  const rollbackIndex = messages.value.length
  messages.value.push({ role: 'user', content: text })
  messages.value.push({ role: 'assistant', content: '' })
  streaming.value = true
  scrollToBottom()

  abortCtrl = new AbortController()
  try {
    const resp = await streamChat(sessionId.value, text, modelProvider.value, abortCtrl.signal, modelName.value)
    if (!resp.ok) {
      const err = await resp.json().catch(() => null)
      const error = new Error((err && err.error) || `HTTP ${resp.status}`)
      error.status = resp.status
      error.code = err?.code || null
      error.quota = err?.quota || null
      throw error
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    const assistantIdx = messages.value.length - 1

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const payload = JSON.parse(line.slice(6))
          if (payload.token) {
            messages.value[assistantIdx].content += payload.token
            scrollToBottom()
          }
          if (payload.error) {
            messages.value[assistantIdx].content += `\n\n⚠️ 错误: ${payload.error}`
          }
        } catch (_) {}
      }
    }
    await refreshCurrentUser()
  } catch (e) {
    if (e?.code === QUOTA_EXCEEDED_CODE) {
      messages.value.splice(rollbackIndex, 2)
      if (e.quota) setQuotaSnapshot(e.quota)
      pushToast('error', e.message || '今日免费体验次数已用完')
    } else {
      const last = messages.value[messages.value.length - 1]
      if (last && last.role === 'assistant' && !last.content) {
        last.content = `⚠️ 请求失败: ${e.message}`
      }
    }
  } finally {
    streaming.value = false
    scrollToBottom()
    await nextTick()
    await typesetMath(listEl.value)
  }
}


const onKeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

onMounted(async () => {
  await loadHistory()
  await nextTick()
  typesetMath(snippetEl.value)
})
watch(sessionId, () => {
  abortCtrl?.abort()
  mdCache.clear()
  loadHistory()
})
watch(snippet, async () => {
  await nextTick()
  typesetMath(snippetEl.value)
})
onBeforeUnmount(() => {
  abortCtrl?.abort()
  if (scrollRafId) { cancelAnimationFrame(scrollRafId); scrollRafId = null }
  if (scrollCheckRaf) { cancelAnimationFrame(scrollCheckRaf); scrollCheckRaf = null }
})
</script>

<template>
  <ContentPanel title="AI 辅导">
  <div class="flex h-full flex-col">
    <!-- 顶栏 -->
    <div
      class="flex shrink-0 items-center gap-3 border-b border-slate-200/60 bg-white/70 px-5 py-4 dark:border-white/10 dark:bg-[#0A0A0F]/60"
    >
      <button
        @click="backToErrorBank()"
        class="flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-white"
      >
        <i class="fa-solid fa-arrow-left"></i>
      </button>

      <div class="min-w-0 flex-1">
        <p ref="snippetEl" class="truncate text-sm font-bold text-slate-800 dark:text-slate-200"
           v-html="snippet"></p>
        <div class="mt-0.5 flex items-center gap-2">
          <span
            v-if="question?.subject"
            class="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-700 dark:bg-blue-500/10 dark:text-blue-400"
          >
            {{ question.subject }}
          </span>
          <span
            v-for="tag in (question?.knowledge_tags || []).slice(0, 3)"
            :key="tag"
            class="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600 dark:bg-white/5 dark:text-slate-400"
          >
            {{ tag }}
          </span>
        </div>
      </div>
    </div>

    <!-- 消息列表 -->
    <div ref="listEl" class="flex-1 overflow-y-auto px-4 py-6 sm:px-6" @scroll="onScroll">
      <!-- 加载更早消息提示 -->
      <div v-if="loadingMore" class="mb-4 flex items-center justify-center">
        <i class="fa-solid fa-circle-notch fa-spin mr-2 text-blue-500"></i>
        <span class="text-xs text-slate-500 dark:text-slate-400">加载更早的消息…</span>
      </div>
      <div
        v-else-if="hasMore"
        class="mb-4 flex items-center justify-center"
      >
        <button
          @click="loadOlder"
          class="rounded-lg border border-slate-200/60 px-3 py-1.5 text-xs font-semibold text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-700 dark:border-white/10 dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-slate-300"
        >
          <i class="fa-solid fa-arrow-up mr-1"></i>加载更早的消息
        </button>
      </div>

      <!-- 空状态 -->
      <div
        v-if="!messages.length && !streaming"
        class="flex h-full flex-col items-center justify-center text-center"
      >
        <div
          class="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50 dark:bg-blue-500/10"
        >
          <i class="fa-solid fa-chalkboard-user text-2xl text-blue-500 dark:text-blue-400"></i>
        </div>
        <h3 class="text-lg font-bold text-slate-800 dark:text-slate-200">向 AI 老师提问吧</h3>
        <p class="mt-2 max-w-sm text-sm text-slate-500 dark:text-slate-400">
          你可以问这道题的解题思路、知识点，或者你不理解的步骤。AI 老师会一步步引导你理解。
        </p>
      </div>

      <!-- 消息气泡 -->
      <div v-else class="mx-auto max-w-3xl space-y-5">
        <div
          v-for="(msg, i) in messages"
          :key="msg.id || `tmp-${i}`"
          class="flex"
          :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <!-- assistant 头像 -->
          <div
            v-if="msg.role === 'assistant'"
            class="mr-3 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-xs text-white shadow-md"
          >
            <i class="fa-solid fa-graduation-cap"></i>
          </div>

          <div
            class="max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm"
            :class="
              msg.role === 'user'
                ? 'bg-blue-600 text-white dark:bg-indigo-500'
                : 'border border-slate-200/60 bg-white text-slate-800 dark:border-white/10 dark:bg-slate-800/80 dark:text-slate-200'
            "
          >
            <div v-if="msg.role === 'assistant'" class="chat-content whitespace-pre-wrap" v-html="cachedRenderMarkdown(msg.content)"></div>
            <div v-else class="whitespace-pre-wrap">{{ msg.content }}</div>

            <!-- 流式加载指示器 -->
            <span
              v-if="msg.role === 'assistant' && streaming && i === messages.length - 1 && !msg.content"
              class="inline-flex items-center gap-1 text-slate-400"
            >
              <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-500 [animation-delay:-0.3s]"></span>
              <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-500 [animation-delay:-0.15s]"></span>
              <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-500"></span>
            </span>
          </div>

          <!-- user 头像 -->
          <div
            v-if="msg.role === 'user'"
            class="ml-3 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 dark:from-indigo-400 dark:to-indigo-600 text-xs font-extrabold text-white shadow-sm"
          >
            {{ username?.[0]?.toUpperCase() ?? '?' }}
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div
      class="shrink-0 border-t border-slate-200/60 bg-white/70 px-4 py-4 dark:border-white/10 dark:bg-[#0A0A0F]/60 sm:px-6"
    >
      <div class="mx-auto flex max-w-3xl items-end gap-3">
        <textarea
          v-model="inputText"
          @keydown="onKeydown"
          :disabled="streaming"
          rows="1"
          placeholder="输入你的问题…（Enter 发送，Shift+Enter 换行）"
          class="flex-1 resize-none rounded-xl border border-slate-200/80 bg-white px-4 py-3 text-sm text-slate-800 placeholder-slate-400 shadow-sm transition-colors focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50 dark:border-white/10 dark:bg-slate-800/80 dark:text-slate-200 dark:placeholder-slate-500 dark:focus:border-indigo-500/50"
        ></textarea>
        <button
          @click="sendMessage"
          :disabled="streaming || !inputText.trim()"
          class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white shadow-md transition-all hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-indigo-500 dark:hover:bg-indigo-600"
        >
          <i class="fa-solid" :class="streaming ? 'fa-circle-notch fa-spin' : 'fa-paper-plane'"></i>
        </button>
      </div>
    </div>
  </div>
  </ContentPanel>
</template>
