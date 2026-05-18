<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  text: { type: String, required: true },
  placement: { type: String, default: 'bottom' },
  align: { type: String, default: 'center' },
  offset: { type: Number, default: 8 },
  disabled: { type: Boolean, default: false },
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

  let left, top

  if (props.placement === 'top' || props.placement === 'bottom') {
    top = props.placement === 'top'
      ? triggerRect.top - props.offset
      : triggerRect.bottom + props.offset

    const viewportPadding = 8

    if (props.align === 'center') {
      left = triggerRect.left + triggerRect.width / 2
      const halfWidth = tooltipRect.width / 2
      left = Math.min(
        Math.max(left, viewportPadding + halfWidth),
        window.innerWidth - viewportPadding - halfWidth,
      )
    } else if (props.align === 'right') {
      left = triggerRect.right
      left = Math.min(
        Math.max(left, viewportPadding + tooltipRect.width),
        window.innerWidth - viewportPadding,
      )
    } else {
      left = triggerRect.left
      left = Math.min(
        Math.max(left, viewportPadding),
        window.innerWidth - viewportPadding - tooltipRect.width,
      )
    }
  } else {
    // left or right placement
    top = triggerRect.top + triggerRect.height / 2
    left = props.placement === 'left'
      ? triggerRect.left - props.offset
      : triggerRect.right + props.offset

    // Vertical viewport check
    const viewportPadding = 8
    const halfHeight = tooltipRect.height / 2
    top = Math.min(
      Math.max(top, viewportPadding + halfHeight),
      window.innerHeight - viewportPadding - halfHeight,
    )
  }

  position.value = { left, top }
}

const isTouch = ref(false)

const show = async () => {
  if (props.disabled || isTouch.value) return
  // 如果设备不支持 hover（如移动端），则不显示 tooltip，防止点击后残留
  if (typeof window !== 'undefined' && !window.matchMedia('(hover: hover)').matches) return
  visible.value = true
  await updatePosition()
}

const hide = () => {
  visible.value = false
}

const handleTouchStart = () => {
  isTouch.value = true
}

const onViewportChange = () => {
  if (visible.value) updatePosition()
}

if (typeof window !== 'undefined') {
  window.addEventListener('resize', onViewportChange)
  window.addEventListener('scroll', onViewportChange, true)
  window.addEventListener('touchstart', handleTouchStart, { passive: true })
}

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', onViewportChange)
    window.removeEventListener('scroll', onViewportChange, true)
    window.removeEventListener('touchstart', handleTouchStart)
  }
})
</script>

<template>
  <span ref="triggerRef" class="inline-flex" @mouseenter="show" @mouseleave="hide" @focusin="show" @focusout="hide">
    <slot></slot>
  </span>

  <Teleport to="body">
    <Transition enter-active-class="transition duration-150 ease-out" enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100" leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100 scale-100" leave-to-class="opacity-0 scale-95">
      <div v-if="visible" ref="tooltipRef" class="pointer-events-none fixed z-[9999]" :style="tooltipStyle">
        <div
          class="relative rounded-md border border-white/[0.08] bg-[#191a1b] px-3 py-1.5 text-xs text-[#d0d6e0] shadow-lg"
          :class="[
            (placement === 'top' || placement === 'bottom') && align === 'center' ? '-translate-x-1/2' : '',
            (placement === 'top' || placement === 'bottom') && align === 'right' ? '-translate-x-full' : '',
            placement === 'top' ? '-translate-y-full' : '',
            placement === 'left' ? '-translate-x-full -translate-y-1/2' : '',
            placement === 'right' ? '-translate-y-1/2' : '',
          ]">
          <slot name="content">{{ text }}</slot>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
