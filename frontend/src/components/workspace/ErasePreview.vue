<script setup>
/**
 * ErasePreview.vue
 * 擦除前后对比预览 — 拖拽滑块对比，单张显示 + 分页
 */
import { ref, computed } from 'vue'
import SplitLoading from './SplitLoading.vue'

const props = defineProps({
  images: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  previewUrl: { type: String, default: '' },
})

// 当前页码（0-based）
const currentPage = ref(0)
const currentImg = computed(() => props.images[currentPage.value])

// 滑块位置（0-100）
const sliderPos = ref(50)

function onPointerDown(event) {
  const container = event.currentTarget.closest('.compare-container')
  if (!container) return

  const onMove = (e) => {
    const rect = container.getBoundingClientRect()
    const x = (e.clientX ?? e.touches?.[0]?.clientX ?? 0) - rect.left
    sliderPos.value = Math.max(0, Math.min(100, (x / rect.width) * 100))
  }
  const onUp = () => {
    document.removeEventListener('pointermove', onMove)
    document.removeEventListener('pointerup', onUp)
  }
  document.addEventListener('pointermove', onMove)
  document.addEventListener('pointerup', onUp)
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- 加载中 -->
    <div v-if="loading" class="flex-1 min-h-0 relative">
      <img v-if="previewUrl" :src="previewUrl" class="absolute inset-0 w-full h-full object-contain opacity-10 blur-sm" alt="" />
      <SplitLoading title="正在擦除手写笔迹" subtitle="EnsExam 模型正在识别并移除手写内容" />
    </div>

    <!-- 无数据 -->
    <div v-else-if="!images.length" class="flex-1 flex items-center justify-center">
      <p class="text-sm text-[#62666d]">暂无擦除数据</p>
    </div>

    <!-- 预览（单张 + 分页） -->
    <template v-else>
      <div
        class="compare-container flex-1 min-h-0 relative select-none overflow-hidden"
        style="touch-action: none;"
      >
        <!-- 擦除后（底层） -->
        <img :src="currentImg.erased_url" class="block w-full h-full object-contain" alt="" draggable="false" />

        <!-- 原图（上层，clip 裁剪） -->
        <div
          class="absolute inset-0 overflow-hidden"
          :style="{ clipPath: `inset(0 ${100 - sliderPos}% 0 0)` }"
        >
          <img :src="currentImg.original_url" class="block w-full h-full object-contain" alt="" draggable="false" />
        </div>

        <!-- 滑块线 -->
        <div
          class="absolute top-0 bottom-0 w-0.5 z-10"
          style="background: rgb(129,115,223);"
          :style="{ left: sliderPos + '%' }"
        >
          <div
            class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex h-8 w-8 cursor-ew-resize items-center justify-center rounded-full shadow-lg"
            style="background: rgb(129,115,223);"
            @pointerdown.prevent="onPointerDown"
          >
            <i class="fa-solid fa-arrows-left-right text-xs text-white"></i>
          </div>
        </div>
      </div>

      <!-- 分页（多张时显示） -->
      <div v-if="images.length > 1" class="flex items-center justify-center gap-2 py-2 shrink-0">
        <button
          v-for="(_, i) in images"
          :key="i"
          @click="currentPage = i; sliderPos = 50"
          class="h-2 rounded-full transition-all"
          :class="i === currentPage ? 'w-6 bg-[rgb(129,115,223)]' : 'w-2 bg-white/20 hover:bg-white/40'"
        />
      </div>
    </template>
  </div>
</template>
