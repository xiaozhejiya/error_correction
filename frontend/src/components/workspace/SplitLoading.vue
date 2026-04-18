<script setup>
/**
 * SplitLoading.vue
 * 分割加载动画
 */
import BaseLogo from '@/components/base/BaseLogo.vue'

defineProps({
  title: { type: String, default: 'AI 正在深度解析' },
  subtitle: { type: String, default: '正在识别题目结构、提取知识点并构建图谱' },
})
</script>

<template>
  <Transition name="fade">
    <div class="loading-overlay">
      <div class="loading-content">
        <!-- 核心扫描动画区 -->
        <div class="scanner-container">
          <!-- 背景光晕 -->
          <div class="scanner-glow"></div>

          <!-- 旋转轨道 -->
          <div class="orbit orbit-1"></div>
          <div class="orbit orbit-2"></div>
          <div class="orbit orbit-3"></div>

          <!-- 核心图标 -->
          <div class="core-icon">
            <BaseLogo size="lg" />
            <!-- 核心脉冲 -->
            <div class="core-pulse"></div>
          </div>

          <!-- 扫描线 -->
          <div class="scan-line"></div>
        </div>

        <!-- 文本引导 -->
        <div class="text-container">
          <h3 class="status-title">{{ title }}</h3>
          <p class="status-subtitle">{{ subtitle }}</p>

          <!-- 模拟进度条 -->
          <div class="progress-container">
            <div class="progress-bar">
              <div class="progress-glow"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.loading-overlay {
  position: absolute;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3rem;
}

/* --- 核心动画容器 --- */
.scanner-container {
  position: relative;
  width: 160px;
  height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.scanner-glow {
  position: absolute;
  width: 120%;
  height: 120%;
  background: radial-gradient(circle, rgba(129, 115, 223, 0.15) 0%, transparent 70%);
  filter: blur(20px);
  animation: breathe 4s ease-in-out infinite;
}

/* 旋转轨道 */
.orbit {
  position: absolute;
  border-radius: 50%;
  border: 1.5px solid rgba(129, 115, 223, 0.1);
  border-top-color: rgba(129, 115, 223, 0.5);
}

.orbit-1 {
  width: 100%;
  height: 100%;
  animation: rotate 8s linear infinite;
}

.orbit-2 {
  width: 75%;
  height: 75%;
  animation: rotate 5s linear infinite reverse;
  border-top-color: rgba(145, 132, 235, 0.5);
}

.orbit-3 {
  width: 50%;
  height: 50%;
  animation: rotate 3s linear infinite;
  border-top-color: rgba(129, 115, 223, 0.5);
}

/* 核心图标 */
.core-icon {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
}

.core-pulse {
  position: absolute;
  inset: -4px;
  border-radius: 1.25rem;
  background: rgba(129, 115, 223, 0.2);
  animation: pulse 2s ease-out infinite;
}

/* 扫描线 */
.scan-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(129, 115, 223, 0.8), transparent);
  box-shadow: 0 0 15px rgba(129, 115, 223, 0.5);
  z-index: 5;
  animation: scan 3s ease-in-out infinite;
}

/* --- 文本容器 --- */
.text-container {
  text-align: center;
  max-width: 300px;
}

.status-title {
  font-size: 1.125rem;
  font-weight: 900;
  color: #0f172a;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

:root.dark .status-title {
  color: white;
}

.status-subtitle {
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
  line-height: 1.5;
}

/* --- 进度条 --- */
.progress-container {
  margin-top: 1.5rem;
  width: 100%;
  height: 4px;
  background: rgba(129, 115, 223, 0.05);
  border-radius: 10px;
  overflow: hidden;
}

.progress-bar {
  width: 40%;
  height: 100%;
  background: linear-gradient(90deg, rgb(129,115,223), rgb(145,132,235));
  border-radius: 10px;
  position: relative;
  animation: progress-move 2.5s ease-in-out infinite;
}

.progress-glow {
  position: absolute;
  top: 0;
  right: 0;
  height: 100%;
  width: 20px;
  background: white;
  filter: blur(4px);
  opacity: 0.5;
}

/* --- 关键帧 --- */
@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes breathe {
  0%, 100% { opacity: 0.5; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.1); }
}

@keyframes pulse {
  0% { transform: scale(0.95); opacity: 0.8; }
  100% { transform: scale(1.4); opacity: 0; }
}

@keyframes scan {
  0%, 100% { top: 0; opacity: 0; }
  20%, 80% { opacity: 1; }
  50% { top: 100%; }
}

@keyframes progress-move {
  0% { transform: translateX(-100%); }
  50% { transform: translateX(150%); }
  100% { transform: translateX(-100%); }
}

/* --- Transition --- */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.4s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
