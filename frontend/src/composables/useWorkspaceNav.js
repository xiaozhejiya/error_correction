/**
 * useWorkspaceNav.js
 * 工作台视图路由 + 侧边栏导航配置 — 单例 composable
 */
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const DEFAULT_SETTINGS_SUBVIEW = 'profile'

const VIEW_TO_PATH = {
  workspace: '/app/workspace',
  workspace_review: '/app/workspace/review',
  dashboard: '/app/dashboard',
  review: '/app/review',
  'error-bank': '/app/error-bank',
  notes: '/app/notes',
  'ai-chat': '/app/ai-chat',
  settings: `/app/settings/${DEFAULT_SETTINGS_SUBVIEW}`,
  'split-history': '/app/split-history',
  chat: '/app/chat',
}

const WORKSPACE_VIEWS = new Set(['workspace', 'workspace_review', 'split-history'])

const SETTINGS_NAV_ITEMS = [
  { id: 'quota', label: '免费额度', icon: 'fa-gauge-high' },
  { id: 'appearance', label: '外观设置', icon: 'fa-palette' },
  { id: 'profile', label: '用户资料设置', icon: 'fa-user-gear' },
  { id: 'api', label: 'API 设置', icon: 'fa-plug-circle-bolt' },
]

const NAV_GROUPS = [
  {
    label: null,
    items: [
      { id: 'workspace', label: '录入工作台', icon: 'fa-wand-magic-sparkles', match: (v) => WORKSPACE_VIEWS.has(v) },
      { id: 'dashboard', label: '数据面板', icon: 'fa-chart-pie', match: (v) => v === 'dashboard' },
    ],
  },
]

// ── 模块级单例状态 ──────────────────────────────────────
let initialized = false
const collapsedGroups = ref({})
const chatCollapsed = ref(false)
const lastWorkspaceView = ref('workspace')

// 响应式状态
const isMobile = ref(false)
const canHover = ref(true)
const sidebarMode = ref('expanded') // 'expanded' | 'collapsed-icon' (仅大屏)
const mobileDrawerOpen = ref(false) // (仅小屏)

const checkMobile = () => {
  if (typeof window !== 'undefined') {
    const mobile = window.innerWidth < 1024
    if (mobile !== isMobile.value) {
      isMobile.value = mobile
      // 从大屏切换到小屏时，强制关闭抽屉
      if (mobile) {
        mobileDrawerOpen.value = false
      }
    }
    canHover.value = window.matchMedia('(hover: hover)').matches
  }
}

// 切换逻辑
const toggleSidebar = () => {
  if (isMobile.value) {
    mobileDrawerOpen.value = !mobileDrawerOpen.value
  } else {
    sidebarMode.value = sidebarMode.value === 'expanded' ? 'collapsed-icon' : 'expanded'
    if (typeof window !== 'undefined') {
      localStorage.setItem('sidebar-mode', sidebarMode.value)
    }
  }
}

const closeDrawer = () => {
  if (isMobile.value) {
    mobileDrawerOpen.value = false
  }
}

export function useWorkspaceNav() {
  const router = useRouter()
  const route = useRoute()

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

  const currentSettingsSubView = computed(() => {
    if (currentView.value !== 'settings') return DEFAULT_SETTINGS_SUBVIEW
    const subview = String(route.params.subview || '').trim()
    return SETTINGS_NAV_ITEMS.some(item => item.id === subview)
      ? subview
      : DEFAULT_SETTINGS_SUBVIEW
  })

  const setSettingsSubView = (subview, { replace = false } = {}) => {
    const target = SETTINGS_NAV_ITEMS.some(item => item.id === subview)
      ? subview
      : DEFAULT_SETTINGS_SUBVIEW
    const path = `/app/settings/${target}`
    if (route.path === path) return
    return replace ? router.replace(path) : router.push(path)
  }

  if (!initialized) {
    initialized = true

    if (typeof window !== 'undefined') {
      checkMobile()
      window.addEventListener('resize', checkMobile)

      const savedMode = localStorage.getItem('sidebar-mode')
      if (savedMode === 'expanded' || savedMode === 'collapsed-icon') {
        sidebarMode.value = savedMode
      }
    }

    watch(currentView, (v) => {
      if (WORKSPACE_VIEWS.has(v)) lastWorkspaceView.value = v
    }, { immediate: true })
  }

  watch(
    () => [route.params.view, route.params.subview],
    ([view, subview]) => {
      if (view === 'settings' && !subview) {
        setSettingsSubView(DEFAULT_SETTINGS_SUBVIEW, { replace: true })
      }
    },
    { immediate: true },
  )

  const navigateToHome = () => {
    document.body.style.transition = 'opacity 0.25s ease, transform 0.25s ease'
    document.body.style.opacity = '0'
    document.body.style.transform = 'translateY(-6px)'
    setTimeout(() => { window.location.href = '/' }, 260)
  }

  return {
    currentView, currentSettingsSubView, setSettingsSubView,
    lastWorkspaceView, collapsedGroups, chatCollapsed,
    sidebarMode, isMobile, canHover, mobileDrawerOpen, toggleSidebar, closeDrawer,
    NAV_GROUPS, WORKSPACE_VIEWS, SETTINGS_NAV_ITEMS, navigateToHome,
  }
}
