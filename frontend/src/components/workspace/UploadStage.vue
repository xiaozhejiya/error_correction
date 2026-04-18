<script setup>
/**
 * UploadStage.vue
 * 工作台第一页：上传与分析（模式切换 + 擦除开关 + 流程步骤 + 文件上传）
 */
import BaseTooltip from '@/components/base/BaseTooltip.vue'
import StatusBar from '@/components/workspace/StatusBar.vue'
import FileUploader from '@/components/workspace/FileUploader.vue'
import FileList from '@/components/workspace/FileList.vue'
import ActionBar from '@/components/workspace/ActionBar.vue'

const props = defineProps({
  uploadMode: String,
  eraseEnabled: Boolean,
  // StatusBar
  statusLoading: Boolean,
  statusError: [String, null],
  statusPills: Array,
  providerOptions: Array,
  selectedModel: String,
  hasConfiguredModel: Boolean,
  splitting: Boolean,
  splitCompleted: Boolean,
  modelSwitching: Boolean,
  // FileUploader / FileList
  pendingFiles: Array,
  fileProgress: Object,
  waitingKeys: Object,
  uploadBusy: Boolean,
  uploadReady: Boolean,
  // ActionBar
  splitEnabled: Boolean,
})

const emit = defineEmits([
  'update:upload-mode',
  'update:erase-enabled',
  'update:selected-model',
  'model-switch',
  'upload',
  'remove-file',
  'split',
])
</script>

