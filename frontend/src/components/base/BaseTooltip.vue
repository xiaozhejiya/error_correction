<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  text: { type: String, required: true },
  placement: { type: String, default: 'bottom' },
  align: { type: String, default: 'center' },
  offset: { type: Number, default: 8 },
})

const visible = ref(false)
const triggerRef = ref(null)
const tooltipRef = ref(null)
const position = ref({ left: 0, top: 0 })

const tooltipStyle = computed(() => ({
  left: `${position.value.left}px`,
  top: `${position.value.top}px`,
}))

const updatePosition = async () => {
  await nextTick()
  if (!triggerRef.value || !tooltipRef.value) return

  const triggerRect = triggerRef.value.getBoundingClientRect()
  const tooltipRect = tooltipRef.value.getBoundingClientRect()

  let left = triggerRect.left + triggerRect.width / 2
  let top = props.placement === 'top'
    ? triggerRect.top - props.offset
    : triggerRect.bottom + props.offset

  if (props.align === 'right') left = triggerRect.right
  if (props.align === 'left') left = triggerRect.left

  const viewportPadding = 8
  if (props.align === 'center') {
    const halfWidth = tooltipRect.width / 2
    left = Math.min(
      Math.max(left, viewportPadding + halfWidth),
      window.innerWidth - viewportPadding - halfWidth,
    )
  } else if (props.align === 'right') {
    left = Math.min(
      Math.max(left, viewportPadding + tooltipRect.width),
      window.innerWidth - viewportPadding,
    )
  } else {
    left = Math.min(
      Math.max(left, viewportPadding),
      window.innerWidth - viewportPadding - tooltipRect.width,
    )
  }

  position.value = { left, top }
}

const show = async () => {
  visible.value = true
  await updatePosition()
}

const hide = () => {
  visible.value = false
}

const onViewportChange = () => {
  if (visible.value) updatePosition()
}

if (typeof window !== 'undefined') {
  window.addEventListener('resize', onViewportChange)
  window.addEventListener('scroll', onViewportChange, true)
}

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', onViewportChange)
    window.removeEventListener('scroll', onViewportChange, true)
  }
})
</script>

<template>
  <span
    ref="triggerRef"
    class="inline-flex"
    @mouseenter="show"
    @mouseleave="hide"
    @focusin="show"
    @focusout="hide"
  >
    <slot></slot>
  </span>

  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="visible"
        ref="tooltipRef"
        class="pointer-events-none fixed z-[9999]"
        :style="tooltipStyle"
      >
        <div
          class="relative rounded-md border border-white/[0.08] bg-[#191a1b] px-3 py-1.5 text-xs text-[#d0d6e0] shadow-lg"
          :class="[
            align === 'center' ? '-translate-x-1/2' : '',
            align === 'right' ? '-translate-x-full' : '',
            placement === 'top' ? '-translate-y-full' : '',
          ]"
        >
          <slot name="content">{{ text }}</slot>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
