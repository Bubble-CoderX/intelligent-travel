<script setup lang="ts">
import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'
import StyleSelector from './StyleSelector.vue'

const emit = defineEmits<{ send: [content: string, tripStyle?: string, imageData?: string] }>()
defineProps<{ disabled?: boolean }>()

const input = ref('')
const tripStyle = ref<string | undefined>(undefined)
const { isListening, transcript, errorMsg, isSupported, start, stop } = useSpeechRecognition()

const PLACEHOLDERS = [
  '输入你想去的地方...',
  '试试说"帮我规划一个周末短途旅行"',
  '输入"杭州三天"马上生成行程',
  '问"今天适合去哪里玩"获取推荐',
]
const placeholderIdx = ref(0)
let placeholderTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  placeholderTimer = setInterval(() => {
    placeholderIdx.value = (placeholderIdx.value + 1) % PLACEHOLDERS.length
  }, 5000)
})

onUnmounted(() => {
  if (placeholderTimer) clearInterval(placeholderTimer)
})

const currentPlaceholder = computed(() => {
  if (isListening.value) return '正在聆听...'
  return PLACEHOLDERS[placeholderIdx.value]
})

watch(transcript, (val) => {
  if (val) input.value = val
})

const TRIP_KEYWORDS = /规划|行程|旅游|旅行|出游|几天|游玩|度假|攻略|出行/
const showStyleSelector = computed(() => TRIP_KEYWORDS.test(input.value))

function handleStyleSelect(style: string) {
  const text = input.value.trim()
  if (!text) return
  if (isListening.value) stop()
  emit('send', text, style)
  input.value = ''
  tripStyle.value = undefined
}

function handleSend() {
  const text = input.value.trim()
  if (!text) return
  if (isListening.value) stop()
  emit('send', text, tripStyle.value)
  input.value = ''
  tripStyle.value = ''
  transcript.value = ''
}

function toggleVoice() {
  if (isListening.value) {
    stop()
  } else {
    input.value = ''
    start()
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

// ── O8: 图片文件上传 ──────────────────────────────────
const fileInput = ref<any>(null)

function triggerFileUpload() {
  fileInput.value?.click()
}

async function handleFileUpload(e: any) {
  const target = e.target
  const file = target.files?.[0]
  if (!file) return

  if (file.size > 10 * 1024 * 1024) {
    alert('文件太大，请选择 10MB 以内的图片')
    return
  }

  const reader = new FileReader()
  reader.onload = async () => {
    const dataUrl = reader.result as string
    const base64 = dataUrl.split(',')[1]

    // 先显示用户消息（用 data URL 临时显示，等后端返回 server URL 后替换）
    const { useChatStore } = await import('@/stores/chat')
    const store = useChatStore()
    const userMsgId = crypto.randomUUID()
    store.addMessage({
      id: userMsgId,
      role: 'user',
      content: '',
      timestamp: Date.now(),
      type: 'text',
      imageData: dataUrl,
    })

    // 调用后端分析图片（同时保存到磁盘）
    try {
      const res = await fetch('http://localhost:8000/chat/image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: localStorage.getItem('travelmate_device_id') || '',
          session_id: store.sessionId || '',
          image_base64: base64,
          filename: file.name,
          question: `请分析这张图片（${file.name}）`,
        }),
      })
      const data = await res.json()
      // 用服务器 URL 替换用户消息中的图片（持久化）
      if (data.image_url) {
        const serverUrl = `http://localhost:8000${data.image_url}`
        const userMsg = store.messages.find(m => m.id === userMsgId)
        if (userMsg) userMsg.imageData = serverUrl
      }
      // 添加 AI 回复
      store.addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.reply || '图片分析完成',
        timestamp: Date.now(),
        type: 'text',
      })
      store.loadSessions()
    } catch (err) {
      console.error('图片分析失败', err)
      store.addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '图片分析暂时不可用，请稍后再试',
        timestamp: Date.now(),
        type: 'text',
      })
    }
  }
  reader.readAsDataURL(file)
  target.value = ''
}
</script>

<template>
  <div>
    <!-- 行程风格选择器 -->
    <StyleSelector v-if="showStyleSelector" class="mb-2" @select="handleStyleSelect" />

    <div class="relative flex items-end gap-2">
      <textarea
        v-model="input"
        :disabled="disabled"
        rows="1"
        :placeholder="currentPlaceholder"
        class="flex-1 resize-none rounded-2xl border bg-transparent px-4 py-3 text-sm outline-none transition-colors placeholder:text-stone-400 focus:border-stone-400 disabled:opacity-50 dark:placeholder:text-stone-500"
        :class="errorMsg
          ? 'border-red-300 dark:border-red-700'
          : 'border-stone-300 dark:border-stone-600 dark:text-stone-100 dark:focus:border-stone-500'"
        :title="errorMsg"
        @keydown="handleKeydown"
      />
      <span v-if="errorMsg" class="absolute bottom-full left-3 mb-1 text-xs text-red-500">{{ errorMsg }}</span>

      <!-- 语音按钮 -->
      <button
        v-if="isSupported"
        :disabled="disabled"
        class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border transition-colors"
        :class="isListening
          ? 'border-red-300 bg-red-50 text-red-500 animate-pulse dark:border-red-800 dark:bg-red-950'
          : 'border-stone-300 text-stone-400 hover:bg-stone-50 dark:border-stone-600 dark:hover:bg-[#2f2f2f]'"
        :title="isListening ? '停止录音' : '语音输入'"
        @click="toggleVoice"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" x2="12" y1="19" y2="22" />
        </svg>
      </button>

      <!-- O8: 图片上传按钮 -->
      <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="handleFileUpload" />
      <button
        :disabled="disabled"
        class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-stone-300 text-stone-400 transition-colors hover:bg-stone-50 dark:border-stone-600 dark:hover:bg-[#2f2f2f]"
        title="上传图片"
        @click="triggerFileUpload"
      >
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
      </button>

      <!-- 发送按钮 -->
      <button
        :disabled="disabled || !input.trim()"
        class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-colors"
        :class="input.trim()
          ? 'bg-stone-800 text-white hover:bg-stone-700 dark:bg-stone-200 dark:text-stone-800 dark:hover:bg-white'
          : 'bg-stone-200 text-stone-400 cursor-not-allowed dark:bg-[#2f2f2f] dark:text-stone-600'"
        @click="handleSend"
      >
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14m-7-7l7 7-7 7" />
        </svg>
      </button>
    </div>
  </div>
</template>
