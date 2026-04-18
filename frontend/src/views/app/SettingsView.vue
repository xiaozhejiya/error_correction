<script setup>
import { computed, ref, onMounted, watch, onBeforeUnmount } from 'vue'
import { fetchAppConfig, updateAppConfig, updateProfile, uploadProfileAvatar, deleteProfileAvatar } from '@/api.js'
import { genId } from '@/utils.js'
import { useAuth } from '@/composables/useAuth.js'
import { useToast } from '@/composables/useToast.js'
import { useSystemStatus } from '@/composables/useSystemStatus.js'
import ContentPanel from '@/components/workspace/ContentPanel.vue'
import ProviderDialog from '@/components/settings/ProviderDialog.vue'
import ProviderSection from '@/components/settings/ProviderSection.vue'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseInput from '@/components/base/BaseInput.vue'

const props = defineProps({
  section: { type: String, default: 'profile' },
})

const { currentUser, quota, setCurrentUser } = useAuth()
const { pushToast } = useToast()
const { doFetchStatus } = useSystemStatus()

const quotaResetText = computed(() => {
  const resetAt = quota.value?.reset_at
  if (!resetAt) return '每日凌晨自动重置免费体验次数'
  const date = new Date(resetAt)
  if (Number.isNaN(date.getTime())) return '每日凌晨自动重置免费体验次数'
  return `下次重置时间：${date.toLocaleString('zh-CN', { hour12: false })}`
})

const isProfileSection = computed(() => props.section === 'profile')
const isQuotaSection = computed(() => props.section === 'quota')
const isApiSection = computed(() => props.section === 'api')
const settingsPageTitle = computed(() => {
  if (isApiSection.value) return 'API 设置'
  if (isQuotaSection.value) return '免费额度'
  return '用户资料设置'
})
const settingsPageDescription = computed(() => {
  if (isApiSection.value) return '集中管理 AI 与 OCR provider 的接口配置。'
  if (isQuotaSection.value) return '查看系统托管 AI / OCR 服务的免费体验额度与每日重置时间。'
  return '配置显示名称、昵称与头像，侧边栏会立即同步展示。'
})
const pageTitle = computed(() => isApiSection.value ? 'API 设置' : '用户资料设置')
const pageDescription = computed(() => {
  return isApiSection.value
    ? '管理 AI 模型供应商与 OCR 服务连接参数，修改即时生效。'
    : '配置显示名称、昵称与头像，侧边栏会立即同步展示。'
})

const loading = ref(true)
const saving = ref(false)
const profileSaving = ref(false)
const profileUploading = ref(false)
const profileDeletingAvatar = ref(false)
const profileError = ref('')
const profileForm = ref({
  display_name: '',
  nickname: '',
})
const avatarInputRef = ref(null)
const selectedAvatarFile = ref(null)
const avatarPreviewUrl = ref('')
const avatarUploadXhr = ref(null)

const userPreviewName = computed(() => {
  return profileForm.value.display_name.trim()
    || profileForm.value.nickname.trim()
    || currentUser.value?.username
    || '未登录用户'
})

const userPreviewInitial = computed(() => {
  return userPreviewName.value?.trim()?.[0]?.toUpperCase() || '?'
})

const displayedAvatarUrl = computed(() => {
  return avatarPreviewUrl.value || currentUser.value?.avatar_url || ''
})

const clearAvatarPreview = () => {
  if (avatarPreviewUrl.value) {
    URL.revokeObjectURL(avatarPreviewUrl.value)
  }
  avatarPreviewUrl.value = ''
  selectedAvatarFile.value = null
  if (avatarInputRef.value) {
    avatarInputRef.value.value = ''
  }
}

const syncProfileForm = () => {
  profileForm.value = {
    display_name: currentUser.value?.display_name || '',
    nickname: currentUser.value?.nickname || '',
  }
}

watch(currentUser, syncProfileForm, { immediate: true })

