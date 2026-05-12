<script setup lang="ts">
import { ref, onMounted, watchEffect } from 'vue'
import ChatContainer from '@/components/chat/ChatContainer.vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { getDeviceId } from '@/utils/device'

const { connected } = useWebSocket(getDeviceId())
const dark = ref(false)

function toggleDark() {
  dark.value = !dark.value
}

onMounted(() => {
  // 读 localStorage 或系统偏好
  const stored = localStorage.getItem('travelmate_dark')
  if (stored !== null) {
    dark.value = stored === 'true'
  } else {
    dark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
  }
})

watchEffect(() => {
  document.documentElement.classList.toggle('dark', dark.value)
  localStorage.setItem('travelmate_dark', String(dark.value))
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
