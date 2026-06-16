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

const props = defineProps<{ dark?: boolean; toggleDark?: () => void }>()
const store = useChatStore()
const listRef = ref<HTMLDivElement>()
const showPrefs = ref(false)
const showSidebar = ref(true)
const showBatchExpand = ref(false)
const switchingStyleMsg = ref<{ id: string; content: string } | null>(null)

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
      } catch { /* 静默失败 */ }
    }
    const params: Record<string, any> = { device_id: getDeviceId() }
    if (lat !== undefined) { params.lat = lat; params.lng = lng }
    const res = await api.get('/weather/current', { params })
    if (res.data.status === 'ok') {
      weather.value = res.data
      // 自动设置天气播报（每天 7:00 / 12:00 / 19:00 / 0:00）
      if (res.data.city) {
        api.post('/proactive/set-weather-check', {
          device_id: getDeviceId(),
          city: res.data.city,
        }).catch(() => {})
      }
    }
  } catch { /* 静默失败 */ }
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

let prevLoading = false
let switchedSessionId = ''

watch(() => store.isLoading, (loading) => {
  if (prevLoading && !loading) {
    if (switchedSessionId && store.messages.length > 0) {
      fetchGreeting()
    }
    switchedSessionId = ''
  }
  prevLoading = loading
})

watch(() => store.sessionId, (newId) => {
  switchedSessionId = newId
})

function handleSend(content: string, tripStyle?: string, imageData?: string) {
  store.sendMessage(content, true, undefined, tripStyle, imageData)
}

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

function handleStyleSwitchSelect(style: string) {
  if (!switchingStyleMsg.value) return
  const content = switchingStyleMsg.value.content
  switchingStyleMsg.value = null
  store.sendMessage(content, false, undefined, style)
}

