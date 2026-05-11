<script setup lang="ts">
import { ref, watch } from 'vue'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'

const emit = defineEmits<{ send: [content: string] }>()
defineProps<{ disabled?: boolean }>()

const input = ref('')
const { isListening, transcript, errorMsg, isSupported, start, stop } = useSpeechRecognition()

watch(transcript, (val) => {
  if (val) input.value = val
})

function handleSend() {
  const text = input.value.trim()
  if (!text) return
  if (isListening.value) stop()
  emit('send', text)
  input.value = ''
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
</script>

<template>
  <div class="flex items-end gap-2 border-t bg-white p-4">
    <textarea
      v-model="input"
      :disabled="disabled"
      rows="1"
      :placeholder="isListening ? '正在聆听...' : '输入消息... (Enter 发送，Shift+Enter 换行)'"
      class="flex-1 resize-none rounded-xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm outline-none transition-colors focus:border-blue-300 focus:bg-white disabled:opacity-50"
      :class="errorMsg ? 'border-red-300' : ''"
      :title="errorMsg"
      @keydown="handleKeydown"
    />
    <span v-if="errorMsg" class="absolute bottom-full left-4 mb-1 text-xs text-red-500">{{ errorMsg }}</span>
    <button
      v-if="isSupported"
      :disabled="disabled"
      class="flex h-10 w-10 items-center justify-center rounded-xl border transition-colors"
      :class="isListening
        ? 'border-red-300 bg-red-50 text-red-600 animate-pulse'
        : 'border-gray-200 bg-gray-50 text-gray-500 hover:bg-gray-100'"
      :title="isListening ? '停止录音' : '语音输入'"
      @click="toggleVoice"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" x2="12" y1="19" y2="22" />
      </svg>
    </button>
    <button
      :disabled="disabled || !input.trim()"
      class="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
      @click="handleSend"
    >
      发送
    </button>
  </div>
</template>
