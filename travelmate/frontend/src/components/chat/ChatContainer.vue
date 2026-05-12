<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import MessageBubble from './MessageBubble.vue'
import ChatInput from './ChatInput.vue'
import TripCard from './TripCard.vue'
import SessionSidebar from './SessionSidebar.vue'
import PreferencesDrawer from '@/components/PreferencesDrawer.vue'

const store = useChatStore()
const listRef = ref<HTMLDivElement>()
const showPrefs = ref(false)
const showSidebar = ref(true)

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

onMounted(async () => {
  await store.loadSessions()
  if (store.sessions.length > 0) {
    await store.switchSession(store.sessions[0].session_id)
  } else {
    await store.createSession()
  }
})
</script>

<template>
  <div class="flex h-screen bg-gray-50">
    <!-- 左侧会话栏 -->
    <SessionSidebar v-show="showSidebar" />

    <!-- 主聊天区域 -->
    <div class="flex flex-1 flex-col min-w-0">
      <header class="flex items-center justify-between border-b bg-white px-4 py-3 shadow-sm sm:px-6 sm:py-4">
        <div class="flex items-center gap-2">
          <!-- 侧边栏开关 -->
          <button
            class="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
            @click="showSidebar = !showSidebar"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <h1 class="text-base font-semibold text-gray-800 sm:text-lg">TravelMate</h1>
          <span class="ml-1 text-xs text-gray-400 sm:text-sm">AI 智游伴</span>
        </div>
        <button
          class="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          @click="showPrefs = true"
        >
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </header>

      <div ref="listRef" class="flex-1 space-y-3 overflow-y-auto px-3 py-4 sm:space-y-4 sm:px-4 sm:py-6">
        <div v-if="store.messages.length === 0" class="flex h-full items-center justify-center">
          <p class="text-gray-400">你好！我是 TravelMate，告诉我你想去哪里旅行吧 ✈</p>
        </div>

        <template v-for="msg in store.messages" :key="msg.id">
          <TripCard
            v-if="isTripCard(msg)"
            :trip-plan="msg.metadata?.trip_plan ?? null"
            :safety-warning="String(msg.metadata?.safety_warning ?? '')"
            :fallback-summary="!msg.metadata?.trip_plan ? msg.content : ''"
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

    <!-- 偏好设置抽屉 -->
    <PreferencesDrawer v-if="showPrefs" @close="showPrefs = false" />
  </div>
</template>
