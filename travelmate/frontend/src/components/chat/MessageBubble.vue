<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import type { Message } from '@/types/chat'

const props = defineProps<{ message: Message }>()

const md = new MarkdownIt({ breaks: true, linkify: true })

const renderedContent = computed(() => {
  if (props.message.role === 'user') return props.message.content
  return md.render(props.message.content)
})

const isUser = computed(() => props.message.role === 'user')
const isSystem = computed(() => props.message.role === 'system')
const isProactive = computed(() => props.message.type === 'proactive')

const proactiveLabel = computed(() => {
  const t = props.message.metadata?.proactive_type
  if (t === 'weather_alert') return '天气提醒'
  if (t === 'arrival_greeting') return '到达问候'
  return '主动消息'
})

const safetyWarning = computed(() => {
  return (props.message.metadata?.safety_warning as string) || ''
})
</script>

<template>
  <div
    class="flex w-full"
    :class="isUser ? 'justify-end' : 'justify-start'"
  >
    <div
      v-if="isSystem"
      class="mx-auto max-w-[80%] rounded-full bg-gray-200 px-4 py-1.5 text-center text-xs text-gray-500"
    >
      {{ message.content }}
    </div>
    <div
      v-else-if="isProactive"
      class="max-w-[75%] rounded-2xl rounded-bl-md border border-amber-100 bg-amber-50 px-4 py-3 text-sm leading-relaxed text-gray-800 shadow-sm"
    >
      <div class="mb-1 text-xs font-medium text-amber-600">{{ proactiveLabel }}</div>
      <div class="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0" v-html="renderedContent" />
    </div>
    <div
      v-else
      class="max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed"
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
      </template>
    </div>
  </div>
</template>
