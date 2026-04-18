import { ref } from 'vue'

const isDark = ref(document.documentElement.classList.contains('dark'))

export function useTheme() {
  function setTheme(dark) {
    isDark.value = dark
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }

  /**
   * 带圆形扩散动画的主题切换
   * @param {HTMLElement} [btnEl] - 触发按钮元素，动画从此处扩散；不传则无动画
   */
  async function toggleTheme(btnEl) {
    const nextDark = !isDark.value

    const prefersReduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    const canTransition = !prefersReduce && typeof document.startViewTransition === 'function'

    if (!canTransition || !btnEl) {
      setTheme(nextDark)
      return
    }

    const rect = btnEl.getBoundingClientRect()
    const x = rect.left + rect.width / 2
    const y = rect.top + rect.height / 2
    const endRadius = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y))

    const transition = document.startViewTransition(() => setTheme(nextDark))
    try {
      await transition.ready
      const duration = 1000
      document.documentElement.animate(
        { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${endRadius}px at ${x}px ${y}px)`] },
        { duration, easing: 'cubic-bezier(0.2, 0, 0, 1)', pseudoElement: '::view-transition-new(root)' },
      )
      document.documentElement.animate(
        { opacity: [1, 0.98] },
        { duration, easing: 'linear', pseudoElement: '::view-transition-old(root)' },
      )
      await transition.finished
    } catch (_) {
      setTheme(nextDark)
    }
  }

  function initTheme() {
    const saved = localStorage.getItem('theme') || 'dark'
    isDark.value = saved === 'dark'
    document.documentElement.classList.toggle('dark', isDark.value)
  }

  return { isDark, setTheme, toggleTheme, initTheme }
}
