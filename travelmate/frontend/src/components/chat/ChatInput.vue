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
  <div class="flex items-end gap-1.5 border-t border-stone-200 bg-white px-3 py-3 sm:gap-2 sm:px-4 sm:py-4 dark:border-stone-700 dark:bg-stone-800">
    <textarea
      v-model="input"
      :disabled="disabled"
      rows="1"
      :placeholder="isListening ? '正在聆听...' : '告诉我你想去哪里旅行...'"
      class="flex-1 resize-none rounded-2xl border border-stone-200 bg-stone-50 px-4 py-2.5 text-sm text-stone-800 outline-none transition-all placeholder:text-stone-400 focus:border-amber-400 focus:bg-white focus:ring-2 focus:ring-amber-100 disabled:opacity-50 dark:border-stone-600 dark:bg-stone-700 dark:text-stone-100 dark:placeholder:text-stone-500 dark:focus:border-amber-500 dark:focus:bg-stone-700"
      :class="errorMsg ? 'border-red-300' : ''"
      :title="errorMsg"
      @keydown="handleKeydown"
    />
    <span v-if="errorMsg" class="absolute bottom-full left-3 mb-1 text-xs text-red-500 sm:left-4">{{ errorMsg }}</span>
    <p v-if="!input.trim() && !isListening" class="hidden text-[11px] text-stone-400 sm:block dark:text-stone-500">试试说"帮我规划一个周末短途旅行"</p>
    <button
      v-if="isSupported"
      :disabled="disabled"
      class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border transition-colors sm:h-10 sm:w-10"
      :class="isListening
        ? 'border-red-300 bg-red-50 text-red-600 animate-pulse'
        : 'border-stone-200 bg-stone-50 text-stone-400 hover:bg-stone-100 dark:border-stone-600 dark:bg-stone-700 dark:hover:bg-stone-600'"
      :title="isListening ? '停止录音' : '语音输入'"
      @click="toggleVoice"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 sm:h-5 sm:w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" x2="12" y1="19" y2="22" />
      </svg>
    </button>
    <button
      :disabled="disabled || !input.trim()"
      class="rounded-xl bg-amber-500 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-amber-600 hover:shadow-md disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:shadow-none sm:px-5 sm:py-2.5"
      @click="handleSend"
    >
      发送
    </button>
  </div>
</template>
