<script setup>
/**
 * ImageModal.vue
 * 图片预览弹窗（缩放 + 拖拽）
 */
import { clampScale } from '@/utils.js'

const props = defineProps({
  open: { type: Boolean, default: false },
  src: { type: String, default: '' },
  scale: { type: Number, default: 1 },
})

const emit = defineEmits(['close', 'update:scale'])

const MIN_SCALE = 0.25
const MAX_SCALE = 5

const onWheel = (e) => {
  e.preventDefault()
  emit('update:scale', clampScale(props.scale, e.deltaY, MIN_SCALE, MAX_SCALE))
}
</script>

<template>
  <div
    v-show="open"
    role="dialog"
    aria-modal="true"
    class="img-modal fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
    @click="emit('close')"
    @wheel.prevent="onWheel"
  >
    <img
      class="max-h-[90vh] w-auto max-w-full rounded-xl shadow-2xl transition-transform duration-100"
      :style="{ transform: `scale(${scale})` }"
      :src="src"
      alt="预览"
      @click.stop
    />
  </div>
</template>
