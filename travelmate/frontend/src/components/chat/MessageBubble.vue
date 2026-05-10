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
      v-else
      class="max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed"
      :class="
        isUser
          ? 'bg-blue-600 text-white rounded-br-md'
          : 'bg-white text-gray-800 shadow-sm border border-gray-100 rounded-bl-md'
      "
    >
      <div v-if="isUser" class="whitespace-pre-wrap">{{ message.content }}</div>
      <div v-else class="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0" v-html="renderedContent" />
    </div>
  </div>
</template>