const saveProfile = async () => {
  if (profileSaving.value) return
  profileSaving.value = true
  profileError.value = ''
  try {
    const user = await updateProfile({
      display_name: profileForm.value.display_name,
      nickname: profileForm.value.nickname,
    })
    setCurrentUser(user)
    pushToast('success', '个人资料已保存')
  } catch (e) {
    profileError.value = e instanceof Error ? e.message : String(e)
    pushToast('error', profileError.value)
  } finally {
    profileSaving.value = false
  }
}

const chooseAvatarFile = () => {
  if (profileUploading.value || profileDeletingAvatar.value) return
  avatarInputRef.value?.click()
}

const onAvatarFileChange = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  clearAvatarPreview()
  selectedAvatarFile.value = file
  avatarPreviewUrl.value = URL.createObjectURL(file)
  profileError.value = ''
}

const submitAvatarUpload = () => {
  if (!selectedAvatarFile.value || profileUploading.value) return
  profileUploading.value = true
  profileError.value = ''
  avatarUploadXhr.value = uploadProfileAvatar(selectedAvatarFile.value, {
    onSuccess: (user) => {
      setCurrentUser(user)
      clearAvatarPreview()
      profileUploading.value = false
      avatarUploadXhr.value = null
      pushToast('success', '头像已更新')
    },
    onError: (error) => {
      profileError.value = error instanceof Error ? error.message : String(error)
      profileUploading.value = false
      avatarUploadXhr.value = null
      pushToast('error', profileError.value)
    },
    onAbort: () => {
      profileUploading.value = false
      avatarUploadXhr.value = null
    },
  })
}

const removeAvatar = async () => {
  if (profileDeletingAvatar.value || profileUploading.value) return
  profileDeletingAvatar.value = true
  profileError.value = ''
  try {
    const user = await deleteProfileAvatar()
    setCurrentUser(user)
    clearAvatarPreview()
    pushToast('success', '头像已删除')
  } catch (e) {
    profileError.value = e instanceof Error ? e.message : String(e)
    pushToast('error', profileError.value)
  } finally {
    profileDeletingAvatar.value = false
  }
}

onBeforeUnmount(() => {
  if (avatarUploadXhr.value) avatarUploadXhr.value.abort()
  clearAvatarPreview()
})

// ---------- 多 Provider 数据结构 ----------

const makeOpenAIProvider = (data = {}) => ({
  id: data.id || genId(),
  name: data.name || '',
  api_key: data.api_key || '',
  base_url: data.base_url || '',
  model_name: data.model_name || '',
  light_model_name: data.light_model_name || '',
  supports_function_calling: data.supports_function_calling ?? true,
  api_key_set: data.api_key_set || false,
  api_key_hint: data.api_key_hint || '',
})

const makeAnthropicProvider = (data = {}) => ({
  id: data.id || genId(),
  name: data.name || '',
  api_key: data.api_key || '',
  base_url: data.base_url || '',
  model_name: data.model_name || '',
  api_key_set: data.api_key_set || false,
  api_key_hint: data.api_key_hint || '',
})

const makePaddleOCRProvider = (data = {}) => ({
  id: data.id || genId(),
  name: data.name || '',
  api_key: data.api_key || '',
  base_url: data.base_url || data.api_url || '',
  model_name: data.model_name || data.model || '',
  use_doc_orientation: data.use_doc_orientation || false,
  use_doc_unwarping: data.use_doc_unwarping || false,
  use_chart_recognition: data.use_chart_recognition || false,
  api_key_set: data.api_key_set || data.api_token_set || false,
  api_key_hint: data.api_key_hint || data.api_token_hint || '',
})

const openaiProviders = ref([])
const anthropicProviders = ref([])
const paddleocrProviders = ref([])

// 当前激活的 provider ID（每类只能激活一个）
const activeOpenaiId = ref(null)
const activeAnthropicId = ref(null)
const activePaddleocrId = ref(null)

