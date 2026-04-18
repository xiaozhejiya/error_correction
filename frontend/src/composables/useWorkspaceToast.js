import { ref } from 'vue'

export function useWorkspaceToast() {
  const toasts = ref([])
  let toastId = 0

  const pushToast = (type, message, timeout = 2600) => {
    const id = ++toastId
    toasts.value = [{ id, type, message }, ...toasts.value].slice(0, 5)
    if (timeout > 0) {
      window.setTimeout(() => {
        toasts.value = toasts.value.filter(t => t.id !== id)
      }, timeout)
    }
  }

  return { toasts, pushToast }
}
