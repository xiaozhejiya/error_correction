/**
 * router/index.js
 * Vue Router 路由配置
 *
 * 三种布局：home（首页）、auth（认证页）、app（工作台）
 * 路由守卫：认证检查 + 跨布局过渡动画
 */
import { nextTick } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '@/composables/useAuth.js'
import { usePageTransition } from '@/composables/usePageTransition.js'

// ── 路由表 ──────────────────────────────────────────────
const routes = [
  // 首页
  {
    path: '/',
    component: () => import('@/views/HomeView.vue'),
    meta: { layout: 'home' },
  },
  // 认证页（登录 / 注册）
  {
    path: '/auth',
    component: () => import('@/views/auth/AuthLayout.vue'),
    redirect: '/auth/login',
    meta: { layout: 'auth' },
    children: [
      { path: 'login',    component: () => import('@/views/auth/LoginView.vue'), meta: { order: 0, layout: 'auth' } },
      { path: 'register', component: () => import('@/views/auth/RegisterView.vue'), meta: { order: 1, layout: 'auth' } },
    ],
  },
  // 笔记详情页（独立路由，支持浏览器前进后退）
  // 注意：必须放在 /app/:view?/:subview? 之前，否则会被通用路由匹配
  {
    path: '/app/notes/:id',
    component: () => import('@/views/app/AppLayout.vue'),
    meta: { requiresAuth: true, layout: 'app', noteDetail: true },
  },
  // 工作台（需要登录，:view 参数决定子视图）
  {
    path: '/app/:view?/:subview?',
    component: () => import('@/views/app/AppLayout.vue'),
    meta: { requiresAuth: true, layout: 'app' },
  },
  // 兜底：未匹配路径重定向到工作台
  {
    path: '/:pathMatch(.*)*',
    redirect: '/app/workspace',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ── 前置守卫：认证检查 + 过渡动画 ─────────────────────────
router.beforeEach(async (to, from) => {
  const { currentUser, authChecked, refreshCurrentUser } = useAuth()

  // 首次导航时请求登录态
  if (!authChecked.value) {
    await refreshCurrentUser()
  }

  // 未登录 → 拦截到登录页
  if (to.meta.requiresAuth && !currentUser.value) {
    return '/auth/login'
  }

  // 已登录 → 跳过认证页
  if (to.path.startsWith('/auth') && currentUser.value) {
    return '/app/workspace'
  }

  // 跨布局跳转：先让 loading 遮罩完全进场，再放行路由
  const fromLayout = from.meta.layout || ''
  const toLayout = to.meta.layout || ''
  if (fromLayout && toLayout && fromLayout !== toLayout) {
    const { show } = usePageTransition()
    await show()
  }
})

// ── 后置守卫：跨布局过渡淡出 ──────────────────────────────
router.afterEach(async (to, from) => {
  const fromLayout = from.meta.layout || ''
  const toLayout = to.meta.layout || ''
  if (fromLayout && toLayout && fromLayout !== toLayout) {
    const { hide } = usePageTransition()
    await nextTick()  // 等待 DOM 更新，确保新页面已挂载
    hide(500)         // 延迟淡出，给渲染留缓冲时间
  }
})

export default router
