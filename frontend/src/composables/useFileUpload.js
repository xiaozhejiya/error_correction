import { ref, reactive, computed } from 'vue'
import { fileKey } from '@/utils.js'
import * as api from '@/api.js'

export function useFileUpload(pushToast, S, questions, selectedIds, splitCompleted, splitting, uploadMode) {
  const uploadBusy = ref(false)
  const uploadReady = ref(false)
  const pendingFiles = reactive([])
  const pendingPreviewUrls = computed(() =>
    pendingFiles.filter(pf => pf.file).map(pf => URL.createObjectURL(pf.file))
  )
  const fileProgress = reactive({})
  const waitingKeys = reactive(new Set())
  const uploadQueue = reactive([])
  let activeXhr = null
  let fakeProgressTimer = null
  let fakeProgressKeys = []

  const setProgress = (key, p) => { fileProgress[key] = Math.max(0, Math.min(100, Number(p) || 0)) }

  const stopFakeProgress = () => {
    if (fakeProgressTimer) {
      window.clearInterval(fakeProgressTimer)
      fakeProgressTimer = null
    }
    fakeProgressKeys = []
  }

  const startFakeProgress = (keys) => {
    stopFakeProgress()
    fakeProgressKeys = Array.from(keys || [])
    const tick = () => {
      if (!uploadBusy.value) { stopFakeProgress(); return }
      for (const key of fakeProgressKeys) {
        const current = Number(fileProgress[key] || 0)
        const cap = 82
        if (current >= cap) continue
        let inc = current < 55 ? 1 + Math.random() * 3 : current < 75 ? 0.4 + Math.random() * 1.1 : 0.08 + Math.random() * 0.25
        setProgress(key, Math.min(cap, current + inc))
      }
    }
    tick()
    fakeProgressTimer = window.setInterval(tick, 360)
  }

  const handleUpload = (files) => {
    const uploadFiles = Array.from(files || []).filter(f => pendingFiles.some(x => x.key === fileKey(f)))
    if (!uploadFiles.length) return
    uploadBusy.value = true
    const step = S.value
    const keys = uploadFiles.map(f => fileKey(f))
    for (const k of keys) waitingKeys.delete(k)
    startFakeProgress(keys)

    const formData = new FormData()
    for (const f of uploadFiles) {
      formData.append('files', f)
      formData.append('file_key', fileKey(f))
    }

    activeXhr = api.uploadFiles(formData, {
      onProgress: (ratio) => {
        const pct = Math.max(0, Math.min(95, ratio * 95))
        for (const k of keys) {
          if (pendingFiles.some(x => x.key === k)) setProgress(k, Math.max(fileProgress[k] || 0, pct))
        }
      },
      onSuccess: () => {
        stopFakeProgress()
        uploadBusy.value = false
        activeXhr = null
        for (const k of keys) {
          if (pendingFiles.some(x => x.key === k)) setProgress(k, 100)
        }
        uploadReady.value = pendingFiles.length > 0
        pushToast('success', '上传成功')
        pumpUploadQueue()
      },
      onError: (msg) => {
        stopFakeProgress()
        uploadBusy.value = false
        activeXhr = null
        pushToast('error', msg)
        pumpUploadQueue()
      },
      onAbort: () => {
        stopFakeProgress()
        uploadBusy.value = false
        activeXhr = null
        pumpUploadQueue()
      },
    })
  }

  const pumpUploadQueue = () => {
    if (uploadBusy.value || !uploadQueue.length) return
    const next = uploadQueue.shift()
    if (next && next.length) handleUpload(next)
  }

  const enqueueUpload = (files) => {
    const list = Array.from(files || [])
    if (!list.length) return
    if (splitCompleted.value || splitting.value) { pushToast('error', '已分割完成，请先重新开始'); return }
    for (const f of list) {
      const k = fileKey(f)
      if (pendingFiles.some(x => x.key === k)) continue
      pendingFiles.push({ key: k, file: f })
      setProgress(k, 0)
    }
    if (uploadBusy.value) {
      for (const f of list) waitingKeys.add(fileKey(f))
      uploadQueue.push(list)
      return
    }
    handleUpload(list)
  }

  const doCancelFile = async (key, step) => {
    try {
      if (fakeProgressKeys.length) fakeProgressKeys = fakeProgressKeys.filter(k => k !== key)
      if (!fakeProgressKeys.length) stopFakeProgress()
      const data = await api.cancelFile(key)
      const idx = pendingFiles.findIndex(x => x.key === key)
      if (idx >= 0) pendingFiles.splice(idx, 1)
      delete fileProgress[key]
      waitingKeys.delete(key)
      questions.value = []
      selectedIds.clear()
      splitCompleted.value = false
      if (!pendingFiles.length) {
        uploadReady.value = false
      }
      pushToast('success', data.message || '已撤销')
      if (!pendingFiles.length && activeXhr) {
        try { activeXhr.abort() } catch (_) {}
      }
    } catch (_) { pushToast('error', '撤销失败: 网络错误') }
  }

  const removePendingFile = async (key) => {
    if (!key || splitting.value || splitCompleted.value) return
    if (uploadBusy.value || uploadReady.value) { await doCancelFile(key, S.value); return }
    const idx = pendingFiles.findIndex(x => x.key === key)
    if (idx >= 0) pendingFiles.splice(idx, 1)
    delete fileProgress[key]
    waitingKeys.delete(key)
    for (let i = uploadQueue.length - 1; i >= 0; i--) {
      uploadQueue[i] = (uploadQueue[i] || []).filter(f => fileKey(f) !== key)
      if (!uploadQueue[i].length) uploadQueue.splice(i, 1)
    }
  }

  const doReset = (providerOptions, selectedModel, step) => {
    uploadBusy.value = false
    uploadReady.value = false
    splitting.value = false
    splitCompleted.value = false
    pendingFiles.splice(0, pendingFiles.length)
    for (const k of Object.keys(fileProgress)) delete fileProgress[k]
    waitingKeys.clear()
    uploadQueue.splice(0, uploadQueue.length)
    questions.value = []
    selectedIds.clear()
    const configured = providerOptions.value.find(m => m.configured)
    selectedModel.value = configured ? configured.default_model : ''
    pushToast('success', '已重置')
  }

  return {
    uploadBusy, uploadReady, pendingFiles, pendingPreviewUrls,
    fileProgress, waitingKeys,
    enqueueUpload, removePendingFile, stopFakeProgress, doReset,
  }
}
