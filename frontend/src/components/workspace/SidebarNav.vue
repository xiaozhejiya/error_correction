<script setup>
/**
 * SidebarNav.vue
 * 工作台左侧边栏导航（PC 端）+ 底部 Tab 导航（移动端）
 */
import { computed } from 'vue'
import BaseLogo from '@/components/base/BaseLogo.vue'

const props = defineProps({
  currentView: { type: String, required: true },
  currentSettingsSubView: { type: String, default: 'profile' },
  settingsNavItems: { type: Array, default: () => [] },
  lastWorkspaceView: { type: String, default: 'workspace' },
  currentUser: { type: Object, default: null },
  isDark: { type: Boolean, default: true },
  theme: { type: String, default: 'dark' },
  // 导航配置
  navGroups: { type: Array, required: true },
  workspaceViews: { type: Object, required: true },
  collapsedGroups: { type: Object, required: true },
  // 指示器
  navRef: { type: Object, default: null },
  navBtnRefs: { type: Object, required: true },
  indicatorStyle: { type: Object, default: () => ({}) },
  indicatorTransition: { type: Boolean, default: false },
  // AI 对话
  chatCollapsed: { type: Boolean, default: false },
  aiChatSessions: { type: Array, default: () => [] },
  activeAiChatId: { type: [String, Number], default: null },
  chatListRef: { type: Object, default: null },
  chatBtnRefs: { type: Object, required: true },
  chatIndicatorStyle: { type: Object, default: () => ({}) },
  chatIndicatorTransition: { type: Boolean, default: false },
  chatMenuOpenId: { type: [String, Number], default: null },
  renamingChatId: { type: [String, Number], default: null },
  renameText: { type: String, default: '' },
  // 用户菜单
  userMenuOpen: { type: Boolean, default: false },
})

const emit = defineEmits([
  'update:currentView', 'update:currentSettingsSubView', 'update:collapsedGroups', 'update:chatCollapsed',
  'update:userMenuOpen', 'update:chatMenuOpenId', 'update:renameText', 'update:renamingChatId',
  'update:navRef', 'update:chatListRef',
  'navigate-home', 'logout', 'toggle-theme',
  'create-ai-chat', 'select-ai-chat',
  'start-rename-chat', 'confirm-rename-chat', 'delete-ai-chat', 'toggle-chat-menu',
])

// 计算对话菜单的固定定位样式
const getChatMenuStyle = computed(() => (sessionId) => {
  const btnEl = props.chatBtnRefs[sessionId]
  if (!btnEl) return {}
  const rect = btnEl.getBoundingClientRect()
  return {
    top: `${rect.bottom + 4}px`,
    left: `${rect.right - 128}px`, // 菜单宽度 128px (w-32)，右对齐
  }
})

const isSettingsView = computed(() => props.currentView === 'settings')

const setView = (view) => emit('update:currentView', view)
const setSettingsEntry = (subview) => emit('update:currentSettingsSubView', subview)
const openSettings = (subview = 'profile') => {
  if (props.currentView !== 'settings') {
    emit('update:currentView', 'settings')
    return
  }
  setSettingsEntry(subview)
}

const returnToApp = () => {
  emit('update:currentView', props.lastWorkspaceView || 'workspace')
}

const toggleGroup = (gi) => {
  const next = { ...props.collapsedGroups }
  next[gi] = !next[gi]
  emit('update:collapsedGroups', next)
}

const userDisplayName = computed(() => {
  const user = props.currentUser || {}
  return user.display_name || user.nickname || user.username || '未登录用户'
})

const userInitial = computed(() => {
  const source = userDisplayName.value || props.currentUser?.username || ''
  return source.trim()?.[0]?.toUpperCase() || '?'
})

const userQuota = computed(() => props.currentUser?.quota || null)
const userQuotaSummary = computed(() => {
  const remaining = userQuota.value?.remaining
  const total = userQuota.value?.daily_free_quota
  if (remaining == null || total == null) return ''
  return `今日剩余 ${remaining} / ${total} 次`
})
</script>

