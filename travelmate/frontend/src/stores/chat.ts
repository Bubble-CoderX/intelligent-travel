import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Message } from '@/types/chat'
import api from '@/api/client'
import { getDeviceId } from '@/utils/device'

interface Session {
  session_id: string
  title: string
  message_count: number
  last_message: string
  created_at: string
  updated_at: string
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<Message[]>([])
  const isLoading = ref(false)
  const sessionId = ref<string>('default')
  const sessions = ref<Session[]>([])

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

  function addProactiveMessage(content: string, msgType: string = 'proactive') {
    addMessage({
      id: crypto.randomUUID(),
      role: 'assistant',
      content,
      timestamp: Date.now(),
      type: 'proactive',
      metadata: { proactive_type: msgType },
    })
  }

  async function loadSessions() {
    try {
      const res = await api.get('/sessions', { params: { device_id: getDeviceId() } })
      sessions.value = res.data.sessions ?? []
    } catch {
      // 静默失败
    }
  }

  async function createSession(title?: string): Promise<string> {
    const res = await api.post('/sessions', {
      device_id: getDeviceId(),
      title: title ?? '新会话',
    })
    const newId = res.data.session_id as string
    sessionId.value = newId
    messages.value = []
    await loadSessions()
    return newId
  }

  async function switchSession(id: string) {
    if (id === sessionId.value) return
    sessionId.value = id
    isLoading.value = true
    try {
      const res = await api.get(`/sessions/${id}/messages`, {
        params: { device_id: getDeviceId() },
      })
      const raw = res.data.messages ?? []
      messages.value = raw.map((m: any) => ({
        id: crypto.randomUUID(),
        role: m.role,
        content: m.content,
        timestamp: new Date(m.created_at).getTime(),
        type: 'text',
      }))
    } catch {
      messages.value = []
      addSystemMessage('加载会话消息失败')
    } finally {
      isLoading.value = false
    }
  }

  async function deleteSession(id: string) {
    try {
      await api.delete(`/sessions/${id}`, { params: { device_id: getDeviceId() } })
      sessions.value = sessions.value.filter(s => s.session_id !== id)
      // 如果删除的是当前会话，切到第一个或新建
      if (id === sessionId.value) {
        if (sessions.value.length > 0) {
          await switchSession(sessions.value[0].session_id)
        } else {
          await createSession()
        }
      }
    } catch {
      // 静默失败
    }
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
      const res = await api.post('/chat', {
        message: content,
        device_id: getDeviceId(),
        session_id: sessionId.value,
      })
      const data = res.data
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.reply,
        timestamp: Date.now(),
        type: data.message_type ?? 'text',
        metadata: data.metadata,
      })
      // 静默刷新会话列表（标题可能已更新）
      loadSessions()
    } catch {
      addSystemMessage('消息发送失败，请检查后端是否启动。')
    } finally {
      isLoading.value = false
    }
  }

  return {
    messages,
    isLoading,
    sessionId,
    sessions,
    sendMessage,
    addMessage,
    addSystemMessage,
    addProactiveMessage,
    loadSessions,
    createSession,
    switchSession,
    deleteSession,
  }
})
