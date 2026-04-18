<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import * as api from '@/api.js'
import { renderMarkdown, typesetMath } from '@/utils.js'
import ContentPanel from '@/components/workspace/ContentPanel.vue'
import { useToast } from '@/composables/useToast.js'
import { useSystemStatus } from '@/composables/useSystemStatus.js'
import { useAuth } from '@/composables/useAuth.js'
import { useAiChatSessions } from '@/composables/useAiChatSessions.js'
import { useWorkspaceNav } from '@/composables/useWorkspaceNav.js'

const QUOTA_EXCEEDED_CODE = 'DAILY_FREE_QUOTA_EXCEEDED'

const { pushToast } = useToast()
const { selectedProvider, selectedModel } = useSystemStatus()
const { currentUser, setQuotaSnapshot, refreshCurrentUser } = useAuth()
const { activeAiChatId, createAiChat, onAiChatTitleUpdated } = useAiChatSessions(pushToast)
const { currentView } = useWorkspaceNav()

const sessionId = computed(() => activeAiChatId.value)
const modelProvider = computed(() => selectedProvider.value)
const modelName = computed(() => selectedModel.value)
const username = computed(() => currentUser.value?.username || '')

// ---- 对话消息 ----
const messages = ref([])
const inputText = ref('')
const streaming = ref(false)
const messagesContainer = ref(null)
const deepThink = ref(false)

watch(sessionId, (id) => {
  if (id) loadMessages()
  else messages.value = []
}, { immediate: true })

async function loadMessages() {
  if (!sessionId.value) return
  try {
    const result = await api.fetchMessages(sessionId.value, { limit: 50 })
    messages.value = result.messages || []
    await nextTick()
    scrollToBottom()
    if (messagesContainer.value) typesetMath(messagesContainer.value)
  } catch (e) {
    pushToast('error', e.message)
  }
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || !sessionId.value || streaming.value) return

  inputText.value = ''
  const rollbackIndex = messages.value.length
  // 消息结构：{ role, content, reasoning?, reasoningOpen? }
  messages.value.push({ role: 'user', content: text })
  messages.value.push({ role: 'assistant', content: '', reasoning: '', reasoningOpen: false })
  await nextTick()
  scrollToBottom()
  // 重置 textarea 高度
  if (textareaRef.value) textareaRef.value.style.height = 'auto'

  streaming.value = true
  const useDeepThink = deepThink.value

  try {
    const resp = await api.streamChat(
      sessionId.value,
      text,
      modelProvider.value,
      null,
      modelName.value,
      { deepThink: useDeepThink },
    )

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
    const lastMsg = () => messages.value[messages.value.length - 1]

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const payload = JSON.parse(line.slice(6))
          if (payload.reasoning) {
            lastMsg().reasoning += payload.reasoning
            lastMsg().reasoningOpen = true
            await nextTick()
            scrollToBottom()
          }
          if (payload.token) {
            if (lastMsg().reasoningOpen && lastMsg().reasoning) {
              lastMsg().reasoningOpen = false
            }
            lastMsg().content += payload.token
            await nextTick()
            scrollToBottom()
          }
          if (payload.done) {
            const firstMsg = text.slice(0, 20) + (text.length > 20 ? '...' : '')
            onAiChatTitleUpdated(sessionId.value, firstMsg)
          }
          if (payload.error) {
            lastMsg().content += `\n\n⚠️ ${payload.error}`
          }
        } catch (_) {}
      }
    }

    await refreshCurrentUser()
    await nextTick()
    if (messagesContainer.value) typesetMath(messagesContainer.value)
  } catch (e) {
    if (e?.code === QUOTA_EXCEEDED_CODE) {
      messages.value.splice(rollbackIndex, 2)
      if (e.quota) setQuotaSnapshot(e.quota)
      pushToast('error', e.message || '今日免费体验次数已用完')
    } else if (e.name !== 'AbortError') {
      messages.value[messages.value.length - 1].content += `\n\n⚠️ ${e.message}`
    }
  } finally {
    streaming.value = false
  }
}


const textareaRef = ref(null)

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 200) + 'px'
}
</script>

