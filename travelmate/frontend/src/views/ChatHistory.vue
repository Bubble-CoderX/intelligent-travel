<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { getDeviceId } from '@/utils/device'
import MarkdownIt from 'markdown-it'

const props = defineProps<{ dark?: boolean; toggleDark?: () => void }>()
const router = useRouter()
const md = new MarkdownIt({ breaks: true, linkify: true })

interface Conversation {
  session_id: string
  title: string
  msg_count: number
  last_msg: string
  last_time: string
}

interface Message {
  role: string
  content: string
  intent: string
  created_at: string
}

const conversations = ref<Conversation[]>([])
const loading = ref(true)
const selectedSession = ref('')
const messages = ref<Message[]>([])
const loadingMessages = ref(false)

async function fetchConversations() {
  loading.value = true
  try {
    const res = await api.get('/chat-history/list', { params: { device_id: getDeviceId() } })
    conversations.value = res.data.conversations ?? []
  } catch { /* ignore */ }
  loading.value = false
}

async function viewMessages(sessionId: string) {
  selectedSession.value = sessionId
  loadingMessages.value = true
  messages.value = []
  try {
    const res = await api.get(`/chat-history/${sessionId}/messages`, { params: { device_id: getDeviceId() } })
    messages.value = res.data.messages ?? []
    await nextTick()
  } catch { /* ignore */ }
  loadingMessages.value = false
}

function formatTime(d: string) {
  if (!d) return ''
  const date = new Date(d)
  const h = String(date.getHours()).padStart(2, '0')
  const m = String(date.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
}

onMounted(fetchConversations)
</script>

<template>
  <div class="min-h-screen" :class="props.dark ? 'bg-[#212121]' : 'bg-stone-50'">
    <!-- 顶部导航 -->
    <div class="sticky top-0 z-30 flex items-center gap-3 border-b px-5 py-3" :class="props.dark ? 'bg-[#212121] border-stone-700' : 'bg-white border-stone-200'">
      <button class="rounded-lg p-1.5 text-stone-400 hover:bg-stone-100 dark:hover:bg-[#2f2f2f]" @click="selectedSession ? selectedSession = '' : router.push('/')">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
      </button>
      <h1 class="text-lg font-semibold" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">
        {{ selectedSession ? '💬 对话详情' : '💬 对话历史' }}
      </h1>
    </div>

    <div class="mx-auto max-w-3xl px-4 py-6">
      <!-- 会话列表 -->
      <div v-if="!selectedSession">
        <div v-if="loading" class="py-12 text-center text-sm text-stone-400">加载中...</div>
        <div v-else-if="conversations.length === 0" class="py-12 text-center">
          <p class="text-3xl mb-2">📭</p>
          <p class="text-sm text-stone-400">暂无对话记录</p>
        </div>
        <div v-else class="space-y-2">
          <div v-for="c in conversations" :key="c.session_id"
            class="rounded-xl border p-3 transition-colors cursor-pointer hover:shadow-md"
            :class="props.dark ? 'border-stone-700 bg-[#2a2a2a] hover:bg-[#333]' : 'border-stone-200 bg-white hover:bg-stone-50'"
            @click="viewMessages(c.session_id)"
          >
            <div class="flex items-center justify-between mb-1">
              <h3 class="font-medium text-sm truncate" :class="props.dark ? 'text-stone-200' : 'text-stone-800'">{{ c.title || '新会话' }}</h3>
              <span class="text-[11px] shrink-0 ml-2" :class="props.dark ? 'text-stone-500' : 'text-stone-400'">{{ c.msg_count }}条消息</span>
            </div>
            <p class="text-xs truncate" :class="props.dark ? 'text-stone-500' : 'text-stone-400'">{{ c.last_msg }}</p>
            <p class="text-[10px] mt-1" :class="props.dark ? 'text-stone-600' : 'text-stone-300'">{{ c.last_time }}</p>
          </div>
        </div>
      </div>

      <!-- 消息详情 -->
      <div v-else>
        <div v-if="loadingMessages" class="py-12 text-center text-sm text-stone-400">加载中...</div>
        <div v-else class="space-y-3">
          <div v-for="(msg, i) in messages" :key="i"
            class="flex gap-3"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed"
              :class="msg.role === 'user'
                ? 'bg-[#f4f4f4] text-stone-800 dark:bg-[#2f2f2f] dark:text-stone-100'
                : 'bg-stone-50 text-stone-700 dark:bg-[#1e1e1e] dark:text-stone-200'"
            >
              <div v-if="msg.role === 'user'" class="whitespace-pre-wrap">{{ msg.content }}</div>
              <div v-else class="prose prose-sm max-w-none prose-p:my-1" v-html="md.render(msg.content)" />
              <div class="mt-1 text-[10px]" :class="props.dark ? 'text-stone-600' : 'text-stone-400'">
                {{ formatTime(msg.created_at) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
