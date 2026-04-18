<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useTheme } from '@/composables/useTheme.js'

const { initTheme, setTheme, isDark } = useTheme()

// 首页固定深色：记住用户原始主题，离开时恢复
let savedTheme = null

import HomeHeader from '@/components/home/HomeHeader.vue'
import HomeSideNav from '@/components/home/HomeSideNav.vue'
import HomeHero from '@/views/home/HomeHero.vue'
import HomeFeatures from '@/views/home/HomeFeatures.vue'
import HomeWorkflow from '@/views/home/HomeWorkflow.vue'
import HomeDemo from '@/views/home/HomeDemo.vue'
import HomeFooter from '@/components/home/HomeFooter.vue'

const SECTIONS = [
  { id: 'hero',     label: '首页' },
  { id: 'features', label: '核心功能' },
  { id: 'workflow', label: '工作流' },
  { id: 'demo',     label: '效果演示' },
  { id: 'cta',      label: '立即开始' },
]

// Refs
const activeSection = ref('hero')
const backToTopVisible = ref(false)
const navScrolled = ref(false)
const indicatorTop = ref(44)
// Cleanup holders
let wheelUnlisten = null
let scrollUnlisten = null
let revealObserver = null

// ── Wheel snap scroll ──
let wheelLock = false

function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3)
}

function scrollToY(target, duration) {
  const start = window.scrollY
  const dist = target - start
  let startTime = null
  function step(ts) {
    if (!startTime) startTime = ts
    const progress = Math.min((ts - startTime) / duration, 1)
    window.scrollTo(0, start + dist * easeOutCubic(progress))
    if (progress < 1) requestAnimationFrame(step)
    else wheelLock = false
  }
  requestAnimationFrame(step)
}

function getSectionTops() {
  const ids = SECTIONS.map(s => s.id)
  return ids.map(id => {
    if (id === 'hero') return 0
    const el = document.getElementById(id)
    return el ? Math.round(el.getBoundingClientRect().top + window.scrollY) : null
  }).filter(v => v !== null)
}

function onWheel(e) {
  if (wheelLock) return
  const y = window.scrollY
  const tops = getSectionTops()
  if (tops.length < 2) return
  const dir = e.deltaY > 0 ? 1 : -1

  // 找到当前所在 section
  let cur = 0
  for (let i = tops.length - 1; i >= 0; i--) {
    if (y >= tops[i] - 10) { cur = i; break }
  }

  const lastIdx = tops.length - 1

  // 只在 Hero(0) ↔ Features(1) 边界做 snap，其他正常滚动
  const isHeroBoundary = (cur === 0 && dir === 1) || (cur === 1 && dir === -1 && y <= tops[1] + 50)

  if (isHeroBoundary) {
    e.preventDefault()
    const next = Math.max(0, Math.min(lastIdx, cur + dir))
    if (next === cur) return
    wheelLock = true
    scrollToY(tops[next], 800)
  }
  // 其他位置：不 preventDefault，浏览器正常滚动
}

// ── Scroll handler ──
let ticking = false

function onScroll() {
  const y = window.scrollY

  // Hero fade + 3D tilt
  const stickyHero = document.getElementById('sticky-hero')
  if (stickyHero) {
    const p = Math.min(y / (window.innerHeight * 0.7), 1)
    stickyHero.style.opacity = 1 - p
    const rotateX = p * 28
    const scale = 1 - p * 0.12
    const heroEl = document.getElementById('hero')
    if (heroEl) {
      heroEl.style.transform = `perspective(900px) rotateX(${rotateX}deg) scale(${scale})`
    }
  }

  // Back to top
  backToTopVisible.value = y > 400

  // Nav scroll state
  navScrolled.value = activeSection.value !== 'hero'

  // Section nav update
  updateNav()

  ticking = false
}

function onScrollThrottled() {
  if (!ticking) {
    requestAnimationFrame(onScroll)
    ticking = true
  }
}

// ── Section nav ──
const DOT_SIZE = 40

function updateNav() {
  const { scrollY, innerHeight } = window
  const scrollHeight = document.documentElement.scrollHeight
  const probe = scrollY + innerHeight / 3
  let next = SECTIONS[0].id

  if (innerHeight + scrollY >= scrollHeight - 100) {
    next = SECTIONS[SECTIONS.length - 1].id
  } else {
    for (let i = SECTIONS.length - 1; i >= 0; i--) {
      const el = document.getElementById(SECTIONS[i].id)
      if (el && probe >= el.getBoundingClientRect().top + scrollY) {
        next = SECTIONS[i].id; break
      }
    }
  }

  if (next === activeSection.value) return
  activeSection.value = next
  const idx = SECTIONS.findIndex(s => s.id === activeSection.value)
  indicatorTop.value = idx * DOT_SIZE + 44
}

