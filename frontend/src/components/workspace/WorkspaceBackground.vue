<script setup>
/**
 * WorkspaceBackground.vue
 * 工作台全局背景装饰（Linear 风格光圈 + 噪点 + 闪烁星星）
 */
const bgStars = (() => {
  const list = []
  for (let i = 0; i < 50; i++) {
    list.push({
      left: Math.random() * 100, top: Math.random() * 100,
      size: 0.5 + Math.random() * 2, opacity: 0.1 + Math.random() * 0.4,
      duration: 2 + Math.random() * 4, delay: Math.random() * 5,
    })
  }
  return list
})()
</script>

<template>
  <div class="fixed inset-0 z-0 pointer-events-none">
    <div class="ws-bg-glow"></div>
    <div class="ws-bg-noise"></div>
    <div
      v-for="(s, i) in bgStars"
      :key="i"
      class="absolute rounded-full bg-white ws-star"
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
</template>

<style>
@keyframes ws-star-twinkle {
  0%, 100% { opacity: var(--star-opacity); }
  50% { opacity: 0.02; }
}
.ws-star {
  animation: ws-star-twinkle ease-in-out infinite;
}
.ws-bg-glow {
  position: absolute;
  top: -20%;
  left: -10%;
  width: 600px;
  height: 600px;
  border-radius: 9999px;
  background: radial-gradient(circle, rgba(129,115,223,0.06) 0%, transparent 70%);
}
.ws-bg-noise {
  position: absolute;
  inset: 0;
  opacity: 0.04;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-size: 256px 256px;
}
</style>
