<script setup>
/**
 * FileUploader.vue
 * 文件上传拖拽区
 */
import { ref } from 'vue'

const props = defineProps({
  pendingFiles: { type: Array, default: () => [] },
  fileProgress: { type: Object, default: () => ({}) },
  waitingKeys: { type: Object, default: () => new Set() },
  uploadBusy: { type: Boolean, default: false },
  uploadReady: { type: Boolean, default: false },
  splitting: { type: Boolean, default: false },
  splitCompleted: { type: Boolean, default: false },
  expand: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['upload', 'remove-file'])

const fileInputEl = ref(null)
const uploadHover = ref(false)

const onFileInput = (e) => {
  if (props.disabled) return
  emit('upload', e.target.files)
  e.target.value = ''
}

const onDrop = (e) => {
  e.preventDefault()
  uploadHover.value = false
  if (props.disabled) return
  emit('upload', e.dataTransfer.files)
}

const onClickZone = () => {
  if (props.disabled) return
  fileInputEl.value?.click()
}
</script>

<template>
  <div :class="{ 'flex flex-col flex-1': expand }">
    <div
      class="group relative flex flex-col items-center justify-center rounded-md border transition-colors"
      :class="[
        uploadHover
          ? 'border-[rgb(129,115,223)]/40 bg-white/[0.04]'
          : 'border-dashed border-white/[0.08] hover:border-white/[0.12] hover:bg-white/[0.02]',
        expand ? 'py-14' : 'py-8',
        disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'
      ]"
      @dragenter.prevent="uploadHover = true"
      @dragover.prevent="uploadHover = true"
      @dragleave.prevent="uploadHover = false"
      @drop="onDrop"
      @click="onClickZone"
      @keydown.enter.prevent="onClickZone"
      @keydown.space.prevent="onClickZone"
      role="button"
      tabindex="0"
    >
      <div class="flex flex-col items-center gap-3">
        <i class="fa-solid fa-cloud-arrow-up text-lg text-[#62666d] group-hover:text-[#8a8f98] transition-colors"></i>

        <div class="text-center">
          <p v-if="disabled" class="text-sm text-[#62666d]">
            请先在 <span class="text-[rgb(145,132,235)]">系统设置</span> 中配置模型
          </p>
          <p v-else class="text-sm text-[#8a8f98]">
            拖拽文件到此处或 <span class="text-[rgb(145,132,235)] cursor-pointer">浏览文件</span>
          </p>
          <p class="mt-1 text-xs text-[#62666d]">PDF, PNG, JPG</p>
        </div>
      </div>

      <input
        ref="fileInputEl"
        type="file"
        class="hidden"
        accept=".pdf,.png,.jpg,.jpeg,.bmp,.tiff,.webp"
        multiple
        @change="onFileInput"
      />
    </div>
  </div>
</template>
