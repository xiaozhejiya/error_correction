<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount, computed } from 'vue'
import * as api from '@/api.js'
import { useTheme } from '@/composables/useTheme.js'
import { useToast } from '@/composables/useToast.js'
import { useWorkspaceNav } from '@/composables/useWorkspaceNav.js'
import ContentPanel from '@/components/workspace/ContentPanel.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import StatCard from '@/components/dashboard/StatCard.vue'

const { isDark } = useTheme()
const { pushToast } = useToast()
const { currentView } = useWorkspaceNav()
const theme = computed(() => isDark.value ? 'dark' : 'light')

// ---- 统计数据 ----
const stats = ref(null)
const statsLoading = ref(false)

// ---- 学科筛选 ----
const selectedSubject = ref('')
const subjects = computed(() => stats.value?.subjects || [])

// ---- 图表 ----
const trendCanvas = ref(null)
const barCanvas = ref(null)
const stackedCanvas = ref(null)
let trendChart = null
let barChart = null
let stackedChart = null

// ---- 颜色常量 ----
const CHART_COLORS = ['#6366f1', '#3b82f6', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#14b8a6', '#f97316', '#06b6d4', '#e11d48']
const STATUS_COLORS = { '待复习': '#f97316', '复习中': '#eab308', '已掌握': '#10b981' }

// ---- 数据加载 ----
const loadStats = async () => {
  statsLoading.value = true
  try {
    const data = await api.fetchDashboardStats(selectedSubject.value || undefined)
    stats.value = data
  } catch (e) {
    pushToast('error', '加载统计数据失败')
  } finally {
    statsLoading.value = false
  }
}

// ---- 学科切换 ----
watch(selectedSubject, () => { loadStats() })

// ---- 图表初始化 ----
const initCharts = async () => {
  await nextTick()
  if (!window.Chart || !stats.value) return
  const dark = isDark.value
  const textColor = dark ? 'rgba(255,255,255,0.7)' : 'rgba(15,23,42,0.8)'
  const gridColor = dark ? 'rgba(255,255,255,0.05)' : 'rgba(15,23,42,0.08)'

  initTrendChart(isDark, textColor, gridColor)
  initBarChart(isDark, textColor, gridColor)
  initStackedChart(isDark, textColor, gridColor)
}

const initTrendChart = (isDark, textColor, gridColor) => {
  if (!trendCanvas.value) return
  if (trendChart) trendChart.destroy()
  const dc = stats.value.daily_counts || []
  trendChart = new window.Chart(trendCanvas.value, {
    type: 'line',
    data: {
      labels: dc.map(d => d.date),
      datasets: [
        {
          label: '每日新增',
          data: dc.map(d => d.count),
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59,130,246,0.1)',
          borderWidth: 2, tension: 0.4, fill: true,
          pointBackgroundColor: '#3b82f6',
          pointRadius: 0, pointHoverRadius: 4,
        },
        {
          label: '每日掌握',
          data: dc.map(d => d.mastered),
          borderColor: '#10b981',
          backgroundColor: 'rgba(16,185,129,0.08)',
          borderWidth: 2, tension: 0.4, fill: true,
          pointBackgroundColor: '#10b981',
          pointRadius: 0, pointHoverRadius: 4,
          borderDash: [4, 3],
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { labels: { color: textColor, usePointStyle: true, boxWidth: 6 } } },
      scales: {
        x: { grid: { display: false }, ticks: { color: textColor, maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } },
        y: { grid: { color: gridColor }, ticks: { color: textColor, stepSize: 1 }, beginAtZero: true },
      }
    }
  })
}

const initBarChart = (isDark, textColor, gridColor) => {
  if (!barCanvas.value) return
  if (barChart) barChart.destroy()
  const ts = stats.value.tag_stats || []
  if (!ts.length) return
  const reversed = [...ts].reverse()
  const colors = reversed.map((_, i) => CHART_COLORS[(reversed.length - 1 - i) % CHART_COLORS.length])
  barChart = new window.Chart(barCanvas.value, {
    type: 'bar',
    data: {
      labels: reversed.map(t => t.tag_name),
      datasets: [{
        label: '错题数',
        data: reversed.map(t => t.count),
        backgroundColor: colors.map(c => c + '99'),
        borderColor: colors,
        borderWidth: 1,
        borderRadius: 2,
        barPercentage: 0.85,
        categoryPercentage: 1.0,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: gridColor }, ticks: { color: textColor, stepSize: 1 }, beginAtZero: true },
        y: { grid: { display: false }, ticks: { color: textColor, font: { size: 11 } } },
      }
    }
  })
}

