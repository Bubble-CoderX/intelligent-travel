<script setup lang="ts">
import { ref, onMounted, watchEffect } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { getDeviceId } from '@/utils/device'

const { connected } = useWebSocket(getDeviceId())

const API_BASE = 'http://localhost:8000'

function initDark(): boolean {
  const stored = localStorage.getItem('travelmate_dark')
  const storedTs = localStorage.getItem('travelmate_startup_ts')
  if (stored !== null && storedTs !== null) {
    return stored === 'true'
  }
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

onMounted(async () => {
  try {
    const res = await fetch(`${API_BASE}/startup-ts`)
    if (!res.ok) return
    const { startup_ts } = await res.json()
    const storedTs = localStorage.getItem('travelmate_startup_ts')
    if (storedTs !== null && String(startup_ts) !== storedTs) {
      dark.value = false
    }
    localStorage.setItem('travelmate_startup_ts', String(startup_ts))
  } catch { /* 后端未启动 */ }
})
</script>

<template>
  <div class="min-h-screen" :class="dark ? 'bg-[#212121]' : 'bg-white'">
    <div
      v-if="!connected"
      class="fixed bottom-4 right-4 z-50 rounded-full bg-stone-200 px-3 py-1 text-xs text-stone-600 shadow-sm dark:bg-[#2f2f2f] dark:text-stone-400"
    >
      实时连接中...
    </div>
    <router-view :dark="dark" :toggle-dark="toggleDark" />
  </div>
</template>
