<script setup>
/**
 * FileList.vue
 * 已上传文件列表
 */
defineProps({
  pendingFiles: { type: Array, default: () => [] },
  fileProgress: { type: Object, default: () => ({}) },
  waitingKeys: { type: Object, default: () => new Set() },
  uploadBusy: { type: Boolean, default: false },
  uploadReady: { type: Boolean, default: false },
  splitting: { type: Boolean, default: false },
  splitCompleted: { type: Boolean, default: false },
})
const emit = defineEmits(['remove-file'])
</script>

<template>
  <Transition
    enter-active-class="transition-all duration-500 ease-out"
    enter-from-class="opacity-0 -translate-y-4 max-h-0"
    enter-to-class="opacity-100 translate-y-0 max-h-40"
    leave-active-class="transition-all duration-300 ease-in"
    leave-from-class="opacity-100 translate-y-0 max-h-40"
    leave-to-class="opacity-0 -translate-y-4 max-h-0"
  >
    <div v-if="pendingFiles.length" class="relative z-20 w-full overflow-hidden shrink-0">
      <div class="flex flex-wrap items-center gap-2">
        <div
          v-for="item in pendingFiles"
          :key="item.key"
          class="relative flex items-center gap-2.5 overflow-hidden rounded-md border border-white/[0.08] bg-white/[0.02] px-3 py-2"
        >
          <!-- 进度条背景 -->
          <div
            class="absolute inset-0 -z-10 bg-[rgba(129,115,223,0.12)] transition-[width] duration-500 ease-out"
            :style="{ width: `${fileProgress[item.key] ?? 0}%` }"
          ></div>

          <i
            class="fa-solid text-sm shrink-0"
            :class="
              item.file.name.toLowerCase().endsWith('.pdf')
                ? 'fa-file-pdf text-rose-400'
                : 'fa-file-image text-[rgb(129,115,223)]'
            "
          ></i>
          <div class="flex flex-col min-w-0 pr-4 text-left">
            <span class="truncate text-xs font-medium text-[#f7f8f8]" :title="item.file.name">
              {{ item.file.name }}
            </span>
            <span class="text-[10px] text-[#62666d]">
              {{ waitingKeys.has(item.key) && uploadBusy ? '等待中' : `${Math.round(fileProgress[item.key] ?? 0)}%` }}
            </span>
          </div>

          <button
            type="button"
            class="absolute right-1.5 top-1.5 flex h-4 w-4 items-center justify-center rounded text-[#62666d] transition-colors hover:text-rose-400"
            :disabled="splitting || splitCompleted"
            @click.stop="() => emit('remove-file', item.key)"
          >
            <i class="fa-solid fa-xmark text-[8px]"></i>
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>
