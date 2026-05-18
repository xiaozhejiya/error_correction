<script setup>
/**
 * AppLayout.vue
 * App 布局容器 — 侧边栏导航 + 内容区视图切换
 * 仅负责：导航、布局、全局状态（主题/认证/弹窗）
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth.js'
import { usePageTransition } from '@/composables/usePageTransition.js'
import { useTheme } from '@/composables/useTheme.js'
import { useImageModal } from '@/composables/useImageModal.js'
import { useSystemStatus } from '@/composables/useSystemStatus.js'
import { useSidebarIndicator } from '@/composables/useSidebarIndicator.js'
import { useAiChatSessions } from '@/composables/useAiChatSessions.js'
import { useWorkspaceNav } from '@/composables/useWorkspaceNav.js'
import { useChatSession } from '@/composables/useChatSession.js'
import { useToast } from '@/composables/useToast.js'
import { useProjects } from '@/composables/useProjects.js'
import SidebarNav from '@/components/workspace/SidebarNav.vue'
import ImageModal from '@/components/base/ImageModal.vue'
import BaseModal from '@/components/base/BaseModal.vue'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import WorkspaceBackground from '@/components/workspace/WorkspaceBackground.vue'
import AnswerInputModal from '@/components/workspace/AnswerInputModal.vue'
import WorkspaceView from '@/views/app/WorkspaceView.vue'
import Dashboard from '@/views/app/DashboardView.vue'
import ReviewView from '@/views/app/ReviewView.vue'
import ErrorBank from '@/views/app/ErrorBankView.vue'
import ChatView from '@/views/app/ChatView.vue'
import SettingsView from '@/views/app/SettingsView.vue'
import NoteView from '@/views/app/NoteView.vue'
import ChatPage from '@/views/app/ChatPageView.vue'

// ── 全局 Composables ────────────────────────────────────
const router = useRouter()
const { currentUser, clearCurrentUser } = useAuth()
const { loading: globalLoading } = usePageTransition()
const { isDark, toggleTheme, initTheme } = useTheme()
const { pushToast } = useToast()
const {
  projects, activeQuestionProjectId, activeNoteProjectId, loadingProjects,
  loadProjects, setActiveProject, createAndSelectProject, renameProject, removeProject,
} = useProjects()
const { modalOpen, modalSrc, modalScale, closeModal } = useImageModal()
const { doFetchStatus, doFetchModelOptions } = useSystemStatus()
const {
  navRef, navBtnRefs, indicatorStyle, indicatorTransition,
  chatListRef, chatBtnRefs, chatIndicatorStyle, chatIndicatorTransition,
  updateIndicator: _updateIndicator,
} = useSidebarIndicator()
const {
  aiChatSessions, activeAiChatId,
  chatMenuOpenId, renamingChatId, renameText,
  loadAiChatSessions, createAiChat: _createAiChat, selectAiChat: _selectAiChat,
  toggleChatMenu, closeChatMenu,
  startRenameChat, confirmRenameChat, deleteAiChat,
} = useAiChatSessions(pushToast)
const {
  currentView, currentSettingsSubView, setSettingsSubView,
  lastWorkspaceView, collapsedGroups, chatCollapsed,
  sidebarMode, isMobile, canHover, mobileDrawerOpen, toggleSidebar, closeDrawer,
  NAV_GROUPS, WORKSPACE_VIEWS, SETTINGS_NAV_ITEMS, navigateToHome,
} = useWorkspaceNav()

// ── 锁定滚动 ──────────────────────────────────────────
watch(mobileDrawerOpen, (val) => {
  if (val) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
}, { immediate: true })
const {
  answerModalOpen, answerModalText, answerModalSaving,
  saveAnswerAndChat,
} = useChatSession()

// ── 认证 ────────────────────────────────────────────────
const theme = computed(() => isDark.value ? 'dark' : 'light')
const userMenuOpen = ref(false)
const projectDialogOpen = ref(false)
const projectDialogName = ref('')
const projectDialogType = ref('question')
const projectDialogMode = ref('create')
const projectDialogTarget = ref(null)
const projectDialogSaving = ref(false)
const deleteProjectDialogOpen = ref(false)
const deleteProjectTarget = ref(null)
const deleteProjectSaving = ref(false)
const projectDialogTitle = computed(() => {
  if (projectDialogMode.value === 'rename') return '重命名'
  return projectDialogType.value === 'note' ? '新建笔记本' : '新建错题库'
})
const projectDialogPlaceholder = computed(() => projectDialogType.value === 'note' ? '比如：语文笔记、数学公式' : '比如：数学错题、语文错题')
const sidebarActiveProjectId = computed(() =>
  currentView.value === 'notes' ? activeNoteProjectId.value : activeQuestionProjectId.value
)

const handleLogout = async () => {
  try { await fetch('/api/auth/logout', { method: 'POST' }) } catch (_) { }
  clearCurrentUser()
  pushToast('success', '已退出登录')
  router.push('/auth')
}

// ── 指示器更新 ──────────────────────────────────────────
const updateIndicator = (animate = true) => {
  _updateIndicator(currentView.value, activeAiChatId.value, NAV_GROUPS, collapsedGroups.value, animate)
}

watch(currentView, () => nextTick(updateIndicator))
watch(collapsedGroups, () => {
  updateIndicator(false)
  nextTick(() => updateIndicator(false))
}, { deep: true })

// ── AI 独立对话包装 ────────────────────────────────────
const createAiChat = () => _createAiChat(currentView)
const selectAiChat = (s) => _selectAiChat(s, currentView)

// ── 视图切换包装 ──────────────────────────────────────
const updateCurrentView = (v) => {
  currentView.value = v
}

const createRefSetter = (target) => (value) => {
  target.value = value
}

const updateCurrentSettingsSubView = (v) => {
  setSettingsSubView(v)
}

const updateCollapsedGroups = createRefSetter(collapsedGroups)
const updateChatCollapsed = createRefSetter(chatCollapsed)
const updateUserMenuOpen = createRefSetter(userMenuOpen)
const updateChatMenuOpenId = createRefSetter(chatMenuOpenId)
const updateRenameText = createRefSetter(renameText)
const updateRenamingChatId = createRefSetter(renamingChatId)
const updateNavRef = createRefSetter(navRef)
const updateChatListRef = createRefSetter(chatListRef)

const openProjectDialog = (projectType = 'question') => {
  projectDialogMode.value = 'create'
  projectDialogTarget.value = null
  projectDialogType.value = projectType === 'note' ? 'note' : 'question'
  projectDialogName.value = ''
  projectDialogOpen.value = true
  nextTick(() => {
    document.querySelector('[data-project-name-input] input')?.focus()
  })
}

const closeProjectDialog = () => {
  if (projectDialogSaving.value) return
  projectDialogOpen.value = false
  projectDialogName.value = ''
  projectDialogTarget.value = null
}

const openRenameProjectDialog = (project) => {
  if (!project || project.is_default) return
  projectDialogMode.value = 'rename'
  projectDialogTarget.value = project
  projectDialogType.value = project.project_type === 'note' ? 'note' : 'question'
  projectDialogName.value = project.name || ''
  projectDialogOpen.value = true
  nextTick(() => {
    const input = document.querySelector('[data-project-name-input] input')
    input?.focus()
    input?.select()
  })
}

const handleCreateProject = async () => {
  const name = projectDialogName.value.trim()
  if (!name || projectDialogSaving.value) return
  projectDialogSaving.value = true
  try {
    if (projectDialogMode.value === 'rename') {
      await renameProject(projectDialogTarget.value.id, name)
      pushToast('success', '项目已重命名')
    } else {
      await createAndSelectProject(name, projectDialogType.value)
      pushToast('success', '项目已创建')
    }
    projectDialogOpen.value = false
    projectDialogName.value = ''
    projectDialogTarget.value = null
  } catch (e) {
    pushToast('error', e instanceof Error ? e.message : (projectDialogMode.value === 'rename' ? '重命名失败' : '创建项目失败'))
  } finally {
    projectDialogSaving.value = false
  }
}

const handleDeleteProject = async (project) => {
  if (!project || project.is_default) return
  deleteProjectTarget.value = project
  deleteProjectDialogOpen.value = true
}

const closeDeleteProjectDialog = () => {
  if (deleteProjectSaving.value) return
  deleteProjectDialogOpen.value = false
  deleteProjectTarget.value = null
}

const confirmDeleteProject = async () => {
  const project = deleteProjectTarget.value
  if (!project || project.is_default || deleteProjectSaving.value) return
  deleteProjectSaving.value = true
  try {
    await removeProject(project.id)
    deleteProjectDialogOpen.value = false
    deleteProjectTarget.value = null
    pushToast('success', '项目已删除')
  } catch (e) {
    pushToast('error', e instanceof Error ? e.message : '删除项目失败')
  } finally {
    deleteProjectSaving.value = false
  }
}

// ── 键盘事件 ────────────────────────────────────────────
const onKeydown = (e) => {
  if (e.key === 'Escape' && modalOpen.value) closeModal()
}

// ── 视图切换 ────────────────────────────────────────────
watch(currentView, (newView) => {
  if (newView === 'ai-chat') loadAiChatSessions()
})

// ── 生命周期 ────────────────────────────────────────────
onMounted(() => {
  initTheme()
  document.addEventListener('keydown', onKeydown)
  document.addEventListener('click', closeChatMenu)
  loadAiChatSessions()
  loadProjects().catch((e) => pushToast('error', e instanceof Error ? e.message : '加载项目失败'))
  nextTick(updateIndicator)
  watch(() => activeAiChatId.value, () => nextTick(updateIndicator))

  if (!globalLoading.value) {
    doFetchStatus()
    doFetchModelOptions()
  } else {
    const unwatch = watch(globalLoading, (val) => {
      if (!val) { doFetchStatus(); doFetchModelOptions(); unwatch() }
    })
  }
})

onBeforeUnmount(() => {
  document.body.style.overflow = ''
  document.removeEventListener('keydown', onKeydown)
  document.removeEventListener('click', closeChatMenu)
})
</script>

<template>
  <div
    class="flex h-screen w-full overflow-hidden bg-slate-50 dark:bg-[#0c0c0e] font-sans text-slate-900 dark:text-slate-300 relative transition-colors duration-200">

    <WorkspaceBackground />

    <!-- 移动端遮罩 -->
    <Transition enter-active-class="transition duration-[var(--mask-transition-duration)] ease-out"
      enter-from-class="opacity-0" enter-to-class="opacity-100"
      leave-active-class="transition duration-[var(--mask-transition-duration)] ease-out" leave-from-class="opacity-100"
      leave-to-class="opacity-0">
      <div v-if="isMobile && mobileDrawerOpen"
        class="fixed inset-0 z-[15] bg-black/40 dark:bg-black/60 backdrop-blur-md" @click="closeDrawer"></div>
    </Transition>

    <!-- 侧边栏导航 -->
    <SidebarNav :current-view="currentView" :current-settings-sub-view="currentSettingsSubView"
      :settings-nav-items="SETTINGS_NAV_ITEMS" :last-workspace-view="lastWorkspaceView" :current-user="currentUser"
      :is-dark="isDark" :theme="theme" :nav-groups="NAV_GROUPS" :workspace-views="WORKSPACE_VIEWS"
      :collapsed-groups="collapsedGroups" :nav-btn-refs="navBtnRefs" :indicator-style="indicatorStyle"
      :indicator-transition="indicatorTransition" :chat-collapsed="chatCollapsed" :ai-chat-sessions="aiChatSessions"
      :active-ai-chat-id="activeAiChatId" :chat-list-ref="chatListRef" :chat-btn-refs="chatBtnRefs"
      :chat-indicator-style="chatIndicatorStyle" :chat-indicator-transition="chatIndicatorTransition"
      :chat-menu-open-id="chatMenuOpenId" :renaming-chat-id="renamingChatId" :rename-text="renameText"
      :projects="projects" :active-project-id="sidebarActiveProjectId" :loading-projects="loadingProjects"
      :user-menu-open="userMenuOpen" :sidebar-mode="sidebarMode" :is-mobile="isMobile" :can-hover="canHover"
      :mobile-drawer-open="mobileDrawerOpen" @update:current-view="updateCurrentView"
      @update:current-settings-sub-view="updateCurrentSettingsSubView" @update:collapsed-groups="updateCollapsedGroups"
      @update:chat-collapsed="updateChatCollapsed" @update:user-menu-open="updateUserMenuOpen"
      @update:chat-menu-open-id="updateChatMenuOpenId" @update:rename-text="updateRenameText"
      @update:renaming-chat-id="updateRenamingChatId" @update:nav-ref="updateNavRef"
      @update:chat-list-ref="updateChatListRef" @navigate-home="navigateToHome" @logout="handleLogout"
      @toggle-theme="toggleTheme" @select-project="setActiveProject" @create-project="openProjectDialog"
      @rename-project="openRenameProjectDialog" @delete-project="handleDeleteProject" @create-ai-chat="createAiChat"
      @select-ai-chat="selectAiChat" @start-rename-chat="startRenameChat" @confirm-rename-chat="confirmRenameChat"
      @delete-ai-chat="deleteAiChat" @toggle-chat-menu="toggleChatMenu" @toggle-sidebar="toggleSidebar" />

    <!-- ================== 右侧整体区域 ================== -->
    <div
      class="relative z-10 flex-1 flex flex-col overflow-hidden lg:pt-3 lg:pr-3 transition-all duration-[var(--sidebar-transition-duration)] ease-[var(--sidebar-transition-timing)]"
      :class="[
        isMobile ? 'ml-0' : (sidebarMode === 'collapsed-icon' ? 'lg:ml-16' : 'lg:ml-64')
      ]">
      <!-- 原内容区 -->
      <div class="flex-1 relative overflow-hidden">
        <Transition name="view-fade" mode="out-in">
          <WorkspaceView v-if="currentView === 'workspace' || currentView === 'workspace_review'" key="workspace"
            :theme="theme" />
          <ReviewView v-else-if="currentView === 'review'" key="review" />
          <Dashboard v-else-if="currentView === 'dashboard'" key="dashboard" />
          <ErrorBank v-else-if="currentView === 'error-bank'" key="error-bank" />
          <SettingsView v-else-if="currentView === 'settings'" key="settings" :section="currentSettingsSubView" />
          <ChatView v-else-if="currentView === 'chat'" key="chat" />
          <NoteView v-else-if="currentView === 'notes'" key="notes" />
          <ChatPage v-else-if="currentView === 'ai-chat'" key="ai-chat" />
        </Transition>
      </div>

      <!-- GitHub Issue 链接 (非浮动，作为底部同级元素正常占位) -->
      <div class="flex-shrink-0 flex justify-end py-2 pr-4 md:pr-2 text-xs text-slate-500/70 z-20">
        <a href="https://github.com/xiaozhejiya/error_correction/issues" target="_blank" rel="noopener noreferrer"
          class="flex items-center gap-1.5 hover:text-slate-300 transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path
              d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
            <path d="M9 18c-4.51 2-5-2-7-2" />
          </svg>
          反馈问题 / GitHub Issues
        </a>
      </div>
    </div>

    <!-- 全局弹窗 -->
    <Teleport to="body">
      <ImageModal :open="modalOpen" :src="modalSrc" :scale="modalScale" @close="closeModal"
        @update:scale="(s) => modalScale = s" />
      <AnswerInputModal :open="answerModalOpen" :text="answerModalText" :saving="answerModalSaving"
        @update:open="(v) => answerModalOpen = v" @update:text="(v) => answerModalText = v"
        @confirm="saveAnswerAndChat" />
      <BaseModal :open="projectDialogOpen" :title="projectDialogTitle" icon="fa-folder-plus" iconBg="accent-bg-soft"
        iconClass="accent-text" maxWidth="max-w-[28rem]" bodyClass="px-6 pb-3 pt-1" @close="closeProjectDialog">
        <form class="space-y-4" @submit.prevent="handleCreateProject">
          <BaseInput v-model="projectDialogName" label="名称" :placeholder="projectDialogPlaceholder" maxlength="100"
            data-project-name-input />
        </form>
        <template #footer>
          <BaseButton variant="secondary" size="sm" :disabled="projectDialogSaving" @click="closeProjectDialog">
            取消
          </BaseButton>
          <BaseButton variant="primary" size="sm" :disabled="projectDialogSaving || !projectDialogName.trim()"
            @click="handleCreateProject">
            {{ projectDialogSaving ? '处理中...' : (projectDialogMode === 'rename' ? '保存' : '创建') }}
          </BaseButton>
        </template>
      </BaseModal>
      <BaseModal :open="deleteProjectDialogOpen" title="删除项目" icon="fa-trash" iconBg="bg-rose-50 dark:bg-rose-500/10"
        iconClass="text-rose-600 dark:text-rose-300" maxWidth="max-w-[28rem]" bodyClass="px-6 pb-3 pt-1"
        @close="closeDeleteProjectDialog">
        <div class="space-y-3 text-sm text-slate-600 dark:text-[#aeb6c2]">
          <p>
            确定删除“<span class="font-semibold text-slate-900 dark:text-[#f7f8f8]">{{ deleteProjectTarget?.name
              }}</span>”吗？
          </p>
          <p class="text-xs text-slate-400 dark:text-[#737b86]">
            默认项目不能删除；已有内容的项目会被系统阻止删除。
          </p>
        </div>
        <template #footer>
          <BaseButton variant="secondary" size="sm" :disabled="deleteProjectSaving" @click="closeDeleteProjectDialog">
            取消
          </BaseButton>
          <BaseButton variant="primary" size="sm" :disabled="deleteProjectSaving" @click="confirmDeleteProject">
            {{ deleteProjectSaving ? '删除中...' : '删除' }}
          </BaseButton>
        </template>
      </BaseModal>
    </Teleport>
  </div>
</template>

<style>
::view-transition-old(root),
::view-transition-new(root) {
  animation: none;
  mix-blend-mode: normal;
}

/* 视图切换淡入淡出 */
.view-fade-enter-active,
.view-fade-leave-active {
  transition: opacity 0.15s ease-out;
}

.view-fade-enter-from,
.view-fade-leave-to {
  opacity: 0;
}
</style>
