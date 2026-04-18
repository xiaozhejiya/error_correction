<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTheme } from '@/composables/useTheme.js'
import HomePill from '@/components/home/HomePill.vue'
import BaseLogo from '@/components/base/BaseLogo.vue'
import BaseButton from '@/components/base/BaseButton.vue'

const { initTheme } = useTheme()
const route = useRoute()
const router = useRouter()
const transitionName = ref('auth-slide-left')

onMounted(() => {
  initTheme()
})

router.beforeEach((to, from) => {
  const toOrder = to.meta.order ?? 0
  const fromOrder = from.meta.order ?? 0
  transitionName.value = toOrder >= fromOrder ? 'auth-slide-left' : 'auth-slide-right'
})

// ── 鼠标跟随发光 ──
const brandRef = ref(null)
const featureRefs = ref([])

function handleMouseMove(e) {
  const el = brandRef.value
  if (!el) return
  // 面板级坐标（用于曲线发光）
  const rect = el.getBoundingClientRect()
  el.style.setProperty('--mx', `${e.clientX - rect.left}px`)
  el.style.setProperty('--my', `${e.clientY - rect.top}px`)
  // 每个图标的相对坐标
  featureRefs.value.forEach(item => {
    if (!item) return
    const r = item.getBoundingClientRect()
    item.style.setProperty('--ix', `${e.clientX - r.left}px`)
    item.style.setProperty('--iy', `${e.clientY - r.top}px`)
  })
}

onMounted(() => {
  brandRef.value?.addEventListener('mousemove', handleMouseMove)
})
onUnmounted(() => {
  brandRef.value?.removeEventListener('mousemove', handleMouseMove)
})

const FEATURES = [
  { icon: 'fa-camera', text: '拍照上传，AI 自动识别题目与公式' },
  { icon: 'fa-brain', text: 'LangGraph Agent 智能拆题纠错' },
  { icon: 'fa-tags', text: '知识点自动打标，构建个人图谱' },
  { icon: 'fa-file-export', text: '一键导出 Markdown / PDF 错题本' },
]

// ── 随机星星 ──
const stars = ref([])

onMounted(() => {
  const list = []
  for (let i = 0; i < 30; i++) {
    list.push({
      left: Math.random() * 100,
      top: 55 + Math.random() * 42,
      size: 1 + Math.random() * 2,
      opacity: 0.08 + Math.random() * 0.35,
      duration: 2 + Math.random() * 3,  // 2~5s
      delay: Math.random() * 4,          // 0~4s 延迟
    })
  }
  stars.value = list
})
</script>

