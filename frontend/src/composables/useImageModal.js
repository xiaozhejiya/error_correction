import { ref } from 'vue'

// ── 模块级单例状态 ──────────────────────────────────────
const modalOpen = ref(false)
const modalSrc = ref('')
const modalScale = ref(1)

const openModal = (src) => {
  modalSrc.value = src || ''
  modalScale.value = 1
  modalOpen.value = !!src
  if (src) document.body.style.overflow = 'hidden'
}

const closeModal = () => {
  modalOpen.value = false
  modalSrc.value = ''
  modalScale.value = 1
  document.body.style.overflow = ''
}

/**
 * useImageModal — 图片预览弹窗单例 composable
 * 任何组件调用 useImageModal() 都操作同一个弹窗实例
 */
export function useImageModal() {
  return { modalOpen, modalSrc, modalScale, openModal, closeModal }
}
