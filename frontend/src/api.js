/**
 * API 调用层 — 集中管理所有 fetch 请求
 */

function _buildModelBody(modelProvider, modelName, providerSource, providerId, extra = {}) {
  const body = { model_provider: modelProvider, ...extra }
  if (modelName) body.model_name = modelName
  if (providerSource) body.provider_source = providerSource
  if (providerId) body.provider_id = providerId
  return body
}

function _createApiError(message, { status, code, quota } = {}) {
  const error = new Error(message || '请求失败')
  error.status = status ?? null
  error.code = code ?? null
  error.quota = quota ?? null
  return error
}

async function _readJsonSafely(resp) {
  return resp.json().catch(() => null)
}

function _getErrorMessage(data, fallback, status) {
  return (data && (data.error || data.message)) || fallback || `HTTP ${status}`
}

async function _assertJsonSuccess(resp, fallbackMessage) {
  const data = await _readJsonSafely(resp)
  if (!resp.ok) {
    throw _createApiError(_getErrorMessage(data, fallbackMessage, resp.status), {
      status: resp.status,
      code: data?.code,
      quota: data?.quota,
    })
  }
  if (data && data.success) return data
  throw _createApiError(_getErrorMessage(data, fallbackMessage, resp.status), {
    status: resp.status,
    code: data?.code,
    quota: data?.quota,
  })
}

function _handleXhrJsonResult(xhr, data, fallbackMessage, onSuccess, onError) {
  if (xhr.status >= 200 && xhr.status < 300 && data?.success) {
    onSuccess?.(data)
    return
  }
  onError?.(_createApiError(_getErrorMessage(data, fallbackMessage, xhr.status), {
    status: xhr.status,
    code: data?.code,
    quota: data?.quota,
  }))
}

export async function fetchModelOptions() {
  const resp = await fetch('/api/models/options')
  return _assertJsonSuccess(resp, '获取模型选项失败')
}

export async function fetchAppConfig() {
  const resp = await fetch('/api/config')
  const data = await _assertJsonSuccess(resp, '获取配置失败')
  return data.config
}

