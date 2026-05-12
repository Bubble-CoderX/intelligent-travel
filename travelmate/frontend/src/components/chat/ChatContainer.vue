<script setup lang="ts">
import { ref, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import api from '@/api/client'
import { getDeviceId } from '@/utils/device'
import MessageBubble from './MessageBubble.vue'
import ChatInput from './ChatInput.vue'
import TripCard from './TripCard.vue'
import SessionSidebar from './SessionSidebar.vue'
import PreferencesDrawer from '@/components/PreferencesDrawer.vue'
import StyleSelector from './StyleSelector.vue'
import BatchExpandModal from './BatchExpandModal.vue'

const props = defineProps<{ dark?: boolean }>()
const store = useChatStore()
const listRef = ref<HTMLDivElement>()
const showPrefs = ref(false)
const showSidebar = ref(true)
const showBatchExpand = ref(false)
const switchingStyleMsg = ref<{ id: string; content: string } | null>(null)

// ── 天气 ────────────────────────────────────────────
const weather = ref<{ city: string; weather: string; temp: string } | null>(null)
let weatherTimer: ReturnType<typeof setInterval> | null = null

function weatherEmoji(w: string): string {
  if (/晴/.test(w)) return '☀️'
  if (/多云|阴/.test(w)) return '⛅'
  if (/雨|雷/.test(w)) return '🌧️'
  if (/雪/.test(w)) return '❄️'
  return '🌤️'
}

async function fetchWeather() {
  try {
    let lat: number | undefined, lng: number | undefined
    if (navigator.geolocation) {
      try {
        const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 })
        })
        lat = pos.coords.latitude
        lng = pos.coords.longitude
      } catch { /* 用户拒绝或超时，走 IP 兜底 */ }
    }
    const params: Record<string, any> = { device_id: getDeviceId() }
    if (lat !== undefined) { params.lat = lat; params.lng = lng }
    const res = await api.get('/weather/current', { params })
    if (res.data.status === 'ok') weather.value = res.data
  } catch { /* 静默失败，不干扰正常使用 */ }
}

function scrollToBottom() {
  nextTick(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  })
}

watch(() => store.messages.length, scrollToBottom)
watch(() => store.isLoading, scrollToBottom)

// isLoading 从 true→false 表示会话切换的消息加载完毕
let prevLoading = false
let switchedSessionId = ''

watch(() => store.isLoading, (loading) => {
  if (prevLoading && !loading) {
    // 加载完毕，如果是切换会话且有消息则触发问候
    if (switchedSessionId && store.messages.length > 0) {
      fetchGreeting()
    }
    switchedSessionId = ''
  }
  prevLoading = loading
})

// 记录切换会话时的 sessionId
watch(() => store.sessionId, (newId) => {
  switchedSessionId = newId
})

function handleSend(content: string, tripStyle?: string) {
  store.sendMessage(content, true, undefined, tripStyle)
}

/** "换种风格" — 找到对应 user 消息，展示风格选择器 */
function handleSwitchStyle(msg: { id: string }) {
  const idx = store.messages.findIndex(m => m.id === msg.id)
  if (idx < 0) return
  for (let i = idx - 1; i >= 0; i--) {
    if (store.messages[i].role === 'user') {
      switchingStyleMsg.value = { id: store.messages[i].id, content: store.messages[i].content }
      return
    }
  }
}

/** 选中新风格后重新发送 */
function handleStyleSwitchSelect(style: string) {
  if (!switchingStyleMsg.value) return
  const content = switchingStyleMsg.value.content
  switchingStyleMsg.value = null
  // 用 false 不再追加 user 消息（因为原 user 消息还在历史里），直接发请求
  store.sendMessage(content, false, undefined, style)
}

function isTripCard(msg: { type: string; role: string; metadata?: Record<string, unknown> }) {
  return msg.type === 'card' && msg.role === 'assistant' && !!msg.metadata?.trip_plan
}

/** 切换到有消息的会话时触发问候（持久化到后端） */
async function fetchGreeting() {
  if (store.messages.length === 0) return

  try {
    const res = await api.post('/proactive/greet-session', {
      device_id: getDeviceId(),
      session_id: store.sessionId,
    })
    if (res.data.status === 'ok') {
      store.addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: res.data.greeting,
        timestamp: Date.now(),
        type: 'proactive',
        metadata: { proactive_type: 'greeting' },
      })
    }
    // status === 'skipped' 表示已有问候，不重复添加
  } catch { /* 问候失败不阻塞 */ }
}

onMounted(async () => {
  await store.loadSessions()
  if (store.sessions.length > 0) {
    await store.switchSession(store.sessions[0].session_id)
  } else {
    await store.createSession()
  }
  fetchWeather()
  weatherTimer = setInterval(fetchWeather, 30 * 60 * 1000)
})

onUnmounted(() => {
  if (weatherTimer) clearInterval(weatherTimer)
})
</script>

