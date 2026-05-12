<script setup lang="ts">
import { computed, ref } from 'vue'
import MarkdownIt from 'markdown-it'
import type { Message } from '@/types/chat'
import { useSpeechSynthesis } from '@/composables/useSpeechSynthesis'
import { useChatStore } from '@/stores/chat'

const props = defineProps<{ message: Message }>()
const store = useChatStore()

const md = new MarkdownIt({ breaks: true, linkify: true })
const { isSpeaking, isSupported: ttsSupported, speak, stop } = useSpeechSynthesis()

const renderedContent = computed(() => {
  if (props.message.role === 'user') return props.message.content
  return md.render(props.message.content)
})

const isUser = computed(() => props.message.role === 'user')
const isSystem = computed(() => props.message.role === 'system')
const isAssistant = computed(() => props.message.role === 'assistant')
const isProactive = computed(() => props.message.type === 'proactive')
const canSpeak = computed(() => !isUser.value && !isSystem.value && ttsSupported.value)
const isFailed = computed(() => !!props.message.failed)

const proactiveLabel = computed(() => {
  const t = props.message.metadata?.proactive_type
  if (t === 'weather_alert') return '天气提醒'
  if (t === 'arrival_greeting') return '到达问候'
  return '主动消息'
})

const safetyWarning = computed(() => {
  return (props.message.metadata?.safety_warning as string) || ''
})

const errorLabel = computed(() => {
  switch (props.message.errorType) {
    case 'network': return '网络连接失败'
    case 'timeout': return '请求超时'
    default: return '服务器错误'
  }
})

function toggleSpeak() {
  if (isSpeaking.value) {
    stop()
  } else {
    speak(props.message.content)
  }
}

// ── 右键菜单 ─────────────────────────────────────────
const showMenu = ref(false)
const menuPos = ref({ x: 0, y: 0 })
const copied = ref(false)

function openMenu(e: MouseEvent) {
  e.preventDefault()
  menuPos.value = { x: e.clientX, y: e.clientY }
  showMenu.value = true
  document.addEventListener('click', closeMenu, { once: true })
}

function closeMenu() {
  showMenu.value = false
}

async function copyText() {
  await navigator.clipboard.writeText(props.message.content)
  copied.value = true
  setTimeout(() => { copied.value = false }, 1200)
  closeMenu()
}

function regenerate() {
  store.regenerateMessage(props.message.id)
  closeMenu()
}

function deleteMsg() {
  store.deleteMessage(props.message.id)
  closeMenu()
}

function speakMsg() {
  toggleSpeak()
  closeMenu()
}
</script>

<template>
  <div
    class="flex w-full"
    :class="isUser ? 'justify-end' : 'justify-start'"
    @contextmenu="openMenu"
  >
    <!-- 系统消息 -->
    <div
      v-if="isSystem"
      class="mx-auto max-w-[85%] rounded-full bg-gray-200 px-3 py-1.5 text-center text-xs text-gray-500 sm:max-w-[80%] sm:px-4"
    >
      {{ message.content }}
    </div>

    <!-- 主动消息 -->
    <div
      v-else-if="isProactive"
      class="max-w-[90%] rounded-2xl rounded-bl-md border border-amber-100 bg-amber-50 px-3 py-2.5 text-sm leading-relaxed text-gray-800 shadow-sm sm:max-w-[75%] sm:px-4 sm:py-3"
    >
      <div class="mb-1 text-xs font-medium text-amber-600">{{ proactiveLabel }}</div>
      <div class="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0" v-html="renderedContent" />
    </div>

    <!-- 普通消息 -->
    <div
      v-else
      class="max-w-[90%] rounded-2xl px-3 py-2.5 text-sm leading-relaxed sm:max-w-[75%] sm:px-4 sm:py-3"
      :class="
        isFailed
          ? 'border border-red-200 bg-red-50 text-red-700 rounded-bl-md'
          : isUser
            ? 'bg-blue-600 text-white rounded-br-md'
            : 'bg-white text-gray-800 shadow-sm border border-gray-100 rounded-bl-md'
      "
    >
      <!-- 失败状态 -->
      <template v-if="isFailed">
        <div class="whitespace-pre-wrap">{{ message.content }}</div>
        <div class="mt-2 flex items-center gap-2">
          <span class="text-xs text-red-400">{{ errorLabel }}</span>
          <button
            class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-200"
            @click="store.retryMessage(message.id)"
          >
            重新发送
          </button>
        </div>
      </template>

      <!-- 正常用户消息 -->
      <div v-else-if="isUser" class="whitespace-pre-wrap">{{ message.content }}</div>

      <!-- 正常 assistant 消息 -->
      <template v-else>
        <div class="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0" v-html="renderedContent" />
        <div
          v-if="safetyWarning"
          class="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700"
        >
          {{ safetyWarning }}
        </div>
        <button
          v-if="canSpeak"
          class="mt-2 flex items-center gap-1 text-xs text-gray-400 transition-colors hover:text-blue-500"
          @click="toggleSpeak"
        >
          <svg v-if="!isSpeaking" xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
            <line x1="23" y1="9" x2="17" y2="15" />
            <line x1="17" y1="9" x2="23" y2="15" />
          </svg>
          {{ isSpeaking ? '停止播报' : '播报' }}
        </button>
      </template>
    </div>

    <!-- 右键菜单 -->
    <Teleport to="body">
      <div
        v-if="showMenu"
        class="fixed z-[100] min-w-[140px] rounded-xl border border-stone-200 bg-white py-1.5 shadow-lg"
        :style="{ left: menuPos.x + 'px', top: menuPos.y + 'px' }"
        @click.stop
      >
        <button
          class="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-stone-700 hover:bg-stone-50"
          @click="copyText"
        >
          <svg class="h-3.5 w-3.5 text-stone-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
          {{ copied ? '已复制 ✓' : '复制文本' }}
        </button>
        <button
          v-if="isAssistant && !isFailed"
          class="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-stone-700 hover:bg-stone-50"
          @click="regenerate"
        >
          <svg class="h-3.5 w-3.5 text-stone-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          重新生成
        </button>
        <button
          v-if="canSpeak"
          class="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-stone-700 hover:bg-stone-50"
          @click="speakMsg"
        >
          <svg class="h-3.5 w-3.5 text-stone-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072M18.364 5.636a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" /></svg>
          {{ isSpeaking ? '停止播报' : '播报' }}
        </button>
        <div class="my-1 border-t border-stone-100" />
        <button
          class="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-red-500 hover:bg-red-50"
          @click="deleteMsg"
        >
          <svg class="h-3.5 w-3.5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
          删除消息
        </button>
      </div>
    </Teleport>
  </div>
</template>
