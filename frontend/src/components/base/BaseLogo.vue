<script setup>
/**
 * BaseLogo.vue
 * 品牌 Logo（支持呼吸动画、多尺寸）
 */
defineProps({
  size: { type: String, default: 'md' }, // sm | md | lg
  breathe: { type: Boolean, default: false },
})
</script>

<template>
  <div
    class="brand-logo relative overflow-hidden flex items-center justify-center"
    :class="[
      breathe ? 'brand-logo--breathe' : '',
      {
        'p-1.5 rounded-lg': size === 'sm',
        'p-2 rounded-xl': size === 'md',
        'p-3 rounded-2xl': size === 'lg',
      },
    ]"
  >
    <span class="brand-logo__grid absolute inset-0 pointer-events-none"></span>
    <img
      src="/logo.svg"
      class="relative brightness-0 invert"
      :class="{
        'w-4 h-4': size === 'sm',
        'w-6 h-6': size === 'md',
        'w-8 h-8': size === 'lg',
      }"
      alt="logo"
    />
  </div>
</template>

<style scoped>
.brand-logo {
  background: linear-gradient(to bottom, rgba(129, 115, 223, 0.9), rgba(99, 87, 199, 0.9));
  box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.12);
}

.brand-logo__grid {
  background-image:
    linear-gradient(to right, rgba(255, 255, 255, 0.06) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255, 255, 255, 0.06) 1px, transparent 1px);
  background-size: 8px 8px;
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
  -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
}

/* 呼吸发光 */
@keyframes brand-breathe {
  0%, 100% {
    box-shadow:
      inset 0 1px 0 0 rgba(255, 255, 255, 0.12),
      0 0 12px rgba(129, 115, 223, 0.3),
      0 0 24px rgba(129, 115, 223, 0.15);
  }
  50% {
    box-shadow:
      inset 0 1px 0 0 rgba(255, 255, 255, 0.15),
      0 0 24px rgba(129, 115, 223, 0.5),
      0 0 48px rgba(129, 115, 223, 0.25);
  }
}

.brand-logo--breathe {
  animation: brand-breathe 3s ease-in-out infinite;
}
</style>
