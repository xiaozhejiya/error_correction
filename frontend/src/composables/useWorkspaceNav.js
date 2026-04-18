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
  { id: 'profile', label: '用户资料设置', icon: 'fa-user-gear' },
  { id: 'api', label: 'API 设置', icon: 'fa-plug-circle-bolt' },
]

const NAV_GROUPS = [
  {
    label: null,
    items: [
      { id: 'workspace', label: '录入工作台', icon: 'fa-wand-magic-sparkles', match: (v) => WORKSPACE_VIEWS.has(v) },
    ],
  },
  {
    label: '数据',
    collapsible: true,
    items: [
      { id: 'dashboard', label: '数据面板', icon: 'fa-chart-pie', match: (v) => v === 'dashboard' },
      { id: 'error-bank', label: '错题库', icon: 'fa-database', match: (v) => v === 'error-bank' },
      { id: 'notes', label: '笔记库', icon: 'fa-book-open', match: (v) => v === 'notes' },
    ],
  },
  {
    label: '更多',
    collapsible: true,
    items: [
      { id: 'review-disabled', label: '刷题', icon: 'fa-clock-rotate-left', disabled: true },
    ],
  },
]

// ── 模块级单例状态 ──────────────────────────────────────
const collapsedGroups = ref({})
const chatCollapsed = ref(false)
const lastWorkspaceView = ref('workspace')
let initialized = false

export function useWorkspaceNav() {
  const router = useRouter()
  const route = useRoute()

  const currentView = computed({
    get() {
      // 处理笔记详情页路由 /app/notes/:id
      if (route.path.startsWith('/app/notes/')) {
        return 'notes'
      }
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
    NAV_GROUPS, WORKSPACE_VIEWS, SETTINGS_NAV_ITEMS,
    navigateToHome,
  }
}
