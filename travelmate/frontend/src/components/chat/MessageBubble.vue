<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import type { Message } from '@/types/chat'
import { useSpeechSynthesis } from '@/composables/useSpeechSynthesis'

const props = defineProps<{ message: Message }>()

const md = new MarkdownIt({ breaks: true, linkify: true })
const { isSpeaking, isSupported: ttsSupported, speak, stop } = useSpeechSynthesis()

const renderedContent = computed(() => {
  if (props.message.role === 'user') return props.message.content
  return md.render(props.message.content)
})

const isUser = computed(() => props.message.role === 'user')
const isSystem = computed(() => props.message.role === 'system')
const isProactive = computed(() => props.message.type === 'proactive')
const canSpeak = computed(() => !isUser.value && !isSystem.value && ttsSupported.value)

const proactiveLabel = computed(() => {
  const t = props.message.metadata?.proactive_type
  if (t === 'weather_alert') return '天气提醒'
  if (t === 'arrival_greeting') return '到达问候'
  return '主动消息'
})

const safetyWarning = computed(() => {
  return (props.message.metadata?.safety_warning as string) || ''
})

function toggleSpeak() {
  if (isSpeaking.value) {
    stop()
  } else {
    speak(props.message.content)
  }
}
</script>

<template>
  <div
    class="flex w-full"
    :class="isUser ? 'justify-end' : 'justify-start'"
  >
    <div
      v-if="isSystem"
      class="mx-auto max-w-[85%] rounded-full bg-gray-200 px-3 py-1.5 text-center text-xs text-gray-500 sm:max-w-[80%] sm:px-4"
    >
      {{ message.content }}
    </div>
    <div
      v-else-if="isProactive"
      class="max-w-[90%] rounded-2xl rounded-bl-md border border-amber-100 bg-amber-50 px-3 py-2.5 text-sm leading-relaxed text-gray-800 shadow-sm sm:max-w-[75%] sm:px-4 sm:py-3"
    >
      <div class="mb-1 text-xs font-medium text-amber-600">{{ proactiveLabel }}</div>
      <div class="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0" v-html="renderedContent" />
    </div>
    <div
      v-else
      class="max-w-[90%] rounded-2xl px-3 py-2.5 text-sm leading-relaxed sm:max-w-[75%] sm:px-4 sm:py-3"
      :class="
        isUser
          ? 'bg-blue-600 text-white rounded-br-md'
          : 'bg-white text-gray-800 shadow-sm border border-gray-100 rounded-bl-md'
      "
    >
      <div v-if="isUser" class="whitespace-pre-wrap">{{ message.content }}</div>
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
  </div>
</template>
