import { ref } from 'vue'
import * as api from '@/api.js'
import { useAuth } from '@/composables/useAuth.js'

const QUOTA_EXCEEDED_CODE = 'DAILY_FREE_QUOTA_EXCEEDED'

export function useSplitPipeline(pushToast, currentView, step, S, uploadReady, splitting, splitCompleted, uploadMode, selectedProvider, selectedModel, questions, selectedIds, pendingFiles, typesetMath) {
  const { setQuotaSnapshot, refreshCurrentUser } = useAuth()
  const eraseLoading = ref(false)
  const eraseImages = ref([])
  const eraseDone = ref(false)
  const ocrLoading = ref(false)
  const ocrPages = ref([])
  const ocrDone = ref(false)
  const eraseEnabled = ref(true)

  const syncQuotaFromError = (error) => {
    if (error?.quota) setQuotaSnapshot(error.quota)
    return error?.code === QUOTA_EXCEEDED_CODE
  }

  const refreshQuotaSnapshot = async () => {
    try {
      await refreshCurrentUser()
    } catch (_) {}
  }

  const startProcess = () => {
    if (eraseEnabled.value) {
      doErase()
    } else {
      doOcr()
    }
  }

  const doErase = async () => {
    if (eraseLoading.value) return
    eraseLoading.value = true
    eraseDone.value = false
    eraseImages.value = []
    currentView.value = 'workspace_review'
    step.value = S.value.ERASE
    try {
      const data = await api.runErase()
      eraseImages.value = data.images || []
      eraseDone.value = true
      pushToast('success', data.message || '擦除完成')
    } catch (e) {
      pushToast('error', e.message || '擦除失败')
      currentView.value = 'workspace'
      step.value = S.value.UPLOAD
    } finally {
      eraseLoading.value = false
    }
  }

  const doOcr = async () => {
    if (ocrLoading.value) return
    ocrLoading.value = true
    ocrDone.value = false
    ocrPages.value = []
    eraseDone.value = false
    currentView.value = 'workspace_review'
    step.value = S.value.OCR
    try {
      const data = await api.runOcr()
      ocrPages.value = data.pages || []
      ocrDone.value = true
      await refreshQuotaSnapshot()
      pushToast('success', `OCR 完成，共 ${data.pages?.length || 0} 页`)
    } catch (e) {
      if (syncQuotaFromError(e)) {
        pushToast('error', e.message || '今日免费体验次数已用完')
      } else {
        pushToast('error', e.message || 'OCR 失败')
      }
      currentView.value = 'workspace'
      step.value = S.value.UPLOAD
    } finally {
      ocrLoading.value = false
    }
  }

  const doSplit = async () => {
    if (!uploadReady.value || splitting.value || splitCompleted.value) return

    if (uploadMode.value === 'note') {
      await doNoteOrganize()
      return
    }

    splitting.value = true
    ocrDone.value = false
    step.value = S.value.SPLIT
    pushToast('info', '正在调用AI分割题目，请稍候...', 1800)
    try {
      const data = await api.splitQuestions(selectedProvider.value, selectedModel.value)
      questions.value = data.questions || []
      selectedIds.clear()
      if (data.warnings && data.warnings.length) {
        for (const w of data.warnings) pushToast('warning', w, 6000)
      }
      if (questions.value.length > 0) {
        splitCompleted.value = true
        step.value = S.value.EXPORT
        if (!data.warnings || !data.warnings.length) {
          pushToast('success', `成功分割 ${questions.value.length} 道题目`)
        }
        await typesetMath()
        await refreshQuotaSnapshot()
        setTimeout(() => {
          if (currentView.value === 'workspace') {
            currentView.value = 'workspace_review'
          }
        }, 800)
      }
    } catch (e) {
      if (syncQuotaFromError(e)) {
        pushToast('error', e.message || '今日免费体验次数已用完')
      } else {
        pushToast('error', '分割失败: ' + (e instanceof Error ? e.message : String(e)))
      }
    } finally {
      splitting.value = false
    }
  }

  const doNoteOrganize = async () => {
    splitting.value = true
    step.value = S.value.SPLIT
    pushToast('info', '正在调用AI整理笔记，请稍候...', 3000)
    try {
      const formData = new FormData()
      for (const pf of pendingFiles) {
        if (pf.file) formData.append('files', pf.file)
      }
      formData.append('model_provider', selectedProvider.value)
      if (selectedModel.value) formData.append('model_name', selectedModel.value)

      await new Promise((resolve, reject) => {
        api.createNote(formData, {
          onSuccess: (data) => resolve(data),
          onError: (error) => reject(error),
        })
      })

      splitCompleted.value = true
      step.value = S.value.EXPORT
      await refreshQuotaSnapshot()
      pushToast('success', '笔记整理完成！')

      setTimeout(() => {
        currentView.value = 'notes'
      }, 800)
    } catch (e) {
      if (syncQuotaFromError(e)) {
        pushToast('error', e.message || '今日免费体验次数已用完')
      } else {
        pushToast('error', '笔记整理失败: ' + (e instanceof Error ? e.message : String(e)))
      }
    } finally {
      splitting.value = false
    }
  }

  const doExport = async () => {
    if (!selectedIds.size) { pushToast('error', '请至少选择一道题目！'); return }
    try {
      const data = await api.exportQuestions(Array.from(selectedIds))
      step.value = S.value.EXPORT + 1
      pushToast('success', `错题本导出成功！已保存到: ${data.output_path}`)
      let filename = 'wrongbook.md'
      if (data.output_path) {
        const parts = String(data.output_path).split(/[/\\]/)
        const last = parts[parts.length - 1]
        if (last) filename = last
      }
      const a = document.createElement('a')
      a.href = `/download/${encodeURIComponent(filename)}?t=${Date.now()}`
      a.download = filename
      a.style.display = 'none'
      document.body.appendChild(a)
      a.click()
      a.remove()
    } catch (e) {
      pushToast('error', '导出失败: ' + (e instanceof Error ? e.message : String(e)))
    }
  }

  const doSaveToDb = async (errorBankRef) => {
    if (!selectedIds.size) { pushToast('error', '请至少选择一道题目！'); return }
    try {
      const answers = questions.value
        .filter(q => selectedIds.has(q.uid) && (q.answer || q.user_answer))
        .map(q => ({ uid: q.uid, answer: q.answer || '', user_answer: q.user_answer || '' }))
      const data = await api.saveToDb(Array.from(selectedIds), answers)
      pushToast('success', data.message || '已导入错题库')
      errorBankRef?.value?.refresh()
    } catch (e) {
      pushToast('error', '导入失败: ' + (e instanceof Error ? e.message : String(e)))
    }
  }

  return {
    eraseEnabled, eraseLoading, eraseImages, eraseDone,
    ocrLoading, ocrPages, ocrDone,
    startProcess, doErase, doOcr, doSplit, doExport, doSaveToDb,
  }
}