<template>
  <ContentPanel title="AI 对话">
  <div class="flex flex-col h-full">
    <!-- 消息区域（含空状态） -->
    <div ref="messagesContainer" class="flex-1 overflow-y-auto custom-scrollbar">
      <div class="mx-auto max-w-5xl px-4 sm:px-8">

        <!-- 空状态：居中问候 -->
        <div v-if="messages.length === 0 && !streaming" class="flex flex-col items-center justify-center" style="min-height: calc(100vh - 200px)">
          <p class="text-2xl font-bold text-[#f7f8f8]">
            Hi，{{ username || '同学' }}
          </p>
          <p class="mt-2 text-sm text-[#62666d]">有问题，尽管问</p>
        </div>

        <!-- 消息列表 -->
        <div v-else class="space-y-6 py-6">
          <div v-for="(msg, i) in messages" :key="i" class="flex" :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">
            <div
              class="max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed"
              :class="msg.role === 'user'
                ? 'brand-btn text-white rounded-br-lg'
                : 'brand-btn text-[#d0d6e0] rounded-bl-lg'"
            >
              <!-- 思考过程折叠面板 -->
              <div v-if="msg.role === 'assistant' && msg.reasoning" class="mb-3">
                <button
                  @click="msg.reasoningOpen = !msg.reasoningOpen"
                  class="flex items-center gap-2 text-xs font-bold text-[#8a8f98] hover:text-[#d0d6e0] transition-colors"
                >
                  <i class="fa-solid fa-brain text-[rgb(129,115,223)]"></i>
                  <span>{{ streaming && i === messages.length - 1 && !msg.content ? '思考中...' : '已深度思考' }}</span>
                  <i class="fa-solid text-[10px] transition-transform" :class="msg.reasoningOpen ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
                </button>
                <Transition
                  enter-active-class="transition-all duration-200 ease-out"
                  enter-from-class="opacity-0 max-h-0"
                  enter-to-class="opacity-100 max-h-[400px]"
                  leave-active-class="transition-all duration-150 ease-in"
                  leave-from-class="opacity-100 max-h-[400px]"
                  leave-to-class="opacity-0 max-h-0"
                >
                  <div v-if="msg.reasoningOpen" class="mt-2 overflow-auto max-h-[400px] rounded-xl bg-white/[0.03] p-3 text-xs text-[#8a8f98] leading-relaxed custom-scrollbar whitespace-pre-wrap">{{ msg.reasoning }}</div>
                </Transition>
              </div>
              <!-- 正文内容 -->
              <div
                v-if="msg.role === 'assistant' && !(streaming && i === messages.length - 1 && !msg.content)"
                v-html="renderMarkdown(msg.content)"
                class="prose prose-sm prose-invert max-w-none"
              ></div>
              <div
                v-else-if="msg.role === 'assistant' && streaming && i === messages.length - 1 && !msg.content"
                class="flex gap-1"
              >
                <span class="w-2 h-2 rounded-full bg-[#62666d] animate-bounce" style="animation-delay: 0ms"></span>
                <span class="w-2 h-2 rounded-full bg-[#62666d] animate-bounce" style="animation-delay: 150ms"></span>
                <span class="w-2 h-2 rounded-full bg-[#62666d] animate-bounce" style="animation-delay: 300ms"></span>
              </div>
              <div v-else class="whitespace-pre-wrap">{{ msg.content }}</div>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- 底部输入区域 -->
    <div class="shrink-0 px-4 pb-4 pt-2 sm:px-8">
      <div class="mx-auto max-w-5xl">
        <div class="rounded-xl brand-btn overflow-hidden">
          <!-- 文本输入 -->
          <textarea
            ref="textareaRef"
            v-model="inputText"
            @keydown="handleKeydown"
            @input="autoResize"
            :disabled="streaming || !sessionId"
            rows="1"
            :placeholder="sessionId ? '有问题，尽管问，shift+enter 换行' : '请先新建或选择一个对话'"
            class="w-full resize-none bg-transparent px-4 pt-3 pb-1 text-sm outline-none text-[#f7f8f8] placeholder-[#62666d]"
            style="min-height: 24px; max-height: 200px;"
          ></textarea>

          <!-- 底部工具栏 -->
          <div class="flex items-center justify-between px-3 pb-2.5 pt-1">
            <!-- 左侧功能按钮 -->
            <div class="flex items-center gap-0.5">
              <button
                @click="deepThink = !deepThink"
                class="h-8 px-2.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors"
                :class="deepThink
                  ? 'bg-[rgb(129,115,223)]/15 text-[rgb(145,132,235)]'
                  : 'text-[#62666d] hover:text-[#8a8f98]'"
                title="深度思考"
              >
                <i class="fa-solid fa-brain text-sm"></i>
                <span class="hidden sm:inline">深度思考</span>
              </button>
              <button
                disabled
                class="h-8 px-2.5 rounded-lg text-xs font-bold flex items-center gap-1.5 text-[#62666d] cursor-not-allowed"
                title="联网搜索（敬请期待）"
              >
                <i class="fa-solid fa-globe text-sm"></i>
                <span class="hidden sm:inline">联网搜索</span>
              </button>
            </div>

            <!-- 右侧操作按钮 -->
            <div class="flex items-center gap-1.5">
              <button
                disabled
                class="h-8 w-8 rounded-lg flex items-center justify-center text-[#62666d] hover:bg-white/[0.04] transition-colors cursor-not-allowed"
                title="附件（敬请期待）"
              >
                <i class="fa-solid fa-plus text-sm"></i>
              </button>
              <button
                @click="sessionId ? sendMessage() : createAiChat(currentView)"
                :disabled="sessionId ? (!inputText.trim() || streaming) : false"
                class="h-8 w-8 rounded-full flex items-center justify-center transition-all"
                :class="inputText.trim() && sessionId
                  ? 'brand-btn text-white'
                  : 'bg-white/[0.06] text-[#62666d] opacity-50'"
              >
                <i class="fa-solid fa-arrow-up text-xs"></i>
              </button>
            </div>
          </div>
        </div>
        <p class="mt-2 text-center text-xs text-[#62666d]">内容由 AI 生成，仅供参考</p>
      </div>
    </div>
  </div>
  </ContentPanel>
</template>