<template>
  <div class="flex h-screen" :class="props.dark ? 'bg-stone-900' : 'bg-stone-50'">
    <!-- 左侧会话栏 -->
    <SessionSidebar v-show="showSidebar" />

    <!-- 主聊天区域 -->
    <div class="flex flex-1 flex-col min-w-0">
      <header class="flex items-center justify-between border-b bg-white px-4 py-3 shadow-sm sm:px-6 sm:py-4 dark:border-stone-700 dark:bg-stone-800">
        <div class="flex items-center gap-2">
          <button
            class="rounded-lg p-1.5 text-stone-400 hover:bg-stone-100 hover:text-stone-600 transition-colors dark:hover:bg-stone-700 dark:hover:text-stone-300"
            @click="showSidebar = !showSidebar"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <h1 class="text-base font-semibold text-stone-800 sm:text-lg dark:text-stone-100">TravelMate</h1>
          <span class="ml-1 text-xs text-stone-400 sm:text-sm dark:text-stone-500">AI 智游伴</span>
        </div>
        <div class="flex items-center gap-3">
          <div v-if="weather" class="flex items-center gap-1 text-sm text-stone-500 dark:text-stone-400">
            <span>{{ weatherEmoji(weather.weather) }}</span>
            <span class="hidden sm:inline">{{ weather.city }}</span>
            <span class="font-medium text-stone-700 dark:text-stone-200">{{ weather.temp }}°</span>
          </div>
          <button
            class="rounded-lg p-2 text-stone-400 hover:bg-stone-100 hover:text-stone-600 transition-colors dark:hover:bg-stone-700 dark:hover:text-stone-300"
            title="批量扩充知识库"
            @click="showBatchExpand = true"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </button>
          <button
            class="rounded-lg p-2 text-stone-400 hover:bg-stone-100 hover:text-stone-600 transition-colors dark:hover:bg-stone-700 dark:hover:text-stone-300"
            @click="showPrefs = true"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>
      </header>

      <div ref="listRef" class="flex-1 space-y-4 overflow-y-auto px-3 py-4 sm:space-y-5 sm:px-4 sm:py-6">
        <!-- 欢迎页 -->
        <div v-if="store.messages.length === 0" class="flex h-full flex-col items-center justify-center px-4">
          <div class="mb-6 text-5xl">🗺️</div>
          <h2 class="mb-2 text-xl font-semibold text-stone-700 dark:text-stone-200">TravelMate</h2>
          <p class="mb-8 text-sm text-stone-400 dark:text-stone-500">你的 AI 旅行伙伴</p>
          <p class="mb-10 text-center text-sm text-stone-500 dark:text-stone-400">
            我可以帮你规划行程、查天气、推荐景点、讲解历史文化～
          </p>
          <div class="grid grid-cols-3 gap-3">
            <button
              class="rounded-xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-600 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300"
              @click="handleSend('帮我规划行程')"
            >🗺️ 规划行程</button>
            <button
              class="rounded-xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-600 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300"
              @click="handleSend('今天天气怎么样')"
            >🌤️ 查天气</button>
            <button
              class="rounded-xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-600 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300"
              @click="handleSend('推荐一些热门景点')"
            >🏯 景点推荐</button>
          </div>
          <p class="mt-8 text-xs text-stone-300 dark:text-stone-600">或直接输入你想去的地方...</p>
        </div>

        <template v-for="msg in store.messages" :key="msg.id">
          <TripCard
            v-if="isTripCard(msg)"
            :trip-plan="msg.metadata?.trip_plan ?? null"
            :safety-warning="String(msg.metadata?.safety_warning ?? '')"
            :fallback-summary="!msg.metadata?.trip_plan ? msg.content : ''"
            :trip-style="msg.metadata?.trip_style"
            @switch-style="handleSwitchStyle(msg)"
          />
          <MessageBubble v-else :message="msg" />
        </template>

        <div v-if="store.isLoading" class="flex justify-start">
          <div class="rounded-2xl rounded-bl-md bg-white px-4 py-3 shadow-sm border border-stone-100 dark:bg-stone-800 dark:border-stone-700">
            <div class="flex gap-1">
              <span class="h-2 w-2 animate-bounce rounded-full bg-amber-400 [animation-delay:-0.3s]" />
              <span class="h-2 w-2 animate-bounce rounded-full bg-amber-400 [animation-delay:-0.15s]" />
              <span class="h-2 w-2 animate-bounce rounded-full bg-amber-400" />
            </div>
          </div>
        </div>
      </div>

      <!-- 换种风格选择器 -->
      <div v-if="switchingStyleMsg" class="border-t border-stone-200 bg-amber-50 px-4 py-2 dark:border-stone-700 dark:bg-stone-800">
        <div class="flex items-center justify-between">
          <span class="text-xs text-stone-500 dark:text-stone-400">选择新风格重新生成：</span>
          <button class="text-xs text-stone-400 hover:text-stone-600 dark:hover:text-stone-300" @click="switchingStyleMsg = null">✕ 取消</button>
        </div>
        <StyleSelector class="mt-1" @select="handleStyleSwitchSelect" />
      </div>
      <ChatInput :disabled="store.isLoading" @send="handleSend" />
    </div>

    <!-- 偏好设置抽屉 -->
    <PreferencesDrawer v-if="showPrefs" @close="showPrefs = false" />

    <!-- 批量扩充知识库 -->
    <BatchExpandModal v-if="showBatchExpand" @close="showBatchExpand = false" />
  </div>
</template>
