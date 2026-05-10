<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{ send: [content: string] }>()
defineProps<{ disabled?: boolean }>()

const input = ref('')

function handleSend() {
  const text = input.value.trim()
  if (!text) return
  emit('send', text)
  input.value = ''
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
      placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
      class="flex-1 resize-none rounded-xl border border-gray-200 bg-gray-50 px-4 py-2.5 text-sm outline-none transition-colors focus:border-blue-300 focus:bg-white disabled:opacity-50"
      @keydown="handleKeydown"
    />
    <button
      :disabled="disabled || !input.trim()"
      class="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
      @click="handleSend"
    >
      发送
    </button>
  </div>
</template>
