import { computed, ref } from 'vue'

// 模块单例，跨组件共享登录状态
const currentUser = ref(null)
const authChecked = ref(false)

const quota = computed(() => currentUser.value?.quota || null)
const remainingQuota = computed(() => quota.value?.remaining ?? null)

function setCurrentUser(user) {
  currentUser.value = user || null
  authChecked.value = true
  return currentUser.value
}

function clearCurrentUser() {
  currentUser.value = null
  authChecked.value = true
}

function setQuotaSnapshot(snapshot) {
  if (!snapshot || !currentUser.value) return currentUser.value
  currentUser.value = {
    ...currentUser.value,
    quota: snapshot,
  }
  authChecked.value = true
  return currentUser.value
}

async function refreshCurrentUser() {
  try {
    const res = await fetch('/api/auth/me', { credentials: 'include' })
    if (!res.ok) {
      clearCurrentUser()
      return null
    }
    const data = await res.json().catch(() => null)
    if (data?.user) {
      return setCurrentUser(data.user)
    }
  } catch (_) {
    clearCurrentUser()
    return null
  }
  clearCurrentUser()
  return null
}

export function useAuth() {
  return {
    currentUser,
    authChecked,
    quota,
    remainingQuota,
    setCurrentUser,
    clearCurrentUser,
    setQuotaSnapshot,
    refreshCurrentUser,
  }
}
