import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Message } from '@/types/chat'
import api from '@/api/client'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const isLoading = ref(false)

  function addMessage(msg: Message) {
    messages.value.push(msg)
  }

  function addSystemMessage(content: string) {
    addMessage({
      id: crypto.randomUUID(),
      role: 'system',
      content,
      timestamp: Date.now(),
      type: 'text',
    })
  }

  async function sendMessage(content: string) {
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: Date.now(),
      type: 'text',
    }
    addMessage(userMsg)

    isLoading.value = true
    try {
      const res = await api.post('/chat', { message: content })
      const data = res.data
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.reply,
        timestamp: Date.now(),
        type: data.type ?? 'text',
        metadata: data.metadata,
      })
    } catch {
      addSystemMessage('消息发送失败，请检查后端是否启动。')
    } finally {
      isLoading.value = false
    }
  }

  return { messages, isLoading, sendMessage, addMessage, addSystemMessage }
})
