<script setup>
/**
 * HomeFooter.vue
 * 落地页底部行动号召区
 */
import BaseButton from '@/components/base/BaseButton.vue'
</script>

<template>
  <section id="cta" class="relative z-10 flex flex-col items-center justify-center py-32 px-6 overflow-hidden min-h-[70vh]">
    <!-- 底部中心光晕 -->
    <div class="absolute bottom-0 left-1/2 -translate-x-1/2 w-[80vw] h-[50vh] pointer-events-none z-0">
      <div class="absolute inset-0 bg-indigo-500/10 blur-[120px] rounded-[100%] transform translate-y-1/2"></div>
      <div class="absolute inset-0 bg-violet-500/5 blur-[150px] rounded-[100%] transform translate-y-1/2 scale-150"></div>
    </div>

    <!-- CTA -->
    <div class="flex-1 flex flex-col items-center justify-center text-center relative z-10 w-full">
      <h2 class="reveal text-4xl sm:text-5xl font-semibold tracking-tight mb-6 text-transparent bg-clip-text animate-gradient-sweep" style="
            background-image: linear-gradient(to right, rgb(151, 137, 222) 0%, rgb(151, 137, 222) 20%, rgb(255, 255, 255) 50%, rgb(151, 137, 222) 80%, rgb(151, 137, 222) 100%);
            background-size: 200% auto;
          ">即刻开启高效学习模式</h2>
      <p class="reveal text-white/40 text-base mb-10 max-w-md mx-auto leading-relaxed">告别低效抄录，让 AI 成为你的超级助教。注册即享完整试卷解析体验。</p>
      <div class="reveal">
        <BaseButton variant="cta" to="/auth" class="shadow-[0_0_30px_rgba(129,115,223,0.3)] hover:shadow-[0_0_50px_rgba(129,115,223,0.5)] transform hover:-translate-y-1 transition-all duration-300">
          免费创建错题库
        </BaseButton>
      </div>
    </div>
  </section>
</template>
