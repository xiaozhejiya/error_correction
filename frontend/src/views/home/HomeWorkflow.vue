<script setup>
/**
 * HomeWorkflow.vue
 * 落地页工作流程展示
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { UploadCloud, BrainCircuit, Sparkles, FileDown } from 'lucide-vue-next'
import WorkflowStep from '@/components/home/WorkflowStep.vue'

const STEPS = [
  { icon: 'upload-cloud', num: '01', title: '上传试卷',   desc: '支持PDF/多图并行处理',  delay: 0 },
  { icon: 'brain-circuit', num: '02', title: 'AI 解析拆题', desc: '智能排版与图文切分',    delay: 150 },
  { icon: 'sparkles',     num: '03', title: '纠错与打标', desc: '公式还原与知识点关联',   delay: 300 },
  { icon: 'file-down',    num: '04', title: '一键导出',   desc: '生成 Markdown/PDF',      delay: 450 },
]

const iconMap = {
  'upload-cloud': UploadCloud,
  'brain-circuit': BrainCircuit,
  sparkles: Sparkles,
  'file-down': FileDown,
}

const activeStep = ref(0)
let intervalId = null

function startStepInterval() {
  intervalId = setInterval(() => {
    activeStep.value = (activeStep.value + 1) % STEPS.length
  }, 3000)
}

function onStepClick(idx) {
  clearInterval(intervalId)
  activeStep.value = idx
  startStepInterval()
}

function getProgressWidth() {
  return `${(activeStep.value / (STEPS.length - 1)) * 100}%`
}

onMounted(() => {
  startStepInterval()
})

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
})
</script>

<template>
  <section id="workflow" class="relative z-10 py-24 overflow-hidden">
    <div class="reveal max-w-5xl mx-auto px-4 sm:px-6 relative z-10">
      <div class="text-center mb-16">
        <h2 class="reveal text-3xl font-semibold tracking-tight mb-4 text-transparent bg-clip-text animate-gradient-sweep" style="
            background-image: linear-gradient(to right, rgb(151, 137, 222) 0%, rgb(151, 137, 222) 20%, rgb(255, 255, 255) 50%, rgb(151, 137, 222) 80%, rgb(151, 137, 222) 100%);
            background-size: 200% auto;
          ">极简四步，自动运转</h2>
        <p class="text-white/40 text-sm">将原本需要耗费数小时的繁杂抄录，浓缩进点击之间。</p>
      </div>

      <div class="relative max-w-4xl mx-auto">
        <div class="grid grid-cols-1 lg:grid-cols-4 gap-4 relative z-10">
          <WorkflowStep
            v-for="(s, i) in STEPS"
            :key="s.num"
            :icon="iconMap[s.icon]"
            :title="s.title"
            :desc="s.desc"
            :isActive="i === activeStep"
            :isPast="i < activeStep"
            @click="onStepClick(i)"
          />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
</style>