const initStackedChart = (isDark, textColor, gridColor) => {
  if (!stackedCanvas.value) return
  if (stackedChart) stackedChart.destroy()
  const tss = stats.value.tag_status_stats || []
  if (!tss.length) return
  stackedChart = new window.Chart(stackedCanvas.value, {
    type: 'bar',
    data: {
      labels: tss.map(t => t.tag_name),
      datasets: [
        { label: '待复习', data: tss.map(t => t['待复习']), backgroundColor: STATUS_COLORS['待复习'] + 'cc', borderRadius: 2 },
        { label: '复习中', data: tss.map(t => t['复习中']), backgroundColor: STATUS_COLORS['复习中'] + 'cc', borderRadius: 2 },
        { label: '已掌握', data: tss.map(t => t['已掌握']), backgroundColor: STATUS_COLORS['已掌握'] + 'cc', borderRadius: 2 },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: textColor, usePointStyle: true, boxWidth: 8 } } },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { color: textColor, font: { size: 10 }, maxRotation: 45 } },
        y: { stacked: true, grid: { color: gridColor }, ticks: { color: textColor, stepSize: 1 }, beginAtZero: true },
      }
    }
  })
}

// 热力图
const heatmapData = computed(() => stats.value?.tag_type_stats || { tags: [], types: [], data: [] })
const heatmapMax = computed(() => {
  const d = heatmapData.value.data
  if (!d.length) return 1
  return Math.max(1, ...d.flat())
})

const heatmapCellColor = (val) => {
  if (!val) return theme.value === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(15,23,42,0.03)'
  const ratio = val / heatmapMax.value
  if (theme.value === 'dark') {
    const alpha = 0.15 + ratio * 0.7
    return `rgba(99, 102, 241, ${alpha})`
  }
  const alpha = 0.08 + ratio * 0.6
  return `rgba(99, 102, 241, ${alpha})`
}

// ---- 生命周期 ----
onMounted(() => loadStats())

watch(() => [isDark.value, stats.value], () => {
  if (stats.value) nextTick(initCharts)
})

onBeforeUnmount(() => {
  if (trendChart) trendChart.destroy()
  if (barChart) barChart.destroy()
  if (stackedChart) stackedChart.destroy()
})
</script>