<template>
  <div class="min-h-screen flex bg-[#0A0A0F]">

    <!-- 左侧品牌区（大屏显示） -->
    <div ref="brandRef" class="hidden lg:flex flex-col justify-between w-[52%] relative overflow-hidden p-12 bg-gradient-to-br from-[#12121a] to-[#0A0A0F]">
      <!-- 底层：紫色曲线（暗态） -->
      <svg class="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 600 800" preserveAspectRatio="none" fill="none">
        <path d="M-50,250 C120,400 280,100 420,280 C560,460 600,180 700,350" stroke="rgba(129,115,223,0.12)" stroke-width="2.5" />
        <path d="M-80,500 C80,650 240,340 400,520 C560,700 620,400 720,580" stroke="rgba(129,115,223,0.08)" stroke-width="2" />
      </svg>
      <!-- 亮层：鼠标跟随发光的紫色曲线（通过 mask 只显示鼠标附近） -->
      <div class="auth-glow-layer absolute inset-0 pointer-events-none">
        <svg class="w-full h-full" viewBox="0 0 600 800" preserveAspectRatio="none" fill="none">
          <path d="M-50,250 C120,400 280,100 420,280 C560,460 600,180 700,350" stroke="rgba(151,137,222,0.9)" stroke-width="3" style="filter: drop-shadow(0 0 14px rgba(129,115,223,0.8)) drop-shadow(0 0 40px rgba(129,115,223,0.4));" />
          <path d="M-80,500 C80,650 240,340 400,520 C560,700 620,400 720,580" stroke="rgba(151,137,222,0.7)" stroke-width="2.5" style="filter: drop-shadow(0 0 12px rgba(129,115,223,0.7)) drop-shadow(0 0 30px rgba(129,115,223,0.3));" />
        </svg>
      </div>
      <!-- 底部紫色光晕 -->
      <div class="absolute bottom-0 left-1/2 -translate-x-1/2 w-[80%] h-[200px] pointer-events-none rounded-full bg-indigo-500/[0.08] blur-[80px]"></div>

      <!-- 不规则星星 -->
      <div class="absolute inset-0 pointer-events-none">
        <div
          v-for="(s, i) in stars"
          :key="i"
          class="absolute rounded-full bg-white star-twinkle"
          :style="{
            left: s.left + '%',
            top: s.top + '%',
            width: s.size + 'px',
            height: s.size + 'px',
            '--star-opacity': s.opacity,
            animationDuration: s.duration + 's',
            animationDelay: s.delay + 's',
          }"
        ></div>
      </div>

      <!-- 右侧分割线 -->
      <div class="absolute top-0 right-0 bottom-0 w-px pointer-events-none bg-gradient-to-b from-transparent via-white/[0.08] to-transparent"></div>

      <!-- 顶部 Logo -->
      <div class="relative flex items-center gap-3">
        <BaseLogo breathe />
        <span class="text-base font-semibold text-white/80 tracking-wide">智卷错题本</span>
      </div>

      <!-- 中部主文案 -->
      <div class="relative">
        <HomePill class="mb-6" />
        <h2 class="text-4xl font-semibold text-white leading-tight mb-4 tracking-tight">
          重塑错题整理<br />
          <span class="text-transparent bg-clip-text animate-gradient-sweep" style="
            background-image: linear-gradient(to right, rgb(151, 137, 222) 0%, rgb(151, 137, 222) 20%, rgb(255, 255, 255) 50%, rgb(151, 137, 222) 80%, rgb(151, 137, 222) 100%);
            background-size: 200% auto;
          ">一键生成知识图谱</span>
        </h2>
        <p class="text-sm text-white/45 leading-relaxed max-w-sm">
          专为中学生与大学生研发。上传凌乱试卷，AI 自动完成图片分割、OCR 纠错及 LaTeX 公式还原。
        </p>

        <!-- 特性列表 — 鼠标跟随染色图标 -->
        <ul class="mt-8 space-y-4">
          <li v-for="(f, i) in FEATURES" :key="f.text" :ref="el => featureRefs[i] = el" class="flex items-center gap-3 text-sm text-white/60">
            <!-- 图标容器: 双层结构 -->
            <div class="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-xl p-px overflow-hidden">
              <!-- 默认边框 -->
              <div class="absolute inset-0 bg-white/[0.08] rounded-xl"></div>
              <!-- 鼠标跟随边框高光 -->
              <div class="pointer-events-none absolute inset-0"
                style="background: radial-gradient(80px circle at var(--ix, -500px) var(--iy, -500px), rgba(151,137,222,0.7), transparent 50%);"></div>
              <!-- 图标内部 -->
              <div class="relative h-full w-full bg-[#15151e] rounded-[11px] flex items-center justify-center">
                <!-- 白色底层图标 -->
                <i :class="`fas ${f.icon} text-xs text-white/50 absolute`"></i>
                <!-- 鼠标跟随染色图标 -->
                <div class="absolute inset-0 flex items-center justify-center"
                  style="mask-image: radial-gradient(80px circle at var(--ix, -500px) var(--iy, -500px), black 0%, transparent 100%);
                         -webkit-mask-image: radial-gradient(80px circle at var(--ix, -500px) var(--iy, -500px), black 0%, transparent 100%);">
                  <i :class="`fas ${f.icon} text-xs text-[#9789de] drop-shadow-[0_0_8px_rgba(151,137,222,0.8)]`"></i>
                </div>
              </div>
            </div>
            {{ f.text }}
          </li>
        </ul>
      </div>

      <!-- 底部版权 -->
      <div class="relative text-xs text-white/20">
        © {{ new Date().getFullYear() }} 智卷错题本 · All rights reserved
      </div>
    </div>

    <!-- 右侧表单区 -->
    <div class="flex-1 flex flex-col items-center justify-center px-4 py-12 lg:px-16 relative bg-[#0e0e16]">

      <!-- 返回主页 -->
      <div class="absolute top-6 right-6 z-10">
        <BaseButton href="/" variant="secondary" size="sm" class="flex items-center gap-2 !px-4 !py-2 !h-auto text-white/50 hover:text-white/70 bg-white/[0.03] border-white/[0.06] hover:bg-white/[0.06] !rounded-lg">
          <i class="fas fa-arrow-left text-xs"></i>
          返回主页
        </BaseButton>
      </div>

      <!-- 移动端 Logo（小屏显示） -->
      <div class="lg:hidden text-center mb-8">
        <div class="relative inline-flex mb-4">
          <div class="bg-white/[0.04] border border-white/[0.08] p-2.5 rounded-xl">
            <img src="/logo.svg" class="w-7 h-7 brightness-0 invert opacity-70" alt="logo" />
          </div>
        </div>
        <h1 class="text-2xl font-semibold text-white tracking-wide">智卷错题本</h1>
      </div>

      <div class="w-full max-w-sm">
        <!-- 标题 -->
        <div class="mb-8">
          <h3 class="text-2xl font-semibold text-white">
            {{ route.path === '/auth/login' ? '欢迎回来' : '创建账户' }}
          </h3>
          <p class="text-sm text-white/35 mt-1">
            {{ route.path === '/auth/login' ? '登录以继续使用你的错题本' : '免费注册，开始智能错题整理' }}
          </p>
        </div>

        <!-- Tab 切换 -->
        <div class="flex rounded-xl bg-white/[0.03] border border-white/[0.06] p-1 mb-6">
          <RouterLink
            to="/auth/login"
            class="flex-1 py-2 text-sm font-medium rounded-lg text-center transition-all"
            :class="route.path === '/auth/login'
              ? 'bg-white/[0.08] text-white'
              : 'text-white/35 hover:text-white/60'"
          >登录</RouterLink>
          <RouterLink
            to="/auth/register"
            class="flex-1 py-2 text-sm font-medium rounded-lg text-center transition-all"
            :class="route.path === '/auth/register'
              ? 'bg-white/[0.08] text-white'
              : 'text-white/35 hover:text-white/60'"
          >注册</RouterLink>
        </div>

        <!-- 表单内容（滑动过渡） -->
        <RouterView v-slot="{ Component }">
          <Transition :name="transitionName" mode="out-in">
            <component :is="Component" :key="route.path" />
          </Transition>
        </RouterView>

        <!-- 底部版权（移动端） -->
        <p class="lg:hidden text-center text-xs text-white/20 mt-8">
          © {{ new Date().getFullYear() }} 智卷错题本
        </p>
      </div>
    </div>

  </div>