const toggleActive = (type, id) => {
  const refMap = { openai: activeOpenaiId, anthropic: activeAnthropicId, paddleocr: activePaddleocrId }
  const target = refMap[type]
  target.value = target.value === id ? null : id
}

// ---------- 加载 / 保存 ----------

const loadConfig = async () => {
  configLoaded.value = false
  loading.value = true
  try {
    const cfg = await fetchAppConfig()

    if (cfg.openai_providers && cfg.openai_providers.length > 0) {
      openaiProviders.value = cfg.openai_providers.map(p => makeOpenAIProvider(p))
    } else if (cfg.openai) {
      openaiProviders.value = [makeOpenAIProvider({ name: 'Default', ...cfg.openai })]
    } else {
      openaiProviders.value = []
    }
    activeOpenaiId.value = cfg.active_openai_id || openaiProviders.value[0]?.id || null

    if (cfg.anthropic_providers && cfg.anthropic_providers.length > 0) {
      anthropicProviders.value = cfg.anthropic_providers.map(p => makeAnthropicProvider(p))
    } else if (cfg.anthropic) {
      anthropicProviders.value = [makeAnthropicProvider({ name: 'Default', ...cfg.anthropic })]
    } else {
      anthropicProviders.value = []
    }
    activeAnthropicId.value = cfg.active_anthropic_id || anthropicProviders.value[0]?.id || null

    if (cfg.paddleocr_providers && cfg.paddleocr_providers.length > 0) {
      paddleocrProviders.value = cfg.paddleocr_providers.map(p => makePaddleOCRProvider(p))
    } else if (cfg.paddleocr) {
      paddleocrProviders.value = [makePaddleOCRProvider({ name: 'Default', ...cfg.paddleocr })]
    } else {
      paddleocrProviders.value = []
    }
    activePaddleocrId.value = cfg.active_paddleocr_id || paddleocrProviders.value[0]?.id || null
  } catch (e) {
    pushToast('error', '加载配置失败: ' + (e instanceof Error ? e.message : String(e)))
  } finally {
    loading.value = false
    setTimeout(() => { configLoaded.value = true }, 0)
  }
}

const saveConfig = async () => {
  if (saving.value) return
  saving.value = true
  try {
    const payload = {}

    payload.openai_providers = openaiProviders.value.map(p => {
      const item = { id: p.id, name: p.name, base_url: p.base_url, model_name: p.model_name, light_model_name: p.light_model_name, supports_function_calling: p.supports_function_calling }
      if (p.api_key) item.api_key = p.api_key
      return item
    })

    payload.anthropic_providers = anthropicProviders.value.map(p => {
      const item = { id: p.id, name: p.name, base_url: p.base_url, model_name: p.model_name }
      if (p.api_key) item.api_key = p.api_key
      return item
    })

    payload.paddleocr_providers = paddleocrProviders.value.map(p => {
      const item = { id: p.id, name: p.name, api_url: p.base_url, model: p.model_name, use_doc_orientation: p.use_doc_orientation, use_doc_unwarping: p.use_doc_unwarping, use_chart_recognition: p.use_chart_recognition }
      if (p.api_key) item.api_token = p.api_key
      return item
    })

    payload.active_openai_id = activeOpenaiId.value
    payload.active_anthropic_id = activeAnthropicId.value
    payload.active_paddleocr_id = activePaddleocrId.value

    await updateAppConfig(payload)
    doFetchStatus()
  } catch (e) {
    pushToast('error', '保存失败: ' + (e instanceof Error ? e.message : String(e)))
  } finally {
    saving.value = false
  }
}

// ---------- 自动保存（防抖） ----------
let autoSaveTimer = null
const configLoaded = ref(false)

watch(
  [openaiProviders, anthropicProviders, paddleocrProviders, activeOpenaiId, activeAnthropicId, activePaddleocrId],
  () => {
    if (!configLoaded.value) return
    clearTimeout(autoSaveTimer)
    autoSaveTimer = setTimeout(() => saveConfig(), 600)
  },
  { deep: true },
)

