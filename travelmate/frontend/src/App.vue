<script setup lang="ts">
import { ref, onMounted, watchEffect } from 'vue'
import ChatContainer from '@/components/chat/ChatContainer.vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { getDeviceId } from '@/utils/device'

const { connected } = useWebSocket(getDeviceId())

const API_BASE = 'http://localhost:8000'

// 同步初始化：读 localStorage → 系统偏好 → 默认浅色，避免 onMounted 异步导致闪白
// 后端重启时通过 startup-ts 对比强制重置为浅色
function initDark(): boolean {
  const stored = localStorage.getItem('travelmate_dark')
  const storedTs = localStorage.getItem('travelmate_startup_ts')

  // 异步检查后端是否重启（不阻塞渲染，onMounted 中处理）
  // 这里先同步读 localStorage，如果从未存过 startup_ts 则保持 stored 值
  // 如果后端重启过（storedTs 不匹配），会在 onMounted 中重置
  if (stored !== null && storedTs !== null) {
    // 先按存储值渲染，onMounted 中再校验
    return stored === 'true'
  }

  // 从未设置过 dark mode：查系统偏好
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

const dark = ref(initDark())

function toggleDark() {
  dark.value = !dark.value
}

watchEffect(() => {
  document.documentElement.classList.toggle('dark', dark.value)
  localStorage.setItem('travelmate_dark', String(dark.value))
})

// 启动后校验后端是否重启：重启则清除暗色偏好，回到浅色
onMounted(async () => {
  try {
    const res = await fetch(`${API_BASE}/startup-ts`)
    if (!res.ok) return
    const { startup_ts } = await res.json()
    const storedTs = localStorage.getItem('travelmate_startup_ts')
    if (storedTs !== null && String(startup_ts) !== storedTs) {
      // 后端重启了 → 强制浅色
      dark.value = false
    }
    localStorage.setItem('travelmate_startup_ts', String(startup_ts))
  } catch {
    // 后端未启动，保持当前状态
  }
})
</script>

<template>
  <div class="min-h-screen" :class="dark ? 'bg-stone-900' : 'bg-stone-50'">
    <div
      v-if="!connected"
      class="fixed right-4 top-4 z-50 rounded-full bg-amber-100 px-3 py-1 text-xs text-amber-700 shadow-sm"
    >
      实时连接中...
    </div>
    <button
      class="fixed right-4 top-12 z-50 rounded-full p-2 text-sm shadow-sm transition-colors"
      :class="dark ? 'bg-stone-700 text-amber-300 hover:bg-stone-600' : 'bg-white text-stone-500 hover:bg-stone-100'"
      @click="toggleDark"
      :title="dark ? '切换到浅色模式' : '切换到暗色模式'"
    >
      <svg v-if="!dark" class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg>
      <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
    </button>
    <ChatContainer :dark="dark" />
  </div>
</template>
