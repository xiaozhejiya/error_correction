<script setup>
/**
 * StatCard.vue
 * 统计数字卡片组件，带数字滚动动画。
 */
import { ref, watch, onMounted } from 'vue'
import BaseCard from '@/components/base/BaseCard.vue'

const props = defineProps({
  label: { type: String, required: true },
  icon: { type: String, required: true },
  value: { type: [Number, String], default: 0 },
  unit: { type: String, default: '' },
  color: { type: String, default: 'indigo' },
})

const colorMap = {
  indigo: 'text-indigo-600 bg-indigo-50 dark:text-indigo-400 dark:bg-indigo-500/10',
  blue: 'text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-500/10',
  emerald: 'text-emerald-600 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-500/10',
  slate: 'text-slate-600 bg-slate-50 dark:text-slate-400 dark:bg-slate-500/10',
  rose: 'text-rose-600 bg-rose-50 dark:text-rose-400 dark:bg-rose-500/10',
}

// 数字滚动动画
const displayValue = ref(0)
let animFrame = null

const animateTo = (target) => {
  const num = typeof target === 'number' ? target : parseInt(target, 10)
  if (isNaN(num)) { displayValue.value = target; return }

  const start = displayValue.value
  const diff = num - start
  if (diff === 0) return

  const duration = 800
  const startTime = performance.now()

  const step = (now) => {
    const elapsed = now - startTime
    const progress = Math.min(elapsed / duration, 1)
    // easeOutExpo
    const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)
    displayValue.value = Math.round(start + diff * ease)
    if (progress < 1) animFrame = requestAnimationFrame(step)
  }

  if (animFrame) cancelAnimationFrame(animFrame)
  animFrame = requestAnimationFrame(step)
}

onMounted(() => { animateTo(props.value) })
watch(() => props.value, (v) => { animateTo(v) })
</script>

<template>
  <BaseCard padding="p-6" class="stat-card group transition-all hover:shadow-md">
    <div class="flex items-center gap-4">
      <div
        class="flex size-12 shrink-0 items-center justify-center rounded-lg transition-transform duration-500 group-hover:scale-110"
        :class="colorMap[color] || colorMap.indigo"
      >
        <i :class="[icon, 'text-xl']"></i>
      </div>

      <div class="flex flex-col gap-1">
        <span class="text-sm font-bold text-slate-500 dark:text-slate-400">
          {{ label }}
        </span>
        <div class="flex items-baseline gap-1">
          <span class="text-2xl font-black tracking-tight text-slate-900 dark:text-white">
            {{ displayValue }}
          </span>
          <span v-if="unit" class="text-xs font-bold text-slate-500 opacity-60 dark:text-slate-400">
            {{ unit }}
          </span>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