const removeProvider = async (type, idx) => {
  const listMap = { openai: openaiProviders, anthropic: anthropicProviders, paddleocr: paddleocrProviders }
  const activeMap = { openai: activeOpenaiId, anthropic: activeAnthropicId, paddleocr: activePaddleocrId }
  const list = listMap[type]
  if (list.value[idx]?.id === activeMap[type].value) activeMap[type].value = null
  list.value.splice(idx, 1)
  clearTimeout(autoSaveTimer)
  try {
    await saveConfig()
    pushToast('success', '已删除')
  } catch { /* saveConfig 内部已 toast error */ }
}

// ---------- 弹窗控制 ----------
const dialogOpen = ref(false)
const dialogType = ref('openai')
const dialogEditData = ref(null)
const dialogEditIndex = ref(-1)

const openAddDialog = (type) => {
  dialogType.value = type
  dialogEditData.value = null
  dialogEditIndex.value = -1
  dialogOpen.value = true
}

const openEditDialog = (type, provider, idx) => {
  dialogType.value = type
  dialogEditData.value = { ...provider }
  dialogEditIndex.value = idx
  dialogOpen.value = true
}

const onDialogConfirm = async (formData) => {
  if (dialogEditIndex.value >= 0) {
    const listMap = { openai: openaiProviders, anthropic: anthropicProviders, paddleocr: paddleocrProviders }
    const list = listMap[dialogType.value]
    const existing = list.value[dialogEditIndex.value]
    if (existing) {
      Object.assign(existing, formData)
      if (dialogType.value === 'paddleocr') {
        existing.base_url = formData.base_url
        existing.model_name = formData.model_name
      }
    }
  } else {
    if (dialogType.value === 'openai') {
      const p = makeOpenAIProvider(formData)
      openaiProviders.value.push(p)
      if (openaiProviders.value.length === 1) activeOpenaiId.value = p.id
    } else if (dialogType.value === 'anthropic') {
      const p = makeAnthropicProvider(formData)
      anthropicProviders.value.push(p)
      if (anthropicProviders.value.length === 1) activeAnthropicId.value = p.id
    } else {
      const p = makePaddleOCRProvider({ name: formData.name, api_key: formData.api_key, api_url: formData.base_url, model: formData.model_name, use_doc_orientation: formData.use_doc_orientation, use_doc_unwarping: formData.use_doc_unwarping, use_chart_recognition: formData.use_chart_recognition })
      paddleocrProviders.value.push(p)
      if (paddleocrProviders.value.length === 1) activePaddleocrId.value = p.id
    }
  }
  const isEdit = dialogEditIndex.value >= 0
  dialogOpen.value = false

  clearTimeout(autoSaveTimer)
  try {
    await saveConfig()
    pushToast('success', isEdit ? '配置已更新' : '供应商已添加')
  } catch { /* saveConfig 内部已 toast error */ }
}

onMounted(() => { loadConfig() })
</script>

