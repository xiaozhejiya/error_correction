<script setup>
/**
 * HomeHero.vue
 * 落地页首屏 Hero 区
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { UploadCloud, ArrowRight } from 'lucide-vue-next'
import BaseButton from '@/components/base/BaseButton.vue'
import HomePill from '@/components/home/HomePill.vue'

const emit = defineEmits(['scrollToSection'])

// ── 底部星星 ──
const stars = ref([])

// ── 可见性检测：离开视口时暂停动画 ──
const heroVisible = ref(true)
let visibilityObserver = null

onMounted(() => {
  const count = 40
  const list = []
  for (let i = 0; i < count; i++) {
    list.push({
      left: Math.random() * 100,
      top: 60 + Math.random() * 38,
      size: 1 + Math.random() * 2,
      opacity: 0.08 + Math.random() * 0.35,
      delay: Math.random() * 4,
    })
  }
  stars.value = list

  // 监听 Hero 是否在视口内
  const heroEl = document.getElementById('sticky-hero')
  if (heroEl) {
    visibilityObserver = new IntersectionObserver(
      ([entry]) => { heroVisible.value = entry.isIntersecting },
      { threshold: 0.05 }
    )
    visibilityObserver.observe(heroEl)
  }
})

onUnmounted(() => {
  visibilityObserver?.disconnect()
})
</script>

<template>
  <!-- ① Sticky Hero 容器 — Linear 风格 -->
  <div id="sticky-hero" class="sticky top-0 h-screen overflow-hidden z-0 flex flex-col justify-center bg-[#0A0A0F]" style="contain: content;">

    <!-- 背景装饰：复杂流体拓扑波纹 (Fluid Topography) 基础层 -->
    <div class="absolute inset-0 pointer-events-none z-0 opacity-20" style="
      background-image: url('data:image/svg+xml,%3Csvg viewBox=%220 0 1000 1000%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.005%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3CfeColorMatrix type=%22matrix%22 values=%221 0 0 0 0, 0 1 0 0 0, 0 0 1 0 0, 0 0 0 10 -4%22 /%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22 fill=%22none%22 stroke=%22%23ffffff%22 stroke-width=%221%22 opacity=%220.3%22/%3E%3Cpath d=%22M0,100 C200,300 300,0 500,100 C700,200 800,-100 1000,100 M0,200 C250,400 350,100 550,200 C750,300 850,0 1000,200 M0,300 C300,500 400,200 600,300 C800,400 900,100 1000,300 M0,400 C350,600 450,300 650,400 C850,500 950,200 1000,400 M0,500 C400,700 500,400 700,500 C900,600 1000,300 1000,500 M0,600 C450,800 550,500 750,600 C950,700 1000,400 1000,600 M0,700 C500,900 600,600 800,700 C1000,800 1000,500 1000,700 M0,800 C550,1000 650,700 850,800 C1000,900 1000,600 1000,800 M0,900 C600,1100 700,800 900,900 C1000,1000 1000,700 1000,900%22 stroke=%22%23ffffff%22 stroke-width=%221%22 fill=%22none%22 opacity=%220.15%22 /%3E%3C/svg%3E');
      background-size: cover;
      background-position: center;
      mask-image: radial-gradient(ellipse 100% 100% at 50% 50%, black, transparent);
      -webkit-mask-image: radial-gradient(ellipse 100% 100% at 50% 50%, black, transparent);
    "></div>

    <!-- 顶部装饰椭圆与土星光环 — 用 vw 统一大小和位置的缩放基准 -->
    <div class="absolute pointer-events-none z-0 flex items-center justify-center" style="
      top: -100vw;
      left: 50%;
      transform: translateX(-50%);
      width: 140vw;
      aspect-ratio: 1.3 / 1;
    ">
      <!-- 椭圆本体 -->
      <div class="absolute inset-0" style="
        border-radius: 50%;
        background: linear-gradient(to bottom, rgba(92,81,148,0.5), rgba(47,40,91,0.95));
        box-shadow:
          inset 0 -20px 24px 0 rgba(255,255,255,0.15),
          0 16px 32px 0 rgba(97,62,210,0.32),
          inset 0 -1px 0 0 rgba(129,115,223,0.6);
      "></div>

      <!-- 土星光环: LaTeX 公式 -->
      <!-- 放大容器以远离"土星"本体，同时增加 Z 轴旋转(rotateX)和倾斜(rotateZ)产生悬浮交错的纵深感 -->
      <div class="absolute pointer-events-none" :class="{ 'rings-paused': !heroVisible }" style="
        width: 120%;
        height: 120%;
        top: -10%;
        left: -10%;
        transform-origin: center center;
        transform: rotateX(15deg) rotateZ(-4deg) translateY(5%);
      ">
        <svg viewBox="-100 -100 1200 1200" preserveAspectRatio="none" class="w-full h-full opacity-60" style="overflow: visible;">
          <!-- 第一圈光环 (内圈，顺时针旋转) -->
          <g class="ring-spin-cw" style="transform-origin: 500px 500px;">
            <!-- 光环轨道 (反向绘制路径以使文字正向朝外) -->
            <path id="saturn-ring-path-1" d="M 500, 980 A 480,480 0 1,0 500,20 A 480,480 0 1,0 500,980" fill="none" />
            
            <!-- 轨道装饰线 -->
            <path d="M 500, 500 m -488, 0 a 488,488 0 1,1 976,0 a 488,488 0 1,1 -976,0" fill="none" stroke="rgba(129,115,223,0.2)" stroke-width="1" />
            <path d="M 500, 500 m -472, 0 a 472,472 0 1,1 944,0 a 472,472 0 1,1 -944,0" fill="none" stroke="rgba(129,115,223,0.2)" stroke-width="1" />

            <!-- 公式文本 -->
            <text fill="currentColor" class="text-indigo-200/80" font-family="'Times New Roman', Times, serif" font-size="18" font-style="italic" letter-spacing="5">
              <textPath href="#saturn-ring-path-1" startOffset="0%">
                ∇⋅E = ρ/ε₀ &nbsp;&nbsp;&nbsp;&nbsp; ∇×B = μ₀J + μ₀ε₀(∂E/∂t) &nbsp;&nbsp;&nbsp;&nbsp; R_μν - ½Rg_μν + Λg_μν = (8πG/c⁴)T_μν &nbsp;&nbsp;&nbsp;&nbsp; iℏ(∂Ψ/∂t) = ĤΨ &nbsp;&nbsp;&nbsp;&nbsp; (iγ^μ∂_μ - m)ψ = 0 &nbsp;&nbsp;&nbsp;&nbsp; e^(iπ) + 1 = 0 &nbsp;&nbsp;&nbsp;&nbsp; S = ∫ L dt &nbsp;&nbsp;&nbsp;&nbsp; ∇⋅E = ρ/ε₀ &nbsp;&nbsp;&nbsp;&nbsp; ∇×B = μ₀J + μ₀ε₀(∂E/∂t) &nbsp;&nbsp;&nbsp;&nbsp; R_μν - ½Rg_μν + Λg_μν = (8πG/c⁴)T_μν &nbsp;&nbsp;&nbsp;&nbsp; iℏ(∂Ψ/∂t) = ĤΨ &nbsp;&nbsp;&nbsp;&nbsp; (iγ^μ∂_μ - m)ψ = 0 &nbsp;&nbsp;&nbsp;&nbsp; e^(iπ) + 1 = 0 &nbsp;&nbsp;&nbsp;&nbsp; S = ∫ L dt &nbsp;&nbsp;&nbsp;&nbsp; ∇⋅E = ρ/ε₀ &nbsp;&nbsp;&nbsp;&nbsp; ∇×B = μ₀J + μ₀ε₀(∂E/∂t) &nbsp;&nbsp;&nbsp;&nbsp; R_μν - ½Rg_μν + Λg_μν = (8πG/c⁴)T_μν &nbsp;&nbsp;&nbsp;&nbsp; iℏ(∂Ψ/∂t) = ĤΨ &nbsp;&nbsp;&nbsp;&nbsp; (iγ^μ∂_μ - m)ψ = 0 &nbsp;&nbsp;&nbsp;&nbsp; e^(iπ) + 1 = 0 &nbsp;&nbsp;&nbsp;&nbsp; S = ∫ L dt
              </textPath>
            </text>
          </g>

          <!-- 第二圈光环 (外圈，逆时针旋转，半径更大，文本不同) -->
          <g class="ring-spin-ccw" style="transform-origin: 500px 500px;">
            <!-- 光环轨道 (半径从 480 增加到 540) -->
            <path id="saturn-ring-path-2" d="M 500, 1040 A 540,540 0 1,0 500,-40 A 540,540 0 1,0 500,1040" fill="none" />
            
            <!-- 轨道装饰线 -->
            <path d="M 500, 500 m -546, 0 a 546,546 0 1,1 1092,0 a 546,546 0 1,1 -1092,0" fill="none" stroke="rgba(129,115,223,0.15)" stroke-width="1" />
            <path d="M 500, 500 m -534, 0 a 534,534 0 1,1 1068,0 a 534,534 0 1,1 -1068,0" fill="none" stroke="rgba(129,115,223,0.15)" stroke-width="1" />

            <!-- 公式文本 (换成另一组数学公式：傅里叶变换、高斯-博内定理、薛定谔、贝叶斯等) -->
            <text fill="currentColor" class="text-indigo-200/70" font-family="'Times New Roman', Times, serif" font-size="14" font-style="italic" letter-spacing="6">
              <textPath href="#saturn-ring-path-2" startOffset="0%">
                F(ω) = ∫ f(t)e^(-iωt)dt &nbsp;&nbsp;&nbsp;&nbsp; ∫K dA + ∫k_g ds = 2πχ(M) &nbsp;&nbsp;&nbsp;&nbsp; P(A|B) = P(B|A)P(A)/P(B) &nbsp;&nbsp;&nbsp;&nbsp; dS ≥ 0 &nbsp;&nbsp;&nbsp;&nbsp; E = mc² &nbsp;&nbsp;&nbsp;&nbsp; V - E + F = 2 &nbsp;&nbsp;&nbsp;&nbsp; F(ω) = ∫ f(t)e^(-iωt)dt &nbsp;&nbsp;&nbsp;&nbsp; ∫K dA + ∫k_g ds = 2πχ(M) &nbsp;&nbsp;&nbsp;&nbsp; P(A|B) = P(B|A)P(A)/P(B) &nbsp;&nbsp;&nbsp;&nbsp; dS ≥ 0 &nbsp;&nbsp;&nbsp;&nbsp; E = mc² &nbsp;&nbsp;&nbsp;&nbsp; V - E + F = 2 &nbsp;&nbsp;&nbsp;&nbsp; F(ω) = ∫ f(t)e^(-iωt)dt &nbsp;&nbsp;&nbsp;&nbsp; ∫K dA + ∫k_g ds = 2πχ(M) &nbsp;&nbsp;&nbsp;&nbsp; P(A|B) = P(B|A)P(A)/P(B) &nbsp;&nbsp;&nbsp;&nbsp; dS ≥ 0 &nbsp;&nbsp;&nbsp;&nbsp; E = mc² &nbsp;&nbsp;&nbsp;&nbsp; V - E + F = 2 &nbsp;&nbsp;&nbsp;&nbsp; F(ω) = ∫ f(t)e^(-iωt)dt &nbsp;&nbsp;&nbsp;&nbsp; ∫K dA + ∫k_g ds = 2πχ(M) &nbsp;&nbsp;&nbsp;&nbsp; P(A|B) = P(B|A)P(A)/P(B) &nbsp;&nbsp;&nbsp;&nbsp; dS ≥ 0 &nbsp;&nbsp;&nbsp;&nbsp; E = mc² &nbsp;&nbsp;&nbsp;&nbsp; V - E + F = 2
              </textPath>
            </text>
          </g>
        </svg>
      </div>
    </div>

    <!-- 装饰: 光斑 -->
    <div class="absolute pointer-events-none z-0 w-80 h-80 rounded-full blur-[120px] bg-indigo-600/[0.07]"
      style="top: 25%; left: 8%;"
    ></div>
    <div class="absolute pointer-events-none z-0 w-64 h-64 rounded-full blur-[100px] bg-violet-500/[0.05]"
      style="top: 55%; right: 10%;"
    ></div>

    <!-- 装饰: 底部简约的环境光晕 -->
    <div class="absolute bottom-0 left-1/2 -translate-x-1/2 w-[80vw] h-[30vh] pointer-events-none z-0">
      <div class="absolute inset-0 bg-indigo-500/10 blur-[100px] rounded-[100%] transform translate-y-1/2"></div>
      <div class="absolute inset-0 bg-violet-500/5 blur-[120px] rounded-[100%] transform translate-y-1/2 scale-150"></div>
    </div>

    <!-- 首屏区块 — 居中布局 -->
    <section id="hero" class="relative w-full px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto z-10">
      <div class="text-center">
        <!-- 标签 -->
        <HomePill class="mb-6" />

        <h1 class="text-4xl sm:text-5xl font-semibold tracking-tight leading-tight mb-6 text-white">
          重塑错题整理<br />
          <span class="text-transparent bg-clip-text animate-gradient-sweep" style="
            background-image: linear-gradient(to right, rgb(151, 137, 222) 0%, rgb(151, 137, 222) 20%, rgb(255, 255, 255) 50%, rgb(151, 137, 222) 80%, rgb(151, 137, 222) 100%);
            background-size: 200% auto;
          ">一键生成知识图谱</span>
        </h1>

        <p class="text-base text-white/40 mb-8 max-w-lg mx-auto leading-relaxed">
          上传试卷或手写笔记，AI 自动完成 OCR 识别、题目分割、公式还原、知识点标注。
        </p>

        <div class="flex gap-3 justify-center">
          <BaseButton to="/auth">
            <UploadCloud class="w-4 h-4" />
            开始使用
          </BaseButton>
          <BaseButton variant="secondary" href="#demo">
            查看演示
            <ArrowRight class="w-4 h-4" />
          </BaseButton>
        </div>
      </div>
    </section>

    <!-- 星星点缀 -->
    <div class="absolute inset-0 pointer-events-none z-[1]">
      <div
        v-for="(s, i) in stars"
        :key="i"
        class="absolute rounded-full bg-white"
        :style="{
          left: s.left + '%',
          top: s.top + '%',
          width: s.size + 'px',
          height: s.size + 'px',
          opacity: s.opacity,
        }"
      ></div>
    </div>

    <!-- 底部箭头 -->
    <button
      @click="emit('scrollToSection', 'features')"
      class="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 text-white/20 hover:text-white/50 transition-colors cursor-pointer"
    >
      <i class="fa-solid fa-chevron-down text-lg animate-bounce"></i>
    </button>
  </div>
</template>

<style scoped>
@keyframes spin-cw {
  0% { transform: rotate(0deg) translateZ(0); }
  100% { transform: rotate(360deg) translateZ(0); }
}

@keyframes spin-ccw {
  0% { transform: rotate(360deg) translateZ(0); }
  100% { transform: rotate(0deg) translateZ(0); }
}

.ring-spin-cw {
  animation: spin-cw 120s linear infinite;
  will-change: transform;
}

.ring-spin-ccw {
  animation: spin-ccw 180s linear infinite;
  will-change: transform;
}

/* 离开视口时暂停旋转，节省渲染开销 */
.rings-paused .ring-spin-cw,
.rings-paused .ring-spin-ccw {
  animation-play-state: paused;
}

@keyframes gradient-sweep {
  0% { background-position: -100% center; }
  100% { background-position: 100% center; }
}

.animate-gradient-sweep {
  animation: gradient-sweep 3s ease-in-out infinite alternate;
}

</style>
