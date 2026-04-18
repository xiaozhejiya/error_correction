<script setup>
/**
 * OcrPreview.vue
 * OCR 结果预览 — 图片 + bbox 标注叠加
 */
import { ref, computed, onBeforeUnmount } from 'vue'
import SplitLoading from './SplitLoading.vue'

const props = defineProps({
  pages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  loadingText: { type: String, default: '正在执行 OCR 识别...' },
  previewUrl: { type: String, default: '' },
})

// 按钮已移至 ContentPanel toolbar，emits 不再需要

// 每张图片在 object-contain 下的实际渲染区域（含偏移）
const imageSizes = ref({})
const imgRef = ref(null)

function calcImageSize(img, pageIndex) {
  if (!img) return
  const cw = img.clientWidth, ch = img.clientHeight
  const nw = img.naturalWidth, nh = img.naturalHeight
  if (!nw || !nh) return
  const scale = Math.min(cw / nw, ch / nh)
  const rw = nw * scale, rh = nh * scale
  const ox = (cw - rw) / 2, oy = (ch - rh) / 2
  imageSizes.value = { ...imageSizes.value, [pageIndex]: { w: rw, h: rh, ox, oy } }
}

function onImageLoad(pageIndex, event) {
  calcImageSize(event.target, pageIndex)
}

// 浏览器缩放/窗口大小变化时重新计算
const resizeObserver = new ResizeObserver(() => {
  if (imgRef.value) {
    calcImageSize(imgRef.value, currentPageData.value?.page_index)
  }
})
onBeforeUnmount(() => resizeObserver.disconnect())

// 颜色映射
const labelColors = {
  text: { border: 'rgba(59,130,246,0.6)', bg: 'rgba(59,130,246,0.15)', tag: 'rgba(59,130,246,0.85)' },
  title: { border: 'rgba(168,85,247,0.6)', bg: 'rgba(168,85,247,0.15)', tag: 'rgba(168,85,247,0.85)' },
  formula: { border: 'rgba(245,158,11,0.6)', bg: 'rgba(245,158,11,0.15)', tag: 'rgba(245,158,11,0.85)' },
  image: { border: 'rgba(16,185,129,0.6)', bg: 'rgba(16,185,129,0.15)', tag: 'rgba(16,185,129,0.85)' },
  chart: { border: 'rgba(16,185,129,0.6)', bg: 'rgba(16,185,129,0.15)', tag: 'rgba(16,185,129,0.85)' },
  table: { border: 'rgba(236,72,153,0.6)', bg: 'rgba(236,72,153,0.15)', tag: 'rgba(236,72,153,0.85)' },
  aside_text: { border: 'rgba(148,163,184,0.4)', bg: 'rgba(148,163,184,0.08)', tag: 'rgba(148,163,184,0.7)' },
  header: { border: 'rgba(148,163,184,0.4)', bg: 'rgba(148,163,184,0.08)', tag: 'rgba(148,163,184,0.7)' },
  footer: { border: 'rgba(148,163,184,0.4)', bg: 'rgba(148,163,184,0.08)', tag: 'rgba(148,163,184,0.7)' },
}
const defaultColor = { border: 'rgba(148,163,184,0.5)', bg: 'rgba(148,163,184,0.1)', tag: 'rgba(148,163,184,0.75)' }

function getColor(label) {
  return labelColors[label] || defaultColor
}

function boxStyle(block, page, pageIndex) {
  const size = imageSizes.value[pageIndex]
  if (!size) return { display: 'none' }
  const scaleX = size.w / page.page_width
  const scaleY = size.h / page.page_height
  const [x1, y1, x2, y2] = block.bbox
  const color = getColor(block.label)
  return {
    position: 'absolute',
    left: `${size.ox + x1 * scaleX}px`,
    top: `${size.oy + y1 * scaleY}px`,
    width: `${(x2 - x1) * scaleX}px`,
    height: `${(y2 - y1) * scaleY}px`,
    border: `1.5px solid ${color.border}`,
    backgroundColor: color.bg,
    pointerEvents: 'none',
  }
}

function tagStyle(block) {
  const color = getColor(block.label)
  return {
    position: 'absolute',
    top: '-1px',
    left: '-1px',
    backgroundColor: color.tag,
    color: '#fff',
    fontSize: '9px',
    lineHeight: '1',
    padding: '2px 4px',
    borderRadius: '0 0 3px 0',
    whiteSpace: 'nowrap',
  }
}

// 分页
const currentPage = ref(0)
const currentPageData = computed(() => props.pages[currentPage.value])

// 悬停的 block
const hoveredBlock = ref(null)
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- 加载中 -->
    <div v-if="loading" class="flex-1 min-h-0 relative">
      <img v-if="previewUrl" :src="previewUrl" class="absolute inset-0 w-full h-full object-contain opacity-10 blur-sm" alt="" />
      <SplitLoading title="正在执行 OCR 识别" subtitle="PaddleOCR 正在解析文档结构与文字内容" />
    </div>

    <!-- 无数据 -->
    <div v-else-if="!pages.length" class="flex-1 flex items-center justify-center">
      <p class="text-sm text-[#62666d]">暂无 OCR 数据</p>
    </div>

    <!-- 预览（单张 + 分页） -->
    <template v-else>
      <div class="flex-1 min-h-0 relative overflow-hidden">
        <img
          v-if="currentPageData.image_url"
          ref="imgRef"
          :src="currentPageData.image_url"
          class="block w-full h-full object-contain"
          alt=""
          @load="(e) => { onImageLoad(currentPageData.page_index, e); resizeObserver.disconnect(); resizeObserver.observe(e.target) }"
        />
        <!-- bbox 叠加层 -->
        <div
          v-for="(block, bi) in currentPageData.blocks"
          :key="bi"
          :style="boxStyle(block, currentPageData, currentPageData.page_index)"
          @mouseenter="hoveredBlock = `${currentPageData.page_index}-${bi}`"
          @mouseleave="hoveredBlock = null"
          style="pointer-events: auto; cursor: default;"
        >
          <span :style="tagStyle(block)">{{ block.label }}</span>
          <div
            v-if="hoveredBlock === `${currentPageData.page_index}-${bi}` && block.content"
            class="absolute left-0 top-full z-50 mt-1 max-w-xs rounded-md bg-slate-900/95 border border-white/10 px-2 py-1 text-xs text-slate-200 shadow-lg"
            style="pointer-events: none;"
          >
            {{ block.content }}
          </div>
        </div>
      </div>

      <!-- 分页（多页时显示） -->
      <div v-if="pages.length > 1" class="flex items-center justify-center gap-2 py-2 shrink-0">
        <button
          v-for="(_, i) in pages"
          :key="i"
          @click="currentPage = i"
          class="h-2 rounded-full transition-all"
          :class="i === currentPage ? 'w-6 bg-[rgb(129,115,223)]' : 'w-2 bg-white/20 hover:bg-white/40'"
        />
      </div>
    </template>
  </div>
</template>
