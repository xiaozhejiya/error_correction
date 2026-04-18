<script setup>
/**
 * AiAnalysisModal.vue
 * AI 分析弹窗（知识点讲解）
 */
const props = defineProps({
  open: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  analysis: { type: Object, default: null },
})

const emit = defineEmits(['close'])
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="open" class="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6">
        <!-- 遮罩 -->
        <div class="absolute inset-0 bg-slate-950/60" @click="emit('close')"></div>

        <!-- 弹窗主体 -->
        <div class="relative flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-[2rem] border border-white/10 bg-white shadow-2xl dark:bg-[#0F111A]">

          <!-- 头部 -->
          <div class="flex items-center justify-between border-b border-slate-100 bg-gradient-to-r from-indigo-50 to-blue-50 px-8 py-5 dark:border-white/5 dark:from-indigo-500/5 dark:to-blue-500/5">
            <div class="flex items-center gap-4">
              <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 text-white shadow-lg shadow-indigo-500/30">
                <i class="fa-solid fa-brain text-lg"></i>
              </div>
              <div>
                <h3 class="text-lg font-black tracking-tight text-slate-900 dark:text-white">AI 错题分析报告</h3>
                <p class="text-[10px] font-black uppercase tracking-widest text-slate-400">Intelligent Error Analysis</p>
              </div>
            </div>
            <button @click="emit('close')" class="h-10 w-10 rounded-xl bg-white/80 text-slate-500 transition-all hover:bg-slate-100 dark:bg-white/5 dark:text-slate-400">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>

          <!-- 内容 -->
          <div class="flex-1 overflow-y-auto p-8">
            <!-- 加载状态 -->
            <div v-if="loading" class="flex flex-col items-center justify-center py-20">
              <div class="relative mb-6">
                <div class="h-16 w-16 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-500"></div>
                <i class="fa-solid fa-brain absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-xl text-indigo-500 animate-pulse"></i>
              </div>
              <p class="text-sm font-black text-slate-600 dark:text-slate-300">AI 正在分析你的错题...</p>
              <p class="mt-1 text-xs text-slate-400">分析知识薄弱点、归纳错因模式</p>
            </div>
            <!-- 分析结果 -->
            <div v-else-if="analysis" class="space-y-8">
              <!-- 综合诊断 -->
              <div class="rounded-2xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/5 to-blue-500/5 p-6">
                <h4 class="mb-3 flex items-center gap-2 text-xs font-black uppercase tracking-widest text-indigo-600 dark:text-indigo-400">
                  <i class="fa-solid fa-stethoscope"></i> 综合诊断
                </h4>
                <p class="text-sm font-medium leading-relaxed text-slate-700 dark:text-slate-300">{{ analysis.summary }}</p>
              </div>

              <!-- 薄弱知识点 -->
              <div>
                <h4 class="mb-4 flex items-center gap-2 text-xs font-black uppercase tracking-widest text-slate-500 dark:text-slate-400">
                  <i class="fa-solid fa-bullseye text-rose-500"></i> 薄弱知识点
                </h4>
                <div class="flex flex-wrap gap-2">
                  <span v-for="wp in analysis.weak_points" :key="wp"
                    class="rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-bold text-rose-600 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-400">
                    {{ wp }}
                  </span>
                </div>
              </div>

              <!-- 错因模式 -->
              <div v-if="analysis.error_patterns?.length">
                <h4 class="mb-4 flex items-center gap-2 text-xs font-black uppercase tracking-widest text-slate-500 dark:text-slate-400">
                  <i class="fa-solid fa-magnifying-glass-chart text-amber-500"></i> 错因归纳
                </h4>
                <div class="space-y-3">
                  <div v-for="(ep, idx) in analysis.error_patterns" :key="idx"
                    class="rounded-xl border border-slate-200/60 bg-white/60 p-4 dark:border-white/5 dark:bg-white/5">
                    <div class="mb-1 text-sm font-bold text-slate-800 dark:text-slate-200">{{ ep.pattern }}</div>
                    <p class="text-xs text-slate-500 dark:text-slate-400">{{ ep.description }}</p>
                    <div v-if="ep.question_ids?.length" class="mt-2 text-[10px] text-slate-400">
                      涉及题目: {{ ep.question_ids.map(id => '#' + id).join(', ') }}
                    </div>
                  </div>
                </div>
              </div>

              <!-- 复习建议 -->
              <div v-if="analysis.suggestions?.length">
                <h4 class="mb-4 flex items-center gap-2 text-xs font-black uppercase tracking-widest text-slate-500 dark:text-slate-400">
                  <i class="fa-solid fa-lightbulb text-emerald-500"></i> 复习建议
                </h4>
                <div class="space-y-2 border-l-2 border-emerald-200 pl-5 dark:border-emerald-500/20">
                  <div v-for="(s, idx) in analysis.suggestions" :key="idx" class="relative">
                    <span class="absolute -left-[25px] flex h-[12px] w-[12px] items-center justify-center rounded-full bg-emerald-500 text-[7px] font-black text-white outline outline-4 outline-white dark:outline-[#0F111A]">
                      {{ idx + 1 }}
                    </span>
                    <p class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ s }}</p>
                  </div>
                </div>
              </div>

              <!-- 逐题分析 -->
              <div v-if="analysis.per_question?.length">
                <h4 class="mb-4 flex items-center gap-2 text-xs font-black uppercase tracking-widest text-slate-500 dark:text-slate-400">
                  <i class="fa-solid fa-list-ol text-blue-500"></i> 逐题诊断
                </h4>
                <div class="space-y-3">
                  <div v-for="pq in analysis.per_question" :key="pq.question_id"
                    class="rounded-xl border border-slate-200/60 bg-slate-50/50 p-4 dark:border-white/5 dark:bg-white/5">
                    <div class="mb-2 text-[10px] font-black uppercase tracking-widest text-blue-500">题目 #{{ pq.question_id }}</div>
                    <p class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ pq.diagnosis }}</p>
                    <p v-if="pq.hint" class="mt-2 rounded-lg bg-blue-50 p-2 text-xs text-blue-600 dark:bg-blue-500/10 dark:text-blue-400">
                      <i class="fa-solid fa-lightbulb mr-1"></i> {{ pq.hint }}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <!-- 空状态 -->
            <div v-else class="flex flex-col items-center justify-center py-20 text-slate-400">
              <i class="fa-solid fa-robot mb-4 text-4xl opacity-20"></i>
              <p class="text-xs font-bold uppercase tracking-widest">暂无分析数据</p>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-fade-enter-active, .modal-fade-leave-active { transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; transform: scale(0.95); }
</style>