<template>
  <!-- ================== PC端：左侧边栏导航 ================== -->
  <aside class="hidden w-64 min-h-0 flex-col md:flex z-20">
    <template v-if="isSettingsView">
      <div class="flex min-h-0 flex-1 flex-col px-4 py-4">
        <button @click="returnToApp"
          class="mb-4 inline-flex items-center gap-2 px-3 pt-2 text-sm font-medium text-[#8a8f98] transition-colors hover:text-white">
          <i class="fa-solid fa-arrow-left text-xs"></i>
          <span>返回应用</span>
        </button>

        <nav :ref="(el) => $emit('update:navRef', el)" class="flex flex-col gap-1.5 relative">
          <div class="px-3 pt-2 pb-1 text-xs font-medium uppercase tracking-[0.15em] text-[#62666d]">
            设置
          </div>
          <div class="flex flex-col gap-1">
            <button v-for="item in settingsNavItems" :key="item.id" @click="setSettingsEntry(item.id)"
              class="group relative z-10 flex items-center gap-3 rounded-lg border px-3 py-2 text-sm font-medium transition-colors duration-200"
              :class="currentSettingsSubView === item.id
                ? 'border-white/[0.10] bg-white/[0.06] text-white'
                : 'border-transparent text-[#8a8f98] hover:bg-white/[0.04] hover:text-[#d0d6e0]'">
              <i class="fa-solid w-4 text-center text-sm" :class="item.icon"></i>
              <span>{{ item.label }}</span>
            </button>
          </div>
        </nav>
      </div>
    </template>

    <template v-else>
      <div class="flex min-h-0 flex-1 flex-col">
        <div>
          <!-- Logo 标题区 -->
          <div class="flex h-20 items-center justify-between px-4 py-6">
            <button @click="emit('navigate-home')"
              class="flex min-w-0 items-center gap-2 rounded-md px-1 py-1 hover:bg-white/[0.04] transition-colors"
              title="返回首页">
              <BaseLogo size="sm" />
              <span class="text-sm font-medium text-[#f7f8f8]">智卷错题本</span>
            </button>
            <div class="flex items-center gap-1">
              <button @click="openSettings('profile')"
                class="flex h-7 w-7 items-center justify-center rounded-md text-[#62666d] hover:bg-white/[0.04] hover:text-[#8a8f98] transition-colors"
                title="系统设置">
                <i class="fa-solid fa-gear text-xs"></i>
              </button>
              <button @click="emit('logout')"
                class="flex h-7 w-7 items-center justify-center rounded-md border border-white/[0.08] text-[#62666d] hover:bg-white/[0.04] hover:text-[#8a8f98] transition-colors"
                title="退出登录">
                <i class="fa-solid fa-right-from-bracket text-xs"></i>
              </button>
            </div>
          </div>

          <!-- 视图切换菜单 — Linear 分组折叠 -->
          <nav :ref="(el) => $emit('update:navRef', el)" class="flex flex-col gap-1.5 px-4 relative">
            <!-- 滑动指示器 -->
            <div class="absolute left-4 right-4 z-0 rounded-lg overflow-hidden brand-btn"
              :class="indicatorTransition ? 'transition-all duration-300 ease-out' : ''" :style="indicatorStyle"></div>

            <template v-for="(group, gi) in navGroups" :key="gi">
              <!-- 分组标题（可折叠） -->
              <button v-if="group.label" @click="group.collapsible && toggleGroup(gi)"
                class="flex items-center gap-1 px-3 pt-4 pb-1 text-xs font-medium uppercase tracking-[0.15em] text-[#62666d] hover:text-[#8a8f98] transition-colors"
                :class="group.collapsible ? 'cursor-pointer' : 'cursor-default'">
                <span>{{ group.label }}</span>
                <i v-if="group.collapsible"
                  class="fa-solid fa-play text-[8px] text-[#62666d] transition-transform duration-200"
                  :class="collapsedGroups[gi] ? '' : 'rotate-90'"></i>
              </button>

              <!-- 分组内容（grid 折叠动画） -->
              <div class="grid transition-[grid-template-rows] duration-200 ease-out"
                :class="collapsedGroups[gi] ? 'grid-rows-[0fr]' : 'grid-rows-[1fr]'">
                <div class="overflow-hidden">
                  <div class="flex flex-col gap-1">
                    <template v-for="item in group.items" :key="item.id">
                      <!-- 禁用项 -->
                      <button v-if="item.disabled" disabled
                        class="flex items-center justify-between rounded-lg px-3 py-3 text-sm cursor-not-allowed text-[#62666d]">
                        <div class="flex items-center gap-3">
                          <i class="fa-solid w-4 text-center text-sm" :class="item.icon"></i>
                          <span>{{ item.label }}</span>
                        </div>
                        <span
                          class="text-[10px] font-medium px-2 py-0.5 rounded-md bg-white/[0.04] text-[#62666d]">敬请期待</span>
                      </button>
                      <!-- 普通项 -->
                      <button v-else :ref="el => navBtnRefs[item.id] = el"
                        @click="setView(item.id === 'workspace' ? lastWorkspaceView : item.id)"
                        class="group relative z-10 flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-200"
                        :class="item.match(currentView)
                          ? 'text-white'
                          : 'text-[#8a8f98] hover:bg-white/[0.04] hover:text-[#d0d6e0]'">
                        <i class="fa-solid w-4 text-center text-sm" :class="item.icon"></i>
                        <span>{{ item.label }}</span>
                      </button>
                    </template>
                  </div>
                </div>
              </div>
            </template>
          </nav>
        </div>

        <!-- AI 对话历史列表 -->
        <div class="mt-4 flex min-h-0 flex-1 flex-col px-4">
          <div class="flex items-center justify-between px-3 pt-4 pb-2">
            <button @click="emit('update:chatCollapsed', !chatCollapsed)"
              class="flex items-center gap-1 text-xs font-medium uppercase tracking-[0.15em] text-[#62666d] hover:text-[#8a8f98] transition-colors cursor-pointer">
              <span>对话</span>
              <i class="fa-solid fa-play text-[8px] text-[#62666d] transition-transform duration-200"
                :class="chatCollapsed ? '' : 'rotate-90'"></i>
            </button>
            <button @click="emit('create-ai-chat')" class="text-[#8a8f98] hover:text-[#d0d6e0] transition-colors">
              <i class="fa-solid fa-plus text-[10px]"></i>
            </button>
          </div>
          <!-- 折叠动画 -->
          <div class="grid min-h-0 flex-1 transition-[grid-template-rows] duration-200 ease-out"
            :class="chatCollapsed ? 'grid-rows-[0fr]' : 'grid-rows-[1fr]'">
            <div class="flex min-h-0 flex-col overflow-hidden">
              <div :ref="(el) => $emit('update:chatListRef', el)"
                class="relative h-full overflow-y-auto pb-2 custom-scrollbar"
                @click="emit('update:chatMenuOpenId', null)">
                <!-- 对话区滑动指示器 -->
                <div class="absolute left-0 right-0 z-0 rounded-lg overflow-hidden brand-btn"
                  :style="chatIndicatorStyle"></div>

                <div v-if="aiChatSessions.length === 0" class="px-3 py-4 text-center text-xs text-[#62666d]">
                  暂无对话
                </div>
                <div v-for="s in aiChatSessions" :key="s.id" :ref="el => chatBtnRefs[s.id] = el"
                  class="group relative mb-px flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
                  :class="[
                    chatMenuOpenId === s.id ? 'z-20' : 'z-10',
                    activeAiChatId === s.id && currentView === 'ai-chat'
                      ? 'text-white'
                      : 'text-[#8a8f98] hover:bg-white/[0.04] hover:text-[#d0d6e0]',
                  ]" @click="renamingChatId !== s.id && emit('select-ai-chat', s)">
                  <i class="fa-solid fa-message w-4 shrink-0 text-center text-sm"
                    :class="activeAiChatId === s.id && currentView === 'ai-chat' ? 'text-white/60' : 'text-[#62666d]'"></i>

                  <!-- 重命名输入框 -->
                  <input v-if="renamingChatId === s.id" :value="renameText"
                    @input="emit('update:renameText', $event.target.value)" data-rename-input @click.stop
                    @keydown.enter="emit('confirm-rename-chat', s)"
                    @keydown.escape="$emit('update:renamingChatId', null)" @blur="emit('confirm-rename-chat', s)"
                    class="flex-1 min-w-0 bg-transparent text-xs outline-none border-b border-white/[0.12] py-0.5 text-[#f7f8f8]" />
                  <span v-else class="relative z-10 flex-1 truncate">{{ s.title }}</span>

                  <!-- 三个点按钮 -->
                  <button @click.stop="emit('toggle-chat-menu', s.id)"
                    class="shrink-0 opacity-0 group-hover:opacity-100 text-[#62666d] hover:text-[#d0d6e0] transition-all">
                    <i class="fa-solid fa-ellipsis text-[10px]"></i>
                  </button>

                  <!-- Dropdown 菜单 -->
                  <Transition enter-active-class="transition duration-100 ease-out"
                    enter-from-class="opacity-0 scale-95" enter-to-class="opacity-100 scale-100"
                    leave-active-class="transition duration-75 ease-in" leave-from-class="opacity-100 scale-100"
                    leave-to-class="opacity-0 scale-95">
                    <div v-if="chatMenuOpenId === s.id"
                      class="absolute right-2 top-full mt-1 z-50 w-32 rounded-md brand-btn overflow-hidden" @click.stop>
                      <button @click="emit('start-rename-chat', s)"
                        class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-[#d0d6e0] hover:bg-white/[0.05] transition-colors">
                        <i class="fa-solid fa-pen text-[10px] w-3 text-center text-[#62666d]"></i> 重命名
                      </button>
                      <button @click="emit('update:chatMenuOpenId', null); emit('delete-ai-chat', s.id)"
                        class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-rose-400 hover:bg-rose-500/10 transition-colors">
                        <i class="fa-solid fa-trash text-[10px] w-4 text-center"></i> 删除
                      </button>
                    </div>
                  </Transition>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部用户区 -->
      <div class="relative p-2">
        <!-- Dropdown 菜单 -->
        <Transition enter-active-class="transition duration-150 ease-out" enter-from-class="opacity-0 translate-y-2"
          enter-to-class="opacity-100 translate-y-0" leave-active-class="transition duration-100 ease-in"
          leave-from-class="opacity-100 translate-y-0" leave-to-class="opacity-0 translate-y-2">
          <div v-if="userMenuOpen"
            class="absolute bottom-full left-2 right-2 mb-1 rounded-md brand-btn overflow-hidden z-50">
            <button @click="openSettings('profile'); emit('update:userMenuOpen', false)"
              class="flex w-full items-center gap-2.5 px-3 py-2 text-sm text-[#d0d6e0] hover:bg-white/[0.05] transition-colors">
              <i class="fa-solid fa-gear w-4 text-center text-xs text-[#62666d]"></i>
              系统设置
            </button>
            <button @click="(e) => { emit('update:userMenuOpen', false); emit('toggle-theme', e.currentTarget) }"
              class="flex w-full items-center gap-2.5 px-3 py-2 text-sm text-[#d0d6e0] hover:bg-white/[0.05] transition-colors">
              <i class="fa-solid w-4 text-center text-xs text-[#62666d]" :class="isDark ? 'fa-sun' : 'fa-moon'"></i>
              {{ isDark ? '浅色模式' : '深色模式' }}
            </button>
            <div class="border-t border-white/[0.05]"></div>
            <button @click="emit('logout'); emit('update:userMenuOpen', false)"
              class="flex w-full items-center gap-3 px-4 py-3 text-sm font-bold text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors">
              <i class="fas fa-right-from-bracket w-4 text-center text-xs"></i>
              退出登录
            </button>
          </div>
        </Transition>

        <!-- 用户信息 -->
        <button @click="emit('update:userMenuOpen', !userMenuOpen)"
          class="flex w-full items-center gap-2 px-2 py-1.5 rounded-md hover:bg-white/[0.04] transition-colors">
          <div
            class="h-8 w-8 shrink-0 rounded-xl relative overflow-hidden flex items-center justify-center text-white text-sm font-medium"
            style="background: linear-gradient(to bottom, rgba(129,115,223,0.9), rgba(99,87,199,0.9)); box-shadow: inset 0 1px 0 0 rgba(255,255,255,0.12);">
            <img v-if="currentUser?.avatar_url" :src="currentUser.avatar_url" alt="用户头像"
              class="h-full w-full object-cover" />
            <template v-else>
              <span class="absolute inset-0 pointer-events-none"
                style="background-image: linear-gradient(to right, rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.06) 1px, transparent 1px); background-size: 8px 8px; mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%); -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);"></span>
              <span class="relative z-10">{{ userInitial }}</span>
            </template>
          </div>
          <div class="flex-1 min-w-0 text-left">
            <p class="text-sm text-[#f7f8f8] truncate leading-tight">{{ userDisplayName }}</p>
            <p v-if="userQuotaSummary" class="mt-0.5 text-xs text-[rgb(145,132,235)] truncate leading-tight">{{
              userQuotaSummary }}</p>
            <p v-else class="text-xs text-[#62666d] truncate leading-tight">@{{ currentUser?.username || 'guest' }}</p>
          </div>
          <i class="fa-solid fa-chevron-up text-[10px] text-[#62666d]"></i>
        </button>
      </div>
    </template>
  </aside>

  <!-- ================== 移动端：底部 Tab 导航栏 ================== -->
  <nav class="fixed bottom-0 left-0 right-0 z-50 border-t border-white/[0.06] bg-[#0A0A0F]/90 pb-2 pt-2 md:hidden">
    <div class="flex justify-around">
      <button @click="setView(lastWorkspaceView)" class="flex flex-col items-center p-2"
        :class="workspaceViews.has(currentView) ? 'text-indigo-400' : 'text-white/40'">
        <i class="fa-solid fa-file-arrow-up text-lg"></i>
        <span class="mt-1 text-xs font-bold">录入</span>
      </button>
      <button @click="setView('notes')" class="flex flex-col items-center p-2"
        :class="currentView === 'notes' ? 'text-indigo-400' : 'text-white/40'">
        <i class="fa-solid fa-book-open text-lg"></i>
        <span class="mt-1 text-xs font-bold">笔记库</span>
      </button>
      <button @click="setView('dashboard')" class="flex flex-col items-center p-2"
        :class="currentView === 'dashboard' ? 'text-indigo-400' : 'text-white/40'">
        <i class="fa-solid fa-chart-pie text-lg"></i>
        <span class="mt-1 text-xs font-bold">数据面板</span>
      </button>
      <button @click="setView('error-bank')" class="flex flex-col items-center p-2"
        :class="currentView === 'error-bank' ? 'text-indigo-400' : 'text-white/40'">
        <i class="fa-solid fa-layer-group text-lg"></i>
        <span class="mt-1 text-xs font-bold">错题本</span>
      </button>
      <button @click="openSettings('profile')" class="flex flex-col items-center p-2"
        :class="currentView === 'settings' ? 'text-indigo-400' : 'text-white/40'">
        <i class="fa-solid fa-sliders text-lg"></i>
        <span class="mt-1 text-xs font-bold">设置</span>
      </button>
      <button @click="(e) => emit('toggle-theme', e.currentTarget)"
        class="flex flex-col items-center p-2 text-white/40">
        <i class="fa-solid text-lg" :class="theme === 'dark' ? 'fa-sun' : 'fa-moon'"></i>
        <span class="mt-1 text-xs font-bold">主题</span>
      </button>
    </div>
  </nav>
</template>
