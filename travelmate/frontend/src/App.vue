<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const healthStatus = ref<string>('checking...')

onMounted(async () => {
  try {
    const res = await api.get('/health')
    healthStatus.value = res.data.status
  } catch {
    healthStatus.value = 'backend unreachable'
  }
})
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center">
    <div class="text-center">
      <h1 class="text-4xl font-bold text-gray-900 mb-4">TravelMate</h1>
      <p class="text-lg text-gray-600 mb-2">AI 智游伴 - 智能旅行规划助手</p>
      <p class="text-sm text-gray-400">
        Backend status:
        <span
          :class="{
            'text-green-600 font-semibold': healthStatus === 'ok',
            'text-red-600 font-semibold': healthStatus !== 'ok' && healthStatus !== 'checking...',
            'text-yellow-500': healthStatus === 'checking...',
          }"
        >
          {{ healthStatus }}
        </span>
      </p>
    </div>
  </div>
</template>
