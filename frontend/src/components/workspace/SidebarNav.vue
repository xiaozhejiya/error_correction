<script setup>
/**
 * SidebarNav.vue
 * 工作台左侧边栏导航（PC 端双模式 + 移动端抽屉）+ 底部 Tab 导航（移动端）
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import BaseLogo from '@/components/base/BaseLogo.vue'
import BaseDropdown from '@/components/base/BaseDropdown.vue'
import BaseTooltip from '@/components/base/BaseTooltip.vue'

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
  projects: { type: Array, default: () => [] },
  activeProjectId: { type: [String, Number], default: null },
  loadingProjects: { type: Boolean, default: false },
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
  // 响应式状态
  sidebarMode: { type: String, default: 'expanded' }, // 'expanded' | 'collapsed-icon'
  isMobile: { type: Boolean, default: false },
  canHover: { type: Boolean, default: true },
  mobileDrawerOpen: { type: Boolean, default: false },
})

const emit = defineEmits([
  'update:currentView', 'update:currentSettingsSubView', 'update:collapsedGroups', 'update:chatCollapsed',
  'update:userMenuOpen', 'update:chatMenuOpenId', 'update:renameText', 'update:renamingChatId',
  'update:navRef', 'update:chatListRef',
  'navigate-home', 'logout', 'toggle-theme',
  'select-project', 'create-project', 'rename-project', 'delete-project',
  'create-ai-chat', 'select-ai-chat',
  'start-rename-chat', 'confirm-rename-chat', 'delete-ai-chat', 'toggle-chat-menu',
  'toggle-sidebar',
])

const isSettingsView = computed(() => props.currentView === 'settings')
const isNarrow = computed(() => !props.isMobile && props.sidebarMode === 'collapsed-icon')
const topNavGroups = computed(() => props.navGroups.filter(group => !group.label))
const lowerNavGroups = computed(() => props.navGroups.filter(group => group.label))
const errorBankProjects = computed(() => props.projects.filter(p => !p.is_default && (p.project_type || 'question') === 'question'))
const noteProjects = computed(() => props.projects.filter(p => !p.is_default && p.project_type === 'note'))
const projectGroupsCollapsed = ref({
  errorBank: false,
  notes: false,
})
const projectMenuOpenId = ref(null)
const projectActiveClass = 'bg-[rgb(var(--accent-rgb)/0.12)] text-[rgb(var(--accent-strong-rgb))] ring-1 ring-[rgb(var(--accent-rgb)/0.18)] dark:bg-[rgb(var(--accent-rgb)/0.10)] dark:text-[rgb(var(--accent-hover-rgb))] dark:ring-[rgb(var(--accent-rgb)/0.14)]'
const projectInactiveClass = 'text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-[#8a8f98] dark:hover:bg-white/[0.035] dark:hover:text-[#d0d6e0]'
const chatScrollReady = ref(!props.chatCollapsed)
let chatScrollTimer = null

const projectDisplayName = (project) => project?.name || ''

const setView = (view) => {
  emit('update:currentView', view)
  if (props.isMobile && props.mobileDrawerOpen) {
    emit('toggle-sidebar')
  }
}

const setSettingsEntry = (subview) => {
  emit('update:currentSettingsSubView', subview)
  if (props.isMobile && props.mobileDrawerOpen) {
    emit('toggle-sidebar')
  }
}

const openSettings = (subview = 'profile') => {
  if (props.currentView !== 'settings') {
    emit('update:currentView', 'settings')
  }
  setSettingsEntry(subview)
}

const returnToApp = () => {
  emit('update:currentView', props.lastWorkspaceView || 'workspace')
  if (props.isMobile && props.mobileDrawerOpen) {
    emit('toggle-sidebar')
  }
}

const selectChat = (s) => {
  projectMenuOpenId.value = null
  emit('update:chatMenuOpenId', null)
  emit('select-ai-chat', s)
  if (props.isMobile && props.mobileDrawerOpen) {
    emit('toggle-sidebar')
  }
}

const createChat = () => {
  emit('create-ai-chat')
  if (props.isMobile && props.mobileDrawerOpen) {
    emit('toggle-sidebar')
  }
}

const selectProjectView = (project, view) => {
  projectMenuOpenId.value = null
  emit('update:chatMenuOpenId', null)
  emit('select-project', project.id)
  setView(view)
}

const renameProject = (project) => {
  projectMenuOpenId.value = null
  emit('update:chatMenuOpenId', null)
  emit('rename-project', project)
}

const deleteProject = (project) => {
  projectMenuOpenId.value = null
  emit('update:chatMenuOpenId', null)
  emit('delete-project', project)
}

const setProjectMenuOpen = (id, open) => {
  projectMenuOpenId.value = open ? id : null
  if (open) emit('update:chatMenuOpenId', null)
}

const setChatMenuOpen = (id, open) => {
  emit('update:chatMenuOpenId', open ? id : null)
  if (open) projectMenuOpenId.value = null
}

const toggleGroup = (gi) => {
  if (isNarrow.value) return // 窄栏模式下不允许折叠分组
  const next = { ...props.collapsedGroups }
  next[gi] = !next[gi]
  emit('update:collapsedGroups', next)
}

const toggleProjectGroup = (key) => {
  if (isNarrow.value) return
  projectMenuOpenId.value = null
  projectGroupsCollapsed.value = {
    ...projectGroupsCollapsed.value,
    [key]: !projectGroupsCollapsed.value[key],
  }
}

const toggleChatCollapsed = () => {
  projectMenuOpenId.value = null
  emit('update:chatMenuOpenId', null)
  emit('update:chatCollapsed', !props.chatCollapsed)
}

const syncChatScroll = (collapsed) => {
  if (chatScrollTimer) {
    window.clearTimeout(chatScrollTimer)
    chatScrollTimer = null
  }
  chatScrollReady.value = false
  if (!collapsed) {
    chatScrollTimer = window.setTimeout(() => {
      chatScrollReady.value = true
      chatScrollTimer = null
    }, 320)
  }
}

watch(() => props.chatCollapsed, syncChatScroll)

onBeforeUnmount(() => {
  if (chatScrollTimer) window.clearTimeout(chatScrollTimer)
})

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
  <!-- ================== 侧边栏容器 ================== -->
  <aside
    class="sidebar-3d-stage flex min-h-0 flex-col z-20 transition-all duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)] overflow-hidden"
    :class="[
      isMobile
        ? 'fixed inset-y-0 left-0 w-64 transform bg-white dark:bg-[#1b1b1d] shadow-2xl ' + (mobileDrawerOpen ? 'translate-x-0' : '-translate-x-full')
        : 'hidden lg:flex lg:fixed lg:left-0 lg:top-0 lg:bottom-0 bg-transparent ' + (isNarrow ? 'w-16' : 'w-64')
    ]">

    <!-- 设置视图 -->
    <div class="sidebar-3d-shell relative min-h-0 flex-1">
      <div class="sidebar-3d-card absolute inset-0" :class="isSettingsView ? 'is-flipped' : ''">
        <div
          class="sidebar-3d-face sidebar-3d-face-back absolute inset-0 flex min-h-0 flex-1 flex-col px-4 py-4 overflow-hidden"
          :class="isSettingsView ? 'sidebar-3d-face-active' : 'sidebar-3d-face-inactive'"
          :aria-hidden="!isSettingsView">
          <button @click="returnToApp"
            class="mb-4 inline-flex w-full items-center gap-2 overflow-hidden px-3 pt-2 text-sm font-medium text-gray-500 transition-all duration-300 ease-[var(--sidebar-transition-timing)] hover:text-gray-700 dark:text-[#8a8f98] dark:hover:text-white">
            <i class="fa-solid fa-arrow-left text-xs"></i>
            <span
              class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-[var(--sidebar-transition-timing)]"
              :class="isNarrow ? 'max-w-0 -translate-x-1 opacity-0' : 'max-w-[72px] translate-x-0 opacity-100'">返回应用</span>
          </button>

          <nav :ref="(el) => $emit('update:navRef', el)" class="flex flex-col gap-1.5 relative pt-2">
            <div
              class="overflow-hidden px-3 text-xs font-medium uppercase tracking-[0.15em] text-gray-400 transition-all duration-300 ease-[var(--sidebar-transition-timing)] dark:text-[#62666d]"
              :class="isNarrow ? 'max-h-0 pt-0 pb-0 opacity-0' : 'max-h-8 pt-2 pb-1 opacity-100'">
              设置
            </div>
            <div class="flex flex-col gap-1">
              <template v-for="item in settingsNavItems" :key="item.id">
                <BaseTooltip :text="item.label" :placement="isNarrow ? 'right' : 'bottom'" :disabled="!isNarrow">
                  <button @click="setSettingsEntry(item.id)"
                    class="group relative z-10 flex items-center rounded-lg border px-3 py-2 text-sm font-medium transition-all duration-300 ease-[var(--sidebar-transition-timing)] w-full"
                    :class="[
                      currentSettingsSubView === item.id
                        ? 'brand-gradient-bg text-white shadow-sm border-transparent'
                        : 'border-transparent text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-[#8a8f98] dark:hover:bg-white/[0.04] dark:hover:text-[#d0d6e0]',
                      'gap-3'
                    ]">
                    <i class="fa-solid w-4 text-center text-sm" :class="item.icon"></i>
                    <span
                      class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-[var(--sidebar-transition-timing)]"
                      :class="isNarrow ? 'max-w-0 -translate-x-1 opacity-0' : 'max-w-[128px] translate-x-0 opacity-100'">{{
                        item.label }}</span>
                  </button>
                </BaseTooltip>
              </template>
            </div>
          </nav>
        </div>


        <!-- 主视图 -->
        <div
          class="sidebar-3d-face sidebar-3d-face-front absolute inset-0 flex min-h-0 flex-1 flex-col overflow-hidden pb-16"
          :class="isSettingsView ? 'sidebar-3d-face-inactive' : 'sidebar-3d-face-active'" :aria-hidden="isSettingsView">
          <div>
            <!-- Logo 标题区 -->
            <div
              class="flex h-14 items-center justify-between gap-2 px-3 transition-all duration-300 ease-[var(--sidebar-transition-timing)]">
              <button @click="emit('navigate-home')"
                class="flex w-[156px] min-w-0 items-center gap-2 rounded-md px-1 py-1 transition-all duration-300 ease-[var(--sidebar-transition-timing)] hover:bg-gray-100 dark:hover:bg-white/[0.04]"
                :title="canHover ? '返回首页' : null">
                <BaseLogo size="sm" class="shrink-0" />
                <span
                  class="overflow-hidden whitespace-nowrap text-sm font-semibold text-gray-900 transition-all duration-300 ease-[var(--sidebar-transition-timing)] dark:text-[#f7f8f8]"
                  :class="isNarrow ? 'max-w-0 -translate-x-1 opacity-0' : 'max-w-[96px] translate-x-0 opacity-100'">
                  智卷错题本
                </span>
              </button>
              <div
                class="flex items-center justify-end overflow-hidden transition-all duration-300 ease-[var(--sidebar-transition-timing)]"
                :class="isNarrow ? 'w-7 -translate-x-1 opacity-0' : 'w-7 translate-x-0 opacity-100'">
                <button @click="openSettings('profile')"
                  class="flex h-7 w-7 items-center justify-center rounded-md text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-[#62666d] dark:hover:bg-white/[0.04] dark:hover:text-[#8a8f98] transition-colors"
                  :title="canHover ? '系统设置' : null">
                  <i class="fa-solid fa-gear text-xs"></i>
                </button>
              </div>
            </div>

            <!-- 视图切换菜单 -->
            <nav :ref="(el) => $emit('update:navRef', el)"
              class="relative flex flex-col gap-1.5 pt-2 transition-all duration-300 ease-[var(--sidebar-transition-timing)]"
              :class="isNarrow ? 'px-3' : 'px-4'">

              <template v-for="(group, gi) in topNavGroups" :key="`top-${gi}`">
                <!-- 分组标题（可折叠） -->
                <button v-if="group.label" @click="group.collapsible && toggleGroup(gi)"
                  class="flex items-center gap-1 overflow-hidden text-xs font-medium uppercase tracking-[0.15em] text-gray-400 transition-all duration-300 ease-[var(--sidebar-transition-timing)] hover:text-gray-700 dark:text-[#62666d] dark:hover:text-[#8a8f98]"
                  :class="[
                    isNarrow ? 'pointer-events-none mt-0 max-h-0 px-3 pb-0 opacity-0' : 'mt-6 max-h-8 px-3 pb-2 opacity-100',
                    group.collapsible ? 'cursor-pointer' : 'cursor-default'
                  ]">
                  <span>{{ group.label }}</span>
                  <i v-if="group.collapsible"
                    class="fa-solid fa-play text-[8px] text-gray-400 dark:text-[#62666d] transition-transform duration-200"
                    :class="collapsedGroups[gi] ? '' : 'rotate-90'"></i>
                </button>

                <!-- 分组内容（grid 折叠动画） -->
                <div class="grid transition-[grid-template-rows] duration-200 ease-out"
                  :class="isNarrow || !collapsedGroups[gi] ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'">
                  <div class="overflow-hidden">
                    <div class="flex flex-col gap-1">
                      <template v-for="item in group.items" :key="item.id">
                        <!-- 禁用项 -->
                        <BaseTooltip :text="item.label" placement="right" :disabled="!isNarrow">
                          <button v-if="item.disabled" disabled
                            class="flex items-center justify-between rounded-lg px-3 py-3 text-sm cursor-not-allowed text-gray-400 dark:text-[#62666d]">
                            <div
                              class="flex items-center gap-3 transition-all duration-300 ease-[var(--sidebar-transition-timing)]">
                              <i class="fa-solid w-4 shrink-0 text-center text-sm" :class="item.icon"></i>
                              <span
                                class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-[var(--sidebar-transition-timing)]"
                                :class="isNarrow ? 'max-w-0 -translate-x-1 opacity-0' : 'max-w-[96px] translate-x-0 opacity-100'">{{
                                  item.label }}</span>
                            </div>
                            <span
                              class="overflow-hidden whitespace-nowrap rounded-md bg-gray-100 text-[10px] font-medium text-gray-500 transition-all duration-300 ease-[var(--sidebar-transition-timing)] dark:bg-white/[0.04] dark:text-[#62666d]"
                              :class="isNarrow ? 'max-w-0 px-0 py-0 opacity-0' : 'max-w-[68px] px-2 py-0.5 opacity-100'">敬请期待</span>
                          </button>
                          <!-- 普通项 -->
                          <button v-else :ref="el => navBtnRefs[item.id] = el"
                            @click="setView(item.id === 'workspace' ? lastWorkspaceView : item.id)"
                            class="group relative z-10 flex items-center rounded-lg text-sm font-medium outline-none transition-[width,height,padding,margin,gap] duration-300 ease-[var(--sidebar-transition-timing)]"
                            :class="[
                              item.match(currentView)
                                ? 'brand-gradient-bg text-white shadow-sm border-none'
                                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-[#8a8f98] dark:hover:bg-white/[0.04] dark:hover:text-[#d0d6e0] transition-colors duration-150',
                              'w-full gap-3 px-3 py-2'
                            ]">
                            <i class="fa-solid w-4 shrink-0 text-center text-sm" :class="item.icon"></i>
                            <span
                              class="overflow-hidden truncate whitespace-nowrap transition-all duration-300 ease-[var(--sidebar-transition-timing)]"
                              :class="isNarrow ? 'max-w-0 -translate-x-1 opacity-0' : 'max-w-[128px] translate-x-0 opacity-100'">
                              {{ item.label }}
                            </span>
                          </button>
                        </BaseTooltip>
                      </template>
                    </div>
                  </div>
                </div>
              </template>

              <section>
                <div
                  class="flex items-center justify-between transition-all duration-300 ease-[var(--sidebar-transition-timing)]"
                  :class="isNarrow ? 'max-h-0 overflow-hidden p-0 opacity-0' : 'mt-5 max-h-7 pb-1.5 pl-2.5 pr-0 opacity-100'">
                  <button @click="toggleProjectGroup('errorBank')"
                    class="flex h-6 items-center gap-1.5 overflow-hidden text-xs font-medium text-gray-400 transition-colors duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)] hover:text-gray-700 dark:text-[#62666d] dark:hover:text-[#9aa0aa]">
                    <span>我的错题库</span>
                    <i class="fa-solid fa-play text-[8px] text-gray-400 dark:text-[#62666d] transition-transform duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)]"
                      :class="projectGroupsCollapsed.errorBank ? '' : 'rotate-90'"></i>
                  </button>
                  <button
                    class="flex h-6 w-6 items-center justify-center rounded-md text-gray-500 transition-colors duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)] hover:bg-gray-100 hover:text-gray-700 dark:text-[#8a8f98] dark:hover:bg-white/[0.04] dark:hover:text-[#d0d6e0]"
                    :title="canHover ? '新建错题库' : null" @click.stop="emit('create-project', 'question')">
                    <i class="fa-solid fa-plus text-[10px]"></i>
                  </button>
                </div>
                <div
                  class="grid transition-[grid-template-rows] duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)]"
                  :class="isNarrow || !projectGroupsCollapsed.errorBank ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'">
                  <div class="min-h-0"
                    :class="projectMenuOpenId?.startsWith('q-') && !projectGroupsCollapsed.errorBank ? 'overflow-visible' : 'overflow-hidden'">
                    <div class="flex flex-col gap-1 pb-px">
                      <BaseTooltip v-if="isNarrow" text="我的错题库" placement="right">
                        <button @click="setView('error-bank')"
                          class="flex w-full items-center justify-center rounded-lg px-3 py-2 text-sm font-medium"
                          :class="currentView === 'error-bank' ? 'brand-gradient-bg text-white shadow-sm' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-[#8a8f98] dark:hover:bg-white/[0.04] dark:hover:text-[#d0d6e0]'">
                          <i class="fa-solid fa-database w-4 text-center text-sm"></i>
                        </button>
                      </BaseTooltip>
                      <template v-else>
                        <div v-for="(project, index) in errorBankProjects" :key="`q-${project.id}`"
                          class="group relative ml-5 flex min-h-7 w-[calc(100%-1.25rem)] items-center rounded-md text-xs font-medium transition-colors duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)]"
                          :class="currentView === 'error-bank' && String(activeProjectId) === String(project.id)
                            ? projectActiveClass
                            : projectInactiveClass">
                          <button @click="selectProjectView(project, 'error-bank')"
                            class="flex min-w-0 flex-1 items-center gap-2.5 rounded-md px-2.5 py-1 text-left">
                            <i class="fa-solid fa-database w-3.5 shrink-0 text-center text-[11px] opacity-90"></i>
                            <span class="min-w-0 truncate">{{ projectDisplayName(project) }}</span>
                          </button>
                          <BaseDropdown :modelValue="projectMenuOpenId === `q-${project.id}`"
                            @update:modelValue="(open) => setProjectMenuOpen(`q-${project.id}`, open)"
                            :position="(errorBankProjects.length > 3 && index >= errorBankProjects.length - 2) ? 'top' : 'bottom'"
                            align="right" width="w-32" wrapperClass="shrink-0"
                            panelClass="rounded-md brand-btn dark:bg-[#1b1b1d] py-1">
                            <template #trigger="{ toggle }">
                              <button
                                class="flex h-6 w-6 items-center justify-center opacity-55 transition-opacity duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)] hover:opacity-100"
                                :title="canHover ? '更多操作' : null" @click.stop="toggle">
                                <i class="fa-solid fa-ellipsis text-[9px]"></i>
                              </button>
                            </template>
                            <template #default="{ close }">
                              <button @click.stop="close(); renameProject(project)"
                                class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-gray-700 transition-colors duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)] hover:bg-gray-50 hover:text-gray-900 dark:text-[#d0d6e0] dark:hover:bg-white/[0.05]">
                                <i
                                  class="fa-solid fa-pen text-[10px] w-3 text-center text-gray-400 dark:text-[#62666d]"></i>
                                重命名
                              </button>
                              <button @click.stop="close(); deleteProject(project)"
                                class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-rose-500 transition-colors duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)] hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-500/10">
                                <i class="fa-solid fa-trash text-[10px] w-3 text-center"></i>
                                删除
                              </button>
                            </template>
                          </BaseDropdown>
                        </div>
                        <div v-if="!loadingProjects && errorBankProjects.length === 0"
                          class="ml-5 mr-1 rounded-md bg-gray-50/70 px-2.5 py-2 text-xs text-gray-400 dark:bg-white/[0.025] dark:text-[#62666d]">
                          <div class="mb-1.5">还没有错题库</div>
                          <button
                            class="accent-text font-medium transition-opacity duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)] hover:opacity-80"
                            @click.stop="emit('create-project', 'question')">
                            <i class="fa-solid fa-plus mr-1 text-[10px]"></i>新建错题库
                          </button>
                        </div>
                      </template>
                    </div>
                  </div>
                </div>
              </section>

              <section>
                <div
                  class="flex items-center justify-between transition-all duration-300 ease-[var(--sidebar-transition-timing)]"
                  :class="isNarrow ? 'max-h-0 overflow-hidden p-0 opacity-0' : 'mt-5 max-h-7 pb-1.5 pl-2.5 pr-0 opacity-100'">
                  <button @click="toggleProjectGroup('notes')"
                    class="flex h-6 items-center gap-1.5 overflow-hidden text-xs font-medium text-gray-400 transition-colors duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)] hover:text-gray-700 dark:text-[#62666d] dark:hover:text-[#9aa0aa]">
                    <span>我的笔记本</span>
                    <i class="fa-solid fa-play text-[8px] text-gray-400 dark:text-[#62666d] transition-transform duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)]"
                      :class="projectGroupsCollapsed.notes ? '' : 'rotate-90'"></i>
                  </button>
                  <button
                    class="flex h-6 w-6 items-center justify-center rounded-md text-gray-500 transition-colors duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)] hover:bg-gray-100 hover:text-gray-700 dark:text-[#8a8f98] dark:hover:bg-white/[0.04] dark:hover:text-[#d0d6e0]"
                    :title="canHover ? '新建笔记本' : null" @click.stop="emit('create-project', 'note')">
                    <i class="fa-solid fa-plus text-[10px]"></i>
                  </button>
                </div>
                <div
                  class="grid transition-[grid-template-rows] duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)]"
                  :class="isNarrow || !projectGroupsCollapsed.notes ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'">
                  <div class="min-h-0"
                    :class="projectMenuOpenId?.startsWith('n-') && !projectGroupsCollapsed.notes ? 'overflow-visible' : 'overflow-hidden'">
                    <div class="flex flex-col gap-1 pb-px">
                      <BaseTooltip v-if="isNarrow" text="我的笔记本" placement="right">
                        <button @click="setView('notes')"
                          class="flex w-full items-center justify-center rounded-lg px-3 py-2 text-sm font-medium"
                          :class="currentView === 'notes' ? 'brand-gradient-bg text-white shadow-sm' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-[#8a8f98] dark:hover:bg-white/[0.04] dark:hover:text-[#d0d6e0]'">
                          <i class="fa-solid fa-book-open w-4 text-center text-sm"></i>
                        </button>
                      </BaseTooltip>
                      <template v-else>
                        <div v-for="(project, index) in noteProjects" :key="`n-${project.id}`"
                          class="group relative ml-5 flex min-h-7 w-[calc(100%-1.25rem)] items-center rounded-md text-xs font-medium transition-colors duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)]"
                          :class="currentView === 'notes' && String(activeProjectId) === String(project.id)
                            ? projectActiveClass
                            : projectInactiveClass">
                          <button @click="selectProjectView(project, 'notes')"
                            class="flex min-w-0 flex-1 items-center gap-2.5 rounded-md px-2.5 py-1 text-left">
                            <i class="fa-solid fa-book-open w-3.5 shrink-0 text-center text-[11px] opacity-90"></i>
                            <span class="min-w-0 truncate">{{ projectDisplayName(project) }}</span>
                          </button>
                          <BaseDropdown :modelValue="projectMenuOpenId === `n-${project.id}`"
                            @update:modelValue="(open) => setProjectMenuOpen(`n-${project.id}`, open)"
                            :position="(noteProjects.length > 3 && index >= noteProjects.length - 2) ? 'top' : 'bottom'"
                            align="right" width="w-32" wrapperClass="shrink-0"
                            panelClass="rounded-md brand-btn dark:bg-[#1b1b1d] py-1">
                            <template #trigger="{ toggle }">
                              <button
                                class="flex h-6 w-6 items-center justify-center opacity-55 transition-opacity duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)] hover:opacity-100"
                                :title="canHover ? '更多操作' : null" @click.stop="toggle">
                                <i class="fa-solid fa-ellipsis text-[9px]"></i>
                              </button>
                            </template>
                            <template #default="{ close }">
                              <button @click.stop="close(); renameProject(project)"
                                class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-gray-700 transition-colors duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)] hover:bg-gray-50 hover:text-gray-900 dark:text-[#d0d6e0] dark:hover:bg-white/[0.05]">
                                <i
                                  class="fa-solid fa-pen text-[10px] w-3 text-center text-gray-400 dark:text-[#62666d]"></i>
                                重命名
                              </button>
                              <button @click.stop="close(); deleteProject(project)"
                                class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-rose-500 transition-colors duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)] hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-500/10">
                                <i class="fa-solid fa-trash text-[10px] w-3 text-center"></i>
                                删除
                              </button>
                            </template>
                          </BaseDropdown>
                        </div>
                        <div v-if="!loadingProjects && noteProjects.length === 0"
                          class="ml-5 mr-1 rounded-md bg-gray-50/70 px-2.5 py-2 text-xs text-gray-400 dark:bg-white/[0.025] dark:text-[#62666d]">
                          <div class="mb-1.5">还没有笔记本</div>
                          <button
                            class="accent-text font-medium transition-opacity duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)] hover:opacity-80"
                            @click.stop="emit('create-project', 'note')">
                            <i class="fa-solid fa-plus mr-1 text-[10px]"></i>新建笔记本
                          </button>
                        </div>
                      </template>
                    </div>
                  </div>
                </div>
              </section>

              <template v-for="(group, gi) in lowerNavGroups" :key="`lower-${gi}`">
                <!-- 分组标题（可折叠） -->
                <button v-if="group.label" @click="group.collapsible && toggleGroup(gi)"
                  class="flex items-center gap-1 overflow-hidden text-xs font-medium uppercase tracking-[0.15em] text-gray-400 transition-all duration-300 ease-[var(--sidebar-transition-timing)] hover:text-gray-700 dark:text-[#62666d] dark:hover:text-[#8a8f98]"
                  :class="[
                    isNarrow ? 'pointer-events-none mt-0 max-h-0 px-3 pb-0 opacity-0' : 'mt-6 max-h-8 px-3 pb-2 opacity-100',
                    group.collapsible ? 'cursor-pointer' : 'cursor-default'
                  ]">
                  <span>{{ group.label }}</span>
                  <i v-if="group.collapsible"
                    class="fa-solid fa-play text-[8px] text-gray-400 dark:text-[#62666d] transition-transform duration-200"
                    :class="collapsedGroups[gi] ? '' : 'rotate-90'"></i>
                </button>

                <!-- 分组内容（grid 折叠动画） -->
                <div class="grid transition-[grid-template-rows] duration-200 ease-out"
                  :class="isNarrow || !collapsedGroups[gi] ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'">
                  <div class="overflow-hidden">
                    <div class="flex flex-col gap-1">
                      <template v-for="item in group.items" :key="item.id">
                        <!-- 禁用项 -->
                        <BaseTooltip :text="item.label" placement="right" :disabled="!isNarrow">
                          <button v-if="item.disabled" disabled
                            class="flex items-center justify-between rounded-lg px-3 py-3 text-sm cursor-not-allowed text-gray-400 dark:text-[#62666d]">
                            <div
                              class="flex items-center gap-3 transition-all duration-300 ease-[var(--sidebar-transition-timing)]">
                              <i class="fa-solid w-4 shrink-0 text-center text-sm" :class="item.icon"></i>
                              <span
                                class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-[var(--sidebar-transition-timing)]"
                                :class="isNarrow ? 'max-w-0 -translate-x-1 opacity-0' : 'max-w-[96px] translate-x-0 opacity-100'">{{
                                  item.label }}</span>
                            </div>
                            <span
                              class="overflow-hidden whitespace-nowrap rounded-md bg-gray-100 text-[10px] font-medium text-gray-500 transition-all duration-300 ease-[var(--sidebar-transition-timing)] dark:bg-white/[0.04] dark:text-[#62666d]"
                              :class="isNarrow ? 'max-w-0 px-0 py-0 opacity-0' : 'max-w-[68px] px-2 py-0.5 opacity-100'">敬请期待</span>
                          </button>
                          <!-- 普通项 -->
                          <button v-else :ref="el => navBtnRefs[item.id] = el"
                            @click="setView(item.id === 'workspace' ? lastWorkspaceView : item.id)"
                            class="group relative z-10 flex items-center rounded-lg text-sm font-medium outline-none transition-[width,height,padding,margin,gap] duration-300 ease-[var(--sidebar-transition-timing)]"
                            :class="[
                              item.match(currentView)
                                ? 'brand-gradient-bg text-white shadow-sm border-none'
                                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-[#8a8f98] dark:hover:bg-white/[0.04] dark:hover:text-[#d0d6e0] transition-colors duration-150',
                              'w-full gap-3 px-3 py-2'
                            ]">
                            <i class="fa-solid w-4 shrink-0 text-center text-sm" :class="item.icon"></i>
                            <span
                              class="overflow-hidden truncate whitespace-nowrap transition-all duration-300 ease-[var(--sidebar-transition-timing)]"
                              :class="isNarrow ? 'max-w-0 -translate-x-1 opacity-0' : 'max-w-[128px] translate-x-0 opacity-100'">
                              {{ item.label }}
                            </span>
                          </button>
                        </BaseTooltip>
                      </template>
                    </div>
                  </div>
                </div>
              </template>
            </nav>
          </div>

          <!-- AI 对话历史列表 -->
          <div
            class="mt-2 flex min-h-0 flex-1 flex-col transition-all duration-300 ease-[var(--sidebar-transition-timing)]"
            :class="isNarrow ? 'px-3' : 'px-4'">
            <div
              class="flex items-center justify-between mt-5 pb-1.5 pl-2.5 pr-0 transition-all duration-300 ease-[var(--sidebar-transition-timing)]">
              <button @click="toggleChatCollapsed"
                class="flex h-6 items-center gap-1.5 overflow-hidden text-xs font-medium text-gray-400 transition-all duration-300 ease-[var(--sidebar-transition-timing)] hover:text-gray-700 dark:text-[#62666d] dark:hover:text-[#9aa0aa] cursor-pointer"
                :class="isNarrow ? 'pointer-events-none max-w-0 -translate-x-1 opacity-0' : 'max-w-[80px] translate-x-0 opacity-100'">
                <span>对话</span>
                <i class="fa-solid fa-play text-[8px] text-gray-400 dark:text-[#62666d] transition-transform duration-200"
                  :class="chatCollapsed ? '' : 'rotate-90'"></i>
              </button>
              <button @click="createChat"
                class="flex items-center justify-center overflow-hidden rounded-md text-gray-500 transition-all duration-300 ease-[var(--sidebar-transition-timing)] hover:bg-gray-100 hover:text-gray-700 dark:text-[#8a8f98] dark:hover:bg-white/[0.04] dark:hover:text-[#d0d6e0]"
                :class="isNarrow ? 'pointer-events-none h-0 w-0 -translate-x-1 opacity-0' : 'h-6 w-6 translate-x-0 opacity-100'"
                :title="canHover ? '新对话' : null">
                <i class="fa-solid fa-plus text-[10px]"></i>
              </button>
            </div>
            <!-- 折叠动画 -->
            <div
              class="grid min-h-0 flex-1 transition-[grid-template-rows] duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)]"
              :class="isNarrow || !chatCollapsed ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'">
              <div class="flex min-h-0 flex-col overflow-hidden">
                <div :ref="(el) => $emit('update:chatListRef', el)"
                  class="hidden-scrollbar relative h-full overflow-x-hidden pb-2"
                  :class="chatScrollReady ? 'overflow-y-auto' : 'overflow-y-hidden'"
                  @click="emit('update:chatMenuOpenId', null)">

                  <div v-if="aiChatSessions.length === 0"
                    class="overflow-hidden px-3 text-center text-xs text-gray-400 transition-all duration-300 ease-[var(--sidebar-transition-timing)] dark:text-[#62666d]"
                    :class="isNarrow ? 'max-h-0 py-0 opacity-0' : 'max-h-16 py-4 opacity-100'">
                    暂无对话
                  </div>
                  <div v-for="(s, index) in aiChatSessions" :key="s.id" :ref="el => chatBtnRefs[s.id] = el"
                    class="group relative mb-px flex cursor-pointer items-center rounded-md text-sm font-medium outline-none transition-[width,height,padding,margin] duration-300"
                    :class="[
                      chatMenuOpenId === s.id ? 'z-20' : 'z-10',
                      activeAiChatId === s.id && currentView === 'ai-chat'
                        ? 'brand-gradient-bg text-white shadow-sm border-none'
                        : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-[#8a8f98] dark:hover:bg-white/[0.04] dark:hover:text-[#d0d6e0] transition-colors duration-150',
                      'w-full gap-2.5 py-1.5 pl-2.5 pr-0'
                    ]" @click="renamingChatId !== s.id && selectChat(s)">
                    <BaseTooltip :text="s.title" placement="right" :disabled="!isNarrow">
                      <i class="fa-solid fa-message w-3.5 shrink-0 text-center text-xs transition-colors"></i>
                    </BaseTooltip>

                    <div
                      class="flex min-w-0 flex-1 items-center gap-2 overflow-visible transition-all duration-300 ease-[var(--sidebar-transition-timing)]"
                      :class="isNarrow ? 'pointer-events-none max-w-0 -translate-x-1 opacity-0' : 'max-w-none translate-x-0 opacity-100'">
                      <!-- 重命名输入框 -->
                      <input v-if="renamingChatId === s.id" :value="renameText"
                        @input="emit('update:renameText', $event.target.value)" data-rename-input @click.stop
                        @keydown.enter="emit('confirm-rename-chat', s)"
                        @keydown.escape="$emit('update:renamingChatId', null)" @blur="emit('confirm-rename-chat', s)"
                        class="flex-1 min-w-0 bg-transparent text-xs outline-none border-b border-gray-300 py-0.5 text-gray-900 dark:border-white/[0.12] dark:text-[#f7f8f8]" />
                      <span v-else class="relative z-10 flex-1 truncate">{{ s.title }}</span>

                      <BaseDropdown :modelValue="chatMenuOpenId === s.id"
                        @update:modelValue="(open) => setChatMenuOpen(s.id, open)"
                        :position="(aiChatSessions.length > 3 && index >= aiChatSessions.length - 2) ? 'top' : 'bottom'"
                        align="right" width="w-32" wrapperClass="shrink-0"
                        panelClass="rounded-md brand-btn dark:bg-[#1b1b1d] py-1">
                        <template #trigger="{ toggle }">
                          <button
                            class="flex h-6 w-6 items-center justify-center opacity-55 transition-opacity hover:opacity-100"
                            :title="canHover ? '更多操作' : null" @click.stop="toggle">
                            <i class="fa-solid fa-ellipsis text-[9px]"></i>
                          </button>
                        </template>
                        <template #default="{ close }">
                          <button @click.stop="close(); emit('start-rename-chat', s)"
                            class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 hover:text-gray-900 dark:text-[#d0d6e0] dark:hover:bg-white/[0.05] transition-colors">
                            <i
                              class="fa-solid fa-pen text-[10px] w-3 text-center text-gray-400 dark:text-[#62666d]"></i>
                            重命名
                          </button>
                          <button @click.stop="close(); emit('delete-ai-chat', s.id)"
                            class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-rose-500 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-500/10 transition-colors">
                            <i class="fa-solid fa-trash text-[10px] w-3 text-center"></i>
                            删除
                          </button>
                        </template>
                      </BaseDropdown>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部用户区 -->
        <div class="absolute inset-x-0 bottom-0 p-1.5">
          <BaseDropdown :modelValue="userMenuOpen" @update:modelValue="(val) => emit('update:userMenuOpen', val)"
            :position="isNarrow ? 'right' : 'top'" :align="isNarrow ? 'end' : 'center'"
            :width="isNarrow ? 'w-48' : 'w-full'" :offset="isNarrow ? 'ml-4' : 'mb-1'"
            panelClass="rounded-md brand-btn dark:bg-[#1b1b1d] backdrop-blur-md"
            :wrapperClass="isNarrow ? 'inline-block' : 'block w-full'">
            <!-- 背景噪点 -->
            <template #background>
              <div class="ws-bg-noise hidden dark:block"></div>
            </template>

            <template #trigger="{ toggle }">
              <!-- 用户信息 -->
              <button @click.stop="toggle"
                class="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 hover:bg-gray-100 dark:bg-white/[0.025] dark:hover:bg-white/[0.045] transition-all">
                <div
                  class="h-7 w-7 shrink-0 rounded-lg relative overflow-hidden flex items-center justify-center text-white text-xs font-medium"
                  style="background: linear-gradient(to bottom, rgb(var(--accent-rgb) / 0.9), rgb(var(--accent-strong-rgb) / 0.9)); box-shadow: inset 0 1px 0 0 rgba(255,255,255,0.12);">
                  <img v-if="currentUser?.avatar_url" :src="currentUser.avatar_url" alt="用户头像"
                    class="h-full w-full object-cover" />
                  <template v-else>
                    <span class="absolute inset-0 pointer-events-none"
                      style="background-image: linear-gradient(to right, rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.06) 1px, transparent 1px); background-size: 8px 8px; mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%); -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);"></span>
                    <span class="relative z-10">{{ userInitial }}</span>
                  </template>
                </div>
                <div
                  class="min-w-0 flex-1 overflow-hidden text-left transition-all duration-300 ease-[var(--sidebar-transition-timing)]"
                  :class="isNarrow ? 'max-w-0 -translate-x-1 opacity-0' : 'max-w-[156px] translate-x-0 opacity-100'">
                  <p
                    class="text-sm font-medium text-gray-900 dark:text-[#f7f8f8] truncate leading-tight transition-colors">
                    {{
                      userDisplayName }}
                  </p>
                  <p v-if="userQuotaSummary"
                    class="mt-0.5 text-xs accent-text truncate leading-tight transition-colors">
                    {{
                      userQuotaSummary }}</p>
                  <p v-else class="text-xs text-gray-500 dark:text-[#62666d] truncate leading-tight transition-colors">
                    @{{
                      currentUser?.username || 'guest' }}</p>
                </div>
                <i class="fa-solid fa-chevron-up overflow-hidden text-[10px] text-gray-400 transition-all duration-300 ease-[var(--sidebar-transition-timing)] dark:text-[#62666d]"
                  :class="isNarrow ? 'w-0 -translate-x-1 opacity-0' : 'w-3 translate-x-0 opacity-100'"></i>
              </button>
            </template>

            <!-- Dropdown 菜单内容 -->
            <template #default="{ close }">
              <button @click="openSettings('profile'); close()"
                class="flex w-full items-center gap-2.5 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-gray-900 dark:text-[#d0d6e0] dark:hover:bg-white/[0.05] transition-colors">
                <i class="fa-solid fa-gear w-4 text-center text-xs text-gray-400 dark:text-[#62666d]"></i>
                系统设置
              </button>
              <button @click="(e) => { close(); emit('toggle-theme', e.currentTarget) }"
                class="flex w-full items-center gap-2.5 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-gray-900 dark:text-[#d0d6e0] dark:hover:bg-white/[0.05] transition-colors">
                <i class="fa-solid w-4 text-center text-xs text-gray-400 dark:text-[#62666d]"
                  :class="isDark ? 'fa-sun' : 'fa-moon'"></i>
                {{ isDark ? '浅色模式' : '深色模式' }}
              </button>
              <div class="border-t border-gray-200 dark:border-white/[0.05]"></div>
              <button @click="emit('logout'); close()"
                class="flex w-full items-center gap-3 px-4 py-3 text-sm font-bold text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors">
                <i class="fas fa-right-from-bracket w-4 text-center text-xs"></i>
                退出登录
              </button>
            </template>
          </BaseDropdown>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar-3d-stage {
  perspective: 1100px;
  transform-style: preserve-3d;
}

.sidebar-3d-shell {
  perspective: 1100px;
  transform-style: preserve-3d;
}

.sidebar-3d-card {
  transform-style: preserve-3d;
  transform-origin: center center;
  transition: filter 280ms cubic-bezier(0.22, 1, 0.36, 1);
  will-change: filter;
}

.sidebar-3d-card.is-flipped {
  filter: brightness(0.985);
}

.sidebar-3d-face {
  backface-visibility: hidden;
  transform-origin: center center;
  transform-style: preserve-3d;
  transition:
    opacity 120ms ease,
    transform 280ms cubic-bezier(0.22, 1, 0.36, 1),
    filter 280ms cubic-bezier(0.22, 1, 0.36, 1);
  will-change: opacity, transform, filter;
}

.sidebar-3d-face-front {
  transform: rotateY(0deg) translateX(0) scale(1);
}

.sidebar-3d-face-back {
  transform: rotateY(0deg) translateX(0) scale(1);
}

.sidebar-3d-face-front.sidebar-3d-face-active,
.sidebar-3d-face-back.sidebar-3d-face-active {
  opacity: 1;
  filter: brightness(1);
  pointer-events: auto;
  transform: rotateY(0deg) translateX(0) scale(1);
}

.sidebar-3d-face-front.sidebar-3d-face-inactive {
  opacity: 0;
  filter: brightness(0.9);
  pointer-events: none;
  transform: rotateY(90deg) scale(0.98);
}

.sidebar-3d-face-back.sidebar-3d-face-inactive {
  opacity: 0;
  filter: brightness(0.9);
  pointer-events: none;
  transform: rotateY(-90deg) scale(0.98);
}

.hidden-scrollbar {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.hidden-scrollbar::-webkit-scrollbar {
  display: none;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 10px;
}

.dark .custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.05);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
