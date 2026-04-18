<script setup>
/**
 * ErrorBankFilterPanel.vue
 * 错题库筛选侧边栏
 */
import BaseSelect from '@/components/base/BaseSelect.vue'

const props = defineProps({
  filters: Object,
  subjects: Array,
  questionTypes: Array,
  tagNames: Array,
  selectedTags: Set,
})

const emit = defineEmits(['close', 'toggle-tag'])
</script>

<template>
  <div class="p-4 space-y-4">
    <div class="flex items-center justify-between">
      <span class="text-xs font-medium text-[#f7f8f8]">筛选设置</span>
      <button @click="emit('close')" class="text-[#62666d] hover:text-[#8a8f98] transition-colors">
        <i class="fa-solid fa-xmark text-xs"></i>
      </button>
    </div>

    <div>
      <label class="mb-1.5 block text-xs font-medium text-[#62666d]">学科</label>
      <BaseSelect v-model="filters.subject" :options="subjects" placeholder="全部学科" />
    </div>

    <div>
      <label class="mb-1.5 block text-xs font-medium text-[#62666d]">题型</label>
      <BaseSelect v-model="filters.question_type" :options="questionTypes" placeholder="全部题型" />
    </div>

    <div>
      <label class="mb-1.5 block text-xs font-medium text-[#62666d]">复习状态</label>
      <BaseSelect v-model="filters.review_status" :options="['待复习', '复习中', '已掌握']" placeholder="全部状态" />
    </div>

    <div v-if="tagNames?.length">
      <label class="mb-1.5 block text-xs font-medium text-[#62666d]">知识点</label>
      <div class="flex flex-wrap gap-1.5">
        <button v-for="tag in tagNames" :key="tag"
          @click="emit('toggle-tag', tag)"
          class="rounded-md px-2 py-0.5 text-xs font-medium transition-all"
          :class="selectedTags?.has(tag)
            ? 'bg-[rgb(129,115,223)] text-white'
            : 'border border-white/[0.06] bg-white/[0.02] text-[#62666d] hover:text-[#8a8f98] hover:border-white/[0.1]'"
        >{{ tag }}</button>
      </div>
    </div>
  </div>
</template>