<template>
  <ContentPanel :title="settingsPageTitle">
    <div class="relative h-full overflow-y-auto">
      <div class="container relative z-10 mx-auto max-w-3xl">
        <div class="mb-8 pl-2 sm:pl-0">
          <p class="text-sm font-medium text-slate-500 dark:text-slate-400">{{ settingsPageDescription }}</p>
        </div>

        <div v-if="loading" class="flex items-center justify-center py-20">
          <i class="fa-solid fa-circle-notch fa-spin mr-3 text-2xl text-blue-500"></i>
          <span class="text-sm font-semibold text-slate-500 dark:text-slate-400">加载配置中...</span>
        </div>

        <div v-else-if="isProfileSection || isQuotaSection" class="space-y-6">
          <section v-if="isQuotaSection" class="rounded-2xl border border-white/[0.06] border-t-white/[0.15] border-b-white/[0.03] bg-white/[0.02] p-6 backdrop-blur-xl">
            <div class="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 class="text-xl font-semibold text-slate-900 dark:text-white">免费体验额度</h2>
                <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">使用平台托管的 AI / OCR 服务时会消耗每日免费次数；使用你自己的已配置 provider 不会扣减。</p>
              </div>
              <div class="rounded-full border border-[rgb(145,132,235)]/20 bg-[rgb(145,132,235)]/10 px-3 py-1 text-xs font-medium text-[rgb(145,132,235)]">
                {{ quota?.remaining ?? '--' }} / {{ quota?.daily_free_quota ?? '--' }}
              </div>
            </div>

            <div class="grid gap-4 md:grid-cols-3">
              <div class="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                <p class="text-xs text-slate-500 dark:text-slate-400">每日额度</p>
                <p class="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{{ quota?.daily_free_quota ?? '--' }}</p>
              </div>
              <div class="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                <p class="text-xs text-slate-500 dark:text-slate-400">今日已用</p>
                <p class="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">{{ quota?.daily_free_used ?? '--' }}</p>
              </div>
              <div class="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                <p class="text-xs text-slate-500 dark:text-slate-400">今日剩余</p>
                <p class="mt-2 text-2xl font-semibold text-[rgb(145,132,235)]">{{ quota?.remaining ?? '--' }}</p>
              </div>
            </div>

            <p class="mt-4 text-sm text-slate-500 dark:text-slate-400">{{ quotaResetText }}</p>
          </section>

          <section v-if="isProfileSection" class="rounded-2xl border border-white/[0.06] border-t-white/[0.15] border-b-white/[0.03] bg-white/[0.02] p-6 backdrop-blur-xl">
            <div class="flex flex-col gap-6 md:flex-row md:items-start">
              <div class="flex items-center gap-4 md:w-56 md:flex-col md:items-center md:text-center">
                <div class="h-20 w-20 overflow-hidden rounded-2xl border border-white/[0.08] bg-white/[0.03] text-white shadow-sm">
                  <img
                    v-if="displayedAvatarUrl"
                    :src="displayedAvatarUrl"
                    alt="头像预览"
                    class="h-full w-full object-cover"
                  />
                  <div
                    v-else
                    class="relative flex h-full w-full items-center justify-center text-2xl font-bold"
                    style="background: linear-gradient(to bottom, rgba(129,115,223,0.9), rgba(99,87,199,0.9)); box-shadow: inset 0 1px 0 0 rgba(255,255,255,0.12);"
                  >
                    <span class="absolute inset-0 pointer-events-none" style="background-image: linear-gradient(to right, rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.06) 1px, transparent 1px); background-size: 8px 8px; mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%); -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);"></span>
                    <span class="relative z-10">{{ userPreviewInitial }}</span>
                  </div>
                </div>
                <div class="min-w-0">
                  <p class="truncate text-base font-semibold text-slate-100 dark:text-[#f7f8f8]">{{ userPreviewName }}</p>
                  <p class="truncate text-sm text-slate-500 dark:text-slate-400">@{{ currentUser?.username || 'guest' }}</p>
                </div>
              </div>

              <div class="flex-1 space-y-4">
                <div>
                  <h2 class="text-xl font-semibold text-slate-900 dark:text-white">个人资料</h2>
                  <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">支持设置显示名称、昵称和自定义上传头像，侧边栏会立即同步展示。</p>
                </div>

                <div class="space-y-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                  <input
                    ref="avatarInputRef"
                    type="file"
                    accept=".png,.jpg,.jpeg,.webp,.bmp,image/png,image/jpeg,image/webp,image/bmp"
                    class="hidden"
                    @change="onAvatarFileChange"
                  />

                  <div class="flex flex-wrap items-center gap-3">
                    <BaseButton variant="secondary" :disabled="profileUploading || profileDeletingAvatar" @click="chooseAvatarFile">
                      <i class="fas fa-image text-xs"></i>
                      <span>{{ selectedAvatarFile ? '重新选择图片' : '选择头像图片' }}</span>
                    </BaseButton>

                    <BaseButton variant="primary" :disabled="!selectedAvatarFile || profileUploading || profileDeletingAvatar" @click="submitAvatarUpload">
                      <i v-if="profileUploading" class="fas fa-spinner fa-spin text-xs"></i>
                      <i v-else class="fas fa-upload text-xs"></i>
                      <span>{{ profileUploading ? '上传中...' : '上传头像' }}</span>
                    </BaseButton>

                    <BaseButton variant="secondary" :disabled="(!currentUser?.avatar_url && !selectedAvatarFile) || profileUploading || profileDeletingAvatar" @click="removeAvatar">
                      <i v-if="profileDeletingAvatar" class="fas fa-spinner fa-spin text-xs"></i>
                      <i v-else class="fas fa-trash text-xs"></i>
                      <span>{{ profileDeletingAvatar ? '删除中...' : '删除头像' }}</span>
                    </BaseButton>
                  </div>

                  <p class="text-sm text-slate-500 dark:text-slate-400">
                    支持 png、jpg、jpeg、webp、bmp，大小不超过 5MB。
                  </p>

                  <p v-if="selectedAvatarFile" class="text-sm text-slate-400 dark:text-slate-400">
                    已选择：{{ selectedAvatarFile.name }}
                  </p>
                </div>

                <BaseInput
                  v-model="profileForm.display_name"
                  label="显示名称"
                  placeholder="例如：小哲"
                  maxlength="50"
                />

                <BaseInput
                  v-model="profileForm.nickname"
                  label="昵称"
                  placeholder="例如：数学冲刺版"
                  maxlength="50"
                />

                <p v-if="profileError" class="flex items-center gap-2 text-sm text-rose-400">
                  <i class="fas fa-circle-exclamation text-xs"></i>
                  <span>{{ profileError }}</span>
                </p>

                <div class="flex justify-end">
                  <BaseButton variant="primary" :disabled="profileSaving || profileUploading || profileDeletingAvatar" @click="saveProfile">
                    <i v-if="profileSaving" class="fas fa-spinner fa-spin text-xs"></i>
                    <span>{{ profileSaving ? '保存中...' : '保存个人资料' }}</span>
                  </BaseButton>
                </div>
              </div>
            </div>
          </section>
        </div>

        <div v-else class="space-y-6">
          <ProviderSection
            icon="fa-solid fa-bolt"
            title="OpenAI 兼容 API"
            subtitle="支持 OpenAI / DeepSeek / Qwen / Moonshot 等"
            :providers="openaiProviders"
            :active-id="activeOpenaiId"
            @add="openAddDialog('openai')"
            @toggle-active="(id) => toggleActive('openai', id)"
            @edit="(p, idx) => openEditDialog('openai', p, idx)"
            @remove="(idx) => removeProvider('openai', idx)"
          />

          <ProviderSection
            icon="fa-solid fa-brain"
            title="Anthropic API"
            subtitle="Claude 系列模型"
            :providers="anthropicProviders"
            :active-id="activeAnthropicId"
            @add="openAddDialog('anthropic')"
            @toggle-active="(id) => toggleActive('anthropic', id)"
            @edit="(p, idx) => openEditDialog('anthropic', p, idx)"
            @remove="(idx) => removeProvider('anthropic', idx)"
          />

          <ProviderSection
            icon="fa-solid fa-eye"
            title="PaddleOCR"
            subtitle="文档 OCR 识别服务"
            :providers="paddleocrProviders"
            :active-id="activePaddleocrId"
            @add="openAddDialog('paddleocr')"
            @toggle-active="(id) => toggleActive('paddleocr', id)"
            @edit="(p, idx) => openEditDialog('paddleocr', p, idx)"
            @remove="(idx) => removeProvider('paddleocr', idx)"
          />
        </div>
      </div>

      <ProviderDialog
        :open="dialogOpen"
        :type="dialogType"
        :edit-data="dialogEditData"
        @close="dialogOpen = false"
        @confirm="onDialogConfirm"
      />
    </div>
  </ContentPanel>
</template>