<template>
  <!-- 工具栏：状态 + 模式切换 + 擦除开关 -->
  <div class="flex flex-wrap items-center gap-3">
    <!-- 模式切换 -->
    <div class="flex items-center rounded-md brand-btn p-0.5">
      <button
        @click="emit('update:upload-mode', 'exam')"
        class="h-7 rounded px-3 text-xs font-medium transition-all"
        :class="uploadMode === 'exam' ? 'bg-white/[0.06] text-[#f7f8f8]' : 'text-[#62666d] hover:text-[#8a8f98]'"
      >
        <i class="fa-solid fa-file-lines mr-1.5"></i>试卷分割
      </button>
      <button
        @click="emit('update:upload-mode', 'note')"
        class="h-7 rounded px-3 text-xs font-medium transition-all"
        :class="uploadMode === 'note' ? 'bg-white/[0.06] text-[#f7f8f8]' : 'text-[#62666d] hover:text-[#8a8f98]'"
      >
        <i class="fa-solid fa-book-open mr-1.5"></i>笔记整理
      </button>
    </div>

    <div class="h-4 w-px bg-white/[0.08]"></div>

    <!-- 擦除开关 -->
    <label class="flex cursor-pointer items-center gap-2" @click="emit('update:erase-enabled', !eraseEnabled)">
      <div
        class="relative h-4 w-7 rounded-full transition-colors"
        :class="eraseEnabled ? 'bg-[rgb(129,115,223)]' : 'bg-white/[0.08]'"
      >
        <div
          class="absolute top-0.5 h-3 w-3 rounded-full bg-white transition-transform"
          :class="eraseEnabled ? 'translate-x-3' : 'translate-x-0.5'"
        ></div>
      </div>
      <span class="text-xs text-[#8a8f98]">擦除笔迹</span>
      <BaseTooltip text="上传后自动擦除图片中的手写笔迹" placement="bottom" align="center">
        <i class="fa-solid fa-circle-question cursor-help text-[10px] text-[#62666d]"></i>
      </BaseTooltip>
    </label>

    <!-- 引擎状态 -->
    <div class="ml-auto">
      <StatusBar
        :status-loading="statusLoading"
        :status-error="statusError"
        :status-pills="statusPills"
        :provider-options="providerOptions"
        :selected-model="selectedModel"
        :disabled="splitting || splitCompleted"
        :no-models="!hasConfiguredModel"
        :model-switching="modelSwitching"
        @update:selected-model="(v) => emit('update:selected-model', v)"
        @model-switch="(payload) => emit('model-switch', payload)"
      />
    </div>
  </div>

  <!-- 上传区 -->
  <div class="flex flex-1 min-h-0 flex-col items-center justify-center gap-6 overflow-y-auto custom-scrollbar py-8">
    <!-- 引导信息 -->
    <div class="w-full max-w-2xl text-center">
      <h3 class="mb-2 text-base font-medium text-[#f7f8f8]">
        {{ uploadMode === 'note' ? '上传手写笔记' : '上传试卷图片' }}
      </h3>
      <p class="text-sm leading-relaxed text-[#62666d] md:whitespace-nowrap">
        {{ uploadMode === 'note'
          ? '支持拍照或扫描件，AI 将自动识别内容并整理为结构化笔记'
          : '支持 PDF 和图片格式，AI 将自动完成 OCR 识别、题目分割和知识点标注'
        }}
      </p>
    </div>

    <!-- 流程步骤卡片 -->
    <div class="grid w-full max-w-2xl grid-cols-4 gap-4">
      <div class="flex flex-col items-center gap-3 rounded-lg brand-btn p-4 text-center">
        <div class="flex h-12 w-12 items-center justify-center rounded-lg bg-white/[0.04]">
          <i class="fa-solid fa-cloud-arrow-up text-xl text-[rgb(129,115,223)]"></i>
        </div>
        <span class="text-sm text-[#8a8f98]">{{ uploadMode === 'note' ? '上传笔记' : '上传文件' }}</span>
      </div>
      <div class="flex flex-col items-center gap-3 rounded-lg brand-btn p-4 text-center">
        <div class="flex h-12 w-12 items-center justify-center rounded-lg bg-white/[0.04]">
          <i class="fa-solid fa-eye text-xl text-[rgb(129,115,223)]"></i>
        </div>
        <span class="text-sm text-[#8a8f98]">AI 识别</span>
      </div>
      <div class="flex flex-col items-center gap-3 rounded-lg brand-btn p-4 text-center">
        <div class="flex h-12 w-12 items-center justify-center rounded-lg bg-white/[0.04]">
          <i class="fa-solid text-xl text-[rgb(129,115,223)]" :class="uploadMode === 'note' ? 'fa-wand-magic-sparkles' : 'fa-scissors'"></i>
        </div>
        <span class="text-sm text-[#8a8f98]">{{ uploadMode === 'note' ? '智能整理' : '分割纠错' }}</span>
      </div>
      <div class="flex flex-col items-center gap-3 rounded-lg brand-btn p-4 text-center">
        <div class="flex h-12 w-12 items-center justify-center rounded-lg bg-white/[0.04]">
          <i class="fa-solid text-xl text-[rgb(129,115,223)]" :class="uploadMode === 'note' ? 'fa-bookmark' : 'fa-file-export'"></i>
        </div>
        <span class="text-sm text-[#8a8f98]">{{ uploadMode === 'note' ? '保存笔记' : '导出归档' }}</span>
      </div>
    </div>

    <!-- 拖拽上传 -->
    <FileUploader
      :pending-files="pendingFiles"
      :file-progress="fileProgress"
      :waiting-keys="waitingKeys"
      :upload-busy="uploadBusy"
      :upload-ready="uploadReady"
      :splitting="splitting"
      :split-completed="splitCompleted"
      :expand="false"
      :disabled="!hasConfiguredModel"
      @upload="(f) => emit('upload', f)"
      @remove-file="(f) => emit('remove-file', f)"
      class="w-full max-w-2xl"
    />

    <!-- 已上传文件 -->
    <FileList
      class="w-full max-w-2xl"
      :pending-files="pendingFiles"
      :file-progress="fileProgress"
      :waiting-keys="waitingKeys"
      :upload-busy="uploadBusy"
      :upload-ready="uploadReady"
      :splitting="splitting"
      :split-completed="splitCompleted"
      @remove-file="(f) => emit('remove-file', f)"
    />

    <!-- 操作按钮 -->
    <ActionBar
      class="mt-4"
      :split-enabled="splitEnabled"
      :export-enabled="false"
      :splitting="splitting"
      :split-completed="splitCompleted"
      :upload-mode="uploadMode"
      :erase-enabled="eraseEnabled"
      @split="emit('split')"
    />
  </div>
</template>