function scrollToSection(id) {
  if (id === 'hero') {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } else {
    const el = document.getElementById(id)
    if (el) {
      const targetY = el.getBoundingClientRect().top + window.scrollY
      window.scrollTo({ top: targetY, behavior: 'smooth' })
    }
  }
}

function scrollToSectionSnap(id) {
  if (id === 'hero') {
    scrollToY(0, 1000)
  } else {
    const el = document.getElementById(id)
    if (el) scrollToY(el.getBoundingClientRect().top + window.scrollY, 1000)
  }
}

// ── Reveal observer ──
function setupRevealObserver() {
  const observerOptions = { threshold: 0.01, rootMargin: '0px 0px 0px 0px' }
  revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('active')
        revealObserver.unobserve(entry.target)
      }
    })
  }, observerOptions)

  document.querySelectorAll('.reveal').forEach(el => {
    const rect = el.getBoundingClientRect()
    if (rect.top < window.innerHeight && rect.bottom > 0) {
      el.classList.add('active')
    } else {
      revealObserver.observe(el)
    }
  })
}

onMounted(async () => {
  initTheme()

  // 首页强制深色模式
  savedTheme = isDark.value ? 'dark' : 'light'
  if (!isDark.value) setTheme(true)

  // 不再锁定 body overflow，中间页面允许正常滚动

  await nextTick()

  // Wheel listener with passive: false
  const wheelHandler = onWheel
  window.addEventListener('wheel', wheelHandler, { passive: false })
  wheelUnlisten = () => window.removeEventListener('wheel', wheelHandler)

  // Scroll listener
  window.addEventListener('scroll', onScrollThrottled, { passive: true })
  scrollUnlisten = () => window.removeEventListener('scroll', onScrollThrottled)

  // Mousemove listener
  // Hero anim
  setTimeout(() => {
    document.querySelectorAll('.hero-anim').forEach(el => el.classList.add('is-visible'))
  }, 100)

  // Reveal observer
  setupRevealObserver()

  // MathJax typeset
  await nextTick()
  window.MathJax?.typesetPromise?.()

  // Initial nav state
  updateNav()
})

onUnmounted(() => {
  // 离开首页时恢复用户原有主题
  if (savedTheme === 'light') setTheme(false)

  if (wheelUnlisten) wheelUnlisten()
  if (scrollUnlisten) scrollUnlisten()
  if (revealObserver) revealObserver.disconnect()
})
</script>

<template>
  <div class="min-h-screen bg-slate-50 text-slate-900 dark:bg-[#0A0A0F] dark:text-slate-300 selection:bg-blue-200 dark:selection:bg-indigo-500/30 page-enter">

    <!-- 🌟 真正的全局绝对底层固定背景 🌟 -->
    <!-- 将背景移出任何可能带有 transform / overflow-hidden 的包裹层，确保 fixed 完美生效 -->
    <HomeHeader
      :navScrolled="navScrolled"
      :activeSection="activeSection"
      :sections="SECTIONS"
      @scrollToSection="scrollToSectionSnap"
    />
    <HomeSideNav
      :activeSection="activeSection"
      :sections="SECTIONS"
      :showBackToTop="backToTopVisible"
      @scrollToSection="scrollToSectionSnap"
      @back-to-top="scrollToY(0, 1000)"
    />

    <!-- 主内容包裹层 -->
    <div class="relative">

      <HomeHero @scrollToSection="scrollToSectionSnap" />

      <!-- ② 滚动叠盖层（实色背景完全遮住 Hero sticky） -->
      <div class="relative z-10 overflow-hidden" style="background: #0A0A0F;">

        <!-- 背景装饰：波纹纹理 -->
        <div class="absolute inset-0 pointer-events-none z-0">
          <div class="home-bg-topo"></div>
        </div>

        <HomeFeatures />

        <HomeWorkflow />

        <HomeDemo />

        <HomeFooter />

        <!-- 全局 Footer -->
        <div class="border-t border-white/[0.06] py-4 relative z-10 bg-[#0A0A0F]/50 w-full mt-auto">
          <div class="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6 text-xs text-white/30 px-4">
            <div class="flex items-center gap-2">
              <div class="footer-logo relative overflow-hidden p-1.5 rounded-lg flex items-center justify-center">
                <span class="footer-logo__grid absolute inset-0 pointer-events-none"></span>
                <img src="/logo.svg" class="relative w-4 h-4 brightness-0 invert" alt="logo" />
              </div>
              <span class="font-semibold text-white/50 tracking-wide">智卷错题本</span>
            </div>
            <p class="text-center">© 2026 Intelligent Error Book Generation System. All rights reserved.</p>
            <div class="flex gap-6 pr-12 md:pr-0">
              <a href="#" class="hover:text-white/70 transition-colors">架构文档</a>
              <a href="#" class="hover:text-white/70 transition-colors">隐私政策</a>
              <a href="#" class="hover:text-white/70 transition-colors">联系我们</a>
            </div>
          </div>
        </div>

      </div><!-- /滚动叠盖层 -->

    </div><!-- /主内容包裹层 -->

  </div>