function isTripCard(msg: { type: string; role: string; metadata?: Record<string, unknown> }) {
  return msg.type === 'card' && msg.role === 'assistant' && !!msg.metadata?.trip_plan
}

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
  } catch { /* 静默失败 */ }
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
  <div class="flex h-screen" :class="props.dark ? 'bg-[#212121]' : 'bg-white'">
    <!-- 左侧会话栏 -->
    <SessionSidebar
      v-show="showSidebar"
      :dark="props.dark"
      :toggle-dark="props.toggleDark"
      @togglePrefs="showPrefs = true"
      @toggleBatchExpand="showBatchExpand = true"
      @toggleSidebar="showSidebar = false"
    />

    <!-- 主聊天区域 -->
    <div class="flex flex-1 flex-col min-w-0">
      <!-- 顶部栏：侧边栏切换 + 标题 + 天气 -->
      <div class="flex items-center justify-between px-3 py-2.5" :class="props.dark ? 'bg-[#212121]' : 'bg-white'">
        <div class="flex items-center gap-2">
          <button
            class="rounded-lg p-1.5 transition-colors"
            :class="props.dark ? 'text-stone-400 hover:text-stone-200 hover:bg-[#2f2f2f]' : 'text-stone-500 hover:text-stone-700 hover:bg-stone-100'"
            @click="showSidebar = !showSidebar"
            title="切换侧边栏"
          >
            <svg v-if="showSidebar" class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            </svg>
            <svg v-else class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span class="text-base font-semibold" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">
            TravelMate
          </span>
        </div>
        <span v-if="weather" class="text-sm" :class="props.dark ? 'text-stone-400' : 'text-stone-500'">
          {{ weatherEmoji(weather.weather) }} {{ weather.city }} {{ weather.weather }} {{ weather.temp }}°
        </span>
      </div>

      <!-- 消息列表 -->
      <div ref="listRef" class="flex-1 overflow-y-auto">
        <div class="mx-auto w-full max-w-5xl px-4 py-6">
          <!-- 欢迎页 -->
          <div v-if="store.messages.length === 0" class="flex h-full flex-col items-center justify-center pt-[15vh]">
            <h1 class="mb-8 text-2xl font-semibold tracking-tight" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">
              TravelMate
            </h1>
            <div class="grid w-full max-w-md grid-cols-2 gap-3">
              <button
                class="rounded-xl border px-4 py-3 text-left text-sm transition-colors"
                :class="props.dark
                  ? 'border-stone-700 text-stone-300 hover:bg-[#2f2f2f]'
                  : 'border-stone-200 text-stone-600 hover:bg-stone-50'"
                @click="handleSend('帮我规划一个三天的杭州行程')"
              >
                <div class="mb-1 text-base">🗺️</div>
                <div class="font-medium">规划行程</div>
                <div class="text-xs opacity-60">帮你安排旅行路线</div>
              </button>
              <button
                class="rounded-xl border px-4 py-3 text-left text-sm transition-colors"
                :class="props.dark
                  ? 'border-stone-700 text-stone-300 hover:bg-[#2f2f2f]'
                  : 'border-stone-200 text-stone-600 hover:bg-stone-50'"
                @click="handleSend('今天天气怎么样，适合出游吗')"
              >
                <div class="mb-1 text-base">🌤️</div>
                <div class="font-medium">查看天气</div>
                <div class="text-xs opacity-60">了解目的地天气情况</div>
              </button>
              <button
                class="rounded-xl border px-4 py-3 text-left text-sm transition-colors"
                :class="props.dark
                  ? 'border-stone-700 text-stone-300 hover:bg-[#2f2f2f]'
                  : 'border-stone-200 text-stone-600 hover:bg-stone-50'"
                @click="handleSend('推荐一些热门旅游景点')"
              >
                <div class="mb-1 text-base">🏯</div>
                <div class="font-medium">景点推荐</div>
                <div class="text-xs opacity-60">发现热门目的地</div>
              </button>
              <button
                class="rounded-xl border px-4 py-3 text-left text-sm transition-colors"
                :class="props.dark
                  ? 'border-stone-700 text-stone-300 hover:bg-[#2f2f2f]'
                  : 'border-stone-200 text-stone-600 hover:bg-stone-50'"
                @click="handleSend('帮我扩充旅行知识库')"
              >
                <div class="mb-1 text-base">📚</div>
                <div class="font-medium">扩充知识库</div>
                <div class="text-xs opacity-60">丰富目的地信息</div>
              </button>
            </div>
          </div>

          <!-- 消息列表 -->
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

          <!-- 加载指示器 -->
          <div v-if="store.isLoading" class="flex justify-start py-2">
            <div class="flex gap-1.5" :class="props.dark ? '' : ''">
              <span class="h-2.5 w-2.5 animate-bounce rounded-full bg-stone-400 [animation-delay:-0.3s]" />
              <span class="h-2.5 w-2.5 animate-bounce rounded-full bg-stone-400 [animation-delay:-0.15s]" />
              <span class="h-2.5 w-2.5 animate-bounce rounded-full bg-stone-400" />
            </div>
          </div>
        </div>
      </div>

      <!-- 换种风格选择器 -->
      <div v-if="switchingStyleMsg" class="mx-auto w-full max-w-5xl px-4 pb-2">
        <div class="flex items-center justify-between">
          <span class="text-xs" :class="props.dark ? 'text-stone-400' : 'text-stone-500'">选择新风格重新生成：</span>
          <button
            class="text-xs transition-colors"
            :class="props.dark ? 'text-stone-500 hover:text-stone-300' : 'text-stone-400 hover:text-stone-600'"
            @click="switchingStyleMsg = null"
          >✕ 取消</button>
        </div>
        <StyleSelector class="mt-1" @select="handleStyleSwitchSelect" />
      </div>

      <!-- 输入区域 -->
      <div class="mx-auto w-full max-w-5xl px-4 pb-4">
        <ChatInput :disabled="store.isLoading" @send="handleSend" />
      </div>
    </div>

    <!-- 偏好设置抽屉 -->
    <PreferencesDrawer v-if="showPrefs" @close="showPrefs = false" />

    <!-- 批量扩充知识库 -->
    <BatchExpandModal v-if="showBatchExpand" @close="showBatchExpand = false" />
  </div>
</template>
