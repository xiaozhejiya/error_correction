import { onMounted, onBeforeUnmount } from 'vue'

/**
 * 点击外部关闭的通用 composable
 * @param {string} selector - CSS 选择器，点击该选择器外部时触发关闭
 * @param {() => void} onClose - 关闭回调
 */
export function useClickOutside(selector, onClose) {
  const handler = (e) => {
    if (!e.target.closest(selector)) {
      onClose()
    }
  }

  onMounted(() => {
    document.addEventListener('click', handler)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('click', handler)
  })
}