export async function updateAppConfig(config) {
  const resp = await fetch('/api/config', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  return _assertJsonSuccess(resp, '更新配置失败')
}

export async function fetchAdminSystemConfig() {
  const resp = await fetch('/api/admin/system-config')
  const data = await _assertJsonSuccess(resp, '获取系统配置失败')
  return data.config
}

export async function updateAdminSystemConfig(config) {
  const resp = await fetch('/api/admin/system-config', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  return _assertJsonSuccess(resp, '更新系统配置失败')
}

export async function updateProfile(profile) {
  const resp = await fetch('/api/auth/profile', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  })
  const data = await _assertJsonSuccess(resp, '更新个人资料失败')
  return data.user
}

export function uploadProfileAvatar(file, { onSuccess, onError, onAbort } = {}) {
  const formData = new FormData()
  formData.append('file', file)

  const xhr = new XMLHttpRequest()
  xhr.open('POST', '/api/auth/profile/avatar', true)

  xhr.addEventListener('load', () => {
    let data = null
    try { data = JSON.parse(xhr.responseText) } catch (_) { }
    _handleXhrJsonResult(
      xhr,
      data,
      '头像上传失败',
      (payload) => onSuccess?.(payload.user),
      onError,
    )
  })

  xhr.addEventListener('error', () => onError?.(_createApiError('头像上传失败: 网络错误')))
  xhr.addEventListener('abort', () => onAbort?.())

  xhr.send(formData)
  return xhr
}

export async function deleteProfileAvatar() {
  const resp = await fetch('/api/auth/profile/avatar', {
    method: 'DELETE',
  })
  const data = await _assertJsonSuccess(resp, '删除头像失败')
  return data.user
}

export async function fetchStatus() {
  const resp = await fetch('/api/status')
  const data = await _assertJsonSuccess(resp, '获取系统状态失败')
  return data.status
}

export async function fetchProjects() {
  const resp = await fetch('/api/projects')
  const data = await _assertJsonSuccess(resp, '获取项目列表失败')
  return data.projects || []
}

export async function createProject(payload) {
  const resp = await fetch('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await _assertJsonSuccess(resp, '创建项目失败')
  return data.project
}

export async function updateProject(projectId, payload) {
  const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await _assertJsonSuccess(resp, '更新项目失败')
  return data.project
}

export async function deleteProject(projectId) {
  const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}`, {
    method: 'DELETE',
  })
  return _assertJsonSuccess(resp, '删除项目失败')
}

export async function cancelFile(fileKey) {
  const resp = await fetch('/api/cancel_file', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_key: fileKey }),
  })
  return _assertJsonSuccess(resp, '撤销失败')
}

export async function resetUploadSession() {
  const resp = await fetch('/api/upload/reset', {
    method: 'POST',
  })
  return _assertJsonSuccess(resp, '重置上传会话失败')
}

export function uploadFiles(formData, { onProgress, onSuccess, onError, onAbort }) {
  const xhr = new XMLHttpRequest()
  xhr.open('POST', '/api/upload', true)

  if (onProgress) {
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total)
    })
  }

  xhr.addEventListener('load', () => {
    let data = null
    try { data = JSON.parse(xhr.responseText) } catch (_) { }
    _handleXhrJsonResult(xhr, data, '文件处理失败', onSuccess, onError)
  })

  xhr.addEventListener('error', () => onError?.(_createApiError('上传失败: 网络错误')))
  xhr.addEventListener('abort', () => onAbort?.())

  xhr.send(formData)
  return xhr
}

export async function runErase() {
  const resp = await fetch('/api/erase', { method: 'POST' })
  return _assertJsonSuccess(resp, '擦除失败')
}

export async function runOcr() {
  const resp = await fetch('/api/ocr', { method: 'POST' })
  return _assertJsonSuccess(resp, 'OCR 执行失败')
}

export async function splitQuestions(modelProvider, modelName, providerSource, providerId) {
  const resp = await fetch('/api/split', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(_buildModelBody(modelProvider, modelName, providerSource, providerId)),
  })
  return _assertJsonSuccess(resp, '题目分割失败')
}

export async function exportQuestions(selectedIds) {
  const resp = await fetch('/api/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ selected_ids: selectedIds }),
  })
  return _assertJsonSuccess(resp, '导出失败')
}

export async function saveToDb(selectedIds, answers = [], projectId) {
  const body = { selected_ids: selectedIds, answers }
  if (projectId) body.project_id = projectId
  const resp = await fetch('/api/save-to-db', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return _assertJsonSuccess(resp, '导入错题库失败')
}

// ── 分割历史 API ────────────────────────────────────────

export async function fetchSplitRecords(limit = 10) {
  const qs = new URLSearchParams({ limit })
  const resp = await fetch(`/api/split-records?${qs}`)
  const data = await _assertJsonSuccess(resp, '获取分割历史失败')
  return data.records
}

export async function fetchSplitRecordDetail(recordId) {
  const resp = await fetch(`/api/split-records/${recordId}`)
  const data = await _assertJsonSuccess(resp, '获取分割记录详情失败')
  return data.record
}

// ── 错题库 API ──────────────────────────────────────────

export async function fetchErrorBank(params = {}) {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== '') qs.set(k, v)
  }
  const resp = await fetch(`/api/error-bank?${qs}`)
  return _assertJsonSuccess(resp, '查询错题库失败')
}

export async function fetchSubjects(projectId) {
  const qs = new URLSearchParams()
  if (projectId) qs.set('project_id', projectId)
  const resp = await fetch(`/api/subjects?${qs}`)
  const data = await _assertJsonSuccess(resp, '获取科目列表失败')
  return data.subjects
}

export async function fetchQuestionTypes(projectId) {
  const qs = new URLSearchParams()
  if (projectId) qs.set('project_id', projectId)
  const resp = await fetch(`/api/question-types?${qs}`)
  const data = await _assertJsonSuccess(resp, '获取题型列表失败')
  return data.question_types
}

export async function fetchTagNames(subject, projectId) {
  const qs = new URLSearchParams()
  if (subject) qs.set('subject', subject)
  if (projectId) qs.set('project_id', projectId)
  const resp = await fetch(`/api/stats?${qs}`)
  const data = await _assertJsonSuccess(resp, '获取标签列表失败')
  return (data.stats || []).map(s => s.tag_name)
}

export async function saveAnswer(questionId, userAnswer) {
  const resp = await fetch(`/api/question/${questionId}/answer`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_answer: userAnswer }),
  })
  return _assertJsonSuccess(resp, '保存答案失败')
}

export async function exportFromDb(selectedIds) {
  const resp = await fetch('/api/export-from-db', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ selected_ids: selectedIds }),
  })
  return _assertJsonSuccess(resp, '导出失败')
}

export async function deleteQuestion(questionId) {
  const resp = await fetch(`/api/question/${questionId}`, { method: 'DELETE' })
  return _assertJsonSuccess(resp, '删除失败')
}

export async function updateReviewStatus(questionId, reviewStatus) {
  const resp = await fetch(`/api/question/${questionId}/review-status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ review_status: reviewStatus }),
  })
  return _assertJsonSuccess(resp, '更新复习状态失败')
}