<template>
  <ContentPanel title="数据面板">
    <template #toolbar>
      <BaseSelect v-if="subjects.length" v-model="selectedSubject" :options="subjects" placeholder="全部学科" width-class="min-w-[140px]" />
      <button @click="currentView = 'workspace'" class="inline-flex items-center gap-2 rounded-md brand-btn px-3 py-1.5 text-xs font-medium text-[#f7f8f8]">
        <i class="fa-solid fa-plus-circle text-[10px]"></i> 录入新题目
      </button>
    </template>
  <div class="relative h-full overflow-y-auto custom-scrollbar">
    <div class="container relative z-10 mx-auto">

      <!-- 骨架屏（加载中） -->
      <template v-if="statsLoading">
        <!-- 统计卡片骨架：精确复刻 StatCard 内部结构 -->
        <div class="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div v-for="i in 4" :key="i"
            class="animate-pulse rounded-2xl border border-slate-200/60 bg-white/70 p-6 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
            <div class="flex items-center gap-4">
              <div class="size-12 shrink-0 rounded-lg bg-slate-200/80 dark:bg-white/[0.07]"></div>
              <div class="flex flex-col gap-2">
                <div class="h-3.5 w-10 rounded bg-slate-200/80 dark:bg-white/[0.07]"></div>
                <div class="h-8 w-14 rounded-lg bg-slate-200/80 dark:bg-white/[0.07]"></div>
              </div>
            </div>
          </div>
        </div>
        <!-- 图表骨架：精确复刻 BaseCard + 标题行 + canvas 区域 -->
        <div class="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div v-for="i in 2" :key="i"
            class="animate-pulse rounded-2xl border border-slate-200/60 bg-white/70 p-6 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
            <div class="mb-4 flex items-center gap-2">
              <div class="h-4 w-4 rounded bg-slate-200/80 dark:bg-white/[0.07]"></div>
              <div class="h-4 w-28 rounded bg-slate-200/80 dark:bg-white/[0.07]"></div>
            </div>
            <div class="h-[240px] w-full rounded-xl bg-slate-100/80 dark:bg-white/[0.04]"></div>
          </div>
        </div>
        <div class="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div class="animate-pulse rounded-2xl border border-slate-200/60 bg-white/70 p-6 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
            <div class="mb-4 flex items-center gap-2">
              <div class="h-4 w-4 rounded bg-slate-200/80 dark:bg-white/[0.07]"></div>
              <div class="h-4 w-28 rounded bg-slate-200/80 dark:bg-white/[0.07]"></div>
            </div>
            <div class="h-[360px] w-full rounded-xl bg-slate-100/80 dark:bg-white/[0.04]"></div>
          </div>
          <div class="animate-pulse rounded-2xl border border-slate-200/60 bg-white/70 p-6 shadow-sm dark:border-white/10 dark:bg-white/[0.03]">
            <div class="mb-4 flex items-center gap-2">
              <div class="h-4 w-4 rounded bg-slate-200/80 dark:bg-white/[0.07]"></div>
              <div class="h-4 w-28 rounded bg-slate-200/80 dark:bg-white/[0.07]"></div>
            </div>
            <div class="h-[240px] w-full rounded-xl bg-slate-100/80 dark:bg-white/[0.04]"></div>
          </div>
        </div>
      </template>

      <!-- 实际内容 -->
      <template v-else>
        <!-- 统计卡片 -->
        <div class="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="总错题" icon="fa-solid fa-layer-group" :value="stats?.total_questions || 0" unit="道" color="indigo" />
          <StatCard label="待复习" icon="fa-solid fa-clock" :value="stats?.review_stats?.['待复习'] || 0" unit="道" color="blue" />
          <StatCard label="已掌握" icon="fa-solid fa-circle-check" :value="stats?.review_stats?.['已掌握'] || 0" unit="道" color="emerald" />
          <StatCard label="今日掌握" icon="fa-solid fa-bolt" :value="stats?.today_mastered || 0" unit="道" color="slate" />
        </div>

        <!-- 图表区第一行：趋势 + 条形图 -->
        <div class="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <BaseCard>
            <h3 class="mb-4 flex items-center gap-2 text-sm font-black text-slate-700 dark:text-slate-300">
              <i class="fa-solid fa-chart-line text-blue-500"></i> 最近 30 天趋势
            </h3>
            <div class="relative h-[240px] w-full"><canvas ref="trendCanvas"></canvas></div>
          </BaseCard>
          <BaseCard>
            <h3 class="mb-4 flex items-center gap-2 text-sm font-black text-slate-700 dark:text-slate-300">
              <i class="fa-solid fa-ranking-star text-indigo-500"></i> Top 10 易错知识点
            </h3>
            <div v-if="stats?.tag_stats?.length" class="relative h-[240px] w-full"><canvas ref="barCanvas"></canvas></div>
            <div v-else class="flex h-[240px] items-center justify-center text-sm text-slate-400">暂无标签数据</div>
          </BaseCard>
        </div>

        <!-- 图表区第二行：堆叠柱状图 + 热力图 -->
        <div class="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <BaseCard>
            <h3 class="mb-4 flex items-center gap-2 text-sm font-black text-slate-700 dark:text-slate-300">
              <i class="fa-solid fa-chart-bar text-emerald-500"></i> 知识点掌握状态
            </h3>
            <div v-if="stats?.tag_status_stats?.length" class="relative h-[360px] w-full"><canvas ref="stackedCanvas"></canvas></div>
            <div v-else class="flex h-[360px] items-center justify-center text-sm text-slate-400">暂无掌握状态数据</div>
          </BaseCard>
          <BaseCard>
            <h3 class="mb-4 flex items-center gap-2 text-sm font-black text-slate-700 dark:text-slate-300">
              <i class="fa-solid fa-fire text-rose-500"></i> 知识点 × 题型分布
            </h3>
            <div v-if="heatmapData.tags.length && heatmapData.types.length" class="overflow-x-auto">
              <table class="heatmap-table w-full text-center text-xs">
                <thead>
                  <tr>
                    <th class="sticky left-0 z-10 bg-white/80 px-2 py-2 text-left font-bold text-slate-500 dark:bg-white/[0.03] dark:text-slate-400"></th>
                    <th v-for="t in heatmapData.types" :key="t" class="px-2 py-2 font-bold text-slate-500 dark:text-slate-400">{{ t }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(tag, ri) in heatmapData.tags" :key="tag">
                    <td class="sticky left-0 z-10 max-w-[120px] truncate bg-white/80 px-2 py-1.5 text-left font-bold text-slate-600 dark:bg-white/[0.03] dark:text-slate-300">{{ tag }}</td>
                    <td v-for="(t, ci) in heatmapData.types" :key="t" class="px-1 py-1">
                      <div
                        class="mx-auto flex h-8 w-full min-w-[40px] items-center justify-center rounded-lg font-bold"
                        :style="{ backgroundColor: heatmapCellColor(heatmapData.data[ri]?.[ci] || 0) }"
                        :class="heatmapData.data[ri]?.[ci] ? 'text-indigo-700 dark:text-indigo-200' : 'text-slate-300 dark:text-slate-600'"
                      >{{ heatmapData.data[ri]?.[ci] || 0 }}</div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="flex h-[240px] items-center justify-center text-sm text-slate-400">暂无题型交叉数据</div>
          </BaseCard>
        </div>
      </template>
    </div>
  </div>
  </ContentPanel>
</template>

<style scoped>
.heatmap-table th, .heatmap-table td {
  white-space: nowrap;
}
</style>
