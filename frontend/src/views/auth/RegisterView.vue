<script setup>
import { ref, reactive, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth.js'
import { useToast } from '@/composables/useToast.js'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseInput from '@/components/base/BaseInput.vue'

const router = useRouter()
const { setCurrentUser } = useAuth()
const { pushToast } = useToast()

const loading = ref(false)
const error = ref('')
const success = ref('')
const form = reactive({ username: '', email: '', password: '', confirm: '', code: '' })

const sendingCode = ref(false)
const countdown = ref(0)
const rateLimitCountdown = ref(0)
let countdownTimer = null
let rateLimitTimer = null
let sendDebounceTimer = null

const passwordMismatch = () => form.confirm && form.password !== form.confirm

function clearCountdown() {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

function startCountdown(seconds = 60) {
  clearCountdown()
  countdown.value = seconds
  countdownTimer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      clearCountdown()
      countdown.value = 0
    }
  }, 1000)
}

function clearRateLimitCountdown() {
  if (rateLimitTimer) {
    clearInterval(rateLimitTimer)
    rateLimitTimer = null
  }
}

function startRateLimitCountdown(seconds) {
  clearRateLimitCountdown()
  rateLimitCountdown.value = seconds
  error.value = `发送过于频繁，请 ${seconds} 秒后再试`
  rateLimitTimer = setInterval(() => {
    rateLimitCountdown.value -= 1
    if (rateLimitCountdown.value <= 0) {
      clearRateLimitCountdown()
      rateLimitCountdown.value = 0
      error.value = ''
    } else {
      error.value = `发送过于频繁，请 ${rateLimitCountdown.value} 秒后再试`
    }
  }, 1000)
}

async function handleSendCode() {
  error.value = ''
  clearRateLimitCountdown()
  if (sendingCode.value || countdown.value > 0) return
  const email = (form.email || '').trim()
  if (!email || !email.includes('@')) {
    pushToast('error', '请先填写有效邮箱')
    return
  }
  if (sendDebounceTimer) clearTimeout(sendDebounceTimer)
  sendDebounceTimer = setTimeout(async () => {
    sendDebounceTimer = null
    sendingCode.value = true
    try {
      const res = await fetch('/api/auth/send-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, type: 'register' }),
      })
      const data = await res.json().catch(() => ({ }))
      if (!res.ok) {
        // 429 频率限制：解析剩余秒数，启动错误提示倒计时
        if (res.status === 429) {
          const match = (data.error || '').match(/(\d+)\s*秒/)
          const wait = match ? parseInt(match[1], 10) : 30
          startRateLimitCountdown(wait)
        } else {
          error.value = data.error || '发送失败'
        }
        return
      }
      pushToast('success', '验证码已发送到邮箱，请查收')
      startCountdown(60)
    } catch {
      error.value = '网络错误，请重试'
    } finally {
      sendingCode.value = false
    }
  }, 280)
}

async function handleRegister() {
  error.value = ''
  success.value = ''
  if (passwordMismatch()) { error.value = '两次密码不一致'; return }
  if (!form.code.trim()) { error.value = '请输入验证码'; return }
  loading.value = true
  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        username: form.username,
        email: form.email,
        password: form.password,
        code: form.code.trim(),
      }),
    })
    const data = await res.json()
    if (!res.ok) {
      error.value = data.error || '注册失败'
    } else {
      success.value = '注册成功！正在登录...'
      setCurrentUser(data.user)
      router.push('/app')
    }
  } catch {
    error.value = '网络错误，请重试'
  } finally {
    loading.value = false
  }
}

onBeforeUnmount(() => {
  clearCountdown()
  clearRateLimitCountdown()
  if (sendDebounceTimer) clearTimeout(sendDebounceTimer)
})
</script>

<template>
  <form @submit.prevent="handleRegister" class="space-y-4">
    <BaseInput
      v-model="form.username"
      label="用户名"
      required
      autocomplete="username"
      placeholder="您的昵称"
      maxlength="50"
    />

    <div>
      <BaseInput
        v-model="form.email"
        type="email"
        label="邮箱"
        required
        autocomplete="email"
        placeholder="your@email.com"
      >
        <template #append>
          <button
            type="button"
            @click="handleSendCode"
            :disabled="sendingCode || countdown > 0"
            class="shrink-0 h-10 px-4 rounded-xl border text-xs font-medium text-white/70 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            :class="countdown > 0
              ? 'bg-white/[0.02] border-white/[0.05] text-white/30'
              : 'bg-white/[0.03] border-white/[0.08] hover:bg-white/[0.06] hover:text-white/85'"
          >
            <i v-if="sendingCode" class="fas fa-spinner fa-spin"></i>
            <template v-else-if="countdown > 0">{{ countdown }}s</template>
            <template v-else>发送验证码</template>
          </button>
        </template>
      </BaseInput>
    </div>

    <BaseInput
      v-model="form.code"
      label="验证码"
      required
      inputmode="numeric"
      maxlength="6"
      placeholder="6 位验证码"
      autocomplete="one-time-code"
      inputClass="tracking-widest"
    />

    <BaseInput
      v-model="form.password"
      type="password"
      label="密码"
      required
      autocomplete="new-password"
      placeholder="至少 6 位"
      inputClass="minlength-6"
    />

    <div>
      <BaseInput
        v-model="form.confirm"
        type="password"
        label="确认密码"
        required
        autocomplete="new-password"
        placeholder="再次输入密码"
        :error="passwordMismatch()"
      />
      <p v-if="passwordMismatch()" class="text-xs text-rose-400 mt-1">两次密码不一致</p>
    </div>

    <p v-if="error" class="text-sm text-rose-400 flex items-center gap-2">
      <i class="fas fa-circle-exclamation text-xs"></i>{{ error }}
    </p>
    <p v-if="success" class="text-sm text-emerald-400 flex items-center gap-2">
      <i class="fas fa-circle-check text-xs"></i>{{ success }}
    </p>

    <BaseButton variant="cta" type="submit" class="w-full" :disabled="loading || passwordMismatch()">
      <i v-if="loading" class="fas fa-spinner fa-spin text-xs"></i>
      <span>{{ loading ? '注册中...' : '创建账户' }}</span>
    </BaseButton>
  </form>
</template>
