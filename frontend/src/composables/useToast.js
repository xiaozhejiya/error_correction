import { inject } from 'vue'

const TOAST_KEY = 'pushToast'
const noopToast = (type, msg) => { console.warn(`[Toast:${type}] ${msg}`) }

/**
 * useToast — 注入 pushToast，带安全 fallback
 * 用于子组件中，替代手写 inject('pushToast', fallback)
 */
export function useToast() {
  const pushToast = inject(TOAST_KEY, noopToast)
  return { pushToast }
}

/** provide 时使用的 key，保持一致 */
export const TOAST_INJECTION_KEY = TOAST_KEY