</template>

<style>
/* 禁用浏览器自动填充背景色 */
input:-webkit-autofill,
input:-webkit-autofill:hover,
input:-webkit-autofill:focus {
  transition: background-color 9999s ease;
  -webkit-text-fill-color: #e2e8f0;
  caret-color: #e2e8f0;
}
</style>

<style scoped>
/* 星星闪烁 */
@keyframes star-twinkle {
  0%, 100% { opacity: var(--star-opacity); }
  50% { opacity: 0.02; }
}
.star-twinkle {
  animation: star-twinkle ease-in-out infinite;
}

/* 鼠标跟随发光层 */
.auth-glow-layer {
  mask-image: radial-gradient(350px circle at var(--mx, -500px) var(--my, -500px), black 0%, transparent 100%);
  -webkit-mask-image: radial-gradient(350px circle at var(--mx, -500px) var(--my, -500px), black 0%, transparent 100%);
}

/* 紫-白-紫渐变扫光 */
@keyframes gradient-sweep {
  0% { background-position: -100% center; }
  100% { background-position: 100% center; }
}
.animate-gradient-sweep {
  animation: gradient-sweep 3s ease-in-out infinite alternate;
}

/* 向左滑（登录 → 注册） */
.auth-slide-left-enter-active,
.auth-slide-left-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.auth-slide-left-enter-from  { opacity: 0; transform: translateX(32px); }
.auth-slide-left-leave-to   { opacity: 0; transform: translateX(-32px); }

/* 向右滑（注册 → 登录） */
.auth-slide-right-enter-active,
.auth-slide-right-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.auth-slide-right-enter-from { opacity: 0; transform: translateX(-32px); }
.auth-slide-right-leave-to  { opacity: 0; transform: translateX(32px); }
</style>