export async function fetchDashboardStats(subject, projectId) {
  const qs = new URLSearchParams()
  if (subject) qs.set('subject', subject)
  if (projectId) qs.set('project_id', projectId)
  const resp = await fetch(`/api/dashboard-stats?${qs}`)
  return _assertJsonSuccess(resp, '获取统计数据失败')
}

export async function requestAiAnalysis(questionIds, { providerSource, providerId, modelProvider, modelName } = {}) {
  const body = { question_ids: questionIds }
  if (modelProvider) body.model_provider = modelProvider
  if (modelName) body.model_name = modelName
  if (providerSource) body.provider_source = providerSource
  if (providerId) body.provider_id = providerId
  
  const resp = await fetch('/api/ai-analysis', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return _assertJsonSuccess(resp, 'AI 分析请求失败')
}

// ── AI 辅导对话 API ──────────────────────────────────────

export async function updateQuestion(questionId, payload) {
  const resp = await fetch(`/api/question/${questionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return _assertJsonSuccess(resp, '保存失败')
}

export async function saveQuestionAnswer(questionId, answer) {
  const resp = await fetch(`/api/question/${questionId}/answer`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answer }),
  })
  return _assertJsonSuccess(resp, '保存答案失败')
}

export async function fetchChatSessions(questionId) {
  const resp = await fetch(`/api/question/${questionId}/chats`)
  const data = await _assertJsonSuccess(resp, '获取对话列表失败')
  return data.sessions
}

export async function createChat(questionId) {
  const resp = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question_id: questionId }),
  })
  const data = await _assertJsonSuccess(resp, '创建对话失败')
  return data.session
}

export async function fetchMessages(sessionId, { limit = 30, beforeId } = {}) {
  const qs = new URLSearchParams({ limit })
  if (beforeId) qs.set('before_id', beforeId)
  const resp = await fetch(`/api/chat/${sessionId}/messages?${qs}`)
  const data = await _assertJsonSuccess(resp, '获取消息失败')
  return { messages: data.messages, hasMore: data.hasMore }
}

export async function streamChat(sessionId, message, modelProvider = 'openai', signal, modelName, { deepThink = false, providerSource, providerId, contextRefs = [] } = {}) {
  const opts = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(_buildModelBody(modelProvider, modelName, providerSource, providerId, { message, deep_think: deepThink, context_refs: contextRefs })),
  }
  if (signal) opts.signal = signal
  return fetch(`/api/chat/${sessionId}/stream`, opts)
}

// ── 笔记模块 ─────────────────────────────────────────────

/**
 * 上传笔记图片 → OCR → LLM 整理 → 保存
 * @param {FormData} formData - 包含 files、model_provider、model_name
 * @param {Object} callbacks - { onProgress, onSuccess, onError }
 * @returns {XMLHttpRequest} xhr 对象，可用于取消
 */
export function createNote(formData, { onProgress, onSuccess, onError } = {}) {
  const xhr = new XMLHttpRequest()
  xhr.open('POST', '/api/notes/')
  xhr.withCredentials = true

  if (onProgress) {
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total)
    }
  }
  xhr.onload = () => {
    let data = null
    try { data = JSON.parse(xhr.responseText) } catch (_) { }
    _handleXhrJsonResult(xhr, data, '笔记创建失败', onSuccess, onError)
  }
  xhr.onerror = () => onError?.(_createApiError('网络错误'))
  xhr.send(formData)
  return xhr
}

/**
 * 分页查询笔记列表
 */
export async function fetchNotes(params = {}) {
  const query = new URLSearchParams()
  if (params.page) query.set('page', params.page)
  if (params.limit) query.set('limit', params.limit)
  if (params.subject) query.set('subject', params.subject)
  if (params.knowledge_tag) query.set('knowledge_tag', params.knowledge_tag)
  if (params.keyword) query.set('keyword', params.keyword)
  if (params.project_id) query.set('project_id', params.project_id)

  const resp = await fetch(`/api/notes/?${query}`)
  return _assertJsonSuccess(resp, '获取笔记列表失败')
}

/**
 * 获取单条笔记详情
 */
export async function fetchNote(noteId) {
  const resp = await fetch(`/api/notes/${noteId}`)
  const data = await _assertJsonSuccess(resp, '获取笔记详情失败')
  return data.note
}

/**
 * 更新笔记
 */
export async function updateNote(noteId, payload) {
  const resp = await fetch(`/api/notes/${noteId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await _assertJsonSuccess(resp, '更新笔记失败')
  return data.note
}

/**
 * 删除笔记
 */
export async function deleteNote(noteId) {
  const resp = await fetch(`/api/notes/${noteId}`, { method: 'DELETE' })
  await _assertJsonSuccess(resp, '删除笔记失败')
  return true
}

/**
 * 获取笔记库科目列表
 */
export async function fetchNoteSubjects(projectId) {
  const qs = new URLSearchParams()
  if (projectId) qs.set('project_id', projectId)
  const resp = await fetch(`/api/notes/subjects?${qs}`)
  const data = await _assertJsonSuccess(resp, '获取科目列表失败')
  return data.subjects
}

/**
 * 获取笔记库知识点标签列表
 */
export async function fetchNoteTagNames(subject, projectId) {
  const qs = new URLSearchParams()
  if (subject) qs.set('subject', subject)
  if (projectId) qs.set('project_id', projectId)
  const resp = await fetch(`/api/notes/tags?${qs}`)
  const data = await _assertJsonSuccess(resp, '获取标签列表失败')
  return data.tags
}

// ── 独立对话 ─────────────────────────────────────────────

/** 创建独立对话 */
export async function createIndependentChat(title = '新对话') {
  const resp = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  const data = await _assertJsonSuccess(resp, '创建对话失败')
  return data.session
}

/** 获取用户的独立对话列表 */
export async function fetchMyChatSessions(params = {}) {
  const query = new URLSearchParams()
  if (params.page) query.set('page', params.page)
  if (params.limit) query.set('limit', params.limit)
  const resp = await fetch(`/api/chat/my-sessions?${query}`)
  return _assertJsonSuccess(resp, '获取对话列表失败')
}

/** 更新对话标题 */
export async function updateChatTitle(sessionId, title) {
  const resp = await fetch(`/api/chat/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  const data = await _assertJsonSuccess(resp, '更新标题失败')
  return data.session
}

/** 删除对话 */
export async function deleteChat(sessionId) {
  const resp = await fetch(`/api/chat/${sessionId}`, { method: 'DELETE' })
  await _assertJsonSuccess(resp, '删除对话失败')
  return true
}
