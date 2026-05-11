<script setup lang="ts">
import ChatContainer from '@/components/chat/ChatContainer.vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { getDeviceId } from '@/utils/device'

const { connected } = useWebSocket(getDeviceId())
</script>

<template>
  <div>
    <div
      v-if="!connected"
      class="fixed right-4 top-4 z-50 rounded-full bg-amber-100 px-3 py-1 text-xs text-amber-700 shadow-sm"
    >
      实时连接中...
    </div>
    <ChatContainer />
  </div>
</template>