</template>

<style>
/* Home page always uses dark mode class - set in onMounted */

@keyframes pageEnter {
  from { opacity: 0; }
  to   { opacity: 1; }
}

.page-enter {
  animation: pageEnter 0.3s ease forwards;
}

@keyframes blob {
  0% { transform: translate(0px, 0px) scale(1); }
  33% { transform: translate(30px, -50px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
  100% { transform: translate(0px, 0px) scale(1); }
}
.animate-blob { animation: blob 10s infinite alternate; }
.animation-delay-2000 { animation-delay: 2s; }
.animation-delay-4000 { animation-delay: 4s; }

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}
.animate-float { animation: float 6s ease-in-out infinite; }

@keyframes scan {
  0% { transform: translateY(-100%); }
  100% { transform: translateY(100%); }
}
.animate-scan { animation: scan 3s ease-in-out infinite; }

/* 动态玻璃态面板 — 统一为 brand-btn 风格 */
.glass-panel {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-top-color: rgba(255, 255, 255, 0.15);
  border-bottom-color: rgba(255, 255, 255, 0.03);
}

/* 平滑滚动时补偿固定导航栏高度 */
html { scroll-padding-top: 80px; }

/* 禁用浏览器默认 View Transitions 淡出 */
::view-transition-old(root),
::view-transition-new(root) {
  animation: none;
  mix-blend-mode: normal;
}

/* 初始隐藏，用于实现加载动画 */
.hero-anim {
  opacity: 0;
  transform: translateY(40px);
  transition: opacity 1s cubic-bezier(0.2, 0.8, 0.2, 1), transform 1s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.hero-anim.is-visible {
  opacity: 1;
  transform: translateY(0);
}

/* 统一的 Section 进场动画 */
.reveal {
  opacity: 0;
  transform: translateY(30px);
  transition: opacity 0.8s cubic-bezier(0.4, 0, 0.2, 1), transform 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}
.reveal.active {
  opacity: 1;
  transform: translateY(0);
}

/* 滚动区背景装饰（与 Hero 一致） */
.home-bg-topo {
  position: absolute;
  inset: 0;
  opacity: 0.2;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 1000 1000' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.005' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='matrix' values='1 0 0 0 0, 0 1 0 0 0, 0 0 1 0 0, 0 0 0 10 -4' /%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' fill='none' stroke='%23ffffff' stroke-width='1' opacity='0.3'/%3E%3Cpath d='M0,100 C200,300 300,0 500,100 C700,200 800,-100 1000,100 M0,200 C250,400 350,100 550,200 C750,300 850,0 1000,200 M0,300 C300,500 400,200 600,300 C800,400 900,100 1000,300 M0,400 C350,600 450,300 650,400 C850,500 950,200 1000,400 M0,500 C400,700 500,400 700,500 C900,600 1000,300 1000,500 M0,600 C450,800 550,500 750,600 C950,700 1000,400 1000,600 M0,700 C500,900 600,600 800,700 C1000,800 1000,500 1000,700 M0,800 C550,1000 650,700 850,800 C1000,900 1000,600 1000,800 M0,900 C600,1100 700,800 900,900 C1000,1000 1000,700 1000,900' stroke='%23ffffff' stroke-width='1' fill='none' opacity='0.15' /%3E%3C/svg%3E");
  background-size: cover;
  background-position: center;
  mask-image: radial-gradient(ellipse 100% 100% at 50% 50%, black, transparent);
  -webkit-mask-image: radial-gradient(ellipse 100% 100% at 50% 50%, black, transparent);
}

.footer-logo {
  background: linear-gradient(to bottom, rgba(129, 115, 223, 0.9), rgba(99, 87, 199, 0.9));
  box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.12);
}

.footer-logo__grid {
  background-image:
    linear-gradient(to right, rgba(255, 255, 255, 0.06) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255, 255, 255, 0.06) 1px, transparent 1px);
  background-size: 8px 8px;
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
  -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
}

</style>
