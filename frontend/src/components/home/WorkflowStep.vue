<script setup>
const props = defineProps({
  icon: {
    type: [Object, Function],
    required: true
  },
  title: {
    type: String,
    required: true
  },
  desc: {
    type: String,
    required: true
  },
  isActive: {
    type: Boolean,
    default: false
  },
  isPast: {
    type: Boolean,
    default: false
  }
})
</script>

<template>
  <div
    class="relative p-4 rounded-lg cursor-pointer transition-all duration-500"
    :class="isActive ? 'brand-btn transform scale-105' : 'border border-transparent hover:bg-white/[0.03] hover:border-white/[0.05]'"
  >
    <div class="flex flex-col items-center text-center">
      <div
        class="relative overflow-hidden w-12 h-12 rounded-xl flex items-center justify-center mb-4 transition-all duration-500"
        :class="isPast || isActive ? 'wf-icon--active text-white' : 'bg-white/[0.04] text-white/25 border border-white/[0.06]'"
      >
        <span v-if="isPast || isActive" class="wf-icon__grid absolute inset-0 pointer-events-none"></span>
        <component :is="icon" class="relative w-5 h-5" />
      </div>
      <h4
        class="text-sm font-semibold mb-1"
        :class="isActive ? 'text-white/90' : 'text-white/40'"
      >
        {{ title }}
      </h4>
      <p
        class="text-xs"
        :class="isActive ? 'text-white/50' : 'text-white/25'"
      >
        {{ desc }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.wf-icon--active {
  background: linear-gradient(to bottom, rgba(129, 115, 223, 0.9), rgba(99, 87, 199, 0.9));
  box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.12);
}

.wf-icon__grid {
  background-image:
    linear-gradient(to right, rgba(255, 255, 255, 0.06) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255, 255, 255, 0.06) 1px, transparent 1px);
  background-size: 8px 8px;
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
  -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
}
</style>
