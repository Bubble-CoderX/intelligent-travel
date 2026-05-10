<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import MessageBubble from './MessageBubble.vue'
import ChatInput from './ChatInput.vue'
import TripCard from './TripCard.vue'

const store = useChatStore()
const listRef = ref<HTMLDivElement>()

function scrollToBottom() {
  nextTick(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  })
}

watch(() => store.messages.length, scrollToBottom)
watch(() => store.isLoading, scrollToBottom)

function handleSend(content: string) {
  store.sendMessage(content)
}

function isTripCard(msg: { type: string }) {
  return msg.type === 'card'
}
</script>

<template>
  <div class="flex h-screen flex-col bg-gray-50">
    <header class="flex items-center border-b bg-white px-6 py-4 shadow-sm">
      <h1 class="text-lg font-semibold text-gray-800">TravelMate</h1>
      <span class="ml-2 text-sm text-gray-400">AI 智游伴</span>
    </header>

    <div ref="listRef" class="flex-1 space-y-4 overflow-y-auto px-4 py-6">
      <div v-if="store.messages.length === 0" class="flex h-full items-center justify-center">
        <p class="text-gray-400">你好！我是 TravelMate，告诉我你想去哪里旅行吧 ✈</p>
      </div>

      <template v-for="msg in store.messages" :key="msg.id">
        <TripCard
          v-if="isTripCard(msg)"
          :title="String(msg.metadata?.title ?? '行程方案')"
          :destination="String(msg.metadata?.destination ?? '')"
          :days="Number(msg.metadata?.days ?? 0)"
          :budget="Number(msg.metadata?.budget ?? 0)"
          :summary="msg.content"
        />
        <MessageBubble v-else :message="msg" />
      </template>

      <div v-if="store.isLoading" class="flex justify-start">
        <div class="rounded-2xl rounded-bl-md bg-white px-4 py-3 shadow-sm border border-gray-100">
          <div class="flex gap-1">
            <span class="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.3s]" />
            <span class="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.15s]" />
            <span class="h-2 w-2 animate-bounce rounded-full bg-gray-400" />
          </div>
        </div>
      </div>
    </div>

    <ChatInput :disabled="store.isLoading" @send="handleSend" />
  </div>
</template>
