<script setup>
/**
 * ProviderSection.vue
 * API Provider 配置区块
 */
defineProps({
  icon: { type: String, required: true },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  providers: { type: Array, default: () => [] },
  activeId: { type: [Number, String, null], default: null },
})

const emit = defineEmits(['add', 'toggle-active', 'edit', 'remove'])
</script>

<template>
  <div>
    <!-- 区块标题 -->
    <div class="mb-3 flex items-center justify-between pl-1">
      <div class="flex items-center gap-3">
        <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 dark:bg-blue-500/10">
          <i :class="icon" class="text-lg text-blue-600 dark:text-blue-400"></i>
        </div>
        <div>
          <h3 class="text-base font-bold text-slate-800 dark:text-slate-200">{{ title }}</h3>
          <p v-if="subtitle" class="text-xs text-slate-500 dark:text-slate-400">{{ subtitle }}</p>
        </div>
      </div>
      <button
        @click="emit('add')"
        class="inline-flex items-center gap-1.5 rounded-xl border border-dashed border-slate-300 px-3 py-1.5 text-xs font-bold text-slate-500 transition-all hover:border-blue-400 hover:bg-blue-50 hover:text-blue-600 dark:border-white/10 dark:text-slate-400 dark:hover:border-blue-500/40 dark:hover:bg-blue-500/10 dark:hover:text-blue-400"
      >
        <i class="fa-solid fa-plus text-[10px]"></i>
        添加
      </button>
    </div>

    <!-- 空状态 -->
    <div v-if="providers.length === 0" class="rounded-2xl border border-dashed border-slate-200/60 py-10 text-center dark:border-white/10">
      <i class="fa-solid fa-plug text-3xl text-slate-300 dark:text-slate-600"></i>
      <p class="mt-3 text-sm font-medium text-slate-400 dark:text-slate-500">尚未配置，点击上方"添加"按钮</p>
    </div>

    <!-- Provider 列表 -->
    <div class="space-y-2">
      <div
        v-for="(provider, idx) in providers" :key="provider.id"
        class="flex cursor-pointer items-center gap-3 rounded-2xl border border-slate-200/60 bg-white/70 px-5 py-3.5 shadow-sm transition-all hover:border-blue-300 dark:border-white/10 dark:bg-white/[0.03] dark:hover:border-blue-500/30"
        @click="emit('toggle-active', provider.id)"
      >
        <!-- 激活单选 -->
        <div
          class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition-all"
          :class="activeId === provider.id
            ? 'border-emerald-500 bg-emerald-500 dark:border-emerald-400 dark:bg-emerald-400'
            : 'border-slate-300 dark:border-slate-600'"
        >
          <i v-if="activeId === provider.id" class="fa-solid fa-check text-[9px] text-white"></i>
        </div>

        <!-- 名称 + 状态 -->
        <div class="flex min-w-0 flex-1 items-center gap-2">
          <span class="truncate text-sm font-bold text-slate-800 dark:text-slate-200">{{ provider.name || '未命名' }}</span>
          <span v-if="activeId === provider.id" class="shrink-0 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-400">
            使用中
          </span>
          <span v-else-if="provider.api_key_set" class="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-500 dark:bg-white/5 dark:text-slate-400">
            已配置
          </span>
        </div>

        <!-- 设置 + 删除 -->
        <button
          @click.stop="emit('edit', provider, idx)"
          class="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-white/5 dark:hover:text-slate-300"
          title="设置"
        >
          <i class="fa-solid fa-gear text-xs"></i>
        </button>
        <button
          @click.stop="emit('remove', idx)"
          class="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-500 dark:hover:bg-rose-500/10"
          title="删除"
        >
          <i class="fa-solid fa-trash-can text-xs"></i>
        </button>
      </div>
    </div>
  </div>
</template>
