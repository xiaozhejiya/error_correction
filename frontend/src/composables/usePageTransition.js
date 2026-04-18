import { ref } from 'vue'

const loading = ref(false)
let hideTimer = null
let resolveEnter = null

/**
 * 全局页面过渡控制
 * 采用 Promise + 事件监听机制，确保路由跳转在遮罩完全覆盖后才开始
 */
export function usePageTransition() {
  /**
   * 显示遮罩
   * 返回一个 Promise，该 Promise 将在 BaseLoading 组件触发 @after-enter 后 resolve
   */
  const show = () => {
    if (hideTimer) {
      clearTimeout(hideTimer)
      hideTimer = null
    }

    // 如果已经在 loading 中，直接返回已有的 Promise 或成功的 Promise
    if (loading.value && resolveEnter) {
      return new Promise(r => {
        const oldResolve = resolveEnter
        resolveEnter = () => {
          oldResolve()
          r()
        }
      })
    }

    loading.value = true

    return new Promise((resolve) => {
      resolveEnter = resolve
    })
  }

  /**
   * 遮罩淡入动画完成后的回调，由 App.vue 监听 BaseLoading 事件后调用
   */
  const notifyEnterCompleted = () => {
    if (resolveEnter) {
      resolveEnter()
      resolveEnter = null
    }
  }

  /**
   * 隐藏遮罩
   * @param {number} delay 延迟毫秒数，确保新组件渲染完成后再淡出
   */
  const hide = (delay = 400) => {
    if (hideTimer) clearTimeout(hideTimer)
    hideTimer = setTimeout(() => {
      loading.value = false
      hideTimer = null
    }, delay)
  }

  return {
    loading,
    show,
    hide,
    notifyEnterCompleted
  }
}
