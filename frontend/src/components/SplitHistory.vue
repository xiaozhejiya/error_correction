<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { fetchSplitRecords, fetchSplitRecord } from '../api.js'

const props = defineProps({ open: Boolean })
const emit = defineEmits(['close', 'load-record'])

const records = ref([])
const loading = ref(false)
const loadingId = ref(null)
const error = ref('')

const relativeTime = (isoStr) => {
  if (!isoStr) return ''
  const ts = isoStr.endsWith('Z') || isoStr.includes('+') ? isoStr : isoStr + 'Z'
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins} 分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days} 天前`
  return new Date(isoStr).toLocaleDateString('zh-CN')
}

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    records.value = await fetchSplitRecords(10)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

const doLoad = async (record) => {
  if (loadingId.value) return
  loadingId.value = record.id
  try {
    const detail = await fetchSplitRecord(record.id)
    emit('load-record', detail.questions || [])
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loadingId.value = null
  }
}

const onKeydown = (e) => { if (e.key === 'Escape') emit('close') }

const cleanup = () => {
  document.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
}

watch(() => props.open, (v) => {
  if (v) {
    load()
    document.addEventListener('keydown', onKeydown)
    document.body.style.overflow = 'hidden'
  } else {
    cleanup()
  }
})

onBeforeUnmount(cleanup)
</script>

<template>
  <Teleport to="body">
    <Transition name="slideover">
      <div v-if="open" class="fixed inset-0 z-[90] flex justify-end">
        <!-- 遮罩 -->
        <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm dark:bg-black/50" @click="emit('close')"></div>

        <!-- 面板 -->
        <div class="relative flex h-full w-96 max-w-[85vw] flex-col border-l border-slate-200/60 bg-white/95 shadow-2xl backdrop-blur-xl dark:border-white/10 dark:bg-[#0A0A0F]/95">
          <!-- 头部 -->
          <div class="flex items-center justify-between border-b border-slate-100 px-5 py-4 dark:border-white/5">
            <h3 class="flex items-center gap-2 text-base font-black text-slate-800 dark:text-white">
              <i class="fa-solid fa-clock-rotate-left text-blue-500"></i> 分割历史
            </h3>
            <button @click="emit('close')" class="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-white/10 dark:hover:text-slate-300">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>

          <!-- 内容 -->
          <div class="flex-1 overflow-y-auto p-4">
            <!-- 加载中 -->
            <div v-if="loading" class="flex justify-center py-12">
              <div class="h-8 w-8 animate-spin rounded-full border-[3px] border-blue-500/20 border-t-blue-500"></div>
            </div>

            <!-- 错误 -->
            <div v-else-if="error" class="rounded-xl border border-rose-200 bg-rose-50 p-4 text-center text-sm text-rose-600 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-400">
              {{ error }}
            </div>

            <!-- 空 -->
            <div v-else-if="!records.length" class="flex flex-col items-center gap-3 py-16 text-slate-400">
              <i class="fa-solid fa-inbox text-3xl"></i>
              <span class="text-sm">暂无分割记录</span>
            </div>

            <!-- 列表 -->
            <div v-else class="space-y-3">
              <div
                v-for="r in records" :key="r.id"
                class="rounded-2xl border border-slate-200/60 bg-white/70 p-4 shadow-sm transition-all hover:shadow-md dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/[0.07]"
              >
                <!-- 上方：学科 + 时间 -->
                <div class="mb-2 flex items-center justify-between">
                  <span v-if="r.subject" class="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-bold text-blue-700 dark:bg-indigo-500/20 dark:text-indigo-300">
                    {{ r.subject }}
                  </span>
                  <span v-else class="text-xs text-slate-400">未分类</span>
                  <span class="text-xs text-slate-400">{{ relativeTime(r.created_at) }}</span>
                </div>

                <!-- 文件列表 -->
                <div class="mb-2 flex flex-wrap gap-1.5">
                  <span
                    v-for="(f, i) in r.file_names.slice(0, 3)" :key="i"
                    class="inline-flex max-w-[140px] items-center gap-1 truncate rounded-lg bg-slate-100 px-2 py-1 text-xs text-slate-600 dark:bg-white/5 dark:text-slate-400"
                  >
                    <i class="fa-solid fa-file-lines shrink-0 text-[10px] text-slate-400"></i>
                    {{ f }}
                  </span>
                  <span v-if="r.file_names.length > 3" class="rounded-lg bg-slate-100 px-2 py-1 text-xs text-slate-500 dark:bg-white/5 dark:text-slate-400">
                    +{{ r.file_names.length - 3 }}
                  </span>
                </div>

                <!-- 底部：题数 + 模型 + 加载按钮 -->
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                    <span><i class="fa-solid fa-list-check mr-1"></i>{{ r.question_count }} 题</span>
                    <span v-if="r.model_provider" class="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] dark:bg-white/5">{{ r.model_provider }}</span>
                  </div>
                  <button
                    @click="doLoad(r)"
                    :disabled="!!loadingId"
                    class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200/60 bg-white px-3 py-1.5 text-xs font-bold text-slate-600 shadow-sm transition-all hover:border-blue-300 hover:text-blue-600 disabled:opacity-50 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:border-indigo-500/30 dark:hover:text-indigo-300"
                  >
                    <i v-if="loadingId === r.id" class="fa-solid fa-spinner animate-spin"></i>
                    <i v-else class="fa-solid fa-rotate-left"></i>
                    加载
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.slideover-enter-active,
.slideover-leave-active {
  transition: opacity 0.25s ease;
}
.slideover-enter-active > :last-child,
.slideover-leave-active > :last-child {
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.slideover-enter-from,
.slideover-leave-to {
  opacity: 0;
}
.slideover-enter-from > :last-child,
.slideover-leave-to > :last-child {
  transform: translateX(100%);
}
</style>
